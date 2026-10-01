import importlib
from io import BytesIO
from pathlib import Path
from struct import pack
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import OcrDebug, OcrDebugDetection, OcrResponse, Point, TextRegion
from app.pipeline.real_ocr import (
    _apply_selection_fallback,
    _crop_filter_reason,
    _polygon,
    _text_filter_reason,
)

client = TestClient(app)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + pack(">II", 200, 300)


def test_health_reports_demo_status() -> None:
    assert client.get("/health").json() == {"status": "ok", "ocr": "demo"}


def test_ocr_returns_geometry_first_response() -> None:
    response = client.post("/api/v1/ocr", files={"image": ("capture.png", PNG, "image/png")})
    assert response.status_code == 200
    data = response.json()
    assert "regions" in data
    assert data["engine"] == "demo"
    assert "debug" not in data
    assert len(data["regions"]) == 1
    region = data["regions"][0]
    assert region["id"] == "selection-boundary-demo"
    assert region["confidence"] == 0
    assert region["polygon"] == [
        {"x": 0, "y": 0},
        {"x": 200, "y": 0},
        {"x": 200, "y": 300},
        {"x": 0, "y": 300},
    ]


def test_ocr_rejects_non_images() -> None:
    response = client.post("/api/v1/ocr", files={"image": ("capture.txt", b"text", "text/plain")})
    assert response.status_code == 415


def test_ocr_rejects_invalid_png() -> None:
    response = client.post(
        "/api/v1/ocr", files={"image": ("capture.png", b"not a png", "image/png")}
    )
    assert response.status_code == 422


def test_detector_box_maps_to_image_polygon() -> None:
    block = SimpleNamespace(lines=[], xyxy=[10, 20, 30, 80])
    assert [(point.x, point.y) for point in _polygon(block)] == [
        (10, 20),
        (30, 20),
        (30, 80),
        (10, 80),
    ]


def test_text_filter_rejects_only_strings_without_japanese_script() -> None:
    assert _text_filter_reason("comipo Play") == "No Japanese characters in the recognized text"
    assert _text_filter_reason("2026!?ー・") == "No Japanese characters in the recognized text"
    assert _text_filter_reason("ＡＢＣ") == "No Japanese characters in the recognized text"
    for text in ("学校", "ゲーム", "こんにちは", "VRゲーム", "ｶﾀｶﾅ", "あ", "々"):
        assert _text_filter_reason(text) is None


def test_nearly_uniform_crop_is_filtered_without_using_a_confidence_guess() -> None:
    image_module = pytest.importorskip("PIL.Image")
    assert _crop_filter_reason(image_module.new("RGB", (40, 80), "white"))
    image = image_module.new("RGB", (40, 80), "white")
    for x in range(10, 30):
        for y in range(15, 65):
            image.putpixel((x, y), (10, 10, 10))
    assert _crop_filter_reason(image) is None


def test_small_selection_retry_preserves_honest_geometry() -> None:
    detected = TextRegion(
        id="region-1",
        text="たまには",
        polygon=[Point(x=92, y=57), Point(x=117, y=57), Point(x=117, y=135)],
        orientation="vertical",
        confidence=0,
        type="other",
        tokens=[],
    )
    regions, used = _apply_selection_fallback([detected], 186, 219, "たまにはいいでしょ")
    assert used
    assert regions[0].text == "たまにはいいでしょ"
    assert regions[0].geometrySource == "selection"
    assert [(point.x, point.y) for point in regions[0].polygon] == [
        (0, 0),
        (186, 0),
        (186, 219),
        (0, 219),
    ]

    unchanged, used = _apply_selection_fallback([detected], 974, 549, "たまにはいいでしょ")
    assert not used
    assert unchanged == [detected]

    unchanged, used = _apply_selection_fallback([detected], 186, 219, "別の文章")
    assert not used
    assert unchanged == [detected]

    unchanged, used = _apply_selection_fallback(
        [detected, detected], 186, 219, "たまにはいいでしょ"
    )
    assert not used
    assert unchanged == [detected, detected]


def test_small_selection_without_detector_box_can_use_whole_crop_text() -> None:
    regions, used = _apply_selection_fallback([], 109, 145, "たまにはいいでしょ")
    assert used
    assert len(regions) == 1
    assert regions[0].text == "たまにはいいでしょ"
    assert regions[0].orientation == "vertical"
    assert regions[0].geometrySource == "selection"
    assert [(point.x, point.y) for point in regions[0].polygon] == [
        (0, 0),
        (109, 0),
        (109, 145),
        (0, 145),
    ]

    unchanged, used = _apply_selection_fallback([], 109, 145, "hello")
    assert not used
    assert unchanged == []

    unchanged, used = _apply_selection_fallback([], 109, 145, "ーーー")
    assert not used
    assert unchanged == []


def test_debug_request_is_opt_in_and_returns_detector_details(monkeypatch) -> None:
    ocr_module = importlib.import_module("app.api.ocr")
    received_debug = []

    def fake_recognize(input_image):
        received_debug.append(input_image.debug)
        return OcrResponse(
            regions=[],
            engine="manga",
            debug=OcrDebug(
                detections=[
                    OcrDebugDetection(
                        id="detection-1",
                        box=[
                            Point(x=10, y=20),
                            Point(x=30, y=20),
                            Point(x=30, y=80),
                            Point(x=10, y=80),
                        ],
                        cropDataUrl="data:image/png;base64,dGVzdA==",
                        text="たまには",
                        status="recognized",
                    ),
                    OcrDebugDetection(
                        id="detection-2",
                        box=[
                            Point(x=40, y=20),
                            Point(x=90, y=20),
                            Point(x=90, y=80),
                            Point(x=40, y=80),
                        ],
                        text="comipo Play",
                        status="filtered",
                        filterReason="No Japanese characters in the recognized text",
                    ),
                ],
                selectionText="たまにはいいでしょ",
            ),
        )

    monkeypatch.setattr(ocr_module.pipeline, "recognize", fake_recognize)
    response = client.post(
        "/api/v1/ocr",
        data={"debug": "true"},
        files={"image": ("capture.png", PNG, "image/png")},
    )
    assert response.status_code == 200
    assert received_debug == [True]
    assert response.json()["debug"]["selectionText"] == "たまにはいいでしょ"
    assert response.json()["debug"]["detections"][0]["status"] == "recognized"
    assert response.json()["debug"]["detections"][0]["cropDataUrl"].startswith("data:image/png;")
    assert response.json()["debug"]["detections"][1]["filterReason"] == (
        "No Japanese characters in the recognized text"
    )


def test_model_adapter_reports_raw_boxes_and_crops(monkeypatch) -> None:
    image_module = pytest.importorskip("PIL.Image")
    image_draw = pytest.importorskip("PIL.ImageDraw")
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    from app.pipeline import real_ocr

    image = image_module.new("RGB", (120, 160), "white")
    image_draw.Draw(image).rectangle((15, 25, 35, 90), fill="black")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    blocks = [
        SimpleNamespace(lines=[], xyxy=[10, 20, 40, 100], vertical=True),
        SimpleNamespace(lines=[], xyxy=[130, 20, 150, 50], vertical=True),
    ]

    def detector(_image):
        return None, None, blocks

    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(real_ocr, "_models", lambda *_paths: (detector, lambda _crop: "学校"))

    result = real_ocr.recognize_with_models(image_bytes.getvalue(), debug=True)
    assert [item.status for item in result.debug.detections] == ["recognized", "invalid"]
    assert result.debug.detections[0].cropDataUrl.startswith("data:image/png;base64,")
    assert result.debug.detections[1].cropDataUrl is None
    assert result.debug.selectionFallbackUsed is False


def test_large_capture_tile_retry_recovers_missed_text_without_duplicate_boxes(monkeypatch) -> None:
    image_module = pytest.importorskip("PIL.Image")
    image_draw = pytest.importorskip("PIL.ImageDraw")
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    from app.pipeline import real_ocr

    image = image_module.new("RGB", (830, 1340), "white")
    draw = image_draw.Draw(image)
    draw.rectangle((105, 155, 140, 225), fill="black")
    draw.rectangle((305, 1035, 335, 1095), fill="black")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    first = SimpleNamespace(lines=[], xyxy=[100, 150, 145, 230], vertical=True)
    missed = SimpleNamespace(
        lines=[object()],
        xyxy=[300, 202, 340, 272],
        vertical=True,
        min_rect=lambda: ([(300, 202), (340, 202), (340, 272), (300, 272)], None),
    )
    shapes = []
    tiles = real_ocr._retry_tiles(830, 1340)

    def detector(crop):
        shapes.append(crop.shape[:2])
        if len(shapes) == 1:
            return None, None, [first]
        tile = tiles[len(shapes) - 2]
        if tile[:2] == (0, 0):
            return None, None, [first]
        if tile[:2] == (0, 828):
            return None, None, [missed]
        return None, None, []

    recognized = iter(["いぶき", "みて", "みて"])
    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(
        real_ocr, "_models", lambda *_paths: (detector, lambda _crop: next(recognized))
    )

    result = real_ocr.recognize_with_models(image_bytes.getvalue(), debug=True)
    assert shapes == [(1340, 830)] + [(512, 512)] * 8
    assert [region.text for region in result.regions] == ["いぶき", "みて"]
    assert all(not region.needsReview for region in result.regions)
    assert result.regions[1].polygon[0] == Point(x=300, y=1030)
    assert [item.detectionPass for item in result.debug.detections] == ["full", "tile"]
    assert [item.id for item in result.debug.detections] == ["detection-1", "detection-2"]
    assert result.debug.tileRetryCount == 8
    assert result.debug.maskRetryCount == 8


def test_text_mask_retry_finds_short_text_but_recognizes_original_pixels(monkeypatch) -> None:
    image_module = pytest.importorskip("PIL.Image")
    image_draw = pytest.importorskip("PIL.ImageDraw")
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    from app.pipeline import real_ocr

    image = image_module.new("RGB", (830, 623), (230, 230, 230))
    image_draw.Draw(image).rectangle((345, 180, 365, 226), fill=(180, 180, 180))
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    tiles = real_ocr._retry_tiles(830, 623)
    calls = []
    mask = np.zeros((512, 512), dtype=np.uint8)
    cv2.rectangle(mask, (27, 180), (46, 199), 200, -1)
    cv2.rectangle(mask, (27, 207), (46, 226), 200, -1)
    overlapping_mask = np.zeros((512, 512), dtype=np.uint8)
    cv2.rectangle(overlapping_mask, (27, 69), (46, 88), 200, -1)
    cv2.rectangle(overlapping_mask, (27, 96), (46, 115), 200, -1)

    def detector(crop):
        calls.append(crop.copy())
        if len(calls) == 3:
            return mask, None, []
        if len(calls) == 5:
            return overlapping_mask, None, []
        return None, None, []

    recognized_pixels = []

    def recognizer(crop):
        recognized_pixels.append(crop.getpixel((0, 0)))
        return "みて"

    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(real_ocr, "_models", lambda *_paths: (detector, recognizer))

    result = real_ocr.recognize_with_models(image_bytes.getvalue(), debug=True)
    assert len(calls) == 1 + len(tiles)
    assert result.debug.maskRetryCount == len(tiles)
    assert [item.detectionPass for item in result.debug.detections] == ["mask"]
    assert [region.text for region in result.regions] == ["みて"]
    assert result.regions[0].polygon[0] == Point(x=342, y=177)
    assert result.regions[0].needsReview is True
    assert "verify on page" in result.regions[0].reviewReason
    assert result.debug.detections[0].decisionReason == result.regions[0].reviewReason
    assert recognized_pixels == [(230, 230, 230)]

    calls.clear()
    monkeypatch.setattr(real_ocr, "_models", lambda *_paths: (detector, lambda _crop: "いっした"))
    rejected = real_ocr.recognize_with_models(image_bytes.getvalue(), debug=True)
    assert rejected.regions == []
    assert rejected.debug.detections[0].status == "filtered"
    assert rejected.debug.detections[0].filterReason == (
        "Mask candidate needs two or three Japanese characters"
    )
    assert rejected.debug.detections[0].decisionReason == rejected.debug.detections[0].filterReason


def test_text_mask_retry_requires_aligned_glyphs_and_produces_deduplicable_box() -> None:
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    from app.pipeline.real_ocr import _mask_candidate_boxes, _overlap_over_smaller

    mask = np.zeros((80, 80), dtype=np.uint8)
    cv2.rectangle(mask, (20, 10), (36, 26), 200, -1)
    assert _mask_candidate_boxes(mask, cv2) == []

    cv2.rectangle(mask, (21, 32), (37, 48), 200, -1)
    boxes = _mask_candidate_boxes(mask, cv2)
    assert boxes == [(17, 7, 41, 52)]
    assert _overlap_over_smaller(boxes[0], (18, 8, 40, 51)) >= 0.6


def test_text_mask_retry_groups_aligned_small_kana_between_full_size_glyphs() -> None:
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    from app.pipeline.real_ocr import _mask_candidate_boxes

    mask = np.zeros((90, 90), dtype=np.uint8)
    cv2.rectangle(mask, (20, 10), (37, 27), 200, -1)
    cv2.rectangle(mask, (25, 33), (32, 40), 200, -1)
    cv2.rectangle(mask, (20, 48), (37, 65), 200, -1)
    assert _mask_candidate_boxes(mask, cv2) == [(17, 7, 41, 69)]

    # A similarly sized mark beside the text must not be joined to the column.
    mask[:, :] = 0
    cv2.rectangle(mask, (20, 10), (37, 27), 200, -1)
    cv2.rectangle(mask, (50, 33), (57, 40), 200, -1)
    cv2.rectangle(mask, (20, 48), (37, 65), 200, -1)
    assert _mask_candidate_boxes(mask, cv2) == []


def test_expanded_short_text_requires_a_longer_plausible_reading() -> None:
    from app.pipeline.real_ocr import _expanded_text_adds_short_word

    assert _expanded_text_adds_short_word("っち", "こっち")
    assert _expanded_text_adds_short_word("あ", "こっち")
    assert not _expanded_text_adds_short_word("っち", "学校")
    assert not _expanded_text_adds_short_word("あ", "学校")
    assert not _expanded_text_adds_short_word("みて", "みて")


def test_longer_mask_result_replaces_partial_one_character_detector_box(monkeypatch) -> None:
    image_module = pytest.importorskip("PIL.Image")
    image_draw = pytest.importorskip("PIL.ImageDraw")
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    from app.pipeline import real_ocr

    image = image_module.new("RGB", (830, 623), "white")
    image_draw.Draw(image).rectangle((330, 190, 348, 207), fill="black")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    partial = SimpleNamespace(lines=[], xyxy=[328, 190, 350, 208], vertical=True)
    mask = np.zeros((512, 512), dtype=np.uint8)
    cv2.rectangle(mask, (12, 150), (29, 167), 200, -1)
    cv2.rectangle(mask, (17, 174), (24, 181), 200, -1)
    cv2.rectangle(mask, (12, 190), (29, 207), 200, -1)
    calls = 0

    def detector(_crop):
        nonlocal calls
        calls += 1
        if calls == 1:
            return None, None, [partial]
        if calls == 3:
            return mask, None, []
        return None, None, []

    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    recognized = iter(["あ", "こっち"])
    monkeypatch.setattr(
        real_ocr, "_models", lambda *_paths: (detector, lambda _crop: next(recognized))
    )
    result = real_ocr.recognize_with_models(image_bytes.getvalue(), debug=True)
    assert [region.text for region in result.regions] == ["こっち"]
    assert result.regions[0].needsReview is True
    assert result.regions[0].polygon[0] == Point(x=327, y=147)
    assert [item.status for item in result.debug.detections] == ["filtered", "recognized"]
    assert "Superseded" in result.debug.detections[0].filterReason

    # A complete detector result must not gain a duplicate mask region.
    calls = 0
    monkeypatch.setattr(real_ocr, "_models", lambda *_paths: (detector, lambda _crop: "こっち"))
    complete = real_ocr.recognize_with_models(image_bytes.getvalue(), debug=True)
    assert [region.text for region in complete.regions] == ["こっち"]
    assert [item.detectionPass for item in complete.debug.detections] == ["full"]

    # If the larger crop still reads as one character, retain the original.
    calls = 0
    monkeypatch.setattr(real_ocr, "_models", lambda *_paths: (detector, lambda _crop: "あ"))
    incomplete = real_ocr.recognize_with_models(image_bytes.getvalue(), debug=True)
    assert [region.text for region in incomplete.regions] == ["あ"]
    assert [item.status for item in incomplete.debug.detections] == ["recognized", "filtered"]


def test_tall_short_detector_box_recovers_longer_vertical_text_from_original_pixels(
    monkeypatch,
) -> None:
    image_module = pytest.importorskip("PIL.Image")
    image_draw = pytest.importorskip("PIL.ImageDraw")
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    from app.pipeline import real_ocr

    image = image_module.new("RGB", (830, 623), "white")
    image_draw.Draw(image).rectangle((330, 190, 348, 229), fill="black")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    partial = SimpleNamespace(lines=[], xyxy=[328, 190, 350, 230], vertical=False)
    crops = []
    recognized = iter(["あ", "こっち"])

    def recognizer(crop):
        crops.append(crop.size)
        return next(recognized)

    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(
        real_ocr,
        "_models",
        lambda *_paths: (
            lambda capture: (None, None, [partial] if capture.shape[:2] == (623, 830) else []),
            recognizer,
        ),
    )
    result = real_ocr.recognize_with_models(image_bytes.getvalue(), debug=True)
    assert crops == [(22, 40), (36, 128)]
    assert [(region.id, region.text) for region in result.regions] == [("region-1", "こっち")]
    assert result.regions[0].orientation == "vertical"
    assert result.regions[0].geometrySource == "expandedCrop"
    assert result.regions[0].needsReview is True
    assert result.regions[0].polygon[0] == Point(x=321, y=110)
    assert "area approximate" in result.debug.detections[0].decisionReason

    # An unrelated two-character retry is not enough to replace a one-character box.
    crops.clear()
    recognized = iter(["あ", "学校"])
    unchanged = real_ocr.recognize_with_models(image_bytes.getvalue())
    assert [region.text for region in unchanged.regions] == ["あ"]
    assert unchanged.regions[0].geometrySource is None


def test_short_vertical_retry_failure_keeps_original_detection(monkeypatch) -> None:
    image_module = pytest.importorskip("PIL.Image")
    image_draw = pytest.importorskip("PIL.ImageDraw")
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    from app.pipeline import real_ocr

    image = image_module.new("RGB", (830, 623), "white")
    image_draw.Draw(image).rectangle((330, 190, 348, 229), fill="black")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    partial = SimpleNamespace(lines=[], xyxy=[328, 190, 350, 230], vertical=True)
    calls = 0

    def recognizer(_crop):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("optional retry failed")
        return "ち"

    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(
        real_ocr,
        "_models",
        lambda *_paths: (
            lambda capture: (None, None, [partial] if capture.shape[:2] == (623, 830) else []),
            recognizer,
        ),
    )
    result = real_ocr.recognize_with_models(image_bytes.getvalue())
    assert calls == 2
    assert [region.text for region in result.regions] == ["ち"]
    assert result.regions[0].needsReview is False


def test_tile_retry_is_bounded_to_small_captures_and_at_most_eight_tiles() -> None:
    from app.pipeline.real_ocr import _retry_tiles

    assert _retry_tiles(640, 400) == []
    assert _retry_tiles(830, 623) == [
        (0, 0, 512, 512),
        (318, 0, 512, 512),
        (0, 111, 512, 512),
        (318, 111, 512, 512),
    ]
    assert len(_retry_tiles(830, 1340)) == 8
    assert _retry_tiles(5000, 3000) == []


def test_model_adapter_filters_latin_ui_text_but_keeps_japanese_and_debug_boxes(
    monkeypatch,
) -> None:
    image_module = pytest.importorskip("PIL.Image")
    image_draw = pytest.importorskip("PIL.ImageDraw")
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    from app.pipeline import real_ocr

    image = image_module.new("RGB", (640, 400), "white")
    draw = image_draw.Draw(image)
    draw.rectangle((25, 25, 45, 90), fill="black")
    draw.rectangle((125, 25, 145, 90), fill="black")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    blocks = [
        SimpleNamespace(lines=[], xyxy=[20, 20, 60, 100], vertical=True),
        SimpleNamespace(lines=[], xyxy=[120, 20, 160, 100], vertical=False),
    ]
    recognized = iter(["学校", "comipo Play"])

    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(
        real_ocr,
        "_models",
        lambda *_paths: (lambda _image: (None, None, blocks), lambda _crop: next(recognized)),
    )

    result = real_ocr.recognize_with_models(image_bytes.getvalue(), debug=True)
    assert [region.text for region in result.regions] == ["学校"]
    assert [item.status for item in result.debug.detections] == ["recognized", "filtered"]
    assert result.debug.detections[1].text == "comipo Play"
    assert (
        result.debug.detections[1].filterReason == "No Japanese characters in the recognized text"
    )
    assert result.debug.detections[1].cropDataUrl.startswith("data:image/png;base64,")


def test_model_adapter_skips_nearly_uniform_detector_crop(monkeypatch) -> None:
    image_module = pytest.importorskip("PIL.Image")
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    from app.pipeline import real_ocr

    image = image_module.new("RGB", (160, 160), "black")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    block = SimpleNamespace(lines=[], xyxy=[20, 20, 60, 100], vertical=True)

    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(
        real_ocr,
        "_models",
        lambda *_paths: (
            lambda _image: (None, None, [block]),
            lambda _crop: pytest.fail("Nearly uniform crop should not reach recognizer"),
        ),
    )

    result = real_ocr.recognize_with_models(image_bytes.getvalue(), debug=True)
    assert result.regions == []
    assert result.debug.detections[0].status == "filtered"
    assert (
        result.debug.detections[0].filterReason == "Almost no visible contrast in the detector crop"
    )
    assert result.debug.selectionText is None


def test_filtered_small_selection_does_not_return_a_whole_crop_hallucination(monkeypatch) -> None:
    image_module = pytest.importorskip("PIL.Image")
    image_draw = pytest.importorskip("PIL.ImageDraw")
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    from app.pipeline import real_ocr

    image = image_module.new("RGB", (160, 160), "white")
    image_draw.Draw(image).rectangle((25, 25, 45, 95), fill="black")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    block = SimpleNamespace(lines=[], xyxy=[20, 20, 60, 100], vertical=False)
    calls = []

    def recognizer(_crop):
        calls.append(True)
        return "comipo Play" if len(calls) == 1 else "これは日本語です"

    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(
        real_ocr,
        "_models",
        lambda *_paths: (lambda _image: (None, None, [block]), recognizer),
    )

    result = real_ocr.recognize_with_models(image_bytes.getvalue(), debug=True)
    assert result.regions == []
    assert result.debug.detections[0].status == "filtered"
    assert result.debug.selectionText is None
    assert calls == [True]


def test_model_adapter_recovers_text_when_detector_finds_no_boxes(monkeypatch) -> None:
    image_module = pytest.importorskip("PIL.Image")
    image_draw = pytest.importorskip("PIL.ImageDraw")
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    from app.pipeline import real_ocr

    image = image_module.new("RGB", (109, 145), "white")
    image_draw.Draw(image).rectangle((35, 30, 55, 100), fill="black")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")

    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(
        real_ocr,
        "_models",
        lambda *_paths: (lambda _image: (None, None, []), lambda _crop: "たまにはいいでしょ"),
    )

    result = real_ocr.recognize_with_models(image_bytes.getvalue(), debug=True)
    assert len(result.regions) == 1
    assert result.regions[0].geometrySource == "selection"
    assert result.debug.detections == []
    assert result.debug.selectionFallbackUsed is True

    normal_result = real_ocr.recognize_with_models(image_bytes.getvalue())
    assert normal_result.regions[0].text == "たまにはいいでしょ"
    assert normal_result.debug is None

    blank = image_module.new("RGB", (109, 145), "white")
    blank_bytes = BytesIO()
    blank.save(blank_bytes, format="PNG")
    blank_result = real_ocr.recognize_with_models(blank_bytes.getvalue())
    assert blank_result.regions == []
