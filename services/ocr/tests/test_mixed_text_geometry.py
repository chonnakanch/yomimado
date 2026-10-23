"""Mixed-content selections must not turn horizontal rows into vertical targets."""

from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from test_region_geometry_recovery import glyph_rows, rectangle, run_pipeline

from app.pipeline import real_ocr
from app.pipeline.geometry import ink_covered_by_rows


def block(box, *, vertical=False, font=32, language="unknown"):
    return SimpleNamespace(xyxy=box, lines=[], vertical=vertical, font_size=font, language=language)


def opening(dark, label, scale):
    image = np.full((200, 500, 3), 0 if dark else 255, dtype=np.uint8)
    for top, count in [(50, 7), (90, 2)]:
        for left in range(60, 60 + count * 40, 40):
            image[top : top + 24, left : left + 28] = 255 if dark else 0
    boxes = [
        block((58, 48, 90, 116), vertical=True),
        block((96, 46, 200, 78)),
        block((201, 46, 332, 78)),
    ]
    if label:
        for left in range(60, 180, 12):
            image[8:22, left : left + 8] = (0, 170, 255)
        boxes.insert(0, block((58, 6, 180, 26), font=14, language="eng"))
    image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    for b in boxes:
        b.xyxy = tuple(round(v * scale) for v in b.xyxy)
        b.font_size *= scale
    return image, boxes


@pytest.mark.parametrize("dark", [False, True])
@pytest.mark.parametrize("scale", [1, 1.5, 2])
def test_header_does_not_change_complete_japanese_row_geometry(monkeypatch, dark, scale):
    # This test supplies full-pass boxes; offset-aware tile behavior is separate.
    monkeypatch.setattr(real_ocr, "_content_retry_tiles", lambda _: [])
    outputs = []
    for label in [False, True]:
        image, boxes = opening(dark, label, scale)
        calls = []

        def recognize(crop, calls=calls):
            calls.append(crop.size)
            # Simulate the Japanese decoder hallucinating Japanese from a label.
            return "これは翻訳です" if crop.height <= 21 * scale else "今日は晴れです"

        response = run_pipeline(monkeypatch, image, boxes, recognize)
        rows = [r for r in response.regions if r.reviewReason == real_ocr.LINE_REVIEW_REASON]
        expected = [
            rectangle((60 * scale - 1, top * scale - 1, right * scale + 1, (top + 24) * scale + 1))
            for top, right in [(50, 328), (90, 128)]
        ]
        assert [r.polygon for r in rows] == expected
        assert all(
            r.orientation == "horizontal" and r.needsReview and r.confidence == 0 for r in rows
        )
        assert not any(r.orientation == "vertical" for r in response.regions)
        assert len(calls) == 2 + int(label)
        original = rectangle(tuple(round(v * scale) for v in (96, 46, 200, 78)))
        assert all(d.box == original for d in response.debug.detections[:2])
        outputs.append([r.polygon for r in rows])
        if label:
            header = response.regions[0]
            assert header.needsReview and header.confidence == 0
            assert header.reviewReason == real_ocr.LANGUAGE_REVIEW_REASON
            assert header.polygon == rectangle(tuple(round(v * scale) for v in (58, 6, 180, 26)))
            assert any(
                real_ocr.LANGUAGE_REVIEW_REASON in d.decisionReason
                for d in response.debug.detections
            )
        assert any(d.status == "filtered" for d in response.debug.detections)
    assert outputs[0] == outputs[1]


@pytest.mark.parametrize("dark", [False, True])
def test_nearby_real_vertical_column_remains_vertical(monkeypatch, dark):
    image = np.full((300, 500, 3), 0 if dark else 255, dtype=np.uint8)
    ink = 255 if dark else 0
    for top in (50, 90, 130, 170, 210):
        image[top : top + 24, 20:44] = ink
    for left in range(60, 340, 40):
        image[50:74, left : left + 28] = ink
    vertical = block((18, 48, 46, 236), vertical=True)
    horizontal = block((58, 46, 332, 78))
    response = run_pipeline(monkeypatch, image, [vertical, horizontal], lambda _: "縦と横の文章")
    assert len(response.regions) == 2
    assert response.regions[0].orientation == "vertical"
    assert response.regions[0].polygon == rectangle(vertical.xyxy)
    assert response.regions[1].orientation == "horizontal"
    assert min(p.x for p in response.regions[1].polygon) >= 46


def test_multiline_columns_keep_their_own_recovery_boundaries(monkeypatch):
    image = glyph_rows(dark=True)
    for top in (50, 90, 130):
        for left in (385, 409, 433, 457):
            image[top : top + 24, left : left + 18] = 255
    boxes = [block((40, 30, 350, 190), font=40), block((375, 30, 499, 190), font=40)]
    response = run_pipeline(monkeypatch, image, boxes, lambda _: "別の段落です")
    assert len(response.regions) == 6
    assert all(max(p.x for p in r.polygon) <= 350 for r in response.regions[:3])
    assert all(min(p.x for p in r.polygon) >= 375 for r in response.regions[3:])


def test_non_japanese_label_on_the_same_baseline_stays_separate(monkeypatch):
    image = np.zeros((180, 500, 3), dtype=np.uint8)
    for left in range(40, 360, 32):
        image[50:74, left : left + 24] = 255
    boxes = [block((38, 46, 196, 78)), block((198, 46, 356, 78), language="eng")]
    response = run_pipeline(monkeypatch, image, boxes, lambda _: "日本語のような出力")
    assert len(response.regions) == 2
    assert max(p.x for p in response.regions[0].polygon) <= 198
    assert min(p.x for p in response.regions[1].polygon) >= 196
    assert response.regions[1].needsReview
    assert real_ocr.LANGUAGE_REVIEW_REASON in response.regions[1].reviewReason


@pytest.mark.parametrize("dark", [False, True])
def test_row_union_uses_ink_and_keeps_an_uncovered_vertical_glyph(dark):
    image = glyph_rows(dark)
    rows = [(59, top - 1, 329, top + 25) for top in (50, 90, 130)]
    box = (58, 48, 90, 156)
    assert ink_covered_by_rows(image, box, rows, cv2, np)
    assert not ink_covered_by_rows(image, box, [rows[0], rows[0]], cv2, np)
    image[77:87, 60:88] = 255 if dark else 0
    assert not ink_covered_by_rows(image, box, rows, cv2, np)


def test_padded_single_row_duplicate_uses_ink_without_covering_extra_text():
    image = glyph_rows(True)
    row = (59, 49, 329, 75)
    box = (200, 37, 330, 87)
    assert ink_covered_by_rows(image, box, [row], cv2, np)
    image[79:87, 205:225] = 255
    assert not ink_covered_by_rows(image, box, [row], cv2, np)


def test_tile_and_mask_fragments_cannot_reintroduce_covered_vertical_runs(monkeypatch):
    image = np.zeros((900, 500, 3), dtype=np.uint8)
    image[:240] = glyph_rows(dark=True)
    paragraph = block((40, 30, 370, 190), font=40)
    tile = block((58, 48, 90, 156), vertical=True)
    mask = block((58, 48, 90, 116), vertical=True)
    monkeypatch.setattr(
        real_ocr,
        "_detected_blocks",
        lambda *_: [(paragraph, 0, 0, "full"), (tile, 0, 0, "tile"), (mask, 0, 0, "mask")],
    )
    calls = []

    def recognize(crop):
        calls.append(crop.size)
        return "今日は晴れです"

    response = run_pipeline(monkeypatch, image, [], recognize)
    assert len(response.regions) == len(calls) == 3
    assert all(r.orientation == "horizontal" for r in response.regions)
    assert [d.status for d in response.debug.detections[-2:]] == ["filtered", "filtered"]


def test_failed_horizontal_recognition_does_not_suppress_the_vertical_fallback(monkeypatch):
    image, boxes = opening(True, False, 1)
    response = run_pipeline(
        monkeypatch,
        image,
        boxes,
        lambda crop: "English only" if crop.width > 100 else "縦の文章です",
    )
    assert any(r.orientation == "vertical" for r in response.regions)


def test_refined_non_japanese_crop_keeps_both_review_reasons(monkeypatch):
    response = run_pipeline(
        monkeypatch,
        glyph_rows(True),
        [block((40, 30, 370, 190), font=40, language="eng")],
        lambda _: "これは日本語に見える出力",
    )
    assert len(response.regions) == 3
    assert all(
        real_ocr.LINE_REVIEW_REASON in r.reviewReason
        and real_ocr.LANGUAGE_REVIEW_REASON in r.reviewReason
        and r.needsReview
        and r.confidence == 0
        for r in response.regions
    )


@pytest.mark.parametrize("dark", [False, True])
@pytest.mark.parametrize("stage", ["full", "tile", "mask"])
@pytest.mark.parametrize("uncovered", [False, True])
def test_overlapping_fragment_is_suppressed_only_when_its_ink_is_covered(
    monkeypatch, dark, stage, uncovered
):
    image = np.full((240, 500, 3), 0 if dark else 255, dtype=np.uint8)
    ink = 255 if dark else 0
    for left in range(60, 340, 40):
        image[50:90, left : left + 28] = ink
    if uncovered:
        # A separate short run lies below the horizontal block's search bounds.
        for left in (205, 245, 285):
            image[96:105, left : left + 20] = ink
    paragraph = block((40, 30, 370, 92), font=40)
    fragment = block((200, 45, 330, 106), font=0, vertical=stage == "mask")
    monkeypatch.setattr(
        real_ocr,
        "_detected_blocks",
        lambda *_: [(paragraph, 0, 0, "full"), (fragment, 0, 0, stage)],
    )
    calls = []

    def recognize(crop):
        calls.append(crop.size)
        return "これは主な文章です" if crop.width > 200 else "別の字"

    response = run_pipeline(monkeypatch, image, [], recognize)
    row = (59, 49, 329, 91)
    assert real_ocr._overlap_over_smaller(fragment.xyxy, row) > 0.6
    assert ink_covered_by_rows(image, fragment.xyxy, [row], cv2, np) == (not uncovered)
    assert [r.text for r in response.regions] == ["これは主な文章です"] + (
        ["別の字"] if uncovered else []
    )
    assert calls == [(270, 42)] + ([(130, 61)] if uncovered else [])
    assert response.regions[0].polygon == rectangle(row)
    if uncovered:
        assert response.regions[1].polygon == rectangle(fragment.xyxy)
    assert response.debug.detections[-1].status == ("recognized" if uncovered else "filtered")


@pytest.mark.parametrize("recovery", ["selection", "expandedCrop"])
def test_text_recovery_preserves_non_japanese_warning(monkeypatch, recovery):
    dimensions = (150, 150) if recovery == "selection" else (200, 900)
    box = (20, 20, 100, 70) if recovery == "selection" else (40, 120, 60, 180)
    image = np.full((dimensions[1], dimensions[0], 3), 255, dtype=np.uint8)
    left, top, right, bottom = box
    image[top + 2 : bottom - 2, left + 2 : right - 2] = 0
    monkeypatch.setattr(real_ocr, "_content_retry_tiles", lambda _: [])
    calls = []

    def recognize(crop):
        calls.append(crop.size)
        return "学校" if crop.size == (right - left, bottom - top) else "学校へ"

    response = run_pipeline(
        monkeypatch,
        image,
        [block(box, font=0, vertical=recovery == "expandedCrop", language="eng")],
        recognize,
    )
    assert len(calls) == 2
    assert len(response.regions) == 1
    region = response.regions[0]
    assert region.text == "学校へ"
    assert region.geometrySource == recovery
    assert region.needsReview and region.confidence == 0
    assert real_ocr.LANGUAGE_REVIEW_REASON in region.reviewReason
    reason = (
        real_ocr.SELECTION_REVIEW_REASON
        if recovery == "selection"
        else real_ocr.EXPANDED_REVIEW_REASON
    )
    assert reason in region.reviewReason
    assert response.debug.detections[0].text == "学校"
    assert real_ocr.LANGUAGE_REVIEW_REASON in response.debug.detections[0].decisionReason
