"""Wire helpers: orthogonal routing, junctions, labels and following moved symbols."""

import math
from collections.abc import Iterable, Mapping
from dataclasses import replace

from sldgridy.model.blocks import BlockDefinition, world_connections
from sldgridy.model.entities import (
    BlockReference,
    Busbar,
    ConnectionPoint,
    Entity,
    JunctionMark,
    Text,
    Wire,
)
from sldgridy.model.geometry import Point, distance

EPS = 1e-6
LABEL_GAP = 1.0  # mm between wire and label


def same(a: Point, b: Point) -> bool:
    return abs(a.x - b.x) <= EPS and abs(a.y - b.y) <= EPS


def simplify(points: Iterable[Point]) -> tuple[Point, ...]:
    """Drop repeated points and points in the middle of straight runs."""
    pts: list[Point] = []
    for p in points:
        if not pts or not same(p, pts[-1]):
            pts.append(p)
    changed = True
    while changed and len(pts) > 2:
        changed = False
        for i in range(1, len(pts) - 1):
            a, b, c = pts[i - 1], pts[i], pts[i + 1]
            if (abs(a.x - b.x) <= EPS and abs(b.x - c.x) <= EPS) or (
                abs(a.y - b.y) <= EPS and abs(b.y - c.y) <= EPS
            ):
                del pts[i]
                changed = True
                break
    return tuple(pts)


def elbow(start: Point, end: Point, horizontal_first: bool | None = None) -> list[Point]:
    """Orthogonal path from ``start`` to ``end`` (without ``start``)."""
    if abs(start.x - end.x) <= EPS or abs(start.y - end.y) <= EPS:
        return [end]
    if horizontal_first is None:
        horizontal_first = abs(end.x - start.x) >= abs(end.y - start.y)
    corner = Point(end.x, start.y) if horizontal_first else Point(start.x, end.y)
    return [corner, end]


def segments(points: tuple[Point, ...]) -> list[tuple[Point, Point]]:
    return list(zip(points, points[1:], strict=False))


def _on_segment_interior(p: Point, a: Point, b: Point) -> bool:
    if same(p, a) or same(p, b):
        return False
    if abs(a.x - b.x) <= EPS:
        return abs(p.x - a.x) <= EPS and min(a.y, b.y) - EPS <= p.y <= max(a.y, b.y) + EPS
    if abs(a.y - b.y) <= EPS:
        return abs(p.y - a.y) <= EPS and min(a.x, b.x) - EPS <= p.x <= max(a.x, b.x) + EPS
    # General segment (should not happen for wires).
    cross = (b.x - a.x) * (p.y - a.y) - (b.y - a.y) * (p.x - a.x)
    if abs(cross) > EPS * max(1.0, distance(a, b)):
        return False
    dot = (p.x - a.x) * (b.x - a.x) + (p.y - a.y) * (b.y - a.y)
    return 0 < dot < distance(a, b) ** 2


JUNCTION_MIN_DIAMETER = 1.0  # mm
JUNCTION_WEIGHT_FACTOR = 4.0  # diameter as a multiple of the wire's line width


def junctions(entities: Iterable[Entity]) -> list[tuple[Point, Entity]]:
    """Connection dots with the entity that gives their style.

    Automatic dots: a wire end on the inside of another wire, a wire end on a
    bus bar, or three or more wire ends at one point. Junction marks then
    force (``connected``) or suppress dots at their position.
    """
    entities = list(entities)
    wires = [e for e in entities if isinstance(e, Wire) and len(e.points) >= 2]
    bars = [e for e in entities if isinstance(e, Busbar)]
    marks = [e for e in entities if isinstance(e, JunctionMark)]
    # Index axis-parallel segments by their constant coordinate.
    vertical: dict[float, list[tuple[str, Point, Point]]] = {}
    horizontal: dict[float, list[tuple[str, Point, Point]]] = {}
    other: list[tuple[str, Point, Point]] = []
    ends: dict[tuple[float, float], list[Wire]] = {}
    for w in wires:
        for a, b in segments(w.points):
            if abs(a.x - b.x) <= EPS:
                vertical.setdefault(round(a.x, 6), []).append((w.id, a, b))
            elif abs(a.y - b.y) <= EPS:
                horizontal.setdefault(round(a.y, 6), []).append((w.id, a, b))
            else:
                other.append((w.id, a, b))
        for p in (w.points[0], w.points[-1]):
            ends.setdefault((round(p.x, 6), round(p.y, 6)), []).append(w)
    result: list[tuple[Point, Entity]] = []
    for (x, y), owners in ends.items():
        p = Point(x, y)
        if len(owners) >= 3:
            result.append((p, owners[0]))
            continue
        candidates = vertical.get(x, []) + horizontal.get(y, []) + other
        owner_ids = {w.id for w in owners}
        if any(
            wid not in owner_ids and _on_segment_interior(p, a, b) for wid, a, b in candidates
        ) or any(on_segment(p, bar.p1, bar.p2) for bar in bars):
            result.append((p, owners[0]))
    for mark in marks:
        result = [(p, o) for p, o in result if not same(p, mark.position)]
        if mark.connected:
            result.append((mark.position, mark))
    return result


def on_segment(p: Point, a: Point, b: Point) -> bool:
    """``p`` lies on the segment a-b, end points included."""
    return same(p, a) or same(p, b) or _on_segment_interior(p, a, b)


def entities_at(entities: Iterable[Entity], p: Point) -> list[Entity]:
    """Wires and bus bars passing through ``p``."""
    out: list[Entity] = []
    for e in entities:
        if (
            isinstance(e, Wire)
            and any(on_segment(p, a, b) for a, b in segments(e.points))
            or isinstance(e, Busbar)
            and on_segment(p, e.p1, e.p2)
        ):
            out.append(e)
    return out


def remove_vertex(wire: Wire, index: int) -> Wire | None:
    """Wire without point ``index``; corners are replaced so segments stay orthogonal."""
    pts = list(wire.points)
    if len(pts) <= 2:
        return None
    if index in (0, len(pts) - 1):
        del pts[index]
        return replace(wire, points=simplify(pts))
    prev, removed, nxt = pts[index - 1], pts[index], pts[index + 1]
    corners = [Point(nxt.x, prev.y), Point(prev.x, nxt.y)]
    others = [c for c in corners if not same(c, removed)]
    pts[index] = others[0] if others else corners[0]
    new = simplify(pts)
    return replace(wire, points=new) if len(new) >= 2 else None


def junction_points(entities: Iterable[Entity]) -> list[Point]:
    return [p for p, _ in junctions(entities)]


def junction_diameter(lineweight: float) -> float:
    return max(JUNCTION_MIN_DIAMETER, JUNCTION_WEIGHT_FACTOR * lineweight)


def label_text(wire: Wire) -> Text | None:
    """The wire's label as a text entity placed at the longest segment."""
    if not wire.label or len(wire.points) < 2:
        return None
    a, b = max(segments(wire.points), key=lambda s: distance(*s))
    mid = Point((a.x + b.x) / 2, (a.y + b.y) / 2)
    h = wire.label_height
    vertical = abs(a.x - b.x) <= EPS
    if vertical:
        # Rotation 90 reads bottom to top; the glyphs extend towards -x.
        x = mid.x - LABEL_GAP if wire.label_side > 0 else mid.x + LABEL_GAP + h
        position, rotation = Point(x, mid.y), 90
    else:
        y = mid.y - LABEL_GAP if wire.label_side > 0 else mid.y + LABEL_GAP + h
        position, rotation = Point(mid.x, y), 0
    return Text(
        id=f"{wire.id}:label",
        layer=wire.layer,
        color=wire.color,
        position=position,
        text=wire.label,
        height=h,
        rotation=rotation,
        halign="center",
    )


def drag_end(wire: Wire, end: int, p: Point) -> Wire:
    """Move one end (0 = start, -1 = end) keeping all segments orthogonal."""
    pts = list(wire.points)
    if end == 0:
        pts.reverse()
    old = pts[-1]
    if len(pts) == 2:
        start = pts[0]
        horizontal = abs(start.y - old.y) <= EPS and abs(start.x - old.x) > EPS
        pts = [start, *elbow(start, p, horizontal_first=horizontal)]
    else:
        a = pts[-2]
        if abs(a.y - old.y) <= EPS:
            pts[-2] = Point(a.x, p.y)
        elif abs(a.x - old.x) <= EPS:
            pts[-2] = Point(p.x, a.y)
        pts[-1] = p
    if end == 0:
        pts.reverse()
    return replace(wire, points=simplify(pts))


def connection_positions(
    entities: Iterable[Entity], blocks: Mapping[str, BlockDefinition]
) -> dict[tuple[str, str], Point]:
    """World positions of connection points keyed by (entity id, connection name)."""
    result: dict[tuple[str, str], Point] = {}
    for e in entities:
        if isinstance(e, BlockReference):
            for c in world_connections(e, blocks):
                result[(e.id, c.name + "#" + c.id)] = c.position
        elif isinstance(e, ConnectionPoint):
            result[(e.id, "")] = e.position
    return result


def follow_connections(
    all_entities: Iterable[Entity],
    old: Iterable[Entity],
    new: Iterable[Entity],
    blocks: Mapping[str, BlockDefinition],
) -> list[Wire]:
    """Wires (not themselves changed) whose ends sat on moved connection points, updated."""
    old_list, new_list = list(old), list(new)
    changed_ids = {e.id for e in new_list}
    before = connection_positions(old_list, blocks)
    after = connection_positions(new_list, blocks)
    moves = [(before[k], after[k]) for k in before if k in after and not same(before[k], after[k])]
    if not moves:
        return []
    result: list[Wire] = []
    for e in all_entities:
        if not isinstance(e, Wire) or e.id in changed_ids or len(e.points) < 2:
            continue
        targets: dict[int, Point] = {}
        for index in (0, -1):
            for src, dst in moves:
                if same(e.points[index], src):
                    targets[index] = dst
                    break
        if not targets:
            continue
        if len(targets) == 2:
            d0 = (targets[0].x - e.points[0].x, targets[0].y - e.points[0].y)
            d1 = (targets[-1].x - e.points[-1].x, targets[-1].y - e.points[-1].y)
            if math.isclose(d0[0], d1[0], abs_tol=EPS) and math.isclose(d0[1], d1[1], abs_tol=EPS):
                result.append(e.translated(*d0))
                continue
        wire = e
        for index, dst in targets.items():
            wire = drag_end(wire, index, dst)
        result.append(wire)
    return result
