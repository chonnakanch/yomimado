"""Conservative work avoidance without dropping faint or colored content."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from app.pipeline import real_ocr


def png(image):
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


@pytest.mark.parametrize("color", ["white", "black", (120, 60, 200)])
def test_uniform_capture_skips_model_loading_with_empty_debug(monkeypatch, color):
    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(real_ocr, "_models", lambda *_: pytest.fail("No content to infer"))
    image = png(Image.new("RGB", (960, 1100), color))
    result = real_ocr.recognize_with_models(image, debug=True)
    assert result.regions == []
    assert result.debug.detections == []
    assert result.debug.tileRetryCount == result.debug.maskRetryCount == 0
    assert result.debug.selectionText is None
    assert not result.debug.selectionFallbackUsed
    assert real_ocr.recognize_with_models(image).debug is None


def test_uniform_capture_preserves_missing_resource_error(monkeypatch):
    def missing():
        raise FileNotFoundError("Missing detector")

    monkeypatch.setattr(real_ocr, "_configured_paths", missing)
    with pytest.raises(FileNotFoundError, match="Missing detector"):
        real_ocr.recognize_with_models(png(Image.new("RGB", (100, 100), "white")))


def test_uniform_check_keeps_single_level_and_equal_luminance_color_changes():
    faint = Image.new("RGB", (20, 20), (230, 230, 230))
    faint.putpixel((10, 10), (230, 230, 229))
    assert not real_ocr._is_uniform_image(faint)
    colored = Image.new("RGB", (20, 20), (255, 0, 0))
    colored.putpixel((10, 10), (0, 130, 0))
    assert colored.convert("L").getextrema() == (76, 76)
    assert not real_ocr._is_uniform_image(colored)


def test_only_uniform_retry_tiles_are_omitted():
    image = Image.new("RGB", (960, 1100), (230, 230, 230))
    assert real_ocr._content_retry_tiles(image) == []
    image.putpixel((10, 10), (230, 230, 229))
    assert real_ocr._content_retry_tiles(image) == [(0, 0, 768, 768)]
    image.putpixel((192, 332), (0, 0, 0))
    assert real_ocr._content_retry_tiles(image) == real_ocr._retry_tiles(960, 1100)


def test_crop_results_reused_only_at_same_bounds_and_within_one_request(monkeypatch):
    image = Image.new("RGB", (640, 400), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 30, 80), fill="black")
    draw.rectangle((110, 20, 120, 80), fill="black")
    boxes = [(10, 10, 50, 100), (10, 10, 50, 100), (100, 10, 140, 100)]
    blocks = [SimpleNamespace(xyxy=box, lines=[], vertical=True) for box in boxes]
    calls = []

    def recognize(crop):
        calls.append(crop.size)
        return "学校"

    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(real_ocr, "_models", lambda *_: (lambda _: (None, None, blocks), recognize))
    for _ in range(2):
        response = real_ocr.recognize_with_models(png(image), debug=True)
        assert [region.text for region in response.regions] == ["学校"] * 3
        assert len(response.debug.detections) == 3
    assert calls == [(40, 90)] * 4


def test_selection_fallback_reuses_identical_full_capture_crop(monkeypatch):
    image = Image.new("RGB", (120, 160), "white")
    ImageDraw.Draw(image).rectangle((20, 20, 40, 100), fill="black")
    block = SimpleNamespace(xyxy=(0, 0, 120, 160), lines=[], vertical=True)
    calls = []

    def recognize(crop):
        calls.append(crop.size)
        return "学校"

    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(
        real_ocr, "_models", lambda *_: (lambda _: (None, None, [block]), recognize)
    )
    response = real_ocr.recognize_with_models(png(image), debug=True)
    assert calls == [(120, 160)]
    assert response.regions[0].text == response.debug.selectionText == "学校"
    assert not response.debug.selectionFallbackUsed
