import pytest
from PyQt6.QtCore import QPointF, QRectF, QSettings, Qt
from PyQt6.QtTest import QTest

from factories import sample_entities
from sldgridy.fileio.files import load_document
from sldgridy.fileio.json_format import document_to_dict
from sldgridy.model.document import Document
from sldgridy.model.geometry import Point
from sldgridy.ui.main_window import MainWindow


@pytest.fixture
def window(qapp):
    QSettings().clear()  # every test starts with default snap, ortho and grid
    w = MainWindow()
    w.show()
    qapp.processEvents()
    yield w
    w.undo_stack.setClean()  # no save prompt on close
    w.close()


def test_status_bar_shows_cursor_in_mm_with_german_decimals(window):
    window.canvas.cursor_moved.emit(QPointF(12.5, -3.25))
    assert window.lbl_position.text() == "X: 12,50 mm   Y: -3,25 mm"


def test_status_bar_shows_zoom(window):
    window.canvas.set_zoom(2.0)
    assert window.lbl_zoom.text() == "Zoom: 200 %"


def test_grid_action_toggles_canvas(window):
    window.act_grid.setChecked(False)
    assert not window.canvas.grid_visible()
    window.act_grid.setChecked(True)
    assert window.canvas.grid_visible()


def test_new_window_has_document_with_one_sheet(window):
    assert [s.name for s in window.document.sheets] == ["Blatt 1"]


def click(window, x, y, button=Qt.MouseButton.LeftButton):
    canvas = window.canvas
    QTest.mouseClick(
        canvas.viewport(), button, pos=canvas.map_from_scene_f(QPointF(x, y)).toPoint()
    )


def test_draw_line_with_mouse_snaps_and_undoes(window):
    window.canvas.fit_rect(QRectF(0, 0, 100, 100))
    window.act_line.trigger()
    click(window, 10.4, 10.2)
    click(window, 40.6, 9.9)
    click(window, 0, 0, Qt.MouseButton.RightButton)
    (line,) = list(window.document.model_space)
    assert (line.p1, line.p2) == (Point(10, 10), Point(40, 10))
    assert window.isWindowModified()
    window.act_undo.trigger()
    assert list(window.document.model_space) == []
    window.act_redo.trigger()
    assert len(window.document.model_space) == 1


def test_ortho_constrains_second_point(window):
    window.canvas.fit_rect(QRectF(0, 0, 100, 100))
    window.act_ortho.setChecked(True)
    window.act_line.trigger()
    click(window, 10, 10)
    click(window, 50, 17.5)
    window.tools.cancel()
    (line,) = list(window.document.model_space)
    assert line.p2 == Point(50, 10)


def test_delete_and_select_all(window):
    for e in sample_entities():
        window.document.model_space.add(e)
    window.act_select_all.trigger()
    window.act_delete.trigger()
    assert len(window.document.model_space) == 0
    window.act_undo.trigger()
    assert len(window.document.model_space) == 6


def test_save_and_open_roundtrip(window, tmp_path):
    for e in sample_entities():
        window.document.model_space.add(e)
    path = tmp_path / "anlage.sldg"
    assert window.save_to(path)
    assert not window.isWindowModified()
    assert window.windowTitle() == "anlage.sldg[*] - SLDGridy"
    window._set_document(Document.new("Blatt 1"), None)
    assert len(window.document.model_space) == 0
    assert window.open_path(path)
    assert document_to_dict(window.document) == document_to_dict(load_document(path))
    from sldgridy.view.items import EntityItem

    assert len([i for i in window.scene.items() if isinstance(i, EntityItem)]) == 6


def test_mouse_side_buttons_undo_and_redo(window):
    from sldgridy.commands.entities import AddEntitiesCommand
    from sldgridy.model.entities import Line

    ms = window.document.model_space
    window.push(AddEntitiesCommand(ms, [Line(id="x", p1=Point(0, 0), p2=Point(5, 0))], "Linie"))
    assert "x" in ms
    for widget in (window.canvas.viewport(), window.library_dock.list.viewport()):
        QTest.mouseClick(widget, Qt.MouseButton.BackButton)
        assert "x" not in ms
        QTest.mouseClick(widget, Qt.MouseButton.ForwardButton)
        assert "x" in ms


def test_layer_cache_is_on_by_default_and_can_be_switched_off(window):
    assert window.act_layer_cache.isChecked()
    assert window.canvas.layer_cache_enabled
    cached = window.canvas.viewport().grab()
    window.act_layer_cache.setChecked(False)
    assert not window.canvas.layer_cache_enabled
    plain = window.canvas.viewport().grab()
    assert cached.size() == plain.size()


def test_display_settings_share_one_submenu(window):
    display = [a.menu() for a in window.view_menu.actions() if a.menu() is not None]
    display = [m for m in display if m.title().replace("&", "") == "Darstellung"][0]
    titles = [a.text().replace("&", "") for a in display.actions()]
    assert "Schnelle Darstellung (Zwischenspeicher)" in titles
    assert "Sprache / Language" in titles
    assert "Fenstersystem" in titles
