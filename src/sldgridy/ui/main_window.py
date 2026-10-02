"""Main application window."""

from dataclasses import replace
from pathlib import Path

from PyQt6.QtCore import QLocale, QPointF, QSettings, Qt
from PyQt6.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
    QKeySequence,
    QUndoCommand,
    QUndoGroup,
    QUndoStack,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGraphicsScene,
    QGroupBox,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sldgridy import __version__
from sldgridy.commands.entities import RemoveEntitiesCommand, ReplaceEntitiesCommand
from sldgridy.fileio.files import DRAWING_SUFFIX, load_document, save_document
from sldgridy.fileio.json_format import FileFormatError
from sldgridy.model.blocks import BlockError, expand, world_connections
from sldgridy.model.container import EntityContainer
from sldgridy.model.document import Document
from sldgridy.model.entities import BlockReference, Busbar, ConnectionPoint, Entity, Text, Wire
from sldgridy.model.geometry import Point
from sldgridy.model.layers import DEFAULT_LAYER
from sldgridy.model.snap import ALL_MODES, SnapHit, SnapMode
from sldgridy.model.wires import label_text
from sldgridy.tools.controller import ToolController, ToolFactory
from sldgridy.tools.coord_input import CoordinateError, parse_coordinate
from sldgridy.tools.draw import (
    ArcTool,
    BusbarTool,
    CircleTool,
    LineTool,
    PolylineTool,
    RectangleTool,
    TextTool,
    WireTool,
)
from sldgridy.tools.edit import CopyTool, MirrorTool, MoveTool, PasteTool, RotateTool
from sldgridy.ui import clipboard
from sldgridy.ui.block_controller import BlockController
from sldgridy.ui.command_line import CommandLine
from sldgridy.ui.grid_dialog import GridDialog
from sldgridy.ui.layers_dock import LayersDock
from sldgridy.ui.library_dock import LibraryDock
from sldgridy.ui.osnap_dialog import OsnapDialog
from sldgridy.ui.properties_dock import PropertiesDock
from sldgridy.ui.sheet_controller import SheetController
from sldgridy.ui.space import BLOCK, MODEL, SHEET, Space
from sldgridy.ui.text_dialog import TextDialog
from sldgridy.view.canvas import BACKGROUND_COLOR, Canvas
from sldgridy.view.items import EntityItem
from sldgridy.view.junctions import JunctionItem
from sldgridy.view.render import Style
from sldgridy.view.scene_sync import SceneSync

APP_NAME = "SLDGridy"


class MainWindow(QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._locale = QLocale(QLocale.Language.German, QLocale.Country.Germany)
        self.document = Document.new(self.tr("Blatt 1"))
        self.file_path: Path | None = None
        self.current_layer = DEFAULT_LAYER

        self.undo_group = QUndoGroup(self)
        self.undo_stack = QUndoStack(self)
        self.undo_group.addStack(self.undo_stack)
        self.undo_group.setActiveStack(self.undo_stack)
        self.undo_stack.cleanChanged.connect(self._on_clean_changed)
        self.undo_group.indexChanged.connect(self._on_undo_index_changed)

        self.canvas = Canvas(QGraphicsScene(self), parent=self)
        self.canvas.resolve_style = self._resolve_style
        self.canvas.expand = self._expand
        self.canvas.snap_decompose = self._decompose
        self.canvas.snap_extra = self._snap_extra
        self.command_line = CommandLine(self)
        self.central_layout = QVBoxLayout()
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.central_layout.setSpacing(0)
        self.central_layout.addWidget(self.canvas, 1)
        self.central_layout.addWidget(self.command_line)
        central = QWidget(self)
        central.setLayout(self.central_layout)
        self.setCentralWidget(central)

        self.tools = ToolController(self, parent=self)
        self.canvas.controller = self.tools
        self.tools.changed.connect(self._on_tool_changed)

        self.model_view = self._make_space(MODEL, self.document.model_space, self.undo_stack)
        self.space = self.model_view
        self.canvas.set_scene(self.space.scene)
        self._subscribe_document()

        self.blocks = BlockController(self)
        self.sheets = SheetController(self)
        self.central_layout.insertWidget(1, self.sheets.tabs)
        self.model_view.extra["overlay"] = self.sheets.model_overlay
        self.canvas.extra_overlay = self.sheets.model_overlay

        self._create_actions()
        self._create_menus()
        self._create_toolbars()
        self._create_docks()
        self._create_status_bar()

        self.canvas.cursor_moved.connect(self._show_cursor_position)
        self.canvas.zoom_changed.connect(self._show_zoom)
        self.canvas.entity_double_clicked.connect(self._edit_entity)
        self.canvas.text_typed.connect(self.command_line.start_typing)
        self.canvas.block_dropped.connect(self.blocks.on_drop)
        self.canvas.empty_double_clicked.connect(self.sheets.on_empty_double_click)
        self.sheets.rebuild_tabs()
        self.command_line.submitted.connect(self._on_command_input)
        self.command_line.cancelled.connect(self._on_command_cancel)

        self.resize(1280, 800)
        self._restore_settings()
        self._update_title()
        self._show_zoom(self.canvas.zoom())
        self._on_tool_changed()

    # -- spaces -------------------------------------------------------------

    @property
    def scene(self) -> QGraphicsScene:
        return self.space.scene

    @property
    def _sync(self) -> SceneSync:
        return self.space.sync

    def _make_space(
        self, kind: str, container: EntityContainer, stack: QUndoStack, item_factory=None
    ) -> Space:
        scene = QGraphicsScene(self)
        sync = SceneSync(
            scene, container, self._resolve_style, self._layer_state, self._expand, item_factory
        )
        scene.selectionChanged.connect(self._on_selection_changed)
        junction_item = JunctionItem(
            container, self._resolve_style, lambda e: self._layer_state(e)[0]
        )
        scene.addItem(junction_item)
        space = Space(kind, container, scene, sync, stack)
        space.extra["junctions"] = junction_item
        return space

    def spaces(self) -> list[Space]:
        result = [self.model_view]
        editor = self.blocks.editor_space if hasattr(self, "blocks") else None
        if editor is not None:
            result.append(editor)
        if hasattr(self, "sheets"):
            result += self.sheets.all_spaces()
        return result

    def activate_space(self, space: Space) -> None:
        if space is self.space:
            return
        self.tools.cancel()
        self.sheets.deactivate_viewport()
        self.space.view = (
            self.canvas.transform(),
            self.canvas.map_to_scene_f(QPointF(self.canvas.viewport().rect().center())),
        )
        self.space = space
        self.canvas.set_scene(space.scene)
        self.canvas.extra_overlay = space.extra.get("overlay")
        self.canvas.set_background(
            space.extra.get("background", BACKGROUND_COLOR), show_origin=space.kind != SHEET
        )
        self.sheets.select_tab_for(space)
        if space.stack not in self.undo_group.stacks():
            self.undo_group.addStack(space.stack)
        self.undo_group.setActiveStack(space.stack)
        if space.view is not None:
            transform, center = space.view
            self.canvas.setTransform(transform)
            self.canvas.center_on_point(center)
            self._show_zoom(self.canvas.zoom())
        else:
            self.canvas.zoom_extents()
        self._on_selection_changed()
        self._update_title()

    def _drop_space(self, space: Space) -> None:
        space.detach()
        space.extra["junctions"].detach()
        if space.stack in self.undo_group.stacks() and space.stack is not self.undo_stack:
            self.undo_group.removeStack(space.stack)
        space.scene.deleteLater()

    # -- ToolContext --------------------------------------------------------

    @property
    def container(self) -> EntityContainer:
        return self.space.container

    def set_current_layer(self, name: str) -> None:
        if not self.document.has_layer(name):
            name = DEFAULT_LAYER
        self.current_layer = name
        self.lbl_layer.setText(self.tr("Ebene: {name}").format(name=name))
        self.layers_dock.rebuild()

    @property
    def block_definitions(self):
        return self.document.blocks

    @property
    def active_stack(self) -> QUndoStack:
        return self.space.stack

    def push(self, command: QUndoCommand) -> None:
        self.active_stack.push(command)

    def begin_macro(self, text: str) -> None:
        self.active_stack.beginMacro(text)

    def end_macro(self) -> None:
        self.active_stack.endMacro()

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
        self.statusBar().showMessage(text, 5000)

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
        return self._action(text, lambda: self.start_tool(factory))

    def _create_actions(self) -> None:
        sk = QKeySequence.StandardKey
        self.act_new = self._action(self.tr("&Neu"), self.new_document, sk.New)
        self.act_open = self._action(self.tr("Ö&ffnen …"), self.open_document, sk.Open)
        self.act_save = self._action(self.tr("&Speichern"), self.save, sk.Save)
        self.act_save_as = self._action(self.tr("Speichern &unter …"), self.save_as, "Ctrl+Shift+S")
        self.act_quit = self._action(self.tr("&Beenden"), self.close, sk.Quit)

        self.act_undo = self._action(self.tr("&Rückgängig"), self.undo, sk.Undo)
        self.act_redo = self._action(self.tr("&Wiederholen"), self.redo, sk.Redo)
        self.undo_group.canUndoChanged.connect(self.act_undo.setEnabled)
        self.undo_group.canRedoChanged.connect(self.act_redo.setEnabled)
        self.act_undo.setEnabled(False)
        self.act_redo.setEnabled(False)
        self.act_select_all = self._action(
            self.tr("Alles &auswählen"), self.select_all, sk.SelectAll
        )
        self.act_delete = self._action(self.tr("&Löschen"), self.delete_selection, sk.Delete)
        self.act_cut = self._action(self.tr("Aus&schneiden"), self.cut, sk.Cut)
        self.act_copy_clip = self._action(self.tr("&Kopieren"), self.copy_to_clipboard, sk.Copy)
        self.act_paste = self._action(self.tr("&Einfügen"), self.paste, sk.Paste)

        self.act_line = self._tool_action(self.tr("&Linie"), LineTool)
        self.act_polyline = self._tool_action(self.tr("&Polylinie"), PolylineTool)
        self.act_rectangle = self._tool_action(self.tr("&Rechteck"), RectangleTool)
        self.act_circle = self._tool_action(self.tr("&Kreis"), CircleTool)
        self.act_arc = self._tool_action(self.tr("&Bogen"), ArcTool)
        self.act_text = self._tool_action(self.tr("&Text"), TextTool)
        self.act_wire = self._tool_action(self.tr("Lei&tung"), WireTool)
        self.act_wire.setShortcut(QKeySequence("Ctrl+W"))
        self.act_busbar = self._tool_action(self.tr("&Sammelschiene"), BusbarTool)
        self.draw_actions = [
            self.act_wire,
            self.act_busbar,
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
        self.act_mirror = self._tool_action(self.tr("S&piegeln"), MirrorTool)
        self.act_explode = self._action(self.tr("&Auflösen"), self.blocks.explode_selection)
        self.modify_actions = [
            self.act_move,
            self.act_copy,
            self.act_rotate,
            self.act_mirror,
            self.act_explode,
        ]

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

        self.act_osnap = self._action(self.tr("&Objektfang"), lambda: None, "F3", "OFANG")
        self.act_osnap.setCheckable(True)
        self.act_osnap.setChecked(self.canvas.osnap_enabled)
        self.act_osnap.toggled.connect(self.canvas.set_osnap_enabled)
        self.act_osnap_settings = self._action(
            self.tr("Objektfang ein&stellen …"), self._edit_osnap_settings
        )
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

        self.blocks.create_actions()
        self.sheets.create_actions()
        self.act_about = self._action(self.tr("Über {app}").format(app=APP_NAME), self._show_about)

    def _create_menus(self) -> None:
        bar = self.menuBar()
        m = bar.addMenu(self.tr("&Datei"))
        m.addActions([self.act_new, self.act_open, self.act_save, self.act_save_as])
        m.addSeparator()
        self.file_menu_tail = m.addSeparator()
        m.addAction(self.act_quit)
        self.file_menu = m

        m = bar.addMenu(self.tr("&Bearbeiten"))
        m.addActions([self.act_undo, self.act_redo])
        m.addSeparator()
        m.addActions([self.act_cut, self.act_copy_clip, self.act_paste])
        m.addSeparator()
        m.addActions([self.act_select_all, self.act_delete])

        m = bar.addMenu(self.tr("&Zeichnen"))
        m.addActions(self.draw_actions)
        self.draw_menu = m

        m = bar.addMenu(self.tr("Ä&ndern"))
        m.addActions(self.modify_actions)

        self.blocks.create_menu(bar)
        self.sheets.create_menu(bar)

        m = bar.addMenu(self.tr("&Ansicht"))
        m.addActions([self.act_zoom_in, self.act_zoom_out, self.act_zoom_extents])
        m.addSeparator()
        m.addActions([self.act_grid, self.act_snap, self.act_ortho, self.act_osnap])
        m.addActions([self.act_grid_settings, self.act_osnap_settings])
        m.addSeparator()
        self.docks_menu = m.addMenu(self.tr("&Fenster"))
        self.view_menu = m

        m = bar.addMenu(self.tr("&Hilfe"))
        m.addAction(self.act_about)

    def _create_toolbars(self) -> None:
        for name, title, actions in (
            ("draw", self.tr("Zeichnen"), self.draw_actions),
            ("modify", self.tr("Ändern"), [*self.modify_actions, self.act_delete]),
            ("blocks", self.tr("Blöcke"), self.blocks.toolbar_actions()),
        ):
            bar = QToolBar(title, self)
            bar.setObjectName(f"toolbar_{name}")
            bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            bar.addActions(actions)
            self.addToolBar(bar)

    def _create_docks(self) -> None:
        self.layers_dock = LayersDock(self, self)
        self.properties_dock = PropertiesDock(self, self)
        self.library_dock = LibraryDock(self, self)
        self.blocks.attach_properties(self.properties_dock)
        self.sheets.attach_properties(self.properties_dock)
        self.properties_dock.extra_type_names.update(
            {Wire: self.tr("Leitung"), Busbar: self.tr("Sammelschiene")}
        )
        self.properties_dock.extra_editors.append(self._wire_label_editor)
        self.library_dock.insert_requested.connect(self.blocks.insert_from_source)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.layers_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.properties_dock)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.library_dock)
        for dock in (self.layers_dock, self.properties_dock, self.library_dock):
            self.docks_menu.addAction(dock.toggleViewAction())
        self.resizeDocks([self.layers_dock], [480], Qt.Orientation.Horizontal)
        self.resizeDocks([self.library_dock], [260], Qt.Orientation.Horizontal)

    def _create_status_bar(self) -> None:
        self.lbl_position = QLabel()
        width = self.lbl_position.fontMetrics().horizontalAdvance(
            "X: -00000,00 mm   Y: -00000,00 mm"
        )
        self.lbl_position.setMinimumWidth(width)
        self.lbl_layer = QLabel(self.tr("Ebene: {name}").format(name=DEFAULT_LAYER))
        self.lbl_zoom = QLabel()
        status = self.statusBar()
        status.addPermanentWidget(self.lbl_position)
        for action in (self.act_grid, self.act_snap, self.act_ortho, self.act_osnap):
            button = QToolButton()
            button.setDefaultAction(action)
            button.setAutoRaise(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            status.addPermanentWidget(button)
        status.addPermanentWidget(self.lbl_layer)
        status.addPermanentWidget(self.lbl_zoom)
        self._show_cursor_position(QPointF(0.0, 0.0))

    # -- style, blocks and snapping -----------------------------------------

    def _resolve_style(self, entity: Entity) -> Style:
        doc = self.document
        return Style(
            QColor(doc.effective_color(entity)),
            doc.effective_lineweight(entity),
            doc.effective_linetype(entity),
        )

    def _layer_state(self, entity: Entity) -> tuple[bool, bool]:
        layer = self.document.layer(entity.layer)
        return layer.visible, layer.locked

    def _expand(self, entity: Entity) -> list[Entity]:
        if isinstance(entity, Wire):
            label = label_text(entity)
            return [entity, label] if label is not None else [entity]
        if isinstance(entity, BlockReference):
            try:
                return expand(entity, self.document.blocks)
            except BlockError:
                return []
        return [entity]

    def _decompose(self, entity: Entity) -> list[Entity]:
        if isinstance(entity, ConnectionPoint):
            return []
        return self._expand(entity)

    def _snap_extra(self, entity: Entity) -> list[SnapHit]:
        if isinstance(entity, ConnectionPoint):
            return [SnapHit(entity.position, SnapMode.CONNECTION)]
        if isinstance(entity, BlockReference):
            return [
                SnapHit(c.position, SnapMode.CONNECTION)
                for c in world_connections(entity, self.document.blocks)
            ]
        return []

    def _subscribe_document(self) -> None:
        self.document.subscribe_layers(self._on_layers_changed)
        self.document.subscribe_blocks(self._on_blocks_changed)
        self.document.subscribe_sheets(self._on_sheets_changed)
        self.document.model_space.subscribe(self._on_model_changed)

    def _unsubscribe_document(self) -> None:
        self.document.unsubscribe_layers(self._on_layers_changed)
        self.document.unsubscribe_blocks(self._on_blocks_changed)
        self.document.unsubscribe_sheets(self._on_sheets_changed)
        self.document.model_space.unsubscribe(self._on_model_changed)

    def _on_sheets_changed(self) -> None:
        self.sheets.on_sheets_changed()

    def _on_model_changed(self, _event: str, _entity: Entity) -> None:
        if hasattr(self, "sheets"):
            self.sheets.refresh_viewports()

    def _refresh_all_spaces(self) -> None:
        for space in self.spaces():
            space.sync.refresh()
            space.extra["junctions"].recompute()
        self.sheets.refresh_viewports()
        self.canvas.viewport().update()

    def _on_layers_changed(self) -> None:
        if not self.document.has_layer(self.current_layer):
            self.current_layer = DEFAULT_LAYER
        self.lbl_layer.setText(self.tr("Ebene: {name}").format(name=self.current_layer))
        self._refresh_all_spaces()
        self.layers_dock.rebuild()
        self.properties_dock.refresh()

    def _on_blocks_changed(self, _name: str) -> None:
        self._refresh_all_spaces()
        self.library_dock.refresh_document()
        self.properties_dock.refresh()

    # -- document -----------------------------------------------------------

    def _set_document(self, document: Document, path: Path | None) -> None:
        self.tools.cancel()
        self.blocks.close_editor(save=False, ask=False)
        self._unsubscribe_document()
        old = self.model_view
        self.document = document
        self.file_path = path
        self.sheets.reset()
        self.model_view = self._make_space(MODEL, document.model_space, self.undo_stack)
        self.model_view.extra["overlay"] = self.sheets.model_overlay
        self.space = self.model_view
        self.canvas.set_scene(self.space.scene)
        self.canvas.extra_overlay = self.sheets.model_overlay
        self.canvas.set_background(BACKGROUND_COLOR, show_origin=True)
        self.undo_group.setActiveStack(self.undo_stack)
        self._drop_space(old)
        self._subscribe_document()
        self.undo_stack.clear()
        self.undo_stack.setClean()
        self.sheets.rebuild_tabs()
        self.set_current_layer(DEFAULT_LAYER)
        self.properties_dock.refresh()
        self.library_dock.refresh_document()
        self._update_title()
        self.canvas.zoom_extents()

    def _update_title(self) -> None:
        name = self.file_path.name if self.file_path else self.tr("Unbenannt")
        suffix = ""
        if self.space.kind == BLOCK:
            suffix = self.tr(" [Blockeditor: {name}]").format(name=self.blocks.editor_name())
        self.setWindowTitle(f"{name}[*]{suffix} - {APP_NAME}")
        self.setWindowModified(not self.undo_stack.isClean())

    def _maybe_save(self) -> bool:
        """Ask to save unsaved changes. False means the user cancelled."""
        if not self.blocks.close_editor(save=None, ask=True):
            return False
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

    def last_dir(self) -> str:
        return str(QSettings().value("files/last_dir", str(Path.home())))

    def remember_dir(self, path: Path) -> None:
        QSettings().setValue("files/last_dir", str(path.parent))

    def open_document(self) -> None:
        if not self._maybe_save():
            return
        name, _ = QFileDialog.getOpenFileName(
            self, self.tr("Zeichnung öffnen"), self.last_dir(), self._file_filter()
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
        self.remember_dir(path)
        self._set_document(document, path)
        return True

    def save(self) -> bool:
        if self.file_path is None:
            return self.save_as()
        return self.save_to(self.file_path)

    def save_as(self) -> bool:
        start = str(self.file_path) if self.file_path else self.last_dir()
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
        self.remember_dir(path)
        self.undo_stack.setClean()
        self._update_title()
        self.message(self.tr("Gespeichert: {path}").format(path=path))
        return True

    # -- editing ------------------------------------------------------------

    def start_tool(self, factory: ToolFactory) -> None:
        self.tools.start(factory)
        self.canvas.setFocus()

    def undo(self) -> None:
        # A running tool may hold snapshots that undo would invalidate.
        self.tools.cancel()
        self.undo_group.undo()

    def redo(self) -> None:
        self.tools.cancel()
        self.undo_group.redo()

    def select_all(self) -> None:
        for item in self.scene.items():
            if (
                isinstance(item, EntityItem)
                and item.isVisible()
                and item.flags() & item.GraphicsItemFlag.ItemIsSelectable
            ):
                item.setSelected(True)

    def delete_selection(self) -> None:
        ids = self.selected_ids()
        if ids:
            self.tools.cancel()
            self.push(RemoveEntitiesCommand(self.container, ids, self.tr("Löschen")))

    def selected_entities(self) -> list[Entity]:
        return [self.container.get(i) for i in self.selected_ids()]

    def selection_base(self) -> Point:
        """Lower left corner of the selection's bounding box."""
        rect = None
        for item in self.scene.selectedItems():
            r = item.sceneBoundingRect()
            rect = r if rect is None else rect.united(r)
        return Point(rect.left(), rect.bottom()) if rect is not None else Point(0.0, 0.0)

    def copy_to_clipboard(self) -> bool:
        entities = self.selected_entities()
        if not entities:
            return False
        clipboard.copy_entities(
            entities, self.selection_base(), self.blocks.clipboard_extra(entities)
        )
        return True

    def cut(self) -> None:
        if self.copy_to_clipboard():
            self.tools.cancel()
            self.push(
                RemoveEntitiesCommand(self.container, self.selected_ids(), self.tr("Ausschneiden"))
            )

    def paste(self) -> None:
        payload = clipboard.clipboard_payload()
        result = clipboard.paste_entities(payload) if payload else None
        if result is None:
            self.message(self.tr("Die Zwischenablage enthält keine Zeichnungsobjekte"))
            return
        entities, base = result
        if not self.blocks.prepare_paste(payload, entities):
            return
        entities = [
            replace(e, layer=e.layer if self.document.has_layer(e.layer) else DEFAULT_LAYER)
            for e in entities
        ]
        self.start_tool(lambda ctx: PasteTool(ctx, entities, base))

    def _on_clean_changed(self, clean: bool) -> None:
        self.setWindowModified(not clean)

    def _on_undo_index_changed(self, _index: int) -> None:
        self.properties_dock.refresh()

    def _on_selection_changed(self) -> None:
        if hasattr(self, "properties_dock"):
            self.properties_dock.refresh()
        self.canvas.viewport().update()

    def _on_command_input(self, text: str) -> None:
        self.canvas.setFocus()
        if not text.strip():
            if self.tools.active is not None:
                self.tools.finish()
            else:
                self.tools.repeat()
            return
        if self.tools.active is None or self.tools.selecting():
            self.message(self.tr("Koordinaten werden nur während eines Zeichenbefehls erwartet"))
            return
        reference = self.tools.base_point() or self.tools.last_point
        try:
            p = parse_coordinate(text, reference, self.canvas.ortho_direction())
        except CoordinateError:
            self.message(self.tr("Ungültige Eingabe: {text}").format(text=text))
            return
        self.tools.hover(p)
        self.tools.pick(p)

    def _on_command_cancel(self) -> None:
        self.tools.cancel()
        self.canvas.setFocus()

    def _edit_osnap_settings(self) -> None:
        dialog = OsnapDialog(self.canvas.osnap_modes, self)
        if dialog.exec() == OsnapDialog.DialogCode.Accepted:
            self.canvas.osnap_modes = dialog.modes()

    def _edit_entity(self, entity_id: str) -> None:
        entity = self.container.get(entity_id)
        if self.blocks.edit_entity(entity):
            return
        if isinstance(entity, Wire):
            label, ok = QInputDialog.getText(
                self, self.tr("Leitung"), self.tr("Beschriftung:"), text=entity.label
            )
            if ok and label != entity.label:
                self.push(
                    ReplaceEntitiesCommand(
                        self.container, [replace(entity, label=label)], self.tr("Beschriftung")
                    )
                )
            return
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

    def _wire_label_editor(self, entities: list[Entity], layout: QVBoxLayout) -> None:
        wires = [e for e in entities if isinstance(e, Wire)]
        if len(wires) != 1 or len(entities) != 1:
            return
        wire = wires[0]
        box = QGroupBox(self.tr("Beschriftung"))
        form = QFormLayout(box)
        edit = QLineEdit(wire.label)
        edit.setPlaceholderText(self.tr("z. B. NYY-J 5x16"))
        side = QComboBox()
        side.addItem(self.tr("oben / links"), 1)
        side.addItem(self.tr("unten / rechts"), -1)
        side.setCurrentIndex(0 if wire.label_side > 0 else 1)
        apply = QPushButton(self.tr("Beschriftung übernehmen"))
        form.addRow(self.tr("Text:"), edit)
        form.addRow(self.tr("Lage:"), side)
        form.addRow(apply)
        layout.addWidget(box)

        def on_apply() -> None:
            current = self.container.get(wire.id)
            new = replace(current, label=edit.text(), label_side=int(side.currentData()))
            if new != current:
                self.push(ReplaceEntitiesCommand(self.container, [new], self.tr("Beschriftung")))

        apply.clicked.connect(on_apply)
        edit.returnPressed.connect(on_apply)

    def _edit_grid_settings(self) -> None:
        dialog = GridDialog(self.canvas.grid_spacing(), self.canvas.snap_spacing, self)
        if dialog.exec() == GridDialog.DialogCode.Accepted:
            self.canvas.set_grid_spacing(dialog.grid_spacing())
            self.canvas.set_snap_spacing(dialog.snap_spacing())

    # -- slots --------------------------------------------------------------

    def _on_tool_changed(self) -> None:
        prompt = self.tools.prompt() or self.tr("Befehl:")
        self.command_line.set_prompt(prompt)
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
        self.act_osnap.setChecked(settings.value("view/osnap_enabled", True, type=bool))
        modes = settings.value("view/osnap_modes", None)
        if isinstance(modes, str):
            modes = [modes] if modes else []
        valid = {m.value for m in SnapMode}
        self.canvas.osnap_modes = (
            frozenset(SnapMode(m) for m in modes if m in valid) if modes is not None else ALL_MODES
        )
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
        settings.setValue("view/osnap_enabled", self.act_osnap.isChecked())
        settings.setValue("view/osnap_modes", sorted(m.value for m in self.canvas.osnap_modes))
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
