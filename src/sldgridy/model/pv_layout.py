"""Placing PV modules on a roof area. Pure Python.

The roof is a simple polygon (rectangle, trapezoid, triangle, hip roof face).
Modules are axis-parallel rectangles in a regular grid. A module is placed when it
lies inside the roof, keeps the edge distance to every roof edge and the obstacle
distance to every obstacle. Several grid offsets are tried; the one with the most
modules wins, ties go to the most centred field.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from sldgridy.model.geometry import Point

Polygon = Sequence[Point]
EPS = 1e-6
OFFSET_STEPS = 12  # grid offsets tried per direction


@dataclass(frozen=True)
class LayoutParams:
    width: float  # module size in the drawing, already turned for the orientation
    height: float
    gap: float = 20.0  # between modules
    edge: float = 300.0  # to the roof edges
    obstacle_gap: float = 200.0  # to obstacles


def polygon_area(poly: Polygon) -> float:
    return (
        abs(sum(a.x * b.y - b.x * a.y for a, b in zip(poly, [*poly[1:], poly[0]], strict=True))) / 2
    )


def contains(poly: Polygon, p: Point) -> bool:
    """Point in polygon (ray casting); points on the boundary count as inside."""
    inside = False
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if _point_segment_distance(p, a, b) <= EPS:
            return True
        if (a.y > p.y) != (b.y > p.y):
            x = a.x + (p.y - a.y) * (b.x - a.x) / (b.y - a.y)
            if x > p.x:
                inside = not inside
    return inside


def _point_segment_distance(p: Point, a: Point, b: Point) -> float:
    dx, dy = b.x - a.x, b.y - a.y
    length2 = dx * dx + dy * dy
    if length2 <= EPS * EPS:
        return math.hypot(p.x - a.x, p.y - a.y)
    t = max(0.0, min(1.0, ((p.x - a.x) * dx + (p.y - a.y) * dy) / length2))
    return math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy))


def _segments_cross(a: Point, b: Point, c: Point, d: Point) -> bool:
    def orient(p: Point, q: Point, r: Point) -> float:
        return (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x)

    d1, d2 = orient(c, d, a), orient(c, d, b)
    d3, d4 = orient(a, b, c), orient(a, b, d)
    return (d1 * d2 < -EPS) and (d3 * d4 < -EPS)


def _segment_distance(a: Point, b: Point, c: Point, d: Point) -> float:
    if _segments_cross(a, b, c, d):
        return 0.0
    return min(
        _point_segment_distance(a, c, d),
        _point_segment_distance(b, c, d),
        _point_segment_distance(c, a, b),
        _point_segment_distance(d, a, b),
    )


def _edges(poly: Polygon) -> list[tuple[Point, Point]]:
    return [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]


def rect_corners(x: float, y: float, w: float, h: float) -> list[Point]:
    return [Point(x, y), Point(x + w, y), Point(x + w, y + h), Point(x, y + h)]


def polygon_distance(a: Polygon, b: Polygon) -> float:
    """Distance between two polygons; 0 when they overlap or one contains the other."""
    if any(contains(b, p) for p in a) or any(contains(a, p) for p in b):
        return 0.0
    return min(_segment_distance(p, q, r, s) for p, q in _edges(a) for r, s in _edges(b))


def fits(
    module: Polygon, roof: Polygon, obstacles: Sequence[Polygon], params: LayoutParams
) -> bool:
    if not all(contains(roof, p) for p in module):
        return False
    if any(_segments_cross(p, q, r, s) for p, q in _edges(module) for r, s in _edges(roof)):
        return False
    edge = min(_segment_distance(p, q, r, s) for p, q in _edges(module) for r, s in _edges(roof))
    if edge < params.edge - EPS:
        return False
    return all(polygon_distance(module, o) >= params.obstacle_gap - EPS for o in obstacles)


def take_modules(corners: list[Point], count: int) -> list[Point]:
    """``count`` of the placed modules: whole rows from the top, the last (partial) row
    centred in its row. ``count`` 0 or more than placed keeps all."""
    if count <= 0 or count >= len(corners):
        return list(corners)
    rows: dict[float, list[Point]] = {}
    for c in corners:
        rows.setdefault(round(c.y, 3), []).append(c)
    chosen: list[Point] = []
    for y in sorted(rows):
        row = sorted(rows[y], key=lambda c: c.x)
        rest = count - len(chosen)
        if rest <= 0:
            break
        if len(row) <= rest:
            chosen.extend(row)
        else:
            start = (len(row) - rest) // 2
            chosen.extend(row[start : start + rest])
    return chosen


def layout_modules(
    roof: Polygon, obstacles: Sequence[Polygon], params: LayoutParams
) -> list[Point]:
    """Top left corners of the modules that fit (most modules, then most centred)."""
    if len(roof) < 3 or params.width <= 0 or params.height <= 0:
        return []
    xs = [p.x for p in roof]
    ys = [p.y for p in roof]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    step_x, step_y = params.width + params.gap, params.height + params.gap
    centre = Point((min_x + max_x) / 2, (min_y + max_y) / 2)
    best: list[Point] = []
    best_key: tuple[int, float] = (0, 0.0)
    for i in range(OFFSET_STEPS):
        for j in range(OFFSET_STEPS):
            ox = min_x + params.edge + step_x * i / OFFSET_STEPS
            oy = min_y + params.edge + step_y * j / OFFSET_STEPS
            placed: list[Point] = []
            y = oy
            while y + params.height <= max_y - params.edge + EPS:
                x = ox
                while x + params.width <= max_x - params.edge + EPS:
                    module = rect_corners(x, y, params.width, params.height)
                    if fits(module, roof, obstacles, params):
                        placed.append(Point(round(x, 6), round(y, 6)))
                    x += step_x
                y += step_y
            if not placed:
                continue
            fx = (min(p.x for p in placed) + max(p.x for p in placed) + params.width) / 2
            fy = (min(p.y for p in placed) + max(p.y for p in placed) + params.height) / 2
            key = (len(placed), -math.hypot(fx - centre.x, fy - centre.y))
            if not best or key > best_key:
                best, best_key = placed, key
    return best
