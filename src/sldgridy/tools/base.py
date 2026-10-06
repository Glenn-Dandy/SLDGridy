"""Tool base class and the context tools operate in."""

from collections.abc import Mapping
from typing import Protocol

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QUndoCommand

from sldgridy.model.blocks import BlockDefinition
from sldgridy.model.container import EntityContainer
from sldgridy.model.entities import Entity
from sldgridy.model.geometry import Point

PREVIEW_ID = "preview"


def tr(text: str) -> str:
    return QCoreApplication.translate("tools", text)


class ToolContext(Protocol):
    @property
    def container(self) -> EntityContainer: ...

    @property
    def current_layer(self) -> str: ...

    @property
    def block_definitions(self) -> Mapping[str, BlockDefinition]: ...

    def push(self, command: QUndoCommand) -> None: ...

    def selected_ids(self) -> list[str]: ...

    def ask_text(self, text: str = "", height: float | None = None) -> tuple[str, float] | None: ...

    def message(self, text: str) -> None: ...


class Tool:
    """State machine fed with already snapped points."""

    def __init__(self, ctx: ToolContext) -> None:
        self.ctx = ctx
        self.done = False
        self.cursor: Point | None = None
        # While True the canvas selects objects instead of picking points.
        self.selecting = False

    def start(self) -> None:
        pass

    def prompt(self) -> str:
        return ""

    def pick(self, p: Point) -> None:
        raise NotImplementedError

    def hover(self, p: Point) -> None:
        self.cursor = p

    def finish(self) -> None:
        """Enter or right click."""
        self.done = True

    def cancel(self) -> None:
        """Escape."""
        self.done = True

    def snap_ignored_ids(self) -> set[str]:
        """Objects the object snap leaves out while this tool runs."""
        return set()

    def base_point(self) -> Point | None:
        """Reference point for ortho mode and the rubber band line."""
        return None

    def dynamic_mode(self) -> tuple[str, Point | None]:
        """Fields for typed values at the cursor: X/Y before a base point, else length
        and angle from it (tools.dynamic_input)."""
        base = self.base_point()
        return ("polar", base) if base is not None else ("xy", None)

    def preview(self) -> list[Entity]:
        return []
