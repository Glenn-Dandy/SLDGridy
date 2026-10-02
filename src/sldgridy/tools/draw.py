"""Tools that create new entities."""

from sldgridy.commands.entities import AddEntitiesCommand
from sldgridy.model.entities import Arc, Circle, Entity, Line, Polyline, Rectangle, Text, new_id
from sldgridy.model.geometry import Point, angle_deg, distance
from sldgridy.tools.base import PREVIEW_ID, Tool, tr


class _DrawTool(Tool):
    def _add(self, entity: Entity, text: str) -> None:
        self.ctx.push(AddEntitiesCommand(self.ctx.container, [entity], text))


class LineTool(_DrawTool):
    """Chained line segments, each one a separate entity."""

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._start: Point | None = None

    def prompt(self) -> str:
        if self._start is None:
            return tr("Linie: Ersten Punkt angeben")
        return tr("Linie: Nächsten Punkt angeben (Enter beendet)")

    def pick(self, p: Point) -> None:
        if self._start is not None and p != self._start:
            line = Line(id=new_id(), layer=self.ctx.current_layer, p1=self._start, p2=p)
            self._add(line, tr("Linie zeichnen"))
        self._start = p

    def base_point(self) -> Point | None:
        return self._start

    def preview(self) -> list[Entity]:
        if self._start is None or self.cursor is None:
            return []
        return [Line(id=PREVIEW_ID, layer=self.ctx.current_layer, p1=self._start, p2=self.cursor)]


class PolylineTool(_DrawTool):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._points: list[Point] = []

    def prompt(self) -> str:
        if not self._points:
            return tr("Polylinie: Startpunkt angeben")
        return tr("Polylinie: Nächsten Punkt angeben (Enter beendet, Startpunkt schließt)")

    def pick(self, p: Point) -> None:
        if self._points and p == self._points[-1]:
            return
        if len(self._points) >= 3 and p == self._points[0]:
            self._commit(closed=True)
            return
        self._points.append(p)

    def finish(self) -> None:
        if len(self._points) >= 2:
            self._commit(closed=False)
        self.done = True

    def _commit(self, closed: bool) -> None:
        poly = Polyline(
            id=new_id(), layer=self.ctx.current_layer, points=tuple(self._points), closed=closed
        )
        self._add(poly, tr("Polylinie zeichnen"))
        self.done = True

    def base_point(self) -> Point | None:
        return self._points[-1] if self._points else None

    def preview(self) -> list[Entity]:
        if not self._points or self.cursor is None:
            return []
        pts = (*self._points, self.cursor)
        return [Polyline(id=PREVIEW_ID, layer=self.ctx.current_layer, points=pts)]


class RectangleTool(_DrawTool):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._corner: Point | None = None

    def prompt(self) -> str:
        if self._corner is None:
            return tr("Rechteck: Erste Ecke angeben")
        return tr("Rechteck: Gegenüberliegende Ecke angeben")

    def pick(self, p: Point) -> None:
        if self._corner is None:
            self._corner = p
            return
        if p.x == self._corner.x or p.y == self._corner.y:
            return
        rect = Rectangle(id=new_id(), layer=self.ctx.current_layer, p1=self._corner, p2=p)
        self._add(rect, tr("Rechteck zeichnen"))
        self.done = True

    def preview(self) -> list[Entity]:
        if self._corner is None or self.cursor is None:
            return []
        return [
            Rectangle(id=PREVIEW_ID, layer=self.ctx.current_layer, p1=self._corner, p2=self.cursor)
        ]


class CircleTool(_DrawTool):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._center: Point | None = None

    def prompt(self) -> str:
        if self._center is None:
            return tr("Kreis: Mittelpunkt angeben")
        return tr("Kreis: Punkt auf dem Umfang angeben")

    def pick(self, p: Point) -> None:
        if self._center is None:
            self._center = p
            return
        r = distance(self._center, p)
        if r <= 0:
            return
        circle = Circle(id=new_id(), layer=self.ctx.current_layer, center=self._center, radius=r)
        self._add(circle, tr("Kreis zeichnen"))
        self.done = True

    def base_point(self) -> Point | None:
        return self._center

    def preview(self) -> list[Entity]:
        if self._center is None or self.cursor is None:
            return []
        r = distance(self._center, self.cursor)
        if r <= 0:
            return []
        return [Circle(id=PREVIEW_ID, layer=self.ctx.current_layer, center=self._center, radius=r)]


class ArcTool(_DrawTool):
    """Arc by center, start point and end point, counter-clockwise."""

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._center: Point | None = None
        self._start: Point | None = None

    def prompt(self) -> str:
        if self._center is None:
            return tr("Bogen: Mittelpunkt angeben")
        if self._start is None:
            return tr("Bogen: Startpunkt angeben")
        return tr("Bogen: Endpunkt angeben (gegen den Uhrzeigersinn)")

    def _arc(self, end: Point, entity_id: str) -> Arc | None:
        assert self._center is not None and self._start is not None
        r = distance(self._center, self._start)
        a0 = angle_deg(self._center, self._start)
        a1 = angle_deg(self._center, end)
        if r <= 0 or end == self._center or abs(a1 - a0) < 1e-9:
            return None
        return Arc(
            id=entity_id,
            layer=self.ctx.current_layer,
            center=self._center,
            radius=r,
            start_angle=a0,
            end_angle=a1,
        )

    def pick(self, p: Point) -> None:
        if self._center is None:
            self._center = p
        elif self._start is None:
            if p != self._center:
                self._start = p
        else:
            arc = self._arc(p, new_id())
            if arc is not None:
                self._add(arc, tr("Bogen zeichnen"))
                self.done = True

    def base_point(self) -> Point | None:
        return self._center

    def preview(self) -> list[Entity]:
        if self._center is None or self.cursor is None:
            return []
        if self._start is None:
            return [
                Line(id=PREVIEW_ID, layer=self.ctx.current_layer, p1=self._center, p2=self.cursor)
            ]
        arc = self._arc(self.cursor, PREVIEW_ID)
        return [arc] if arc else []


class TextTool(_DrawTool):
    def prompt(self) -> str:
        return tr("Text: Einfügepunkt angeben")

    def pick(self, p: Point) -> None:
        result = self.ctx.ask_text()
        if result is not None:
            content, height = result
            if content.strip():
                text = Text(
                    id=new_id(),
                    layer=self.ctx.current_layer,
                    position=p,
                    text=content,
                    height=height,
                )
                self._add(text, tr("Text einfügen"))
        self.done = True
