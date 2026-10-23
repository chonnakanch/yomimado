"""Adapters for a user-local comic-text-detector checkout and Manga OCR model."""

from __future__ import annotations

import base64
import logging
import sys
from functools import lru_cache
from io import BytesIO
from os import environ
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

from app.models import OcrDebug, OcrDebugDetection, OcrResponse, Point, TextRegion
from app.pipeline.geometry import (
    clip_polygon,
    extend_to_visible_ink,
    horizontal_text_lines,
    ink_covered_by_rows,
)
from app.security import validate_capture_dimensions

SMALL_SELECTION_MAX_SIDE = 320
DETECTOR_INPUT_SIZE = 1024
RETRY_MIN_LONG_SIDE = 800
RETRY_TILE_SIDES = (512, 768)
RETRY_TILE_OVERLAP = 128
MAX_RETRY_TILES = 8
# Only strong segmentation activations qualify for the short-text fallback.
# This is not a calibrated OCR confidence score.
MASK_TEXT_THRESHOLD = 150
MAX_MASK_CANDIDATES_PER_TILE = 20
MAX_SHORT_VERTICAL_RETRIES = 6
MAX_HORIZONTAL_LINE_CROPS = 32
# Only skip crops that are almost flat; this is not an OCR confidence estimate.
MIN_CROP_LUMINANCE_RANGE = 12
MASK_REVIEW_REASON = "Short Japanese-looking text found only in the detector mask; verify on page"
EXPANDED_REVIEW_REASON = (
    "Short vertical text recovered from an expanded crop; area approximate—verify on page"
)
INK_REVIEW_REASON = "Detector boundary extended around visible strokes; verify on page"
LINE_REVIEW_REASON = (
    "Horizontal text localized from visible glyph rows; area approximate—verify on page"
)
CLIPPED_REVIEW_REASON = "Detector polygon clipped to the captured image; verify on page"
OVERLAP_REVIEW_REASON = "Overlapping detector regions need review on the page"
LANGUAGE_REVIEW_REASON = (
    "Detector classified this crop as non-Japanese; Japanese OCR may be unreliable"
)
SELECTION_REVIEW_REASON = "Text recovered from the whole selection; area approximate—verify on page"
logger = logging.getLogger(__name__)


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
    from manga_ocr import ocr as manga

    from app.pipeline.ocr_tokenizer import load_ocr_tokenizer

    detector = TextDetector(
        model_path=str(detector_model), input_size=DETECTOR_INPUT_SIZE, device="cpu"
    )
    # Manga OCR constructs a tokenizer internally. Restrict this override to its
    # constructor; translation and Transformers' global loader stay untouched.
    original = manga.AutoTokenizer
    manga.AutoTokenizer = SimpleNamespace(from_pretrained=load_ocr_tokenizer)
    try:
        recognizer = MangaOcr(pretrained_model_name_or_path=str(recognizer_model), force_cpu=True)
    finally:
        manga.AutoTokenizer = original
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


def _tile_starts(length: int, tile_side: int) -> list[int]:
    if length <= tile_side:
        return [0]
    final_start = length - tile_side
    starts = list(range(0, final_start + 1, tile_side - RETRY_TILE_OVERLAP))
    if starts[-1] != final_start:
        starts.append(final_start)
    return starts


def _retry_tiles(width: int, height: int) -> list[tuple[int, int, int, int]]:
    if max(width, height) < RETRY_MIN_LONG_SIDE:
        return []
    for tile_side in RETRY_TILE_SIDES:
        xs, ys = _tile_starts(width, tile_side), _tile_starts(height, tile_side)
        if 1 < len(xs) * len(ys) <= MAX_RETRY_TILES:
            tile_width, tile_height = min(width, tile_side), min(height, tile_side)
            return [(x, y, tile_width, tile_height) for y in ys for x in xs]
    return []


def _is_uniform_image(image: Any) -> bool:
    # Images are RGB here. Check every channel: equal luminance does not mean
    # equal pixels. Any variation, even one channel by one level, keeps OCR.
    return all(low == high for low, high in image.getextrema())


def _content_retry_tiles(image: Any) -> list[tuple[int, int, int, int]]:
    tiles = []
    for x, y, width, height in _retry_tiles(image.width, image.height):
        if not _is_uniform_image(image.crop((x, y, x + width, y + height))):
            tiles.append((x, y, width, height))
    return tiles


def _mask_candidate_boxes(mask: Any, cv2: Any) -> list[tuple[int, int, int, int]]:
    if mask is None:
        return []
    _, binary = cv2.threshold(mask, MASK_TEXT_THRESHOLD, 255, cv2.THRESH_BINARY)
    _, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    glyphs = sorted(
        (
            (int(x), int(y), int(width), int(height))
            for x, y, width, height, area in stats[1:]
            if area >= 20
            and 6 <= width <= 64
            and 6 <= height <= 64
            and 0.3 <= width / height <= 2.5
        ),
        key=lambda glyph: (glyph[1], glyph[0]),
    )
    successors: dict[int, int] = {}
    used_successors: set[int] = set()
    for index, (x, y, width, height) in enumerate(glyphs):
        center_x = x + width / 2
        options = []
        for next_index in range(index + 1, len(glyphs)):
            next_x, next_y, next_width, next_height = glyphs[next_index]
            gap = next_y - (y + height)
            if gap > height:
                break
            if (
                next_index in used_successors
                or gap < -height / 4
                # Small kana in vertical manga text can be much smaller than
                # the characters on either side. Keep the center alignment
                # requirement, but allow that size change in both directions.
                or not 0.35 <= next_height / height <= 2.9
                or not 0.35 <= next_width / width <= 2.9
                or abs(next_x + next_width / 2 - center_x) > max(width, next_width) * 0.45
            ):
                continue
            options.append((max(0, gap), abs(next_x + next_width / 2 - center_x), next_index))
        if options:
            next_index = min(options)[2]
            successors[index] = next_index
            used_successors.add(next_index)

    boxes = []
    for index in range(len(glyphs)):
        if index in used_successors or index not in successors:
            continue
        chain = [index]
        while chain[-1] in successors:
            chain.append(successors[chain[-1]])
        left = min(glyphs[item][0] for item in chain)
        top = min(glyphs[item][1] for item in chain)
        right = max(glyphs[item][0] + glyphs[item][2] for item in chain)
        bottom = max(glyphs[item][1] + glyphs[item][3] for item in chain)
        boxes.append(
            (
                max(0, left - 3),
                max(0, top - 3),
                min(mask.shape[1], right + 3),
                min(mask.shape[0], bottom + 3),
            )
        )
    return boxes[:MAX_MASK_CANDIDATES_PER_TILE]


def _detected_blocks(
    detector: Any, bgr: Any, retry_tiles: list[tuple[int, int, int, int]], cv2: Any
):
    _, _, blocks = detector(bgr)
    for block in blocks:
        yield block, 0, 0, "full"

    mask_candidates = []
    for x, y, tile_width, tile_height in retry_tiles:
        tile = bgr[y : y + tile_height, x : x + tile_width].copy()
        try:
            tile_mask, _, tile_blocks = detector(tile)
        except Exception as error:  # noqa: BLE001 - optional retry must not discard the full pass
            logger.warning("Tile detector retry failed: %s", type(error).__name__)
            continue
        for block in tile_blocks:
            yield block, x, y, "tile"
        try:
            for box in _mask_candidate_boxes(tile_mask, cv2):
                mask_candidates.append((box, x, y))
        except Exception as error:  # noqa: BLE001 - optional mask retry must not discard tile boxes
            logger.warning("Text-mask retry failed: %s", type(error).__name__)
    # Masks can contain short glyph runs that the detector's box-grouping stage
    # omits. Process these after regular boxes so duplicate candidates disappear.
    for box, x, y in mask_candidates:
        yield SimpleNamespace(xyxy=box, lines=[], vertical=True), x, y, "mask"


def _refine_horizontal_blocks(
    candidates: list[tuple[Any, int, int, str]], bgr: Any, cv2: Any, np: Any
) -> list[tuple[Any, int, int, str, tuple[int, int]]]:
    height, width = bgr.shape[:2]
    bounds = [
        tuple(int(v + (x if i % 2 == 0 else y)) for i, v in enumerate(block.xyxy))
        for block, x, y, _ in candidates
    ]
    full = [
        i
        for i, (_, _, _, stage) in enumerate(candidates)
        if stage == "full" and bounds[i][2] > bounds[i][0] and bounds[i][3] > bounds[i][1]
    ]
    horizontal = [
        i
        for i in full
        if not candidates[i][0].vertical and abs(getattr(candidates[i][0], "angle", 0)) <= 5
    ]

    # Join touching horizontal detector fragments before applying column guards.
    # Similar row height/alignment and a sub-glyph gap distinguish these from
    # separately bounded columns. A tiny partial glyph gets a little more room.
    groups: list[list[int]] = []
    remaining = set(horizontal)
    while remaining:
        group = [min(remaining)]
        remaining.remove(group[0])
        for i in group:
            l, t, r, b = bounds[i]
            h = b - t
            glyph_i = float(getattr(candidates[i][0], "font_size", 0))
            for j in sorted(remaining):
                ll, tt, rr, bb = bounds[j]
                hh = bb - tt
                glyph_j = float(getattr(candidates[j][0], "font_size", 0))
                language_i = getattr(candidates[i][0], "language", "unknown")
                language_j = getattr(candidates[j][0], "language", "unknown")
                gap = max(l - rr, ll - r, 0)
                narrow = min(r - l, rr - ll) < min(h, hh)
                if (
                    0 < h <= glyph_i * 1.5
                    and 0 < hh <= glyph_j * 1.5
                    and min(h, hh) >= max(h, hh) * 0.6
                    and min(b, bb) - max(t, tt) >= min(h, hh) * 0.7
                    and gap <= min(h, hh) * (0.5 if narrow else 0.25)
                    and (language_i == "eng") == (language_j == "eng")
                ):
                    group.append(j)
                    remaining.remove(j)
        groups.append(group)

    def enclosing(indices: list[int]) -> tuple[int, int, int, int]:
        boxes = [bounds[i] for i in indices]
        return (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )

    proposals = {}
    for group in groups:
        raw_box = enclosing(group)
        l, t, r, b = raw_box
        glyph = max(float(getattr(candidates[i][0], "font_size", 0)) for i in group)
        # Only dispute a nearby tall fragment when complete, wide glyph rows
        # also explain its pixels. A genuine adjacent vertical column contributes
        # narrow rows and therefore keeps its detector interpretation and barrier.
        disputed = []
        for i in full:
            if not candidates[i][0].vertical:
                continue
            ll, tt, rr, bb = bounds[i]
            if (
                glyph > 0
                and rr - ll <= glyph * 1.75
                and bb - tt >= (b - t) * 1.4
                and max(l - rr, ll - r, 0) <= glyph * 0.65
                and min(b, bb) - max(t, tt) >= min(b - t, bb - tt) * 0.5
            ):
                disputed.append(i)
        members = group + disputed
        search = enclosing(members)
        clipped = (
            max(0, search[0]),
            max(0, search[1]),
            min(width, search[2]),
            min(height, search[3]),
        )
        barriers = [bounds[i] for i in full if i not in members]
        lines = horizontal_text_lines(bgr, clipped, glyph, barriers, cv2, np)
        if disputed and (len(lines) < 2 or any(r - l < (b - t) * 1.4 for l, t, r, b in lines)):
            # Keep the original column guards when horizontal evidence is weak.
            search = raw_box
            clipped = (max(0, l), max(0, t), min(width, r), min(height, b))
            lines = horizontal_text_lines(
                bgr, clipped, glyph, [bounds[i] for i in full if i not in group], cv2, np
            )
        if lines:
            proposals[min(group)] = (search, lines)
    prepared = []
    line_crops = 0
    for source_order, (block, x, y, stage) in enumerate(candidates):
        lines = []
        raw_box = bounds[source_order]
        recovery_box = raw_box
        if source_order in proposals:
            recovery_box, lines = proposals[source_order]
        if not lines or line_crops + len(lines) > MAX_HORIZONTAL_LINE_CROPS:
            prepared.append((block, x, y, stage, (source_order, 0)))
            continue
        line_crops += len(lines)
        for line_order, line in enumerate(lines):
            prepared.append(
                (
                    SimpleNamespace(
                        xyxy=line,
                        lines=[],
                        vertical=False,
                        font_size=line[3] - line[1],
                        original_box=raw_box,
                        recovery_box=recovery_box,
                        refined_line=True,
                        language=getattr(block, "language", "unknown"),
                    ),
                    0,
                    0,
                    stage,
                    (source_order, line_order),
                )
            )

    # Localized full-pass rows establish coverage before their competing raw
    # fragments. Tile/mask candidates retain their existing fallback priority.
    def priority(item):
        refined = getattr(item[0], "refined_line", False)
        bounds = item[0].recovery_box if refined else item[0].xyxy
        area = (bounds[2] - bounds[0]) * (bounds[3] - bounds[1]) if refined else 0
        return item[3] != "full", not refined, -area

    return sorted(prepared, key=priority)


def _overlap_over_smaller(
    box: tuple[int, int, int, int], other: tuple[int, int, int, int]
) -> float:
    x1 = max(box[0], other[0])
    y1 = max(box[1], other[1])
    x2 = min(box[2], other[2])
    y2 = min(box[3], other[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    box_area = (box[2] - box[0]) * (box[3] - box[1])
    other_area = (other[2] - other[0]) * (other[3] - other[1])
    return (x2 - x1) * (y2 - y1) / min(box_area, other_area)


def _mask_extends_vertical_box(
    mask_box: tuple[int, int, int, int], previous: tuple[int, int, int, int]
) -> bool:
    mask_width = mask_box[2] - mask_box[0]
    previous_width = previous[2] - previous[0]
    return (
        mask_box[3] - mask_box[1] >= (previous[3] - previous[1]) * 1.7
        and mask_width <= previous_width * 1.8
        and _overlap_over_smaller(mask_box, previous) >= 0.8
    )


def _expanded_short_vertical_box(
    box: tuple[int, int, int, int], width: int, height: int, character_count: int
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    box_width, box_height = x2 - x1, y2 - y1
    side_padding = max(3, box_width // 3)
    top_padding = box_height * (2 if character_count == 1 else 0.6)
    return (
        max(0, x1 - side_padding),
        max(0, round(y1 - top_padding)),
        min(width, x2 + side_padding),
        min(height, y2 + round(box_height * 0.2)),
    )


def _expanded_text_adds_short_word(original: str, expanded: str) -> bool:
    original_count = _japanese_character_count(original)
    expanded_count = _japanese_character_count(expanded)
    if not (original_count in (1, 2) and original_count < expanded_count <= 4):
        return False
    if len(expanded) > 6 or any(character.isspace() for character in expanded):
        return False
    return original in expanded or (original_count == 1 and expanded_count == 3)


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
    return _japanese_character_count(text) >= 3


def _japanese_character_count(text: str) -> int:
    return sum(_is_japanese_script_character(character) for character in text)


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
    if not partial or partial not in full:
        return False
    if len(full) >= len(partial) + 2:
        return True
    # A crop may omit just one kana (学校へ -> 学校). Require two existing
    # Japanese characters and one additional script character; punctuation or
    # a changed reading is not evidence for this smaller recovery.
    return (
        len(full) == len(partial) + 1
        and _japanese_character_count(partial) >= 2
        and _japanese_character_count(full) == _japanese_character_count(partial) + 1
    )


def _selection_orientation(
    width: int, height: int, regions: list[TextRegion]
) -> Literal["vertical", "horizontal"]:
    if not regions:
        return "vertical" if height > width else "horizontal"
    region = regions[0]
    xs = [point.x for point in region.polygon]
    ys = [point.y for point in region.polygon]
    # A short vertical run can be mislabeled horizontal. Require both the
    # selected area and the detected ink bounds to agree, rather than using
    # capture aspect alone (which can include arbitrary surrounding whitespace).
    if (
        height >= width * 1.5
        and max(ys) - min(ys) >= (max(xs) - min(xs)) * 1.5
        and 1 <= _japanese_character_count(region.text) <= 3
    ):
        return "vertical"
    return region.orientation


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
        orientation=_selection_orientation(width, height, regions),
        confidence=0,
        type=regions[0].type if regions else "other",
        tokens=[],
        geometrySource="selection",
        needsReview=True,
        reviewReason=(
            f"{regions[0].reviewReason}; {SELECTION_REVIEW_REASON}"
            if regions and regions[0].reviewReason
            else SELECTION_REVIEW_REASON
        ),
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

    with Image.open(BytesIO(image_bytes), formats=["PNG"]) as source:
        validate_capture_dimensions(*source.size)
        image = source.convert("RGB")
    repo, detector_path, recognizer_path = _configured_paths()
    if _is_uniform_image(image):
        return OcrResponse(
            regions=[], engine="manga", debug=OcrDebug(detections=[]) if debug else None
        )
    detector, recognizer = _models(repo, detector_path, recognizer_path)
    bgr = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    retry_tiles = _content_retry_tiles(image)
    recognized_crops: dict[tuple[int, int, int, int], str] = {}

    def recognize_crop(box: tuple[int, int, int, int], crop: Any) -> str:
        # Only exact image-space bounds share a result, and only in this request.
        # Failed recognition is not cached: optional recovery can still retry.
        if box not in recognized_crops:
            recognized_crops[box] = recognizer(crop).strip()
        return recognized_crops[box]

    regions: list[TextRegion] = []
    region_boxes: list[tuple[int, int, int, int]] = []
    region_debug_indices: list[int | None] = []
    region_orders: list[tuple[int, int]] = []
    detections: list[OcrDebugDetection] = []
    seen_boxes: list[tuple[int, int, int, int]] = []
    refined_boxes: list[tuple[int, int, int, int]] = []
    filtered_detection = False
    index = 0
    candidates = list(_detected_blocks(detector, bgr, retry_tiles, cv2))
    for block, offset_x, offset_y, detection_pass, source_order in _refine_horizontal_blocks(
        candidates, bgr, cv2, np
    ):
        raw_x1, raw_y1, raw_x2, raw_y2 = [int(value) for value in block.xyxy]
        x1, y1 = raw_x1 + offset_x, raw_y1 + offset_y
        x2, y2 = raw_x2 + offset_x, raw_y2 + offset_y
        raw_box = getattr(block, "original_box", (x1, y1, x2, y2))
        refined_line = getattr(block, "refined_line", False)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(image.width, x2), min(image.height, y2)
        index += 1
        if x2 <= x1 or y2 <= y1:
            if debug:
                detections.append(
                    OcrDebugDetection(
                        id=f"detection-{index}",
                        box=_box_polygon(raw_box),
                        text="",
                        status="invalid",
                        decisionReason="Detector box lies outside the captured image",
                        detectionPass=detection_pass,
                    )
                )
            continue
        box = (x1, y1, x2, y2)
        if ink_covered_by_rows(bgr, box, refined_boxes, cv2, np):
            if debug:
                detections.append(
                    OcrDebugDetection(
                        id=f"detection-{index}",
                        box=_box_polygon(raw_box),
                        text="",
                        status="filtered",
                        filterReason="Covered by a localized horizontal text row",
                        decisionReason="Covered by a localized horizontal text row",
                        detectionPass=detection_pass,
                    )
                )
            continue
        if detection_pass != "full":
            overlapping = [
                previous for previous in seen_boxes if _overlap_over_smaller(box, previous) >= 0.6
            ]
            if overlapping and (
                detection_pass != "mask"
                or not all(_mask_extends_vertical_box(box, previous) for previous in overlapping)
                or any(
                    _overlap_over_smaller(box, previous_box) >= 0.6
                    and _japanese_character_count(region.text) != 1
                    for region, previous_box in zip(regions, region_boxes)
                )
            ):
                index -= 1
                continue
        # Successful localized rows suppress fragments through ink coverage
        # above. Area overlap must not discard their uncovered tile/mask text,
        # and failed row recognition must leave those fallback crops available.
        if not refined_line:
            seen_boxes.append(box)
        polygon = [Point(x=point.x + offset_x, y=point.y + offset_y) for point in _polygon(block)]
        geometry_adjusted = refined_line
        if detection_pass != "mask" and not refined_line:
            box, polygon, geometry_adjusted = extend_to_visible_ink(
                bgr,
                box,
                polygon,
                float(getattr(block, "font_size", 0)),
                bool(block.vertical),
                cv2,
                np,
            )
        polygon, geometry_clipped = clip_polygon(polygon, image.width, image.height)
        if not polygon:
            if debug:
                detections.append(
                    OcrDebugDetection(
                        id=f"detection-{index}",
                        box=_box_polygon(raw_box),
                        text="",
                        status="invalid",
                        decisionReason="Detector polygon has no area inside the captured image",
                        detectionPass=detection_pass,
                    )
                )
            continue
        crop = image.crop(box)
        non_japanese = getattr(block, "language", "unknown") == "eng"
        filter_reason = _crop_filter_reason(crop)
        text = "" if filter_reason else recognize_crop(box, crop)
        if not filter_reason:
            filter_reason = _text_filter_reason(text)
        if (
            detection_pass == "mask"
            and not filter_reason
            and not 2 <= _japanese_character_count(text) <= 3
        ):
            filter_reason = "Mask candidate needs two or three Japanese characters"
        if filter_reason:
            filtered_detection = True
        if filter_reason:
            decision_reason = filter_reason
        elif not text:
            decision_reason = "Manga OCR returned no text"
        elif detection_pass == "mask":
            decision_reason = MASK_REVIEW_REASON
        elif refined_line:
            decision_reason = LINE_REVIEW_REASON
        elif geometry_adjusted:
            decision_reason = INK_REVIEW_REASON
        elif geometry_clipped:
            decision_reason = CLIPPED_REVIEW_REASON
        else:
            decision_reason = "Japanese script recognized inside a detector box"
        if non_japanese and not filter_reason:
            decision_reason += "; " + LANGUAGE_REVIEW_REASON
        if debug:
            detections.append(
                OcrDebugDetection(
                    id=f"detection-{index}",
                    box=_box_polygon(raw_box),
                    cropDataUrl=_crop_data_url(crop),
                    text=text,
                    status="filtered" if filter_reason else "recognized" if text else "empty",
                    filterReason=filter_reason,
                    decisionReason=decision_reason,
                    detectionPass=detection_pass,
                )
            )
        if not text or filter_reason:
            continue
        if detection_pass == "mask":
            for previous_index in reversed(range(len(regions))):
                if (
                    regions[previous_index].orientation == "vertical"
                    and _japanese_character_count(regions[previous_index].text) == 1
                    and _mask_extends_vertical_box(box, region_boxes[previous_index])
                ):
                    debug_index = region_debug_indices.pop(previous_index)
                    if debug_index is not None:
                        previous_detection = detections[debug_index]
                        previous_detection.status = "filtered"
                        previous_detection.filterReason = (
                            "Superseded by longer aligned text-mask recognition"
                        )
                        previous_detection.decisionReason = previous_detection.filterReason
                    del regions[previous_index]
                    del region_boxes[previous_index]
                    del region_orders[previous_index]
        regions.append(
            TextRegion(
                id=f"region-{len(regions) + 1}",
                text=text,
                polygon=polygon,
                orientation="vertical" if block.vertical else "horizontal",
                # Manga OCR does not expose a calibrated confidence score.
                confidence=0,
                type="other",
                tokens=[],
                geometrySource="expandedCrop" if geometry_adjusted else None,
                needsReview=detection_pass == "mask"
                or geometry_adjusted
                or geometry_clipped
                or non_japanese,
                reviewReason=MASK_REVIEW_REASON
                if detection_pass == "mask"
                else LINE_REVIEW_REASON
                if refined_line
                else INK_REVIEW_REASON
                if geometry_adjusted
                else CLIPPED_REVIEW_REASON
                if geometry_clipped
                else None,
            )
        )
        if non_japanese:
            region = regions[-1]
            region.reviewReason = (
                region.reviewReason + "; " + LANGUAGE_REVIEW_REASON
                if region.reviewReason
                else LANGUAGE_REVIEW_REASON
            )
        region_boxes.append(box)
        region_debug_indices.append(len(detections) - 1 if debug else None)
        region_orders.append(source_order)
        if refined_line:
            refined_boxes.append(box)

    short_retries = 0
    if max(image.width, image.height) >= RETRY_MIN_LONG_SIDE:
        for region_index, region in enumerate(regions):
            character_count = _japanese_character_count(region.text)
            box = region_boxes[region_index]
            tall_short_box = (box[3] - box[1]) >= (box[2] - box[0]) * 1.5
            if (
                short_retries >= MAX_SHORT_VERTICAL_RETRIES
                or (region.orientation != "vertical" and not tall_short_box)
                or region.reviewReason == MASK_REVIEW_REASON
                or character_count not in (1, 2)
            ):
                continue
            expanded_box = _expanded_short_vertical_box(
                region_boxes[region_index], image.width, image.height, character_count
            )
            if any(
                other_index != region_index
                and _overlap_over_smaller(expanded_box, other_box) >= 0.3
                for other_index, other_box in enumerate(region_boxes)
            ):
                continue
            short_retries += 1
            try:
                expanded_text = recognize_crop(expanded_box, image.crop(expanded_box))
            except Exception as error:  # noqa: BLE001 - optional retry must preserve the original
                logger.warning("Short vertical OCR retry failed: %s", type(error).__name__)
                continue
            if not _expanded_text_adds_short_word(region.text, expanded_text):
                continue
            region.text = expanded_text
            region.orientation = "vertical"
            region.polygon = _box_polygon(expanded_box)
            region.geometrySource = "expandedCrop"
            region.needsReview = True
            region.reviewReason = (
                f"{region.reviewReason}; {EXPANDED_REVIEW_REASON}"
                if region.reviewReason
                else EXPANDED_REVIEW_REASON
            )
            region_boxes[region_index] = expanded_box
            debug_index = region_debug_indices[region_index]
            if debug_index is not None:
                debug_detection = detections[debug_index]
                debug_detection.decisionReason = (
                    f"{debug_detection.decisionReason}; "
                    f"Expanded short vertical crop recognized {expanded_text}; area approximate"
                )

    ordered = sorted(zip(region_orders, regions, region_boxes), key=lambda item: item[0])
    regions = [item[1] for item in ordered]
    region_boxes = [item[2] for item in ordered]
    for i, region in enumerate(regions):
        if not region.needsReview and any(
            j != i and _overlap_over_smaller(region_boxes[i], other) >= 0.8
            for j, other in enumerate(region_boxes)
        ):
            region.needsReview = True
            region.reviewReason = OVERLAP_REVIEW_REASON

    for region_number, region in enumerate(regions, start=1):
        region.id = f"region-{region_number}"

    selection_text: str | None = None
    fallback_used = False
    retry_selection = (
        (bool(regions) or not filtered_detection)
        and _should_retry_selection(image.width, image.height, regions)
        and (bool(regions) or _has_visible_ink(image))
    )
    if retry_selection:
        selection_text = recognize_crop((0, 0, image.width, image.height), image)
        regions, fallback_used = _apply_selection_fallback(
            regions, image.width, image.height, selection_text
        )

    return OcrResponse(
        regions=regions,
        engine="manga",
        debug=(
            OcrDebug(
                detections=detections,
                tileRetryCount=len(retry_tiles),
                maskRetryCount=len(retry_tiles),
                selectionText=selection_text,
                selectionFallbackUsed=fallback_used,
            )
            if debug
            else None
        ),
    )
