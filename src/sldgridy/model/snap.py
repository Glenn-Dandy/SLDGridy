"""Object snap: find characteristic points of entities near the cursor."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum

from sldgridy.model.entities import Arc, Busbar, Circle, Entity, Line, Polyline, Rectangle, Wire
from sldgridy.model.geometry import Point, distance
from sldgridy.model.primitives import (
    arc_endpoints,
    arc_midpoint,
    intersect,
    primitives,
    rect_corners,
    segment_midpoint,
)


class SnapMode(StrEnum):
    CONNECTION = "connection"
    ENDPOINT = "endpoint"
    MIDPOINT = "midpoint"
    INTERSECTION = "intersection"
    CENTER = "center"


ALL_MODES = frozenset(SnapMode)

# Tie-break for hits at the same distance.
_RANK = {
    SnapMode.CONNECTION: 0,
    SnapMode.ENDPOINT: 1,
    SnapMode.INTERSECTION: 2,
    SnapMode.MIDPOINT: 3,
    SnapMode.CENTER: 4,
}


@dataclass(frozen=True)
class SnapHit:
    point: Point
    mode: SnapMode


# Hook for entity types that contribute extra candidates (block references,
# connection points). Each returns hits regardless of the cursor position.
ExtraCandidates = Callable[[Entity], list[SnapHit]]


def candidates(e: Entity, modes: frozenset[SnapMode]) -> list[SnapHit]:
    hits: list[SnapHit] = []
    end, mid, cen = SnapMode.ENDPOINT, SnapMode.MIDPOINT, SnapMode.CENTER
    match e:
        case Line() | Busbar():
            if end in modes:
                hits += [SnapHit(e.p1, end), SnapHit(e.p2, end)]
        case Wire():
            if end in modes:
                hits += [SnapHit(p, end) for p in e.points]
        case Polyline() | Rectangle():
            pts = rect_corners(e) if isinstance(e, Rectangle) else list(e.points)
            if end in modes:
                hits += [SnapHit(p, end) for p in pts]
        case Circle():
            if cen in modes:
                hits.append(SnapHit(e.center, cen))
        case Arc():
            if end in modes:
                hits += [SnapHit(p, end) for p in arc_endpoints(e)]
            if mid in modes:
                hits.append(SnapHit(arc_midpoint(e), mid))
            if cen in modes:
                hits.append(SnapHit(e.center, cen))
    if mid in modes and isinstance(e, Line | Polyline | Rectangle | Wire | Busbar):
        hits += [SnapHit(segment_midpoint(s), mid) for s in primitives(e)]
    return hits


def nearest_on_segment(p: Point, a: Point, b: Point) -> Point:
    # Exact results for axis-parallel segments (bus bars), so wire ends lie on them.
    if a.y == b.y:
        return Point(min(max(p.x, min(a.x, b.x)), max(a.x, b.x)), a.y)
    if a.x == b.x:
        return Point(a.x, min(max(p.y, min(a.y, b.y)), max(a.y, b.y)))
    dx, dy = b.x - a.x, b.y - a.y
    length2 = dx * dx + dy * dy
    if length2 == 0:
        return a
    t = max(0.0, min(1.0, ((p.x - a.x) * dx + (p.y - a.y) * dy) / length2))
    return Point(a.x + t * dx, a.y + t * dy)


def find_snap(
    cursor: Point,
    entities: Iterable[Entity],
    aperture: float,
    modes: frozenset[SnapMode] = ALL_MODES,
    extra: ExtraCandidates | None = None,
    decompose: Callable[[Entity], list[Entity]] | None = None,
) -> SnapHit | None:
    """Best snap point within ``aperture`` mm of ``cursor``.

    Connection points always win; otherwise the nearest hit is used.
    ``decompose`` may expand compound entities into simple ones.
    """
    simple: list[Entity] = []
    hits: list[SnapHit] = []
    for e in entities:
        if extra is not None:
            hits += [h for h in extra(e) if h.mode in modes]
        simple += decompose(e) if decompose is not None else [e]
    for e in simple:
        hits += candidates(e, modes)
        if isinstance(e, Busbar) and SnapMode.CONNECTION in modes:
            # Bus bars accept connections anywhere along their length.
            hits.append(SnapHit(nearest_on_segment(cursor, e.p1, e.p2), SnapMode.CONNECTION))
    if SnapMode.INTERSECTION in modes:
        prims = [p for e in simple for p in primitives(e)]
        for i, p in enumerate(prims):
            for q in prims[i + 1 :]:
                hits += [SnapHit(x, SnapMode.INTERSECTION) for x in intersect(p, q)]

    near = [h for h in hits if distance(h.point, cursor) <= aperture]
    if not near:
        return None
    connections = [h for h in near if h.mode is SnapMode.CONNECTION]
    pool = connections or near
    return min(pool, key=lambda h: (round(distance(h.point, cursor), 9), _RANK[h.mode]))
