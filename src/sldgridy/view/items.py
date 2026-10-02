"""QGraphicsItem wrapper around a model entity."""

from collections.abc import Callable

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPainterPathStroker
from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem

from sldgridy.model.entities import Entity, Text
from sldgridy.view.render import Style, entity_bounds, entity_path, paint_entity, text_scene_path

SELECTION_COLOR = QColor("#1e88e5")

StyleResolver = Callable[[Entity], Style]


class EntityItem(QGraphicsItem):
    def __init__(self, entity: Entity, resolve_style: StyleResolver) -> None:
        super().__init__()
        self._resolve_style = resolve_style
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
        style = self._resolve_style(self.entity)
        self._bounds = entity_bounds(self.entity, style.lineweight)
        if isinstance(self.entity, Text):
            self._shape = text_scene_path(self.entity)
        else:
            stroker = QPainterPathStroker()
            stroker.setWidth(max(style.lineweight, 0.01))
            self._shape = stroker.createStroke(entity_path(self.entity))

    def boundingRect(self) -> QRectF:
        return self._bounds

    def shape(self) -> QPainterPath:
        return self._shape

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None) -> None:
        style = self._resolve_style(self.entity)
        if self.isSelected():
            style = Style(SELECTION_COLOR, style.lineweight, style.linetype)
        lod = option.levelOfDetailFromTransform(painter.worldTransform())
        paint_entity(painter, self.entity, style, lod)
