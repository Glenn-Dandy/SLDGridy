"""Drawing entities. Immutable: edits create new instances with the same id."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Self

from sldgridy.model.geometry import Point, mirror_point, rotate_quarter
from sldgridy.model.layers import DEFAULT_LAYER

TEXT_HEIGHTS = (2.5, 3.5, 5.0, 7.0)
DEFAULT_TEXT_HEIGHT = 3.5


def new_id() -> str:
    return uuid.uuid4().hex


@dataclass(frozen=True, kw_only=True)
class Entity:
    id: str
    layer: str = DEFAULT_LAYER
    # None means "by layer".
    color: str | None = None
    lineweight: float | None = None
    linetype: str | None = None

    def with_new_id(self) -> Self:
        return replace(self, id=new_id())

    def translated(self, dx: float, dy: float) -> Self:
        return self._mapped(lambda p: p.translated(dx, dy), 0)

    def rotated(self, center: Point, quarters: int) -> Self:
        return self._mapped(lambda p: rotate_quarter(p, center, quarters), quarters % 4)

    def mirrored(self, axis: Point, horizontal: bool) -> Self:
        """Mirror at the horizontal (``horizontal``) or vertical line through ``axis``.

        Texts keep their reading direction; only the insertion point moves.
        """
        return self._mapped(lambda p: mirror_point(p, axis, horizontal), 0)

    def _mapped(self, fn: Callable[[Point], Point], quarters: int) -> Self:
        raise NotImplementedError


@dataclass(frozen=True, kw_only=True)
class Line(Entity):
    p1: Point
    p2: Point

    def _mapped(self, fn, quarters):
        return replace(self, p1=fn(self.p1), p2=fn(self.p2))


@dataclass(frozen=True, kw_only=True)
class Polyline(Entity):
    points: tuple[Point, ...]
    closed: bool = False

    def _mapped(self, fn, quarters):
        return replace(self, points=tuple(fn(p) for p in self.points))


@dataclass(frozen=True, kw_only=True)
class Rectangle(Entity):
    """Axis-aligned rectangle given by two opposite corners."""

    p1: Point
    p2: Point

    def _mapped(self, fn, quarters):
        return replace(self, p1=fn(self.p1), p2=fn(self.p2))


@dataclass(frozen=True, kw_only=True)
class Circle(Entity):
    center: Point
    radius: float

    def _mapped(self, fn, quarters):
        return replace(self, center=fn(self.center))


@dataclass(frozen=True, kw_only=True)
class Arc(Entity):
    """Arc from ``start_angle`` counter-clockwise to ``end_angle`` (degrees)."""

    center: Point
    radius: float
    start_angle: float
    end_angle: float

    def _mapped(self, fn, quarters):
        return replace(
            self,
            center=fn(self.center),
            start_angle=(self.start_angle + 90 * quarters) % 360,
            end_angle=(self.end_angle + 90 * quarters) % 360,
        )

    def mirrored(self, axis: Point, horizontal: bool) -> Self:
        # Mirroring reverses the direction, so start and end swap.
        def flip(a: float) -> float:
            return (-a if horizontal else 180.0 - a) % 360

        return replace(
            self,
            center=mirror_point(self.center, axis, horizontal),
            start_angle=flip(self.end_angle),
            end_angle=flip(self.start_angle),
        )

    @property
    def sweep(self) -> float:
        s = (self.end_angle - self.start_angle) % 360
        return s if s else 360.0


@dataclass(frozen=True, kw_only=True)
class Text(Entity):
    """Single or multi-line text. ``position`` is the left end of the first baseline."""

    position: Point
    text: str
    height: float = DEFAULT_TEXT_HEIGHT
    rotation: int = 0

    def _mapped(self, fn, quarters):
        return replace(
            self, position=fn(self.position), rotation=(self.rotation + 90 * quarters) % 360
        )
