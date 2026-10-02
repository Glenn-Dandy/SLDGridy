import pytest
from PyQt6.QtCore import QPointF, QRectF, QSettings, Qt
from PyQt6.QtTest import QTest

from blocks_fixtures import blocks, fuse
from sldgridy.fileio.files import load_library, save_library
from sldgridy.fileio.paths import user_library_dir
from sldgridy.model.entities import BlockReference, Circle, Line, Text
from sldgridy.model.geometry import Point
from sldgridy.ui import block_controller, block_dialogs
from sldgridy.ui.block_dialogs import (
    AttributeValuesDialog,
    BlockChooserDialog,
    CreateBlockDialog,
)
from sldgridy.ui.main_window import MainWindow
from sldgridy.ui.space import BLOCK, MODEL


@pytest.fixture
def window(qapp, monkeypatch):
    QSettings().clear()
    # Dialogs are answered automatically.
    monkeypatch.setattr(AttributeValuesDialog, "exec", lambda self: 1)
    w = MainWindow()
    w.resize(1200, 800)
    w.show()
    qapp.processEvents()
    w.canvas.fit_rect(QRectF(0, 0, 200, 150))
    w.act_osnap.setChecked(False)
    yield w
    w.undo_stack.setClean()
    for space in w.spaces():
        space.stack.setClean()
    w.close()


def click(window, x, y, button=Qt.MouseButton.LeftButton):
    pos = window.canvas.map_from_scene_f(QPointF(x, y)).toPoint()
    QTest.mouseClick(window.canvas.viewport(), button, pos=pos)


def refs(window):
    return [e for e in window.container if isinstance(e, BlockReference)]


def with_blocks(window):
    window.document.blocks.update(blocks())
    window._on_blocks_changed("")


def test_create_block_from_selection(window, monkeypatch):
    ms = window.document.model_space
    ms.add(Line(id="a", p1=Point(10, 10), p2=Point(10, 30)))
    ms.add(Circle(id="b", center=Point(10, 20), radius=3))
    window.act_select_all.trigger()

    def fake_exec(self):
        self.name.setText("Mein Block")
        return 1

    monkeypatch.setattr(CreateBlockDialog, "exec", fake_exec)
    window.blocks.act_create.trigger()
    click(window, 10, 10)
    assert "Mein Block" in window.document.blocks
    definition = window.document.blocks["Mein Block"]
    assert {type(e).__name__ for e in definition.entities} == {"Line", "Circle"}
    assert definition.entities.get("a").p1 == Point(0, 0)
    (ref,) = refs(window)
    assert ref.insert == Point(10, 10)
    window.act_undo.trigger()
    assert "Mein Block" not in window.document.blocks
    assert len(ms) == 2 and not refs(window)


def test_insert_block_with_tool_and_attributes(window, monkeypatch):
    with_blocks(window)
    monkeypatch.setattr(AttributeValuesDialog, "values", lambda self: {"BMK": "-F3"})
    window.blocks.insert_from_source("", "Sicherung")
    assert window.tools.active is not None
    click(window, 50, 50)
    (ref,) = refs(window)
    assert ref.insert == Point(50, 50) and ref.attribute("BMK") == "-F3"


def test_explode_reference(window):
    with_blocks(window)
    window.document.model_space.add(BlockReference(id="r", name="Sicherung", insert=Point(50, 50)))
    window._sync.item("r").setSelected(True)
    window.act_explode.trigger()
    kinds = sorted(type(e).__name__ for e in window.document.model_space)
    assert kinds == ["Circle", "Line", "Text"]
    window.act_undo.trigger()
    assert [e.id for e in window.document.model_space] == ["r"]


def test_block_editor_changes_all_references(window):
    with_blocks(window)
    ms = window.document.model_space
    ms.add(BlockReference(id="r1", name="Sicherung", insert=Point(20, 20)))
    ms.add(BlockReference(id="r2", name="Sicherung", insert=Point(60, 20)))
    window.blocks.open_editor("Sicherung")
    assert window.space.kind == BLOCK
    assert "Blockeditor" in window.windowTitle()
    # Draw an extra line inside the definition.
    window.act_line.trigger()
    click(window, -5, 0)
    click(window, 5, 0)
    window.tools.cancel()
    assert len(window.document.blocks["Sicherung"].entities) == 5  # unchanged until saved
    window.blocks.close_editor(save=True)
    assert window.space.kind == MODEL
    assert len(window.document.blocks["Sicherung"].entities) == 6
    item_rect = window._sync.item("r1").sceneBoundingRect()
    assert item_rect.left() <= 15.1  # new line reaches 5 mm left of the insert point
    window.act_undo.trigger()
    assert len(window.document.blocks["Sicherung"].entities) == 5


def test_block_editor_discard_and_base_point(window):
    with_blocks(window)
    window.blocks.open_editor("Sicherung")
    window.blocks.act_base.trigger()
    click(window, 0, 10)
    assert window.space.extra["definition"].base_point == Point(0, 10)
    window.act_undo.trigger()
    assert window.space.extra["definition"].base_point == Point(0, 0)
    window.act_redo.trigger()
    window.blocks.close_editor(save=False)
    assert window.document.blocks["Sicherung"].base_point == Point(0, 0)


def test_editor_rejects_self_reference(window):
    with_blocks(window)
    window.blocks.open_editor("Sicherung")
    window.blocks.insert_from_source("", "Feld", Point(0, 0))
    assert not refs(window)
    window.blocks.close_editor(save=False)


def test_attribute_edit_in_properties_dock(window):
    with_blocks(window)
    window.document.model_space.add(BlockReference(id="r", name="Sicherung", insert=Point(50, 50)))
    window._sync.item("r").setSelected(True)
    dock = window.properties_dock
    from PyQt6.QtWidgets import QLineEdit, QPushButton

    edits = dock.widget().findChildren(QLineEdit)
    edit = [e for e in edits if e.text() == "F1"][0]
    edit.setText("-F9")
    [b for b in dock.widget().findChildren(QPushButton) if "Attribute" in b.text()][0].click()
    assert window.document.model_space.get("r").attribute("BMK") == "-F9"


def write_library(name="test"):
    path = user_library_dir() / f"{name}.sldglib"
    path.parent.mkdir(parents=True, exist_ok=True)
    save_library(list(blocks().values()), path, "Testbibliothek")
    return path


def test_library_drop_copies_definitions(window):
    path = write_library()
    window.library_dock.reload()
    assert str(path) in window.library_dock.libraries
    window.canvas.block_dropped.emit({"path": str(path), "name": "Feld"}, QPointF(40, 40))
    assert {"Feld", "Sicherung"} <= set(window.document.blocks)
    (ref,) = refs(window)
    assert ref.name == "Feld" and ref.insert == Point(40, 40)
    window.act_undo.trigger()
    assert not refs(window)


def test_library_conflict_rename(window, monkeypatch):
    path = write_library("konflikt")
    window.library_dock.reload()
    other = fuse()
    other.entities.remove("c")
    window.document.blocks["Sicherung"] = other
    monkeypatch.setattr(block_controller, "ask_block_conflict", lambda *_: block_dialogs.RENAME)
    window.blocks.insert_from_source(str(path), "Feld", Point(0, 0))
    assert "Sicherung (2)" in window.document.blocks
    nested = [
        e.name for e in window.document.blocks["Feld"].entities if isinstance(e, BlockReference)
    ]
    assert nested == ["Sicherung (2)", "Sicherung (2)"]


def test_library_conflict_keep(window, monkeypatch):
    path = write_library("behalten")
    window.library_dock.reload()
    other = fuse()
    other.entities.remove("c")
    window.document.blocks["Sicherung"] = other
    monkeypatch.setattr(block_controller, "ask_block_conflict", lambda *_: block_dialogs.KEEP)
    window.blocks.insert_from_source(str(path), "Sicherung", Point(0, 0))
    assert window.document.blocks["Sicherung"] is other
    assert len(refs(window)) == 1


def test_save_to_user_library(window, monkeypatch):
    with_blocks(window)
    window.document.model_space.add(BlockReference(id="r", name="Feld", insert=Point(0, 0)))
    window._sync.item("r").setSelected(True)
    window.blocks.save_to_user_library()
    _, loaded = load_library(user_library_dir() / "eigene.sldglib")
    assert {b.name for b in loaded} >= {"Feld", "Sicherung"}


def test_clipboard_carries_block_definitions(window):
    with_blocks(window)
    window.document.model_space.add(BlockReference(id="r", name="Sicherung", insert=Point(10, 10)))
    window.act_select_all.trigger()
    window.act_copy_clip.trigger()
    window._set_document(type(window.document).new("Blatt 1"), None)
    window.act_paste.trigger()
    click(window, 30, 30)
    assert "Sicherung" in window.document.blocks
    assert len(refs(window)) == 1


def test_snap_to_reference_connection_point(window):
    with_blocks(window)
    window.act_osnap.setChecked(True)
    window.act_snap.setChecked(False)
    window.document.model_space.add(BlockReference(id="r", name="Sicherung", insert=Point(50, 50)))
    window.act_line.trigger()
    click(window, 50.5, 60.4)
    click(window, 50.5, 90)
    window.tools.cancel()
    (line,) = [e for e in window.document.model_space if isinstance(e, Line)]
    assert line.p1 == Point(50, 60)


def test_insert_dialog_lists_blocks(window, monkeypatch):
    with_blocks(window)

    def fake_exec(self):
        self.list.setCurrentRow(0)
        self.list.item(0).setSelected(True)
        return 1

    monkeypatch.setattr(BlockChooserDialog, "exec", fake_exec)
    window.blocks.act_insert.trigger()
    assert window.tools.active is not None
    window.tools.cancel()


def test_attribute_and_connection_definition_tools(window, monkeypatch):
    from sldgridy.ui.block_dialogs import AttributeDefinitionDialog, ConnectionPointDialog

    def att_exec(self):
        self.tag.setText("typ")
        return 1

    monkeypatch.setattr(AttributeDefinitionDialog, "exec", att_exec)
    monkeypatch.setattr(ConnectionPointDialog, "exec", lambda self: 1)
    window.blocks.act_attribute.trigger()
    click(window, 10, 10)
    window.blocks.act_connection.trigger()
    click(window, 20, 10)
    kinds = [type(e).__name__ for e in window.document.model_space]
    assert kinds == ["AttributeDefinition", "ConnectionPoint"]
    att = list(window.document.model_space)[0]
    assert att.tag == "TYP"


def test_text_entities_in_blocks_render(window):
    with_blocks(window)
    window.document.model_space.add(BlockReference(id="r", name="Feld", insert=Point(80, 80)))
    item = window._sync.item("r")
    assert not item.boundingRect().isEmpty()
    assert any(isinstance(p, Text) for p in item._parts)
