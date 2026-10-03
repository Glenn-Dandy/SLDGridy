"""Right-click menu on a point: connect, separate, remove point, extend."""

from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

from PyQt6.QtCore import QCoreApplication

from sldgridy.commands.entities import (
    AddEntitiesCommand,
    RemoveEntitiesCommand,
    ReplaceEntitiesCommand,
)
from sldgridy.model.entities import JunctionMark, Line, Polyline, Wire, new_id
from sldgridy.model.geometry import Point
from sldgridy.model.wires import entities_at, junction_points, remove_vertex, same
from sldgridy.tools.draw import ExtendTool, LineTool

if TYPE_CHECKING:
    from sldgridy.ui.main_window import MainWindow


def tr(text: str) -> str:
    return QCoreApplication.translate("PointMenu", text)


def point_actions(w: "MainWindow", p: Point) -> list[tuple[str, Callable[[], None]]]:
    """Menu entries for the point ``p`` of the active container."""
    container = w.container
    entities = list(container)
    actions: list[tuple[str, Callable[[], None]]] = []

    def push(command) -> None:
        w.tools.cancel()
        w.push(command)

    marks = [e for e in entities if isinstance(e, JunctionMark) and same(e.position, p)]
    through = entities_at(entities, p)
    automatic = any(
        same(q, p) for q in junction_points(e for e in entities if not isinstance(e, JunctionMark))
    )
    if marks:
        mark = marks[0]
        label = tr("Verbindungspunkt entfernen") if mark.connected else tr("Trennung aufheben")
        actions.append((label, lambda: push(RemoveEntitiesCommand(container, [mark.id], label))))
    elif automatic:
        separate = JunctionMark(id=new_id(), position=p, connected=False)
        actions.append(
            (
                tr("Trennen (hier kein Verbindungspunkt)"),
                lambda: push(AddEntitiesCommand(container, [separate], tr("Trennen"))),
            )
        )
    elif len(through) >= 2:
        connect = JunctionMark(id=new_id(), layer=through[0].layer, position=p, connected=True)
        actions.append(
            (
                tr("Verbinden (Verbindungspunkt setzen)"),
                lambda: push(AddEntitiesCommand(container, [connect], tr("Verbinden"))),
            )
        )

    for e in entities:
        if isinstance(e, Wire | Polyline):
            name = tr("Leitung") if isinstance(e, Wire) else tr("Polylinie")
            last = len(e.points) - 1
            for i, q in enumerate(e.points):
                if not same(q, p):
                    continue
                new = _without_point(e, i)
                if new is not None:
                    actions.append(
                        (
                            tr("Punkt entfernen ({name})").format(name=name),
                            lambda n=new: push(
                                ReplaceEntitiesCommand(container, [n], tr("Punkt entfernen"))
                            ),
                        )
                    )
                closed = isinstance(e, Polyline) and e.closed
                if i in (0, last) and not closed:
                    end = 0 if i == 0 else -1
                    actions.append(
                        (
                            tr("Verlängern ({name})").format(name=name),
                            lambda eid=e.id, end=end: w.start_tool(
                                lambda ctx: ExtendTool(ctx, eid, end)
                            ),
                        )
                    )
        elif isinstance(e, Line) and (same(e.p1, p) or same(e.p2, p)):
            actions.append((tr("Verlängern (Linie)"), lambda: w.start_tool(_line_from(p))))
    return actions


def _without_point(e: Wire | Polyline, index: int) -> Wire | Polyline | None:
    if isinstance(e, Wire):
        return remove_vertex(e, index)
    minimum = 3 if e.closed else 2
    if len(e.points) <= minimum:
        return None
    pts = list(e.points)
    del pts[index]
    return replace(e, points=tuple(pts))


def _line_from(p: Point):
    def factory(ctx):
        tool = LineTool(ctx)
        tool.pick(p)
        return tool

    return factory
