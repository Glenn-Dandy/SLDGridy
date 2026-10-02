"""Sample entities shared by several tests."""

from sldgridy.model.entities import Arc, Circle, Line, Polyline, Rectangle, Text
from sldgridy.model.geometry import Point


def sample_entities():
    return [
        Line(id="l1", p1=Point(0, 0), p2=Point(10, 0)),
        Polyline(id="p1", points=(Point(0, 0), Point(5, 0), Point(5, 5)), closed=True),
        Rectangle(id="r1", p1=Point(10, 10), p2=Point(30, 20), color="#ff0000"),
        Circle(id="c1", center=Point(50, 50), radius=7.5, lineweight=0.5),
        Arc(id="a1", center=Point(0, 0), radius=5, start_angle=0, end_angle=90, linetype="dashed"),
        Text(id="t1", position=Point(1, 2), text="Zeile 1\nZeile 2 äöü", height=5.0, rotation=90),
    ]
