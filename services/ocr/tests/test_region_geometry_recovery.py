"""Image-space regressions for loose title/paragraph detections on both polarities."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from PIL import Image

from app.models import Point
from app.pipeline import real_ocr
from app.pipeline.geometry import clip_polygon, extend_to_visible_ink, horizontal_text_lines


def rectangle(box):
    l, t, r, b = box
    return [Point(x=l, y=t), Point(x=r, y=t), Point(x=r, y=b), Point(x=l, y=b)]


def glyph_rows(dark=False):
    image = np.full((240, 500, 3), 0 if dark else 255, dtype=np.uint8)
    ink = 255 if dark else 0
    for top in (50, 90, 130):
        for left in range(60, 340, 40):
            image[top : top + 24, left : left + 28] = ink
    return image


@pytest.mark.parametrize("scale", [1, 2])
@pytest.mark.parametrize("dark", [False, True])
def test_plain_paragraph_is_localized_to_separate_complete_rows(dark, scale):
    image = glyph_rows(dark)
    image = np.repeat(np.repeat(image, scale, axis=0), scale, axis=1)
    lines = horizontal_text_lines(
        image, tuple(v * scale for v in (40, 30, 370, 190)), 40 * scale, [], cv2, np
    )
    assert lines == [
        (60 * scale - 1, top * scale - 1, 328 * scale + 1, (top + 24) * scale + 1)
        for top in (50, 90, 130)
    ]


@pytest.mark.parametrize("dark", [False, True])
def test_loose_title_recovers_full_glyphs_and_stops_at_separate_detector_region(dark):
    image = np.full((240, 500, 3), 0 if dark else 255, dtype=np.uint8)
    for left in (108, 152, 196, 240, 284, 328):
        image[90:135, left : left + 34] = 255 if dark else 0
    box = (100, 70, 260, 145)
    assert horizontal_text_lines(image, box, 75, [], cv2, np) == [(107, 89, 363, 136)]
    assert horizontal_text_lines(image, box, 75, [(280, 85, 370, 138)], cv2, np) == [
        (107, 89, 275, 136)
    ]


def test_line_localization_keeps_columns_separate_and_declines_low_contrast_or_art():
    image = glyph_rows()
    for top in (50, 90, 130):
        image[top : top + 24, 415:440] = 0
        image[top : top + 24, 455:480] = 0
    lines = horizontal_text_lines(image, (40, 30, 370, 190), 40, [], cv2, np)
    assert len(lines) == 3
    assert all(line[2] == 329 for line in lines)
    low_contrast = np.where(image == 0, 210, 230).astype(np.uint8)
    assert horizontal_text_lines(low_contrast, (40, 30, 370, 190), 40, [], cv2, np) == []
    artwork = np.zeros_like(image)
    artwork[30:190, 40:370] = 255
    assert horizontal_text_lines(artwork, (40, 30, 370, 190), 40, [], cv2, np) == []


def test_recovered_end_glyph_has_an_enclosing_rectangle_instead_of_pointed_hull():
    image = np.full((240, 500, 3), 255, dtype=np.uint8)
    image[105:130, 240:275] = 0
    box = (100, 80, 250, 160)
    crop, polygon, changed = extend_to_visible_ink(image, box, rectangle(box), 60, False, cv2, np)
    assert changed
    assert crop == (100, 80, 276, 160)
    assert len(polygon) == 4
    assert {(round(p.x), round(p.y)) for p in polygon} == {
        (100, 80),
        (276, 80),
        (276, 160),
        (100, 160),
    }


def test_polygon_clipping_intersects_edges_without_squashing_rotated_vertices():
    polygon = [Point(x=-5, y=10), Point(x=10, y=-5), Point(x=25, y=10), Point(x=10, y=25)]
    clipped, changed = clip_polygon(polygon, 20, 20)
    assert changed
    assert {(p.x, p.y) for p in clipped} == {
        (0, 5),
        (5, 0),
        (15, 0),
        (20, 5),
        (20, 15),
        (15, 20),
        (5, 20),
        (0, 15),
    }
    assert clip_polygon(rectangle((1, 2, 10, 15)), 20, 20) == (rectangle((1, 2, 10, 15)), False)
    assert clip_polygon(rectangle((-10, -10, -5, -5)), 20, 20)[0] == []
    assert clip_polygon([Point(x=float("nan"), y=0)], 20, 20) == ([], True)


def run_pipeline(monkeypatch, image, blocks, recognize):
    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)
    monkeypatch.setattr(real_ocr, "_models", lambda *_: (lambda _: (None, None, blocks), recognize))
    output = BytesIO()
    Image.fromarray(image).save(output, format="PNG")
    return real_ocr.recognize_with_models(output.getvalue(), debug=True)


@pytest.mark.parametrize("dark", [False, True])
def test_pipeline_replaces_loose_paragraph_and_nested_fragment_with_reviewable_rows(
    monkeypatch, dark
):
    box = (40, 30, 370, 190)
    fragment = SimpleNamespace(xyxy=(60, 48, 90, 76), lines=[], vertical=True, font_size=24)
    paragraph = SimpleNamespace(xyxy=box, lines=[], vertical=False, font_size=40)
    calls = []

    def recognize(crop):
        calls.append(crop.size)
        return ["今日は晴れです", "学校へ行きます", "また明日ね"][len(calls) - 1]

    response = run_pipeline(monkeypatch, glyph_rows(dark), [fragment, paragraph], recognize)
    assert len(response.regions) == 3
    assert calls == [(270, 26)] * 3
    assert all(
        r.orientation == "horizontal" and r.needsReview and r.confidence == 0
        for r in response.regions
    )
    assert all(r.geometrySource == "expandedCrop" for r in response.regions)
    assert all(r.reviewReason == real_ocr.LINE_REVIEW_REASON for r in response.regions)
    assert all(d.box == rectangle(box) for d in response.debug.detections[:3])
    assert response.debug.detections[-1].status == "filtered"
    assert "localized" in response.debug.detections[-1].filterReason
    assert not response.debug.selectionFallbackUsed


def test_pipeline_keeps_rotated_geometry_and_clips_it_to_capture(monkeypatch):
    image = np.full((100, 150, 3), 255, dtype=np.uint8)
    image[10:70, 10:90] = 0
    original = [Point(x=-5, y=10), Point(x=50, y=-5), Point(x=70, y=60), Point(x=5, y=75)]
    block = SimpleNamespace(
        xyxy=(-5, -5, 70, 75),
        lines=[1],
        vertical=False,
        font_size=20,
        angle=15,
        min_rect=lambda: [np.array([(p.x, p.y) for p in original])],
    )
    response = run_pipeline(monkeypatch, image, [block], lambda _: "学校")
    assert response.regions[0].polygon == clip_polygon(original, 150, 100)[0]
    assert response.regions[0].needsReview
    assert response.regions[0].reviewReason == real_ocr.CLIPPED_REVIEW_REASON


def test_unresolved_overlapping_text_is_retained_with_review_instead_of_silently_dropped(
    monkeypatch,
):
    image = np.full((400, 500, 3), 255, dtype=np.uint8)
    image[40:180, 40:350] = 0
    image[55:65, 65:85] = 255
    blocks = [
        SimpleNamespace(xyxy=box, lines=[], vertical=False)
        for box in [(40, 40, 350, 180), (50, 50, 150, 100)]
    ]
    texts = iter(["今日は晴れです", "別の文字"])
    response = run_pipeline(monkeypatch, image, blocks, lambda _: next(texts))
    assert [r.text for r in response.regions] == ["今日は晴れです", "別の文字"]
    assert all(
        r.needsReview and r.reviewReason == real_ocr.OVERLAP_REVIEW_REASON for r in response.regions
    )


def test_refinement_caps_crop_count_and_falls_back_to_original_blocks(monkeypatch):
    first = SimpleNamespace(xyxy=(0, 0, 200, 200), lines=[], vertical=False, font_size=20)
    second = SimpleNamespace(xyxy=(200, 0, 500, 200), lines=[], vertical=False, font_size=20)
    third = SimpleNamespace(xyxy=(0, 200, 500, 400), lines=[], vertical=False, font_size=20)
    monkeypatch.setattr(real_ocr, "MAX_HORIZONTAL_LINE_CROPS", 3)
    monkeypatch.setattr(real_ocr, "horizontal_text_lines", lambda *_: [(10, 10, 100, 30)] * 2)
    candidates = [(block, 0, 0, "full") for block in (first, second, third)]
    refined = real_ocr._refine_horizontal_blocks(candidates, np.zeros((400, 500, 3)), cv2, np)
    assert len(refined) == 4
    assert [item[4] for item in refined] == [(0, 0), (0, 1), (1, 0), (2, 0)]
    assert refined[-1][0] is third


def test_pipeline_retains_source_order_after_processing_localized_rows_first(monkeypatch):
    image = glyph_rows()
    image[10:25, 10:35] = 0
    header = SimpleNamespace(xyxy=(5, 5, 45, 30), lines=[], vertical=False)
    paragraph = SimpleNamespace(xyxy=(40, 30, 370, 190), lines=[], vertical=False, font_size=40)
    response = run_pipeline(
        monkeypatch,
        image,
        [header, paragraph],
        lambda crop: "見出し" if crop.width == 40 else "本文です",
    )
    assert response.regions[0].text == "見出し"
    assert [r.id for r in response.regions] == ["region-1", "region-2", "region-3", "region-4"]
