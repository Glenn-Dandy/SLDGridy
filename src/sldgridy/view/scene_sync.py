"""Keeps the items of a QGraphicsScene in sync with an entity container."""

from PyQt6.QtWidgets import QGraphicsScene

from sldgridy.model.container import EntityContainer
from sldgridy.model.entities import Entity
from sldgridy.view.items import EntityItem, StyleResolver


class SceneSync:
    def __init__(
        self, scene: QGraphicsScene, container: EntityContainer, resolve_style: StyleResolver
    ) -> None:
        self._scene = scene
        self._container = container
        self._resolve_style = resolve_style
        self._items: dict[str, EntityItem] = {}
        self._next_z = 0
        for e in container:
            self._add(e)
        self._restack()
        container.subscribe(self._on_change)

    def detach(self) -> None:
        self._container.unsubscribe(self._on_change)
        for item in self._items.values():
            self._scene.removeItem(item)
        self._items.clear()

    def item(self, entity_id: str) -> EntityItem:
        return self._items[entity_id]

    def _add(self, e: Entity) -> None:
        item = EntityItem(e, self._resolve_style)
        self._items[e.id] = item
        self._scene.addItem(item)

    def _restack(self) -> None:
        for z, e in enumerate(self._container):
            self._items[e.id].setZValue(z)
        self._next_z = len(self._container)

    def _on_change(self, event: str, e: Entity) -> None:
        if event == "added":
            self._add(e)
            if self._container.index_of(e.id) == len(self._container) - 1:
                self._items[e.id].setZValue(self._next_z)
                self._next_z += 1
            else:
                self._restack()
        elif event == "removed":
            item = self._items.pop(e.id)
            self._scene.removeItem(item)
        elif event == "changed":
            self._items[e.id].set_entity(e)
