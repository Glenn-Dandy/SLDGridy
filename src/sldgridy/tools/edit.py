"""Tools that modify existing entities."""

from collections.abc import Sequence

from PyQt6.QtCore import QTimer

from sldgridy.commands.entities import AddEntitiesCommand, ReplaceEntitiesCommand
from sldgridy.model.entities import Entity
from sldgridy.model.geometry import Point, quarters_towards
from sldgridy.model.grips import grip_points, move_grip
from sldgridy.model.wires import follow_connections
from sldgridy.tools.base import Tool, tr


def with_followers(ctx, old: list[Entity], new: list[Entity]) -> list[Entity]:
    """``new`` plus wires whose ends were attached to moved connection points."""
    blocks = getattr(ctx, "block_definitions", {})
    return new + follow_connections(list(ctx.container), old, new, blocks)


class _SelectionTool(Tool):
    """Works on the current selection; asks for one first if nothing is selected."""

    @property
    def name(self) -> str:
        return ""

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._base: Point | None = None
        self._entities: list[Entity] = []

    def start(self) -> None:
        if not self._take_selection():
            self.selecting = True

    def _take_selection(self) -> bool:
        container = self.ctx.container
        self._entities = [container.get(i) for i in self.ctx.selected_ids() if i in container]
        return bool(self._entities)

    def finish(self) -> None:
        if self.selecting:
            if self._take_selection():
                self.selecting = False
            else:
                self.done = True
            return
        self.done = True

    def prompt(self) -> str:
        if self.selecting:
            return tr("{name}: Objekte wählen, Enter bestätigt").format(name=self.name)
        return self._point_prompt()

    def _point_prompt(self) -> str:
        return ""

    def base_point(self) -> Point | None:
        return self._base

    def _offset(self) -> tuple[float, float] | None:
        if self._base is None or self.cursor is None:
            return None
        return self.cursor.x - self._base.x, self.cursor.y - self._base.y


class MoveTool(_SelectionTool):
    @property
    def name(self) -> str:
        return tr("Verschieben")

    def _point_prompt(self) -> str:
        if self._base is None:
            return tr("Verschieben: Basispunkt angeben")
        return tr("Verschieben: Zielpunkt angeben")

    def pick(self, p: Point) -> None:
        if self._base is None:
            self._base = p
            return
        dx, dy = p.x - self._base.x, p.y - self._base.y
        if dx or dy:
            moved = with_followers(
                self.ctx, self._entities, [e.translated(dx, dy) for e in self._entities]
            )
            self.ctx.push(ReplaceEntitiesCommand(self.ctx.container, moved, tr("Verschieben")))
        self.done = True

    def preview(self) -> list[Entity]:
        offset = self._offset()
        if not offset:
            return []
        return with_followers(
            self.ctx, self._entities, [e.translated(*offset) for e in self._entities]
        )


class CopyTool(_SelectionTool):
    """Places copies until the user finishes."""

    @property
    def name(self) -> str:
        return tr("Kopieren")

    def _point_prompt(self) -> str:
        if self._base is None:
            return tr("Kopieren: Basispunkt angeben")
        return tr("Kopieren: Zielpunkt angeben (Enter beendet)")

    def pick(self, p: Point) -> None:
        if self._base is None:
            self._base = p
            return
        dx, dy = p.x - self._base.x, p.y - self._base.y
        if dx or dy:
            copies = [e.translated(dx, dy).with_new_id() for e in self._entities]
            self.ctx.push(AddEntitiesCommand(self.ctx.container, copies, tr("Kopieren")))

    def preview(self) -> list[Entity]:
        offset = self._offset()
        return [e.translated(*offset) for e in self._entities] if offset else []


class RotateTool(_SelectionTool):
    """Rotate in 90 degree steps towards the cursor direction."""

    @property
    def name(self) -> str:
        return tr("Drehen")

    def _point_prompt(self) -> str:
        if self._base is None:
            return tr("Drehen: Drehpunkt angeben")
        return tr("Drehen: Richtung angeben (90°-Schritte)")

    def _quarters(self, p: Point | None) -> int:
        if self._base is None or p is None or p == self._base:
            return 0
        return quarters_towards(self._base, p)

    def pick(self, p: Point) -> None:
        if self._base is None:
            self._base = p
            return
        k = self._quarters(p)
        if k:
            rotated = with_followers(
                self.ctx, self._entities, [e.rotated(self._base, k) for e in self._entities]
            )
            self.ctx.push(ReplaceEntitiesCommand(self.ctx.container, rotated, tr("Drehen")))
        self.done = True

    def preview(self) -> list[Entity]:
        if self._base is None:
            return []
        k = self._quarters(self.cursor)
        return with_followers(
            self.ctx, self._entities, [e.rotated(self._base, k) for e in self._entities]
        )


class MirrorTool(_SelectionTool):
    """Mirror in place at a horizontal or vertical axis."""

    @property
    def name(self) -> str:
        return tr("Spiegeln")

    def _point_prompt(self) -> str:
        if self._base is None:
            return tr("Spiegeln: Punkt auf der Spiegelachse angeben")
        return tr("Spiegeln: Richtung der Achse angeben (waagerecht oder senkrecht)")

    def _horizontal(self, p: Point) -> bool:
        assert self._base is not None
        return abs(p.x - self._base.x) >= abs(p.y - self._base.y)

    def pick(self, p: Point) -> None:
        if self._base is None:
            self._base = p
            return
        if p == self._base:
            return
        horizontal = self._horizontal(p)
        mirrored = with_followers(
            self.ctx, self._entities, [e.mirrored(self._base, horizontal) for e in self._entities]
        )
        self.ctx.push(ReplaceEntitiesCommand(self.ctx.container, mirrored, tr("Spiegeln")))
        self.done = True

    def preview(self) -> list[Entity]:
        if self._base is None or self.cursor is None or self.cursor == self._base:
            return []
        horizontal = self._horizontal(self.cursor)
        return with_followers(
            self.ctx, self._entities, [e.mirrored(self._base, horizontal) for e in self._entities]
        )


class PasteTool(Tool):
    """Insert entities from the clipboard relative to their base point."""

    def __init__(self, ctx, entities: Sequence[Entity], base: Point) -> None:
        super().__init__(ctx)
        self._entities = list(entities)
        self._base = base

    def prompt(self) -> str:
        return tr("Einfügen: Einfügepunkt angeben")

    def _placed(self, p: Point) -> list[Entity]:
        dx, dy = p.x - self._base.x, p.y - self._base.y
        return [e.translated(dx, dy) for e in self._entities]

    def pick(self, p: Point) -> None:
        entities = [e.with_new_id() for e in self._placed(p)]
        self.ctx.push(AddEntitiesCommand(self.ctx.container, entities, tr("Einfügen")))
        self.done = True

    def preview(self) -> list[Entity]:
        return self._placed(self.cursor) if self.cursor else []


class GripEditTool(Tool):
    """Drag one grip of one entity."""

    def __init__(self, ctx, entity_id: str, index: int) -> None:
        super().__init__(ctx)
        self._entity = ctx.container.get(entity_id)
        self._index = index
        self._origin = grip_points(self._entity)[index]

    def prompt(self) -> str:
        return tr("Griff: Neue Position angeben")

    def base_point(self) -> Point | None:
        return self._origin

    def pick(self, p: Point) -> None:
        new = move_grip(self._entity, self._index, p)
        if new is not None and new != self._entity:
            changed = with_followers(self.ctx, [self._entity], [new])
            self.ctx.push(ReplaceEntitiesCommand(self.ctx.container, changed, tr("Griff ziehen")))
        self.done = True

    def preview(self) -> list[Entity]:
        if self.cursor is None:
            return []
        new = move_grip(self._entity, self._index, self.cursor)
        return with_followers(self.ctx, [self._entity], [new]) if new is not None else []


class SelectObjectsTool(_SelectionTool):
    """Only asks for objects; Enter hands the selected ids to ``on_selected``."""

    def __init__(self, ctx, title: str, on_selected) -> None:
        super().__init__(ctx)
        self._title = title
        self._on_selected = on_selected

    @property
    def name(self) -> str:
        return self._title

    def start(self) -> None:
        self.selecting = True

    def finish(self) -> None:
        ids = self.ctx.selected_ids() if self.selecting else []
        self.done = True
        if ids:
            # Run after the current mouse/key event: the callback may open dialogs
            # and start the next tool.
            QTimer.singleShot(0, lambda: self._on_selected(ids))

    def pick(self, p: Point) -> None:
        pass
