"""Painting of model entities with Qt. Shared by scene items, previews and later printing."""

import math
from dataclasses import dataclass

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QTransform

from sldgridy.model.entities import (
    Arc,
    AttributeDefinition,
    Circle,
    ConnectionPoint,
    Entity,
    Line,
    Polyline,
    Rectangle,
    Text,
)
from sldgridy.model.geometry import Point

TEXT_FONT_FAMILY = "DejaVu Sans"
# Fonts are laid out at this pixel size and scaled down to the text height in mm.
_FONT_LAYOUT_PX = 100
LINE_SPACING = 1.6  # baseline distance as a multiple of the text height

CONNECTION_COLOR = QColor("#c000c0")
CONNECTION_RADIUS = 0.8  # mm
CONNECTION_TICK = 2.0  # mm


# ISO 128-20 patterns in multiples of the line width d: dashed 12d/3d,
# long dash dot 24d/3d/0.5d/3d.
DASH_PATTERNS: dict[str, list[float]] = {
    "dashed": [12.0, 3.0],
    "dashdot": [24.0, 3.0, 0.5, 3.0],
}


@dataclass(frozen=True)
class Style:
    color: QColor
    lineweight: float  # mm
    linetype: str = "continuous"


def qpt(p: Point) -> QPointF:
    return QPointF(p.x, p.y)


def mpt(p: QPointF) -> Point:
    return Point(p.x(), p.y())


def entity_path(e: Entity) -> QPainterPath:
    """Outline path of a non-text entity in scene mm."""
    path = QPainterPath()
    match e:
        case Line():
            path.moveTo(qpt(e.p1))
            path.lineTo(qpt(e.p2))
        case Polyline():
            path.moveTo(qpt(e.points[0]))
            for p in e.points[1:]:
                path.lineTo(qpt(p))
            if e.closed:
                path.closeSubpath()
        case Rectangle():
            path.addRect(QRectF(qpt(e.p1), qpt(e.p2)).normalized())
        case Circle():
            path.addEllipse(qpt(e.center), e.radius, e.radius)
        case Arc():
            r = e.radius
            rect = QRectF(e.center.x - r, e.center.y - r, 2 * r, 2 * r)
            path.arcMoveTo(rect, e.start_angle)
            path.arcTo(rect, e.start_angle, e.sweep)
    return path


# -- text -----------------------------------------------------------------


def _layout_font() -> QFont:
    font = QFont(TEXT_FONT_FAMILY)
    font.setPixelSize(_FONT_LAYOUT_PX)
    return font


def _text_scale(height: float) -> float:
    """Factor from layout pixels to mm so that capital letters are ``height`` mm tall."""
    return height / QFontMetricsF(_layout_font()).capHeight()


def _text_lines(e: Text) -> list[str]:
    return e.text.split("\n")


def _line_widths(e: Text) -> list[float]:
    fm = QFontMetricsF(_layout_font())
    k = _text_scale(e.height)
    return [fm.horizontalAdvance(line) * k for line in _text_lines(e)]


def _x_offset(e: Text, width: float) -> float:
    if e.halign == "center":
        return -width / 2
    if e.halign == "right":
        return -width
    return 0.0


def _y_offset(e: Text) -> float:
    """Shift of the first baseline relative to the anchor."""
    if e.valign == "middle":
        last = (len(_text_lines(e)) - 1) * LINE_SPACING * e.height
        return (e.height - last) / 2
    return 0.0


def text_local_rect(e: Text) -> QRectF:
    """Bounding box in the text's unrotated local frame (origin at the anchor, mm)."""
    fm = QFontMetricsF(_layout_font())
    k = _text_scale(e.height)
    widths = _line_widths(e)
    left = min(_x_offset(e, w) for w in widths)
    right = max(_x_offset(e, w) + w for w in widths)
    dy = _y_offset(e)
    top = dy - fm.ascent() * k
    bottom = dy + (len(widths) - 1) * LINE_SPACING * e.height + fm.descent() * k
    return QRectF(left, top, right - left, bottom - top)


def text_scene_path(e: Text) -> QPainterPath:
    """Bounding box of a text as a polygon in scene coordinates."""
    path = QPainterPath()
    path.addRect(text_local_rect(e))
    return _text_transform(e).map(path)


def _text_transform(e: Text) -> QTransform:
    t = QTransform()
    t.translate(e.position.x, e.position.y)
    t.rotate(-e.rotation)  # positive model rotation is counter-clockwise on screen
    return t


def _paint_text(painter: QPainter, e: Text, color: QColor) -> None:
    painter.save()
    painter.setTransform(_text_transform(e), combine=True)
    k = _text_scale(e.height)
    widths = _line_widths(e)
    dy = _y_offset(e)
    painter.scale(k, k)
    painter.setFont(_layout_font())
    painter.setPen(QPen(color))
    for i, (line, w) in enumerate(zip(_text_lines(e), widths, strict=True)):
        x = _x_offset(e, w) / k
        y = (dy + i * LINE_SPACING * e.height) / k
        painter.drawText(QPointF(x, y), line)
    painter.restore()


# -- painting -------------------------------------------------------------


def make_pen(
    color: QColor, lineweight: float, px_per_mm: float, linetype: str = "continuous"
) -> QPen:
    """Pen with a real mm width that is never thinner than one screen pixel.

    ``px_per_mm`` 0 disables the minimum width (used for output devices).
    """
    width = max(lineweight, 1.0 / px_per_mm) if px_per_mm > 0 else lineweight
    pen = QPen(color, width)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pattern = DASH_PATTERNS.get(linetype)
    if pattern:
        # Qt scales dash patterns by the pen width; keep the mm lengths of the
        # nominal width when the pen was widened for the screen.
        k = lineweight / width
        pen.setDashPattern([max(v * k, 0.01) for v in pattern])
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
    else:
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    return pen


def displayed(e: Entity) -> Entity:
    """Attribute definitions show their tag outside of block references."""
    if isinstance(e, AttributeDefinition):
        return e.as_text(e.tag)
    return e


def connection_marker_path(c: ConnectionPoint) -> QPainterPath:
    path = QPainterPath()
    p = qpt(c.position)
    path.addEllipse(p, CONNECTION_RADIUS, CONNECTION_RADIUS)
    rad = math.radians(c.direction)
    path.moveTo(p)
    path.lineTo(p + QPointF(math.cos(rad), -math.sin(rad)) * CONNECTION_TICK)
    return path


def paint_entity(
    painter: QPainter, e: Entity, style: Style, px_per_mm: float, helpers: bool = True
) -> None:
    """Paint one simple entity. ``helpers`` False leaves out connection markers (output)."""
    if isinstance(e, ConnectionPoint):
        if helpers:
            pen = QPen(CONNECTION_COLOR, 0)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(connection_marker_path(e))
        return
    e = displayed(e)
    if isinstance(e, Text):
        _paint_text(painter, e, style.color)
        return
    painter.setPen(make_pen(style.color, style.lineweight, px_per_mm, style.linetype))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(entity_path(e))


def entity_bounds(e: Entity, lineweight: float) -> QRectF:
    e = displayed(e)
    if isinstance(e, ConnectionPoint):
        r = CONNECTION_TICK
        return QRectF(e.position.x - r, e.position.y - r, 2 * r, 2 * r)
    if isinstance(e, Text):
        return text_scene_path(e).boundingRect()
    half = lineweight / 2
    return entity_path(e).boundingRect().adjusted(-half, -half, half, half)
