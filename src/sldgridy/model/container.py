"""Ordered entity collection with change notification."""

from collections.abc import Callable, Iterable, Iterator

from sldgridy.model.entities import Entity

# Listener signature: (event, entity) with event in {"added", "removed", "changed"}.
Listener = Callable[[str, Entity], None]


class EntityContainer:
    def __init__(self, entities: Iterable[Entity] = ()) -> None:
        self._items: list[Entity] = []
        self._listeners: list[Listener] = []
        for e in entities:
            self.add(e)

    def __iter__(self) -> Iterator[Entity]:
        return iter(list(self._items))

    def __len__(self) -> int:
        return len(self._items)

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def unsubscribe(self, listener: Listener) -> None:
        self._listeners.remove(listener)

    def _notify(self, event: str, entity: Entity) -> None:
        for listener in list(self._listeners):
            listener(event, entity)

    def index_of(self, entity_id: str) -> int:
        for i, e in enumerate(self._items):
            if e.id == entity_id:
                return i
        raise KeyError(entity_id)

    def get(self, entity_id: str) -> Entity:
        return self._items[self.index_of(entity_id)]

    def __contains__(self, entity_id: object) -> bool:
        return any(e.id == entity_id for e in self._items)

    def add(self, entity: Entity, index: int | None = None) -> None:
        if entity.id in self:
            raise ValueError(f"duplicate entity id {entity.id}")
        if index is None:
            self._items.append(entity)
        else:
            self._items.insert(index, entity)
        self._notify("added", entity)

    def remove(self, entity_id: str) -> tuple[int, Entity]:
        i = self.index_of(entity_id)
        entity = self._items.pop(i)
        self._notify("removed", entity)
        return i, entity

    def replace(self, entity: Entity) -> None:
        self._items[self.index_of(entity.id)] = entity
        self._notify("changed", entity)
