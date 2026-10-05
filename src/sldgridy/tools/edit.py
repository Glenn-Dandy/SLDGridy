"""Tools that modify existing entities."""

from collections.abc import Sequence

from PyQt6.QtCore import QTimer

from sldgridy.commands.entities import AddEntitiesCommand, ReplaceEntitiesCommand
from sldgridy.model.entities import Entity, JunctionMark, new_id
from sldgridy.model.geometry import Point, quarters_towards
from sldgridy.model.grips import grip_kinds, grip_points, move_grip
from sldgridy.model.wires import follow_connections, follow_marks, follow_wires, new_contacts
from sldgridy.tools.base import Tool, tr

MAX_FOLLOW_DEPTH = 20  # wires pulled along by wires, at most this deep


def with_followers(
    ctx, old: list[Entity], new: list[Entity], separate: bool = False
) -> list[Entity]:
    """``new`` plus wires whose ends were attached to moved connection points or to
    moved wires and bus bars (and the junction marks there).

    ``separate`` (when the change is committed): where a pulled-along wire now touches
    another wire by chance, add a separation mark so it does not become connected.
    """
    blocks = getattr(ctx, "block_definitions", {})
    entities = list(ctx.container)
    by_id = {e.id: e for e in entities}
    result = list(new)
    taken = {e.id for e in result}
    # Changes travel along: a wire pulled by a block pulls its branches, and so on.
    step_old, step_new = list(old), list(new)
    for _ in range(MAX_FOLLOW_DEPTH):
        followers = follow_connections(entities, step_old, step_new, blocks)
        followers += follow_wires(entities, step_old, step_new)
        fresh: dict[str, Entity] = {}
        for e in followers:
            if e.id not in taken and e.id not in fresh:
                fresh[e.id] = e
        if not fresh:
            break
        result += fresh.values()
        taken |= fresh.keys()
        step_old = [by_id[i] for i in fresh if i in by_id]
        step_new = list(fresh.values())
    # Connection marks on crossings stay on the crossing of the same two wires.
    result += [m for m in follow_marks(entities, result) if m.id not in taken]
    if separate:
        follower_ids = {e.id for e in result} - {e.id for e in new}
        result += [
            JunctionMark(id=new_id(), position=p, connected=False)
            for p in new_contacts(entities, result, follower_ids)
        ]
    return result


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
                self.ctx,
                self._entities,
                [e.translated(dx, dy) for e in self._entities],
                separate=True,
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
                self.ctx,
                self._entities,
                [e.rotated(self._base, k) for e in self._entities],
                separate=True,
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
            self.ctx,
            self._entities,
            [e.mirrored(self._base, horizontal) for e in self._entities],
            separate=True,
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
        kinds = grip_kinds(self._entity)
        kind = kinds[self._index] if self._index < len(kinds) else "point"
        if kind == "segment":
            return tr("Abschnitt verschieben: neue Lage angeben (loslassen oder klicken)")
        if kind == "label":
            return tr("Beschriftung verschieben: Stelle auf der Leitung angeben")
        return tr("Griff: Neue Position angeben (loslassen oder klicken)")

    def snap_ignored_ids(self) -> set[str]:
        return {self._entity.id}

    def base_point(self) -> Point | None:
        return self._origin

    def pick(self, p: Point) -> None:
        new = move_grip(self._entity, self._index, p)
        if new is not None and new != self._entity:
            changed = with_followers(self.ctx, [self._entity], [new], separate=True)
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
