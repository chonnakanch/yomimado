"""Recover a missing edge kana without accepting unrelated OCR alternatives."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from app.models import Point, TextRegion
from app.pipeline import real_ocr


def region(text="学校", *, box=(20, 20, 45, 75), orientation="horizontal"):
    left, top, right, bottom = box
    return TextRegion(
        id="region-1",
        text=text,
        polygon=[
            Point(x=left, y=top),
            Point(x=right, y=top),
            Point(x=right, y=bottom),
            Point(x=left, y=bottom),
        ],
        orientation=orientation,
        confidence=0,
        type="other",
        tokens=[],
    )


@pytest.mark.parametrize(
    "original,recovered",
    [("学校", "学校へ"), ("兄ちゃん", "お兄ちゃん"), ("学校", "学 校 へ"), ("𠮷田", "𠮷田へ")],
)
def test_one_additional_japanese_character_can_recover_a_small_selection(original, recovered):
    detected = region(original)
    result, used = real_ocr._apply_selection_fallback([detected], 100, 240, recovered)
    assert used
    assert result[0].text == recovered
    assert result[0].geometrySource == "selection"
    assert result[0].needsReview
    assert result[0].reviewReason == real_ocr.SELECTION_REVIEW_REASON
    assert result[0].confidence == 0
    assert [(p.x, p.y) for p in result[0].polygon] == [(0, 0), (100, 0), (100, 240), (0, 240)]
    # Recovery returns a new region, preserving the detector's evidence.
    assert detected.text == original
    assert detected.orientation == "horizontal"


@pytest.mark.parametrize(
    "original,alternative",
    [
        ("学校", "学校。"),
        ("学校", "学校ー"),
        ("学校", "学校A"),
        ("学校", "学 校"),
        ("学校", "学へ校"),
        ("学校", "学生へ"),
        ("学", "学校"),
        ("A学", "A学校"),
        ("", "学校へ"),
    ],
)
def test_single_character_recovery_rejects_punctuation_substitution_and_weak_matches(
    original, alternative
):
    detected = region(original)
    result, used = real_ocr._apply_selection_fallback([detected], 100, 240, alternative)
    assert not used
    assert result == [detected]


@pytest.mark.parametrize("dimensions", [(321, 240), (100, 321)])
def test_single_character_recovery_keeps_the_existing_selection_size_limit(dimensions):
    detected = region()
    result, used = real_ocr._apply_selection_fallback([detected], *dimensions, "学校へ")
    assert not used
    assert result == [detected]


def test_single_character_recovery_does_not_combine_separate_regions():
    detected = [region(), region("へ")]
    result, used = real_ocr._apply_selection_fallback(detected, 100, 240, "学校へ")
    assert not used
    assert result == detected


@pytest.mark.parametrize(
    "dimensions,box,text,expected",
    [
        ((100, 240), (20, 20, 60, 100), "学校", "vertical"),
        ((100, 240), (20, 20, 80, 50), "学校", "horizontal"),
        ((240, 100), (20, 20, 60, 100), "学校", "horizontal"),
        ((200, 240), (20, 20, 60, 100), "学校", "horizontal"),
        ((100, 240), (20, 20, 60, 100), "学校へ行く", "horizontal"),
    ],
)
def test_orientation_correction_requires_agreeing_selection_and_short_text_shapes(
    dimensions, box, text, expected
):
    result, used = real_ocr._apply_selection_fallback(
        [region(text, box=box)], *dimensions, text + "よ"
    )
    assert used
    assert result[0].orientation == expected


@pytest.mark.parametrize("scale", [1, 2])
@pytest.mark.parametrize("vertical", [False, True])
def test_pipeline_recovers_one_kana_and_keeps_original_debug_evidence(monkeypatch, scale, vertical):
    dimensions = (90, 150) if vertical else (150, 120)
    box = (20, 20, 45, 75) if vertical else (20, 20, 75, 45)
    dimensions = tuple(value * scale for value in dimensions)
    box = tuple(value * scale for value in box)
    image = Image.new("RGB", dimensions, "white")
    ImageDraw.Draw(image).rectangle((box[0] + 2, box[1] + 2, box[2] - 2, box[3] - 2), fill="black")
    output = BytesIO()
    image.save(output, format="PNG")
    block = SimpleNamespace(xyxy=box, lines=[], vertical=False)
    calls = []

    def recognize(crop):
        calls.append(crop.size)
        if crop.size == dimensions:
            assert crop.tobytes() == image.tobytes()
            return "学校へ"
        return "学校"

    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(
        real_ocr, "_models", lambda *_: (lambda _: (None, None, [block]), recognize)
    )
    response = real_ocr.recognize_with_models(output.getvalue(), debug=True)
    assert calls == [(box[2] - box[0], box[3] - box[1]), dimensions]
    assert len(response.regions) == 1
    recovered = response.regions[0]
    assert recovered.text == "学校へ"
    assert recovered.orientation == ("vertical" if vertical else "horizontal")
    assert recovered.geometrySource == "selection"
    assert recovered.needsReview and recovered.confidence == 0
    assert response.debug.selectionFallbackUsed
    assert response.debug.selectionText == "学校へ"
    assert response.debug.tileRetryCount == 0
    assert response.debug.detections[0].text == "学校"
    assert response.debug.detections[0].box == region(box=box).polygon
