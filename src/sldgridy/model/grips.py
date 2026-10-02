"""Grip points of entities and how dragging a grip changes the entity."""

from dataclasses import replace

from sldgridy.model.entities import (
    Arc,
    AttributeDefinition,
    BlockReference,
    Busbar,
    Circle,
    ConnectionPoint,
    Entity,
    Line,
    Polyline,
    Rectangle,
    Text,
    Wire,
)
from sldgridy.model.geometry import Point, angle_deg
from sldgridy.model.primitives import arc_endpoints, rect_corners


def grip_points(e: Entity) -> list[Point]:
    match e:
        case Line() | Busbar():
            return [e.p1, e.p2]
        case Wire():
            return [e.points[0], e.points[-1]]
        case BlockReference():
            return [e.insert]
        case AttributeDefinition() | ConnectionPoint():
            return [e.position]
        case Polyline():
            return list(e.points)
        case Rectangle():
            return rect_corners(e)
        case Circle():
            return [e.center]
        case Arc():
            return [*arc_endpoints(e), e.center]
        case Text():
            return [e.position]
    return []


def move_grip(e: Entity, index: int, p: Point) -> Entity | None:
    """Entity with grip ``index`` moved to ``p``, or None if the result is degenerate."""
    match e:
        case Line() | Busbar():
            new = replace(e, p1=p) if index == 0 else replace(e, p2=p)
            return new if new.p1 != new.p2 else None
        case Wire():
            from sldgridy.model.wires import drag_end

            new = drag_end(e, 0 if index == 0 else -1, p)
            return new if len(new.points) >= 2 else None
        case Polyline():
            pts = list(e.points)
            pts[index] = p
            return replace(e, points=tuple(pts))
        case Rectangle():
            opposite = rect_corners(e)[(index + 2) % 4]
            if p.x == opposite.x or p.y == opposite.y:
                return None
            return replace(e, p1=opposite, p2=p)
        case Arc():
            if index == 2:
                return e.translated(p.x - e.center.x, p.y - e.center.y)
            if p == e.center:
                return None
            a = angle_deg(e.center, p)
            new = replace(e, start_angle=a) if index == 0 else replace(e, end_angle=a)
            return new if abs(new.end_angle - new.start_angle) > 1e-9 else None
    # Circle, Text, references, attributes and connections: the grip moves the entity.
    ref = grip_points(e)[index]
    return e.translated(p.x - ref.x, p.y - ref.y)
