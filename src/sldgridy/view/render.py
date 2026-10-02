"""Painting of model entities with Qt. Shared by scene items, previews and later printing."""

from dataclasses import dataclass

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QTransform

from sldgridy.model.entities import Arc, Circle, Entity, Line, Polyline, Rectangle, Text
from sldgridy.model.geometry import Point

TEXT_FONT_FAMILY = "DejaVu Sans"
# Fonts are laid out at this pixel size and scaled down to the text height in mm.
_FONT_LAYOUT_PX = 100
LINE_SPACING = 1.6  # baseline distance as a multiple of the text height


@dataclass(frozen=True)
class Style:
    color: QColor
    lineweight: float  # mm


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


def text_local_rect(e: Text) -> QRectF:
    """Bounding box in the text's unrotated local frame (origin at first baseline, mm)."""
    fm = QFontMetricsF(_layout_font())
    k = _text_scale(e.height)
    lines = _text_lines(e)
    width = max(fm.horizontalAdvance(line) for line in lines) * k
    top = -fm.ascent() * k
    bottom = (len(lines) - 1) * LINE_SPACING * e.height + fm.descent() * k
    return QRectF(0.0, top, width, bottom - top)


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
    painter.scale(k, k)
    painter.setFont(_layout_font())
    painter.setPen(QPen(color))
    for i, line in enumerate(_text_lines(e)):
        painter.drawText(QPointF(0.0, i * LINE_SPACING * e.height / k), line)
    painter.restore()


# -- painting -------------------------------------------------------------


def make_pen(color: QColor, lineweight: float, px_per_mm: float) -> QPen:
    """Pen with a real mm width that is never thinner than one screen pixel."""
    width = max(lineweight, 1.0 / px_per_mm) if px_per_mm > 0 else lineweight
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def paint_entity(painter: QPainter, e: Entity, style: Style, px_per_mm: float) -> None:
    if isinstance(e, Text):
        _paint_text(painter, e, style.color)
        return
    painter.setPen(make_pen(style.color, style.lineweight, px_per_mm))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(entity_path(e))


def entity_bounds(e: Entity, lineweight: float) -> QRectF:
    if isinstance(e, Text):
        return text_scene_path(e).boundingRect()
    half = lineweight / 2
    return entity_path(e).boundingRect().adjusted(-half, -half, half, half)
