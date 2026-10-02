import pytest
from PyQt6.QtCore import QPointF, QRectF, QSettings, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtTest import QTest

from factories import sample_entities
from sldgridy.model.entities import Line, Text
from sldgridy.model.geometry import Point
from sldgridy.model.layers import Layer
from sldgridy.ui.main_window import MainWindow
from sldgridy.ui.styles import BY_LAYER
from sldgridy.view.render import make_pen


@pytest.fixture
def window(qapp):
    QSettings().clear()
    w = MainWindow()
    w.resize(1200, 800)
    w.show()
    qapp.processEvents()
    w.canvas.fit_rect(QRectF(0, 0, 100, 100))
    yield w
    w.undo_stack.setClean()
    w.close()


def vp(window, x, y):
    return window.canvas.map_from_scene_f(QPointF(x, y)).toPoint()


def click(window, x, y, button=Qt.MouseButton.LeftButton):
    QTest.mouseClick(window.canvas.viewport(), button, pos=vp(window, x, y))


def drag(window, a, b):
    viewport = window.canvas.viewport()
    QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=vp(window, *a))
    QTest.mouseMove(viewport, vp(window, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    QTest.mouseMove(viewport, vp(window, *b))
    QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=vp(window, *b))


def add_line(window, id_="a", y=50.0, layer="0"):
    line = Line(id=id_, layer=layer, p1=Point(20, y), p2=Point(80, y))
    window.document.model_space.add(line)
    return line


def test_drag_selected_object_moves_it(window):
    window.act_osnap.setChecked(False)
    add_line(window)
    click(window, 50, 50)
    drag(window, (50, 50), (50, 70))
    line = window.document.model_space.get("a")
    assert (line.p1, line.p2) == (Point(20, 70), Point(80, 70))
    window.act_undo.trigger()
    assert window.document.model_space.get("a").p1 == Point(20, 50)


def test_drag_unselected_object_selects_and_moves(window):
    window.act_osnap.setChecked(False)
    add_line(window)
    drag(window, (50, 50), (60, 50))
    assert window.document.model_space.get("a").p1 == Point(30, 50)


def test_move_command_asks_for_selection(window):
    window.act_osnap.setChecked(False)
    add_line(window)
    window.act_move.trigger()
    assert window.tools.selecting()
    click(window, 50, 50)
    QTest.keyClick(window.canvas, Qt.Key.Key_Return)
    assert not window.tools.selecting()
    click(window, 50, 50)
    click(window, 50, 30)
    assert window.document.model_space.get("a").p1 == Point(20, 30)


def test_grip_drag_stretches_line(window):
    window.act_osnap.setChecked(False)
    add_line(window)
    click(window, 50, 50)
    click(window, 80, 50)  # grip at the end point
    assert window.tools.active is not None
    click(window, 90, 60)
    line = window.document.model_space.get("a")
    assert (line.p1, line.p2) == (Point(20, 50), Point(90, 60))


def test_object_snap_to_endpoint(window):
    window.act_snap.setChecked(False)
    add_line(window)
    window.act_line.trigger()
    click(window, 80.6, 50.4)
    click(window, 80.6, 90)
    window.tools.cancel()
    new = [e for e in window.document.model_space if e.id != "a"][0]
    assert new.p1 == Point(80, 50)


def test_typed_coordinates_draw_line(window):
    window.act_line.trigger()
    window.command_line.submitted.emit("10,10")
    window.command_line.submitted.emit("@30,0")
    window.command_line.submitted.emit("")
    (line,) = list(window.document.model_space)
    assert (line.p1, line.p2) == (Point(10, 10), Point(40, 10))
    assert window.tools.active is None


def test_typing_on_canvas_goes_to_command_line(window):
    window.act_line.trigger()
    window.canvas.setFocus()
    QTest.keyClicks(window.canvas, "5")
    assert window.command_line.edit.text() == "5"


def test_hidden_and_locked_layers(window):
    window.document.insert_layer(1, Layer("Kabel"))
    add_line(window, "k", layer="Kabel")
    item = window._sync.item("k")
    layer = window.document.layer("Kabel")
    from dataclasses import replace

    from sldgridy.commands.layers import ChangeLayerCommand

    window.push(ChangeLayerCommand(window.document, "Kabel", replace(layer, locked=True), "x"))
    click(window, 50, 50)
    assert window.selected_ids() == []
    window.push(
        ChangeLayerCommand(
            window.document, "Kabel", replace(layer, locked=False, visible=False), "x"
        )
    )
    assert not item.isVisible()
    window.act_undo.trigger()
    assert item.isVisible()


def test_layer_color_drives_rendering(window):
    window.document.insert_layer(1, Layer("Kabel", color="#0000ff", lineweight=0.5))
    line = add_line(window, "k", layer="Kabel")
    style = window._resolve_style(line)
    assert style.color == QColor("#0000ff") and style.lineweight == 0.5


def test_properties_dock_changes_selection(window):
    for e in sample_entities():
        window.document.model_space.add(e)
    window.act_select_all.trigger()
    dock = window.properties_dock
    assert "6 Objekte" in dock.lbl_selection.text()
    dock.cmb_weight.setCurrentIndex(dock.cmb_weight.findData(0.7))
    dock.cmb_weight.activated.emit(dock.cmb_weight.currentIndex())
    assert all(e.lineweight == 0.7 for e in window.document.model_space)
    window.act_undo.trigger()
    assert window.document.model_space.get("l1").lineweight is None
    dock.refresh()
    dock.cmb_color.setCurrentIndex(dock.cmb_color.findData(BY_LAYER))
    dock.cmb_color.activated.emit(dock.cmb_color.currentIndex())
    assert all(e.color is None for e in window.document.model_space)


def test_properties_dock_edits_text(window):
    window.document.model_space.add(Text(id="t", position=Point(10, 10), text="alt"))
    window._sync.item("t").setSelected(True)
    dock = window.properties_dock
    dock.txt_text.setPlainText("neu")
    dock.btn_apply_text.click()
    assert window.document.model_space.get("t").text == "neu"


def test_layers_dock_add_rename_current_delete(window):
    dock = window.layers_dock
    dock.add_layer()
    assert window.document.layers[-1].name == "Ebene 1"
    row = len(window.document.layers) - 1
    dock.table.item(row, 1).setText("Kabel")
    assert window.document.layers[-1].name == "Kabel"
    dock.table.selectRow(row)
    dock.btn_current.click()
    assert window.current_layer == "Kabel"
    window.act_line.trigger()
    click(window, 10, 10)
    click(window, 30, 10)
    window.tools.cancel()
    (line,) = list(window.document.model_space)
    assert line.layer == "Kabel"
    dock.delete_selected()  # current and in use: refused
    assert window.document.has_layer("Kabel")


def test_clipboard_copy_and_paste(window):
    add_line(window)
    window.act_select_all.trigger()
    window.act_copy_clip.trigger()
    window.act_paste.trigger()
    click(window, 20, 80)
    lines = list(window.document.model_space)
    assert len(lines) == 2
    assert lines[1].p1.y == pytest.approx(80, abs=0.5)


def test_cut_removes_and_paste_restores(window):
    add_line(window)
    window.act_select_all.trigger()
    window.act_cut.trigger()
    assert len(window.document.model_space) == 0
    window.act_paste.trigger()
    click(window, 20, 50)
    assert len(window.document.model_space) == 1


def test_dashed_pen_pattern_in_mm():
    pen = make_pen(QColor("black"), 0.25, 20.0, "dashed")
    assert pen.dashPattern() == [12.0, 3.0]
    # Widened on screen: pattern shrinks so dash lengths stay 3 mm / 0.75 mm.
    pen = make_pen(QColor("black"), 0.25, 2.0, "dashed")
    assert pen.widthF() == pytest.approx(0.5)
    assert [v * pen.widthF() for v in pen.dashPattern()] == pytest.approx([3.0, 0.75])


def test_floating_docks_can_be_docked_again(window):
    from sldgridy.ui.dock_title import DockTitleBar

    for dock in window.docks():
        bar = dock.titleBarWidget()
        assert isinstance(bar, DockTitleBar)
        bar.btn_float.click()
        assert dock.isFloating()
        bar.btn_float.click()
        assert not dock.isFloating()
    window.layers_dock.setFloating(True)
    window.properties_dock.close()
    window.reset_dock_layout()
    assert not window.layers_dock.isFloating() and window.properties_dock.isVisible()
    assert window.dockWidgetArea(window.library_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    window.library_dock.setFloating(True)
    window.dock_all()
    assert not window.library_dock.isFloating()
