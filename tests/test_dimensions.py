import pytest

from sldgridy.model.dimensions import (
    auto_orientation,
    dimension_geometry,
    format_value,
    measured,
)
from sldgridy.model.entities import Dimension, Line, Text
from sldgridy.model.geometry import Point


def dim(p1, p2, pos, orientation="aligned", **kw):
    return Dimension(
        id="d", p1=Point(*p1), p2=Point(*p2), position=Point(*pos), orientation=orientation, **kw
    )


def test_measured_values():
    assert measured(dim((0, 0), (30, 40), (0, 0))) == pytest.approx(50)
    assert measured(dim((0, 0), (30, 40), (0, -10), "horizontal")) == pytest.approx(30)
    assert measured(dim((0, 0), (30, 40), (-10, 0), "vertical")) == pytest.approx(40)
    assert format_value(1250.0) == "1250"
    assert format_value(12.5) == "12,5" and format_value(12.5, decimal_comma=False) == "12.5"


def test_horizontal_dimension_above_two_points():
    parts = dimension_geometry(dim((0, 0), (100, 20), (50, -15), "horizontal"))
    line = next(p for p in parts if p.id == "d:line")
    assert line.p1 == Point(0, -15) and line.p2 == Point(100, -15)
    text = next(p for p in parts if isinstance(p, Text))
    assert text.text == "100" and text.rotation == 0
    assert text.position.y < -15  # above the dimension line
    exts = [p for p in parts if p.id.startswith("d:ext")]
    assert len(exts) == 2
    # Extension lines run a little past the dimension line (upwards here).
    assert min(e.p2.y for e in exts) < -15
    arrows = [p for p in parts if p.id.startswith("d:arrow")]
    assert len(arrows) == 4 and all(isinstance(a, Line) for a in arrows)


def test_vertical_value_reads_from_the_right_and_override_text():
    parts = dimension_geometry(dim((0, 0), (0, 80), (-20, 40), "vertical", text="ca. 8 m"))
    text = next(p for p in parts if isinstance(p, Text))
    assert text.text == "ca. 8 m" and text.rotation == 90


def test_auto_orientation_follows_the_dragged_side():
    p1, p2 = Point(0, 0), Point(100, 50)
    assert auto_orientation(p1, p2, Point(50, -20)) == "horizontal"  # above
    assert auto_orientation(p1, p2, Point(130, 25)) == "vertical"  # right of both
    assert auto_orientation(Point(0, 0), Point(0, 50), Point(50, 50)) == "vertical"


def test_rotating_a_dimension_swaps_its_orientation():
    d = dim((0, 0), (100, 0), (50, -10), "horizontal")
    turned = d.rotated(Point(0, 0), 1)
    assert turned.orientation == "vertical"
    assert measured(turned) == pytest.approx(100)


def test_dimension_height_follows_the_viewport_scale():
    from dataclasses import replace

    from sldgridy.model.dimensions import default_height
    from sldgridy.model.document import Document

    doc = Document.new("Blatt 1")
    sheet = doc.sheets[0]
    vp = sheet.viewports()[0]
    sheet.entities.replace(replace(vp, scale=0.02))  # 1:50
    a, b = sheet.entities.get(vp.id).model_rect()
    inside = Point((a.x + b.x) / 2, (a.y + b.y) / 2)
    assert default_height(doc.sheets, inside) == pytest.approx(125)  # 2.5 mm on paper
    assert default_height(doc.sheets, Point(b.x + 1e6, 0)) == pytest.approx(2.5)
