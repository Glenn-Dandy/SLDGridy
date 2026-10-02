"""Frame geometry after DIN EN ISO 5457 and helpers for sheets."""

from sldgridy.model.entities import BlockReference, Entity, Line, Rectangle, Viewport, new_id
from sldgridy.model.geometry import Point

MARGIN_LEFT = 20.0
MARGIN = 10.0
FRAME_WEIGHT = 0.7
CENTER_MARK = 5.0  # length of the centring marks beyond the frame


def frame_corners(width: float, height: float) -> tuple[Point, Point]:
    return Point(MARGIN_LEFT, MARGIN), Point(width - MARGIN, height - MARGIN)


def frame_entities(width: float, height: float) -> list[Entity]:
    """Frame line and centring marks of a sheet."""
    a, b = frame_corners(width, height)
    cx, cy = width / 2, height / 2
    marks = [
        ((cx, a.y - CENTER_MARK), (cx, a.y)),
        ((cx, b.y), (cx, b.y + CENTER_MARK)),
        ((a.x - CENTER_MARK, cy), (a.x, cy)),
        ((b.x, cy), (b.x + CENTER_MARK, cy)),
    ]
    out: list[Entity] = [Rectangle(id="frame", p1=a, p2=b, lineweight=FRAME_WEIGHT)]
    for i, (p, q) in enumerate(marks):
        out.append(Line(id=f"mark{i}", p1=Point(*p), p2=Point(*q), lineweight=FRAME_WEIGHT))
    return out


def title_block_insert(width: float, height: float) -> Point:
    return frame_corners(width, height)[1]


def default_viewport(width: float, height: float) -> Viewport:
    """Viewport filling the drawing area; model (0, 0) at the frame's top left corner."""
    a, b = frame_corners(width, height)
    w, h = b.x - a.x, b.y - a.y
    return Viewport(id=new_id(), p1=a, p2=b, center=Point(w / 2, h / 2), scale=1.0)


def title_block_reference(
    name: str, width: float, height: float, values: dict[str, str]
) -> BlockReference:
    return BlockReference(
        id="title_block",
        name=name,
        insert=title_block_insert(width, height),
        attributes=tuple(sorted(values.items())),
    )
