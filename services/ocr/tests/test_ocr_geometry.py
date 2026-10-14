from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw

from app.models import Point
from app.pipeline.geometry import extend_to_visible_ink


def rectangle(bounds):
    l, t, r, b = bounds
    return [Point(x=l, y=t), Point(x=r, y=t), Point(x=r, y=b), Point(x=l, y=b)]


@pytest.mark.parametrize("scale", [1, 2])
@pytest.mark.parametrize("vertical", [False, True])
def test_cut_stroke_and_end_punctuation_are_included_at_image_scale(scale, vertical):
    image = np.full((300, 400, 3), 255, dtype=np.uint8)
    box = (100, 80, 250, 120)
    # Thin leading 一 crosses the detector edge; trailing punctuation is detached.
    image[98:102, 78:115] = 0
    image[95:105, 255:266] = 0
    # A nearby full character outside the detector must not join this region.
    image[85:115, 65:75] = 0
    if vertical:
        image = image.transpose(1, 0, 2).copy()
        box = (box[1], box[0], box[3], box[2])
    image = np.repeat(np.repeat(image, scale, axis=0), scale, axis=1)
    box = tuple(value * scale for value in box)
    corrected, polygon, changed = extend_to_visible_ink(
        image, box, rectangle(box), 40 * scale, vertical, cv2, np
    )
    assert changed
    if vertical:
        assert corrected[1] == 78 * scale - 1
        assert corrected[3] == 266 * scale + 1
    else:
        assert corrected[0] == 78 * scale - 1
        assert corrected[2] == 266 * scale + 1
    contour = np.array([(p.x, p.y) for p in polygon], dtype=np.float32)
    for point in rectangle(box):
        assert cv2.pointPolygonTest(contour, (point.x, point.y), False) >= 0


def test_bubble_border_and_search_edge_art_do_not_expand_region():
    image = np.full((200, 400, 3), 255, dtype=np.uint8)
    box = (100, 80, 250, 120)
    cv2.rectangle(image, (85, 73), (265, 127), (0, 0, 0), 2)
    # Art entering the bounded search edge has an unknown full extent.
    image[95:105, 60:110] = 0
    polygon = rectangle(box)
    assert extend_to_visible_ink(image, box, polygon, 40, False, cv2, np) == (box, polygon, False)


@pytest.mark.parametrize(
    "background,glyph_size", [(255, 0), (255, float("nan")), (20, 40), (255, 40)]
)
def test_blank_dark_or_unknown_scale_preserves_original_polygon(background, glyph_size):
    image = np.full((200, 400, 3), background, dtype=np.uint8)
    box = (100, 80, 250, 120)
    polygon = [Point(x=100, y=85), Point(x=250, y=80), Point(x=250, y=115), Point(x=100, y=120)]
    assert extend_to_visible_ink(image, box, polygon, glyph_size, False, cv2, np) == (
        box,
        polygon,
        False,
    )


def test_recognition_uses_recovered_stroke_and_reports_review_geometry(monkeypatch):
    from app.pipeline import real_ocr

    image = Image.new("RGB", (500, 400), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 100, 79, 104), fill="black")
    draw.rectangle((90, 85, 110, 115), fill="black")
    block = SimpleNamespace(lines=[], xyxy=[60, 80, 220, 120], vertical=False, font_size=40)
    monkeypatch.setattr(real_ocr, "_configured_paths", lambda: (Path("."),) * 3)

    def recognize(crop):
        assert crop.width == 181  # Full leading stroke plus its one-pixel margin.
        return "一緒"

    monkeypatch.setattr(
        real_ocr, "_models", lambda *_: (lambda _: (None, None, [block]), recognize)
    )
    output = BytesIO()
    image.save(output, format="PNG")
    response = real_ocr.recognize_with_models(output.getvalue(), debug=True)
    region = response.regions[0]
    assert region.text == "一緒"
    assert min(point.x for point in region.polygon) == 39
    assert region.geometrySource == "expandedCrop"
    assert region.needsReview and "visible strokes" in region.reviewReason
    # Keep the detector's original diagnostic box distinct from adjusted geometry.
    assert response.debug.detections[0].box == rectangle((60, 80, 220, 120))
