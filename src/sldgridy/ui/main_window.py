"""Main application window."""

from dataclasses import replace
from pathlib import Path

from PyQt6.QtCore import QLocale, QPointF, QSettings, Qt
from PyQt6.QtGui import QAction, QCloseEvent, QColor, QKeySequence, QUndoCommand, QUndoStack
from PyQt6.QtWidgets import (
    QFileDialog,
    QGraphicsScene,
    QLabel,
    QMainWindow,
    QMessageBox,
    QToolBar,
    QToolButton,
)

from sldgridy import __version__
from sldgridy.commands.entities import RemoveEntitiesCommand, ReplaceEntitiesCommand
from sldgridy.fileio.files import DRAWING_SUFFIX, load_document, save_document
from sldgridy.fileio.json_format import FileFormatError
from sldgridy.model.container import EntityContainer
from sldgridy.model.document import Document
from sldgridy.model.entities import Entity, Text
from sldgridy.model.layers import DEFAULT_LAYER
from sldgridy.tools.controller import ToolController, ToolFactory
from sldgridy.tools.draw import ArcTool, CircleTool, LineTool, PolylineTool, RectangleTool, TextTool
from sldgridy.tools.edit import CopyTool, MoveTool, RotateTool
from sldgridy.ui.grid_dialog import GridDialog
from sldgridy.ui.text_dialog import TextDialog
from sldgridy.view.canvas import Canvas
from sldgridy.view.items import EntityItem
from sldgridy.view.render import Style
from sldgridy.view.scene_sync import SceneSync

APP_NAME = "SLDGridy"


class MainWindow(QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._locale = QLocale(QLocale.Language.German, QLocale.Country.Germany)
        self.document = Document.new(self.tr("Blatt 1"))
        self.file_path: Path | None = None

        self.undo_stack = QUndoStack(self)
        self.undo_stack.cleanChanged.connect(lambda clean: self.setWindowModified(not clean))

        self.scene = QGraphicsScene(self)
        self.canvas = Canvas(self.scene, parent=self)
        self.canvas.resolve_style = self._resolve_style
        self.setCentralWidget(self.canvas)
        self._sync = SceneSync(self.scene, self.document.model_space, self._resolve_style)

        self.tools = ToolController(self, parent=self)
        self.canvas.controller = self.tools
        self.tools.changed.connect(self._on_tool_changed)

        self._create_actions()
        self._create_menus()
        self._create_toolbars()
        self._create_status_bar()

        self.canvas.cursor_moved.connect(self._show_cursor_position)
        self.canvas.zoom_changed.connect(self._show_zoom)
        self.canvas.entity_double_clicked.connect(self._edit_entity)

        self.resize(1280, 800)
        self._restore_settings()
        self._update_title()
        self._show_zoom(self.canvas.zoom())
        self._on_tool_changed()

    # -- ToolContext --------------------------------------------------------

    @property
    def container(self) -> EntityContainer:
        return self.document.model_space

    @property
    def current_layer(self) -> str:
        return DEFAULT_LAYER

    def push(self, command: QUndoCommand) -> None:
        self.undo_stack.push(command)

    def selected_ids(self) -> list[str]:
        items = [i for i in self.scene.selectedItems() if isinstance(i, EntityItem)]
        items.sort(key=lambda i: i.zValue())
        return [i.entity_id for i in items]

    def ask_text(self, text: str = "", height: float | None = None) -> tuple[str, float] | None:
        dialog = TextDialog(self, text, height)
        if dialog.exec() != TextDialog.DialogCode.Accepted:
            return None
        return dialog.text(), dialog.text_height()

    def message(self, text: str) -> None:
        self.statusBar().showMessage(text, 4000)

    # -- setup --------------------------------------------------------------

    def _action(self, text: str, slot, shortcut=None, icon_text: str | None = None) -> QAction:
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        if icon_text is not None:
            action.setIconText(icon_text)
        action.triggered.connect(slot)
        return action

    def _tool_action(self, text: str, factory: ToolFactory) -> QAction:
        return self._action(text, lambda: self._start_tool(factory))

    def _create_actions(self) -> None:
        sk = QKeySequence.StandardKey
        self.act_new = self._action(self.tr("&Neu"), self.new_document, sk.New)
        self.act_open = self._action(self.tr("Ö&ffnen …"), self.open_document, sk.Open)
        self.act_save = self._action(self.tr("&Speichern"), self.save, sk.Save)
        self.act_save_as = self._action(self.tr("Speichern &unter …"), self.save_as, "Ctrl+Shift+S")
        self.act_quit = self._action(self.tr("&Beenden"), self.close, sk.Quit)

        self.act_undo = self._action(self.tr("&Rückgängig"), self.undo, sk.Undo)
        self.act_redo = self._action(self.tr("&Wiederholen"), self.redo, sk.Redo)
        self.undo_stack.canUndoChanged.connect(self.act_undo.setEnabled)
        self.undo_stack.canRedoChanged.connect(self.act_redo.setEnabled)
        self.act_undo.setEnabled(False)
        self.act_redo.setEnabled(False)
        self.act_select_all = self._action(
            self.tr("Alles &auswählen"), self.select_all, sk.SelectAll
        )
        self.act_delete = self._action(self.tr("&Löschen"), self.delete_selection, sk.Delete)

        self.act_line = self._tool_action(self.tr("&Linie"), LineTool)
        self.act_polyline = self._tool_action(self.tr("&Polylinie"), PolylineTool)
        self.act_rectangle = self._tool_action(self.tr("&Rechteck"), RectangleTool)
        self.act_circle = self._tool_action(self.tr("&Kreis"), CircleTool)
        self.act_arc = self._tool_action(self.tr("&Bogen"), ArcTool)
        self.act_text = self._tool_action(self.tr("&Text"), TextTool)
        self.draw_actions = [
            self.act_line,
            self.act_polyline,
            self.act_rectangle,
            self.act_circle,
            self.act_arc,
            self.act_text,
        ]

        self.act_move = self._tool_action(self.tr("&Verschieben"), MoveTool)
        self.act_copy = self._tool_action(self.tr("&Kopieren"), CopyTool)
        self.act_rotate = self._tool_action(self.tr("&Drehen 90°"), RotateTool)
        self.modify_actions = [self.act_move, self.act_copy, self.act_rotate]

        self.act_grid = self._action(self.tr("&Raster anzeigen"), lambda: None, "F7", "RASTER")
        self.act_grid.setCheckable(True)
        self.act_grid.setChecked(self.canvas.grid_visible())
        self.act_grid.toggled.connect(self.canvas.set_grid_visible)

        self.act_ortho = self._action(self.tr("&Ortho"), lambda: None, "F8", "ORTHO")
        self.act_ortho.setCheckable(True)
        self.act_ortho.toggled.connect(self.canvas.set_ortho_enabled)

        self.act_snap = self._action(self.tr("Raster&fang"), lambda: None, "F9", "FANG")
        self.act_snap.setCheckable(True)
        self.act_snap.setChecked(self.canvas.snap_enabled)
        self.act_snap.toggled.connect(self.canvas.set_snap_enabled)

        self.act_grid_settings = self._action(
            self.tr("Raster und Fang &einstellen …"), self._edit_grid_settings
        )

        self.act_zoom_extents = self._action(
            self.tr("&Grenzen zoomen"), self.canvas.zoom_extents, "Home"
        )
        self.act_zoom_in = self._action(
            self.tr("Ver&größern"),
            lambda: self.canvas.set_zoom(self.canvas.zoom() * 1.5),
            sk.ZoomIn,
        )
        self.act_zoom_out = self._action(
            self.tr("Ver&kleinern"),
            lambda: self.canvas.set_zoom(self.canvas.zoom() / 1.5),
            sk.ZoomOut,
        )

        self.act_about = self._action(self.tr("Über {app}").format(app=APP_NAME), self._show_about)

    def _create_menus(self) -> None:
        bar = self.menuBar()
        m = bar.addMenu(self.tr("&Datei"))
        m.addActions([self.act_new, self.act_open, self.act_save, self.act_save_as])
        m.addSeparator()
        m.addAction(self.act_quit)

        m = bar.addMenu(self.tr("&Bearbeiten"))
        m.addActions([self.act_undo, self.act_redo])
        m.addSeparator()
        m.addActions([self.act_select_all, self.act_delete])

        m = bar.addMenu(self.tr("&Zeichnen"))
        m.addActions(self.draw_actions)

        m = bar.addMenu(self.tr("Ä&ndern"))
        m.addActions(self.modify_actions)

        m = bar.addMenu(self.tr("&Ansicht"))
        m.addActions([self.act_zoom_in, self.act_zoom_out, self.act_zoom_extents])
        m.addSeparator()
        m.addActions([self.act_grid, self.act_snap, self.act_ortho, self.act_grid_settings])

        m = bar.addMenu(self.tr("&Hilfe"))
        m.addAction(self.act_about)

    def _create_toolbars(self) -> None:
        for name, title, actions in (
            ("draw", self.tr("Zeichnen"), self.draw_actions),
            ("modify", self.tr("Ändern"), [*self.modify_actions, self.act_delete]),
        ):
            bar = QToolBar(title, self)
            bar.setObjectName(f"toolbar_{name}")
            bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            bar.addActions(actions)
            self.addToolBar(bar)

    def _create_status_bar(self) -> None:
        self.lbl_prompt = QLabel()
        self.lbl_position = QLabel()
        self.lbl_layer = QLabel(self.tr("Ebene: {name}").format(name=DEFAULT_LAYER))
        self.lbl_zoom = QLabel()
        status = self.statusBar()
        status.addWidget(self.lbl_prompt, 1)
        status.addPermanentWidget(self.lbl_position)
        for action in (self.act_grid, self.act_snap, self.act_ortho):
            button = QToolButton()
            button.setDefaultAction(action)
            button.setAutoRaise(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            status.addPermanentWidget(button)
        status.addPermanentWidget(self.lbl_layer)
        status.addPermanentWidget(self.lbl_zoom)
        self._show_cursor_position(QPointF(0.0, 0.0))

    # -- style --------------------------------------------------------------

    def _resolve_style(self, entity: Entity) -> Style:
        doc = self.document
        return Style(QColor(doc.effective_color(entity)), doc.effective_lineweight(entity))

    # -- document -----------------------------------------------------------

    def _set_document(self, document: Document, path: Path | None) -> None:
        self.tools.cancel()
        self._sync.detach()
        self.scene.clear()
        self.document = document
        self.file_path = path
        self._sync = SceneSync(self.scene, document.model_space, self._resolve_style)
        self.undo_stack.clear()
        self.undo_stack.setClean()
        self._update_title()
        self.canvas.zoom_extents()

    def _update_title(self) -> None:
        name = self.file_path.name if self.file_path else self.tr("Unbenannt")
        self.setWindowTitle(f"{name}[*] - {APP_NAME}")
        self.setWindowModified(not self.undo_stack.isClean())

    def _maybe_save(self) -> bool:
        """Ask to save unsaved changes. False means the user cancelled."""
        if self.undo_stack.isClean():
            return True
        buttons = QMessageBox.StandardButton
        answer = QMessageBox.question(
            self,
            APP_NAME,
            self.tr("Die Zeichnung wurde geändert. Änderungen speichern?"),
            buttons.Save | buttons.Discard | buttons.Cancel,
            buttons.Save,
        )
        if answer == buttons.Save:
            return self.save()
        return answer == buttons.Discard

    def new_document(self) -> None:
        if self._maybe_save():
            self._set_document(Document.new(self.tr("Blatt 1")), None)

    def _file_filter(self) -> str:
        return self.tr("SLDGridy-Zeichnung (*{suffix})").format(suffix=DRAWING_SUFFIX)

    def _last_dir(self) -> str:
        return str(QSettings().value("files/last_dir", str(Path.home())))

    def open_document(self) -> None:
        if not self._maybe_save():
            return
        name, _ = QFileDialog.getOpenFileName(
            self, self.tr("Zeichnung öffnen"), self._last_dir(), self._file_filter()
        )
        if name:
            self.open_path(Path(name))

    def open_path(self, path: Path) -> bool:
        try:
            document = load_document(path)
        except (OSError, FileFormatError) as exc:
            QMessageBox.critical(
                self,
                APP_NAME,
                self.tr("Die Datei {name} kann nicht geöffnet werden:\n{error}").format(
                    name=path.name, error=exc
                ),
            )
            return False
        QSettings().setValue("files/last_dir", str(path.parent))
        self._set_document(document, path)
        return True

    def save(self) -> bool:
        if self.file_path is None:
            return self.save_as()
        return self.save_to(self.file_path)

    def save_as(self) -> bool:
        start = str(self.file_path) if self.file_path else self._last_dir()
        name, _ = QFileDialog.getSaveFileName(
            self, self.tr("Zeichnung speichern"), start, self._file_filter()
        )
        if not name:
            return False
        path = Path(name)
        if path.suffix != DRAWING_SUFFIX:
            path = path.with_name(path.name + DRAWING_SUFFIX)
        return self.save_to(path)

    def save_to(self, path: Path) -> bool:
        try:
            save_document(self.document, path)
        except OSError as exc:
            QMessageBox.critical(
                self,
                APP_NAME,
                self.tr("Die Datei {name} kann nicht gespeichert werden:\n{error}").format(
                    name=path.name, error=exc
                ),
            )
            return False
        self.file_path = path
        QSettings().setValue("files/last_dir", str(path.parent))
        self.undo_stack.setClean()
        self._update_title()
        self.message(self.tr("Gespeichert: {path}").format(path=path))
        return True

    # -- editing ------------------------------------------------------------

    def _start_tool(self, factory: ToolFactory) -> None:
        self.tools.start(factory)
        self.canvas.setFocus()

    def undo(self) -> None:
        # A running tool may hold snapshots that undo would invalidate.
        self.tools.cancel()
        self.undo_stack.undo()

    def redo(self) -> None:
        self.tools.cancel()
        self.undo_stack.redo()

    def select_all(self) -> None:
        for item in self.scene.items():
            if isinstance(item, EntityItem):
                item.setSelected(True)

    def delete_selection(self) -> None:
        ids = self.selected_ids()
        if ids:
            self.tools.cancel()
            self.push(RemoveEntitiesCommand(self.container, ids, self.tr("Löschen")))

    def _edit_entity(self, entity_id: str) -> None:
        entity = self.container.get(entity_id)
        if not isinstance(entity, Text):
            return
        result = self.ask_text(entity.text, entity.height)
        if result is None:
            return
        content, height = result
        if not content.strip() or (content, height) == (entity.text, entity.height):
            return
        changed = replace(entity, text=content, height=height)
        self.push(ReplaceEntitiesCommand(self.container, [changed], self.tr("Text ändern")))

    def _edit_grid_settings(self) -> None:
        dialog = GridDialog(self.canvas.grid_spacing(), self.canvas.snap_spacing, self)
        if dialog.exec() == GridDialog.DialogCode.Accepted:
            self.canvas.set_grid_spacing(dialog.grid_spacing())
            self.canvas.set_snap_spacing(dialog.snap_spacing())

    # -- slots --------------------------------------------------------------

    def _on_tool_changed(self) -> None:
        prompt = self.tools.prompt() or self.tr("Bereit")
        self.lbl_prompt.setText(prompt)
        self.canvas.viewport().update()

    def _fmt_mm(self, value: float) -> str:
        return self._locale.toString(value, "f", 2)

    def _show_cursor_position(self, pos: QPointF) -> None:
        self.lbl_position.setText(
            self.tr("X: {x} mm   Y: {y} mm").format(
                x=self._fmt_mm(pos.x()), y=self._fmt_mm(pos.y())
            )
        )

    def _show_zoom(self, zoom: float) -> None:
        percent = self._locale.toString(zoom * 100, "f", 0 if zoom >= 0.1 else 1)
        self.lbl_zoom.setText(self.tr("Zoom: {percent} %").format(percent=percent))

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            self.tr("Über {app}").format(app=APP_NAME),
            self.tr(
                "<b>{app}</b> {version}<br>"
                "Einpolige Übersichtsschaltpläne für Photovoltaik, "
                "Transformatorstationen und Niederspannungsverteilungen.<br><br>"
                "Lizenz: GPL-3.0-or-later"
            ).format(app=APP_NAME, version=__version__),
        )

    # -- settings -----------------------------------------------------------

    def _restore_settings(self) -> None:
        settings = QSettings()
        geometry = settings.value("main_window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = settings.value("main_window/state")
        if state is not None:
            self.restoreState(state)
        self.act_grid.setChecked(settings.value("view/grid_visible", True, type=bool))
        self.act_snap.setChecked(settings.value("view/snap_enabled", True, type=bool))
        self.act_ortho.setChecked(settings.value("view/ortho_enabled", False, type=bool))
        grid = settings.value("view/grid_spacing", self.canvas.grid_spacing(), type=float)
        snap = settings.value("view/snap_spacing", self.canvas.snap_spacing, type=float)
        if grid > 0:
            self.canvas.set_grid_spacing(grid)
        if snap > 0:
            self.canvas.set_snap_spacing(snap)

    def _save_settings(self) -> None:
        settings = QSettings()
        settings.setValue("main_window/geometry", self.saveGeometry())
        settings.setValue("main_window/state", self.saveState())
        settings.setValue("view/grid_visible", self.act_grid.isChecked())
        settings.setValue("view/snap_enabled", self.act_snap.isChecked())
        settings.setValue("view/ortho_enabled", self.act_ortho.isChecked())
        settings.setValue("view/grid_spacing", self.canvas.grid_spacing())
        settings.setValue("view/snap_spacing", self.canvas.snap_spacing)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not getattr(self, "_initial_view_done", False):
            self._initial_view_done = True
            self.canvas.zoom_extents()

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._maybe_save():
            event.ignore()
            return
        self.tools.cancel()
        self._save_settings()
        super().closeEvent(event)
