"""Bounded image-space correction for detector boxes that cut visible strokes."""

from __future__ import annotations

import math
from typing import Any

from app.models import Point


def clip_polygon(polygon: list[Point], width: int, height: int) -> tuple[list[Point], bool]:
    """Intersect a polygon with the capture, preserving its edges and orientation."""
    if any(not math.isfinite(p.x) or not math.isfinite(p.y) for p in polygon):
        return [], True
    points = polygon
    for axis, edge, lower in (
        ("x", 0, True),
        ("x", width, False),
        ("y", 0, True),
        ("y", height, False),
    ):
        output = []
        for previous, current in zip(points[-1:] + points[:-1], points):
            a, b = getattr(previous, axis), getattr(current, axis)
            a_inside = a >= edge if lower else a <= edge
            b_inside = b >= edge if lower else b <= edge
            if a_inside != b_inside:
                ratio = (edge - a) / (b - a)
                output.append(
                    Point(
                        x=previous.x + ratio * (current.x - previous.x),
                        y=previous.y + ratio * (current.y - previous.y),
                    )
                )
            if b_inside:
                output.append(current)
        points = output
    unique = []
    for point in points:
        if not unique or point != unique[-1]:
            unique.append(point)
    if len(unique) > 1 and unique[0] == unique[-1]:
        unique.pop()
    area = abs(sum(a.x * b.y - b.x * a.y for a, b in zip(unique[-1:] + unique[:-1], unique)))
    return (unique if len(unique) >= 3 and area > 0 else []), unique != polygon


def horizontal_text_lines(
    bgr: Any,
    box: tuple[int, int, int, int],
    glyph_size: float,
    barriers: list[tuple[int, int, int, int]],
    cv2: Any,
    np: Any,
) -> list[tuple[int, int, int, int]]:
    """Refine ambiguous horizontal blocks on a plain light or dark background.

    Require several glyph components on a common row. Whitespace separates rows
    and columns; known neighboring detector blocks bound any end recovery. This
    deliberately declines artwork, low contrast and unsupported rotated text.
    """
    if not math.isfinite(glyph_size) or glyph_size <= 0:
        return []
    height, width = bgr.shape[:2]
    x1, y1, x2, y2 = box
    if x2 <= x1 or y2 - y1 < 6:
        return []
    padding = math.ceil(min(y2 - y1, glyph_size) * 3)
    left, right = max(0, x1 - padding), min(width, x2 + padding)
    for l, t, r, b in barriers:
        overlap = min(b, y2) - max(t, y1)
        if overlap < min(b - t, y2 - y1) * 0.5:
            continue
        if r <= x1:
            left = max(left, r)
        elif l >= x2:
            right = min(right, l)
    gray = cv2.cvtColor(bgr[y1:y2, left:right], cv2.COLOR_BGR2GRAY)
    background = float(np.median(gray))
    if float(np.mean(np.abs(gray.astype(np.float32) - background) < 20)) < 0.55:
        return []
    if background >= 220:
        ink = gray < min(180, background - 40)
    elif background <= 35:
        ink = gray > max(75, background + 40)
    else:
        return []
    _, _, stats, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    components = [
        (int(x + left), int(y + y1), int(x + left + w), int(y + y1 + h))
        for x, y, w, h, area in stats[1:]
        if area >= 4 and h >= 3 and 0.08 <= w / h <= 5
    ]
    if len(components) < 4:
        return []
    typical_height = float(np.percentile([b - t for _, t, _, b in components], 80))
    components = [c for c in components if c[3] - c[1] <= typical_height * 1.8]
    bands: list[list[tuple[int, int, int, int]]] = []
    for component in sorted(components, key=lambda c: c[1]):
        if not bands or component[1] > max(c[3] for c in bands[-1]) + 1:
            bands.append([component])
        else:
            bands[-1].append(component)
    lines = []
    strong_line = False
    for band in bands:
        top, bottom = min(c[1] for c in band), max(c[3] for c in band)
        line_height = bottom - top
        if line_height < 5:
            continue
        runs: list[list[tuple[int, int, int, int]]] = []
        for component in sorted(band):
            if not runs or component[0] - max(c[2] for c in runs[-1]) > line_height:
                runs.append([component])
            else:
                runs[-1].append(component)
        for run in runs:
            l, r = min(c[0] for c in run), max(c[2] for c in run)
            if r <= x1 or l >= x2:
                continue
            # Do not use a partial glyph cut by the horizontal search boundary
            # as evidence for extending into another text area.
            if (l == left and l < x1) or (r == right and r > x2):
                return []
            strong_line |= len(run) >= 4 and r - l >= line_height * 3
            lines.append(
                (max(0, l - 1), max(0, top - 1), min(width, r + 1), min(height, bottom + 1))
            )
    if not strong_line or not 1 <= len(lines) <= 16:
        return []
    if len(lines) == 1:
        l, t, r, b = lines[0]
        h = b - t
        if y2 - y1 < h * 1.4 and l >= x1 - h * 0.25 and r <= x2 + h * 0.25:
            return []
    return lines


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
    # Preserve an enclosing text rectangle rather than forming a pointed hull
    # between a tall detector box and a smaller recovered end glyph.
    hull = cv2.boxPoints(cv2.minAreaRect(points))
    adjusted, _ = clip_polygon([Point(x=float(x), y=float(y)) for x, y in hull], width, height)
    return (
        (max(0, bounds[0]), max(0, bounds[1]), min(width, bounds[2]), min(height, bounds[3])),
        adjusted,
        True,
    )
