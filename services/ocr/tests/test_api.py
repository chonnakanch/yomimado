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
