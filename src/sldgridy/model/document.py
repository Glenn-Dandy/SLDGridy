"""Top-level drawing document: one model space plus one or more sheet layouts."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from sldgridy.model.container import EntityContainer
from sldgridy.model.entities import Entity
from sldgridy.model.layers import DEFAULT_LAYER, Layer
from sldgridy.model.paper import DEFAULT_FORMAT, DEFAULT_ORIENTATION, Orientation, sheet_size


class ModelSpace(EntityContainer):
    """Unbounded drawing area holding the schematic itself."""


@dataclass
class SheetLayout:
    """A drawing frame: a paper sheet with border, title block and viewports."""

    name: str
    paper: str = DEFAULT_FORMAT
    orientation: Orientation = DEFAULT_ORIENTATION
    entities: EntityContainer = field(default_factory=EntityContainer)

    @property
    def size(self) -> tuple[float, float]:
        return sheet_size(self.paper, self.orientation)


@dataclass
class Document:
    model_space: ModelSpace = field(default_factory=ModelSpace)
    sheets: list[SheetLayout] = field(default_factory=list)
    layers: list[Layer] = field(default_factory=lambda: [Layer(DEFAULT_LAYER)])
    _layer_listeners: list[Callable[[], None]] = field(
        default_factory=list, repr=False, compare=False
    )

    @classmethod
    def new(cls, first_sheet_name: str) -> "Document":
        """Create an empty drawing with one A0 landscape sheet."""
        return cls(sheets=[SheetLayout(name=first_sheet_name)])

    def containers(self) -> Iterator[EntityContainer]:
        """Every entity container of the drawing."""
        yield self.model_space
        for sheet in self.sheets:
            yield sheet.entities

    # -- layers -------------------------------------------------------------

    def subscribe_layers(self, listener: Callable[[], None]) -> None:
        self._layer_listeners.append(listener)

    def unsubscribe_layers(self, listener: Callable[[], None]) -> None:
        self._layer_listeners.remove(listener)

    def _layers_changed(self) -> None:
        for listener in list(self._layer_listeners):
            listener()

    def has_layer(self, name: str) -> bool:
        return any(layer.name == name for layer in self.layers)

    def layer_index(self, name: str) -> int:
        for i, layer in enumerate(self.layers):
            if layer.name == name:
                return i
        raise KeyError(name)

    def insert_layer(self, index: int, layer: Layer) -> None:
        if self.has_layer(layer.name):
            raise ValueError(f"layer {layer.name!r} exists")
        self.layers.insert(index, layer)
        self._layers_changed()

    def remove_layer(self, name: str) -> tuple[int, Layer]:
        if name == DEFAULT_LAYER:
            raise ValueError("layer 0 cannot be removed")
        i = self.layer_index(name)
        layer = self.layers.pop(i)
        self._layers_changed()
        return i, layer

    def set_layer(self, index: int, layer: Layer) -> None:
        """Replace the layer at ``index`` (also used for renaming)."""
        old = self.layers[index]
        if old.name == DEFAULT_LAYER and layer.name != DEFAULT_LAYER:
            raise ValueError("layer 0 cannot be renamed")
        if layer.name != old.name and self.has_layer(layer.name):
            raise ValueError(f"layer {layer.name!r} exists")
        self.layers[index] = layer
        self._layers_changed()

    def layer_in_use(self, name: str) -> bool:
        return any(e.layer == name for c in self.containers() for e in c)

    def layer(self, name: str) -> Layer:
        """Layer by name; unknown names fall back to layer 0."""
        for layer in self.layers:
            if layer.name == name:
                return layer
        return self.layers[0]

    def effective_color(self, entity: Entity) -> str:
        return entity.color or self.layer(entity.layer).color

    def effective_lineweight(self, entity: Entity) -> float:
        if entity.lineweight is not None:
            return entity.lineweight
        return self.layer(entity.layer).lineweight

    def effective_linetype(self, entity: Entity) -> str:
        return entity.linetype or self.layer(entity.layer).linetype
