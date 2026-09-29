"""Adapters for a user-local comic-text-detector checkout and Manga OCR model."""

from __future__ import annotations

import base64
import sys
from functools import lru_cache
from io import BytesIO
from os import environ
from pathlib import Path
from typing import Any

from app.models import OcrDebug, OcrDebugDetection, OcrResponse, Point, TextRegion

SMALL_SELECTION_MAX_SIDE = 320
# Only skip crops that are almost flat; this is not an OCR confidence estimate.
MIN_CROP_LUMINANCE_RANGE = 12


def _configured_paths() -> tuple[Path, Path, Path]:
    repo = Path(environ["YOMIMADO_DETECTOR_REPO"]).expanduser()
    detector_model = Path(environ.get("YOMIMADO_DETECTOR_MODEL", "")).expanduser()
    recognizer_model = Path(environ.get("YOMIMADO_MANGA_OCR_MODEL", "")).expanduser()
    if not (repo / "inference.py").is_file():
        raise FileNotFoundError(f"comic-text-detector checkout not found: {repo}")
    if not detector_model.is_file():
        raise FileNotFoundError("Set YOMIMADO_DETECTOR_MODEL to a local detector model file")
    if not recognizer_model.is_dir():
        raise FileNotFoundError("Set YOMIMADO_MANGA_OCR_MODEL to a local model directory")
    return repo, detector_model, recognizer_model


@lru_cache(maxsize=1)
def _models(repo: Path, detector_model: Path, recognizer_model: Path) -> tuple[Any, Any]:
    # The detector is a source checkout rather than a distributable Python
    # package. Keep its imports confined to this adapter.
    sys.path.insert(0, str(repo))
    from inference import TextDetector  # type: ignore[import-not-found]
    from manga_ocr import MangaOcr  # type: ignore[import-not-found]

    detector = TextDetector(model_path=str(detector_model), input_size=1024, device="cpu")
    recognizer = MangaOcr(pretrained_model_name_or_path=str(recognizer_model), force_cpu=True)
    return detector, recognizer


def _polygon(block: Any) -> list[Point]:
    if block.lines:
        corners = block.min_rect()[0]
        return [Point(x=float(x), y=float(y)) for x, y in corners]
    x1, y1, x2, y2 = block.xyxy
    return [
        Point(x=x1, y=y1),
        Point(x=x2, y=y1),
        Point(x=x2, y=y2),
        Point(x=x1, y=y2),
    ]


def _box_polygon(bounds: Any) -> list[Point]:
    x1, y1, x2, y2 = [float(value) for value in bounds]
    return [
        Point(x=x1, y=y1),
        Point(x=x2, y=y1),
        Point(x=x2, y=y2),
        Point(x=x1, y=y2),
    ]


def _should_retry_selection(width: int, height: int, regions: list[TextRegion]) -> bool:
    return (
        width <= SMALL_SELECTION_MAX_SIDE
        and height <= SMALL_SELECTION_MAX_SIDE
        and len(regions) <= 1
    )


def _has_visible_ink(image: Any) -> bool:
    dark_pixels = sum(image.convert("L").histogram()[:180])
    return dark_pixels >= max(20, image.width * image.height // 200)


def _is_japanese_script_character(character: str) -> bool:
    return (
        ("\u3040" <= character <= "\u30ff" and character not in {"ー", "・"})
        or "\u3400" <= character <= "\u9fff"
        or "\uf900" <= character <= "\ufaff"
        or "\uff66" <= character <= "\uff9f"
        or "\U00020000" <= character <= "\U0002fa1f"
        or character == "々"
    )


def _has_plausible_japanese_text(text: str) -> bool:
    return sum(_is_japanese_script_character(character) for character in text) >= 3


def _has_japanese_script(text: str) -> bool:
    return any(_is_japanese_script_character(character) for character in text)


def _crop_filter_reason(crop: Any) -> str | None:
    low, high = crop.convert("L").getextrema()
    if high - low < MIN_CROP_LUMINANCE_RANGE:
        return "Almost no visible contrast in the detector crop"
    return None


def _text_filter_reason(text: str) -> str | None:
    if text and not _has_japanese_script(text):
        return "No Japanese characters in the recognized text"
    return None


def _selection_adds_text(selection_text: str, detected_text: str) -> bool:
    full = "".join(selection_text.split())
    partial = "".join(detected_text.split())
    return bool(partial) and partial in full and len(full) >= len(partial) + 2


def _apply_selection_fallback(
    regions: list[TextRegion], width: int, height: int, selection_text: str
) -> tuple[list[TextRegion], bool]:
    if not _should_retry_selection(width, height, regions):
        return regions, False
    if regions and not _selection_adds_text(selection_text, regions[0].text):
        return regions, False
    if not regions and not _has_plausible_japanese_text(selection_text):
        return regions, False
    # The whole selection may contain text outside the detector box. Keep its
    # geometry honest: this covers the selected crop, not a precise text polygon.
    fallback = TextRegion(
        id="region-1",
        text=selection_text,
        polygon=_box_polygon((0, 0, width, height)),
        orientation=regions[0].orientation
        if regions
        else ("vertical" if height > width else "horizontal"),
        confidence=0,
        type=regions[0].type if regions else "other",
        tokens=[],
        geometrySource="selection",
    )
    return [fallback], True


def _crop_data_url(crop: Any) -> str:
    output = BytesIO()
    crop.save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


def recognize_with_models(image_bytes: bytes, *, debug: bool = False) -> OcrResponse:
    try:
        import cv2  # type: ignore[import-not-found]
        import numpy as np  # type: ignore[import-not-found]
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError as error:
        raise ImportError("Install the detector requirements and yomimado-ocr[ocr]") from error

    repo, detector_path, recognizer_path = _configured_paths()
    detector, recognizer = _models(repo, detector_path, recognizer_path)

    with Image.open(BytesIO(image_bytes)) as source:
        image = source.convert("RGB")
    bgr = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    _, _, blocks = detector(bgr)
    regions: list[TextRegion] = []
    detections: list[OcrDebugDetection] = []
    filtered_detection = False
    for index, block in enumerate(blocks, start=1):
        x1, y1, x2, y2 = [int(value) for value in block.xyxy]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(image.width, x2), min(image.height, y2)
        if x2 <= x1 or y2 <= y1:
            if debug:
                detections.append(
                    OcrDebugDetection(
                        id=f"detection-{index}",
                        box=_box_polygon(block.xyxy),
                        text="",
                        status="invalid",
                    )
                )
            continue
        crop = image.crop((x1, y1, x2, y2))
        filter_reason = _crop_filter_reason(crop)
        text = "" if filter_reason else recognizer(crop).strip()
        if not filter_reason:
            filter_reason = _text_filter_reason(text)
        if filter_reason:
            filtered_detection = True
        if debug:
            detections.append(
                OcrDebugDetection(
                    id=f"detection-{index}",
                    box=_box_polygon(block.xyxy),
                    cropDataUrl=_crop_data_url(crop),
                    text=text,
                    status="filtered" if filter_reason else "recognized" if text else "empty",
                    filterReason=filter_reason,
                )
            )
        if not text or filter_reason:
            continue
        regions.append(
            TextRegion(
                id=f"region-{len(regions) + 1}",
                text=text,
                polygon=_polygon(block),
                orientation="vertical" if block.vertical else "horizontal",
                # Manga OCR does not expose a calibrated confidence score.
                confidence=0,
                type="other",
                tokens=[],
            )
        )

    selection_text: str | None = None
    fallback_used = False
    retry_selection = (
        (bool(regions) or not filtered_detection)
        and _should_retry_selection(image.width, image.height, regions)
        and (bool(regions) or _has_visible_ink(image))
    )
    if retry_selection:
        selection_text = recognizer(image).strip()
        regions, fallback_used = _apply_selection_fallback(
            regions, image.width, image.height, selection_text
        )

    return OcrResponse(
        regions=regions,
        engine="manga",
        debug=(
            OcrDebug(
                detections=detections,
                selectionText=selection_text,
                selectionFallbackUsed=fallback_used,
            )
            if debug
            else None
        ),
    )
