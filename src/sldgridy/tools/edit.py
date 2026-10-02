"""Tools that modify the current selection."""

from sldgridy.commands.entities import AddEntitiesCommand, ReplaceEntitiesCommand
from sldgridy.model.entities import Entity
from sldgridy.model.geometry import Point, quarters_towards
from sldgridy.tools.base import Tool, tr


class _SelectionTool(Tool):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._base: Point | None = None
        self._entities: list[Entity] = []

    def start(self) -> None:
        container = self.ctx.container
        self._entities = [container.get(i) for i in self.ctx.selected_ids() if i in container]
        if not self._entities:
            self.ctx.message(tr("Zuerst Objekte auswählen"))
            self.done = True

    def base_point(self) -> Point | None:
        return self._base

    def _offset(self) -> tuple[float, float] | None:
        if self._base is None or self.cursor is None:
            return None
        return self.cursor.x - self._base.x, self.cursor.y - self._base.y


class MoveTool(_SelectionTool):
    def prompt(self) -> str:
        if self._base is None:
            return tr("Verschieben: Basispunkt angeben")
        return tr("Verschieben: Zielpunkt angeben")

    def pick(self, p: Point) -> None:
        if self._base is None:
            self._base = p
            return
        dx, dy = p.x - self._base.x, p.y - self._base.y
        if dx or dy:
            moved = [e.translated(dx, dy) for e in self._entities]
            self.ctx.push(ReplaceEntitiesCommand(self.ctx.container, moved, tr("Verschieben")))
        self.done = True

    def preview(self) -> list[Entity]:
        offset = self._offset()
        return [e.translated(*offset) for e in self._entities] if offset else []


class CopyTool(_SelectionTool):
    """Places copies until the user finishes."""

    def prompt(self) -> str:
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

    def prompt(self) -> str:
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
            rotated = [e.rotated(self._base, k) for e in self._entities]
            self.ctx.push(ReplaceEntitiesCommand(self.ctx.container, rotated, tr("Drehen")))
        self.done = True

    def preview(self) -> list[Entity]:
        k = self._quarters(self.cursor)
        if self._base is None:
            return []
        return [e.rotated(self._base, k) for e in self._entities]
