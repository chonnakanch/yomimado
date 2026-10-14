"""Bounded image-space correction for detector boxes that cut visible strokes."""

from __future__ import annotations

import math
from typing import Any

from app.models import Point


def extend_to_visible_ink(
    bgr: Any,
    box: tuple[int, int, int, int],
    polygon: list[Point],
    glyph_size: float,
    vertical: bool,
    cv2: Any,
    np: Any,
) -> tuple[tuple[int, int, int, int], list[Point], bool]:
    """Recover cut strokes, omitted thin strokes and nearby end punctuation.

    Search distances follow the detector's glyph size in captured image pixels.
    Large components (bubble borders/art), components cut by the search edge and
    dark backgrounds are excluded. Changed geometry remains explicitly approximate.
    """
    if not math.isfinite(glyph_size) or glyph_size <= 0:
        return box, polygon, False
    height, width = bgr.shape[:2]
    x1, y1, x2, y2 = box
    # A full-screen detector can omit an entire 一 or long-vowel stroke.
    # Leave enough search space to observe the complete component, rather than
    # rejecting it as cut by the search edge. Acceptance remains glyph-bounded.
    along = math.ceil(glyph_size * 1.5)
    across = math.ceil(glyph_size * 0.2)
    px, py = (across, along) if vertical else (along, across)
    left, top = max(0, x1 - px), max(0, y1 - py)
    right, bottom = min(width, x2 + px), min(height, y2 + py)
    gray = cv2.cvtColor(bgr[top:bottom, left:right], cv2.COLOR_BGR2GRAY)
    background = float(np.percentile(gray, 80))
    if background < 200:
        return box, polygon, False
    ink = (gray < min(180, background - 40)).astype(np.uint8)
    _, _, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    contour = np.array([(point.x, point.y) for point in polygon], dtype=np.float32)
    added: list[tuple[float, float]] = []
    bounds = list(box)
    for cx, cy, cw, ch, area in stats[1:]:
        if area < max(3, glyph_size * glyph_size * 0.002):
            continue
        if max(cw, ch) > glyph_size * 1.5:
            continue
        # A truncated search component cannot establish its true extent.
        if cx == 0 or cy == 0 or cx + cw == right - left or cy + ch == bottom - top:
            continue
        l, t = int(cx + left), int(cy + top)
        r, b = l + int(cw), t + int(ch)
        intersects = l < x2 and r > x1 and t < y2 and b > y1
        if vertical:
            aligned = l < x2 and r > x1
            gap = max(y1 - b, t - y2, 0)
        else:
            aligned = t < y2 and b > y1
            gap = max(x1 - r, l - x2, 0)
        near_end = gap <= glyph_size * 0.35
        punctuation = max(cw, ch) <= glyph_size * 0.5
        thin_stroke = (
            min(cw, ch) <= glyph_size * 0.2
            and max(cw, ch) >= glyph_size * 0.45
            and max(cw, ch) >= min(cw, ch) * 3
        )
        if not intersects and not (aligned and near_end and (punctuation or thin_stroke)):
            continue
        corners = [(l - 1, t - 1), (r + 1, t - 1), (r + 1, b + 1), (l - 1, b + 1)]
        if all(cv2.pointPolygonTest(contour, point, False) >= 0 for point in corners):
            continue
        added.extend(corners)
        bounds = [
            min(bounds[0], l - 1),
            min(bounds[1], t - 1),
            max(bounds[2], r + 1),
            max(bounds[3], b + 1),
        ]
    if not added:
        return box, polygon, False
    points = np.array([(point.x, point.y) for point in polygon] + added, dtype=np.float32)
    hull = cv2.convexHull(points).reshape(-1, 2)
    adjusted = [
        Point(x=max(0, min(width, float(x))), y=max(0, min(height, float(y)))) for x, y in hull
    ]
    return (
        (max(0, bounds[0]), max(0, bounds[1]), min(width, bounds[2]), min(height, bounds[3])),
        adjusted,
        True,
    )
