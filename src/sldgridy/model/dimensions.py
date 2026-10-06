"""Geometry of linear dimensions: extension lines, dimension line, arrows and value.

Pure Python. Proportions follow DIN 406 in spirit: extension lines start a little
off the object and run a little past the dimension line, the value sits above the
dimension line and reads from below or from the right.
"""

import math

from sldgridy.model.entities import Dimension, Entity, Line, Text
from sldgridy.model.geometry import Point

GAP = 0.4  # × text height: space between object and extension line
OVERSHOOT = 0.8  # × text height: extension line past the dimension line
ARROW = 1.0  # × text height: arrow length
ARROW_ANGLE = 15.0  # degrees, half opening
TEXT_GAP = 0.4  # × text height: value above the dimension line
EPS = 1e-9


def _direction(d: Dimension) -> tuple[float, float] | None:
    if d.orientation == "horizontal":
        return 1.0, 0.0
    if d.orientation == "vertical":
        return 0.0, 1.0
    dx, dy = d.p2.x - d.p1.x, d.p2.y - d.p1.y
    length = math.hypot(dx, dy)
    return (dx / length, dy / length) if length > EPS else None


def measured(d: Dimension) -> float:
    u = _direction(d)
    if u is None:
        return 0.0
    return abs((d.p2.x - d.p1.x) * u[0] + (d.p2.y - d.p1.y) * u[1])


def format_value(value: float, decimal_comma: bool = True) -> str:
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return text.replace(".", ",") if decimal_comma else text


def auto_orientation(p1: Point, p2: Point, cursor: Point) -> str:
    """Horizontal or vertical, depending on where the dimension line is dragged."""
    if abs(p1.y - p2.y) <= EPS:
        return "horizontal"
    if abs(p1.x - p2.x) <= EPS:
        return "vertical"
    beside = cursor.x < min(p1.x, p2.x) or cursor.x > max(p1.x, p2.x)
    above_or_below = cursor.y < min(p1.y, p2.y) or cursor.y > max(p1.y, p2.y)
    return "vertical" if beside and not above_or_below else "horizontal"


def dimension_geometry(d: Dimension, decimal_comma: bool = True) -> list[Entity]:
    """Lines and the value text that draw ``d`` (in the dimension's own style)."""
    u = _direction(d)
    if u is None:
        return []
    n = (-u[1], u[0])
    h = d.height
    style = {
        "layer": d.layer,
        "color": d.color,
        "lineweight": d.lineweight,
        "linetype": None,
    }

    def foot(p: Point) -> Point:
        s = (d.position.x - p.x) * n[0] + (d.position.y - p.y) * n[1]
        return Point(p.x + n[0] * s, p.y + n[1] * s)

    a, b = foot(d.p1), foot(d.p2)
    parts: list[Entity] = []
    for i, (p, q) in enumerate(((d.p1, a), (d.p2, b))):
        dx, dy = q.x - p.x, q.y - p.y
        length = math.hypot(dx, dy)
        if length <= EPS:
            continue
        ex, ey = dx / length, dy / length
        start = Point(p.x + ex * GAP * h, p.y + ey * GAP * h)
        end = Point(q.x + ex * OVERSHOOT * h, q.y + ey * OVERSHOOT * h)
        if length > GAP * h:
            parts.append(Line(id=f"{d.id}:ext{i}", p1=start, p2=end, **style))
    parts.append(Line(id=f"{d.id}:line", p1=a, p2=b, **style))
    # Arrows point outwards at both ends of the dimension line.
    span = math.hypot(b.x - a.x, b.y - a.y)
    if span > EPS:
        tx, ty = (b.x - a.x) / span, (b.y - a.y) / span
        for k, (tip, sign) in enumerate(((a, 1.0), (b, -1.0))):
            for j, turn in enumerate((ARROW_ANGLE, -ARROW_ANGLE)):
                r = math.radians(turn)
                wx = sign * (tx * math.cos(r) - ty * math.sin(r))
                wy = sign * (tx * math.sin(r) + ty * math.cos(r))
                wing = Point(tip.x + wx * ARROW * h, tip.y + wy * ARROW * h)
                parts.append(Line(id=f"{d.id}:arrow{k}{j}", p1=tip, p2=wing, **style))
    # Value: readable from below or from the right, above the dimension line.
    angle = math.degrees(math.atan2(-(b.y - a.y), b.x - a.x)) if span > EPS else 0.0
    angle = (angle + 180) % 360 - 180  # -180 < angle <= 180
    if angle > 90 + 1e-6:
        angle -= 180
    elif angle <= -90 + 1e-6:
        angle += 180  # vertical reads from the right: 90°
    r = math.radians(angle)
    up = (-math.sin(r), -math.cos(r))
    mid = Point((a.x + b.x) / 2, (a.y + b.y) / 2)
    value = d.text or format_value(measured(d), decimal_comma)
    parts.append(
        Text(
            id=f"{d.id}:text",
            position=Point(mid.x + up[0] * TEXT_GAP * h, mid.y + up[1] * TEXT_GAP * h),
            text=value,
            height=h,
            rotation=round(angle, 6),
            halign="center",
            **{k: v for k, v in style.items() if k != "linetype"},
        )
    )
    return parts


PAPER_TEXT_HEIGHT = 2.5  # mm on paper


def scale_at(sheets, p: Point) -> float:
    """Scale (paper mm per model mm) of the first viewport that shows ``p``, else 1."""
    for sheet in sheets:
        for vp in sheet.viewports():
            a, b = vp.model_rect()
            if a.x <= p.x <= b.x and a.y <= p.y <= b.y:
                return vp.scale
    return 1.0


def default_height(sheets, p: Point) -> float:
    """Model height of a dimension value that is 2.5 mm high on the sheet showing ``p``."""
    return round(PAPER_TEXT_HEIGHT / scale_at(sheets, p), 6)
