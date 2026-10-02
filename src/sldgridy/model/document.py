"""Top-level drawing document: one model space plus one or more sheet layouts."""

from dataclasses import dataclass, field

from sldgridy.model.paper import DEFAULT_FORMAT, DEFAULT_ORIENTATION, Orientation, sheet_size


@dataclass
class ModelSpace:
    """Unbounded drawing area holding the schematic itself."""

    entities: list = field(default_factory=list)


@dataclass
class SheetLayout:
    """A drawing frame: a paper sheet with border, title block and viewports."""

    name: str
    paper: str = DEFAULT_FORMAT
    orientation: Orientation = DEFAULT_ORIENTATION
    entities: list = field(default_factory=list)

    @property
    def size(self) -> tuple[float, float]:
        return sheet_size(self.paper, self.orientation)


@dataclass
class Document:
    model_space: ModelSpace = field(default_factory=ModelSpace)
    sheets: list[SheetLayout] = field(default_factory=list)

    @classmethod
    def new(cls, first_sheet_name: str) -> "Document":
        """Create an empty drawing with one A0 landscape sheet."""
        return cls(sheets=[SheetLayout(name=first_sheet_name)])
