"""QGraphicsItem wrapper around a model entity."""

from collections.abc import Callable

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPainterPathStroker
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem

from sldgridy.model.entities import ConnectionPoint, Entity, JunctionMark, Text
from sldgridy.view.render import (
    Style,
    connection_marker_path,
    displayed,
    entity_bounds,
    entity_path,
    junction_mark_path,
    paint_entity,
    text_scene_path,
)

SELECTION_COLOR = QColor("#1e88e5")

StyleResolver = Callable[[Entity], Style]
# Resolves compound entities (block references) into simple ones; identity otherwise.
Expander = Callable[[Entity], list[Entity]]


def _identity(e: Entity) -> list[Entity]:
    return [e]


class EntityItem(QGraphicsItem):
    def __init__(
        self, entity: Entity, resolve_style: StyleResolver, expand: Expander = _identity
    ) -> None:
        super().__init__()
        self._resolve_style = resolve_style
        self._expand = expand
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.entity = entity
        self._update_geometry()

    @property
    def entity_id(self) -> str:
        return self.entity.id

    def set_layer_state(self, visible: bool, locked: bool) -> None:
        self.setVisible(visible)
        selectable = visible and not locked
        if not selectable and self.isSelected():
            self.setSelected(False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, selectable)

    def refresh(self) -> None:
        """Style may have changed (layer properties)."""
        self.set_entity(self.entity)

    def set_entity(self, entity: Entity) -> None:
        self.prepareGeometryChange()
        self.entity = entity
        self._update_geometry()
        self.update()

    def _update_geometry(self) -> None:
        self._parts = self._expand(self.entity)
        bounds = QRectF()
        shape = QPainterPath()
        for part in self._parts:
            style = self._resolve_style(part)
            bounds = bounds.united(entity_bounds(part, style.lineweight))
            shown = displayed(part)
            if isinstance(shown, Text):
                shape.addPath(text_scene_path(shown))
            elif isinstance(shown, ConnectionPoint):
                shape.addPath(connection_marker_path(shown))
            elif isinstance(shown, JunctionMark):
                shape.addPath(junction_mark_path(shown))
            else:
                stroker = QPainterPathStroker()
                stroker.setWidth(max(style.lineweight, 0.01))
                shape.addPath(stroker.createStroke(entity_path(shown)))
        self._bounds = bounds
        self._shape = shape

    def boundingRect(self) -> QRectF:
        return self._bounds

    def shape(self) -> QPainterPath:
        return self._shape

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None) -> None:
        lod = option.levelOfDetailFromTransform(painter.worldTransform())
        for part in self._parts:
            style = self._resolve_style(part)
            if self.isSelected():
                style = Style(SELECTION_COLOR, style.lineweight, style.linetype)
            paint_entity(painter, part, style, lod)
