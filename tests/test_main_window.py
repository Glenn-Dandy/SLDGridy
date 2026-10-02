import pytest
from PyQt6.QtCore import QPointF

from sldgridy.ui.main_window import MainWindow


@pytest.fixture
def window(qapp):
    w = MainWindow()
    w.show()
    qapp.processEvents()
    yield w
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
