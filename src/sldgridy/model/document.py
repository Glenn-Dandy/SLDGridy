"""Top-level drawing document: one model space plus one or more sheet layouts."""

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

    @classmethod
    def new(cls, first_sheet_name: str) -> "Document":
        """Create an empty drawing with one A0 landscape sheet."""
        return cls(sheets=[SheetLayout(name=first_sheet_name)])

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
