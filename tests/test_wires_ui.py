import pytest
from PyQt6.QtCore import QPointF, QRectF, QSettings, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QLineEdit, QPushButton

from blocks_fixtures import blocks
from sldgridy.model.entities import BlockReference, Busbar, Wire
from sldgridy.model.geometry import Point
from sldgridy.ui.main_window import MainWindow


@pytest.fixture
def window(qapp):
    QSettings().clear()
    w = MainWindow()
    w.resize(1200, 800)
    w.show()
    qapp.processEvents()
    w.canvas.fit_rect(QRectF(-20, -20, 160, 120))
    yield w
    w.undo_stack.setClean()
    w.close()


def vp(window, x, y):
    return window.canvas.map_from_scene_f(QPointF(x, y)).toPoint()


def click(window, x, y, button=Qt.MouseButton.LeftButton):
    QTest.mouseClick(window.canvas.viewport(), button, pos=vp(window, x, y))


def wires(window):
    return [e for e in window.document.model_space if isinstance(e, Wire)]


def test_draw_wire_from_connection_point(window):
    window.document.blocks.update(blocks())
    window.document.model_space.add(BlockReference(id="r", name="Sicherung", insert=Point(50, 20)))
    window.act_snap.setChecked(False)
    window.act_wire.trigger()
    click(window, 50.6, 30.5)  # snaps to connection 2 at (50, 30)
    click(window, 80.3, 60.2)
    click(window, 0, 0, Qt.MouseButton.RightButton)
    (wire,) = wires(window)
    assert wire.points[0] == Point(50, 30)
    assert len(wire.points) == 3


def test_drag_block_pulls_wire(window):
    window.document.blocks.update(blocks())
    ms = window.document.model_space
    ms.add(BlockReference(id="r", name="Sicherung", insert=Point(50, 20)))
    ms.add(Wire(id="w", points=(Point(50, 30), Point(50, 60))))
    window.act_osnap.setChecked(False)
    click(window, 50, 25)  # select the reference via its line
    viewport = window.canvas.viewport()
    QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=vp(window, 50, 25))
    QTest.mouseMove(viewport, vp(window, 55, 25))
    QTest.mouseMove(viewport, vp(window, 60, 25))
    QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=vp(window, 60, 25))
    assert ms.get("r").insert == Point(60, 20)
    assert ms.get("w").points[0] == Point(60, 30)


def test_junction_dots_follow_model(window):
    ms = window.document.model_space
    ms.add(Wire(id="a", points=(Point(0, 0), Point(100, 0))))
    junctions = window.space.extra["junctions"]
    assert junctions._dots == []
    ms.add(Wire(id="b", points=(Point(50, 0), Point(50, 40))))
    assert len(junctions._dots) == 1
    ms.remove("b")
    assert junctions._dots == []


def test_wire_label_in_properties_dock(window):
    window.document.model_space.add(Wire(id="w", points=(Point(0, 0), Point(60, 0))))
    window._sync.item("w").setSelected(True)
    dock = window.properties_dock
    edit = [e for e in dock.widget().findChildren(QLineEdit) if "NYY" in e.placeholderText()][0]
    edit.setText("NYY-J 5x10")
    [b for b in dock.widget().findChildren(QPushButton) if "Beschriftung" in b.text()][0].click()
    assert window.document.model_space.get("w").label == "NYY-J 5x10"
    assert any(p.id == "w:label" for p in window._sync.item("w")._parts)


def test_busbar_tool_in_window(window):
    window.act_busbar.trigger()
    click(window, 0, 50)
    click(window, 100, 52)
    (bar,) = [e for e in window.document.model_space if isinstance(e, Busbar)]
    assert bar.p2 == Point(100, 50)


def test_shipped_library_in_dock(window):
    dock = window.library_dock
    titles = [lib.title for lib in dock.libraries.values() if lib.shipped]
    assert "DIN EN 60617" in titles
    assert dock.list.count() >= 40
