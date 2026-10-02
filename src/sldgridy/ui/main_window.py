"""Main application window."""

from PyQt6.QtCore import QLocale, QPointF, QSettings
from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import QLabel, QMainWindow, QMessageBox

from sldgridy import __version__
from sldgridy.model.document import Document
from sldgridy.view.canvas import Canvas

APP_NAME = "SLDGridy"


class MainWindow(QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._locale = QLocale(QLocale.Language.German, QLocale.Country.Germany)
        self.document = Document.new(self.tr("Blatt 1"))

        self.canvas = Canvas(parent=self)
        self.setCentralWidget(self.canvas)

        self._create_actions()
        self._create_menus()
        self._create_status_bar()

        self.canvas.cursor_moved.connect(self._show_cursor_position)
        self.canvas.zoom_changed.connect(self._show_zoom)

        self.setWindowTitle(self.tr("Unbenannt - {app}").format(app=APP_NAME))
        self.resize(1280, 800)
        self._restore_settings()
        self._show_zoom(self.canvas.zoom())

    # -- setup --------------------------------------------------------------

    def _create_actions(self) -> None:
        self.act_quit = QAction(self.tr("&Beenden"), self)
        self.act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_quit.triggered.connect(self.close)

        self.act_grid = QAction(self.tr("&Raster anzeigen"), self)
        self.act_grid.setCheckable(True)
        self.act_grid.setChecked(self.canvas.grid_visible())
        self.act_grid.setShortcut(QKeySequence("F7"))
        self.act_grid.toggled.connect(self.canvas.set_grid_visible)

        self.act_zoom_extents = QAction(self.tr("&Grenzen zoomen"), self)
        self.act_zoom_extents.setShortcut(QKeySequence("Home"))
        self.act_zoom_extents.triggered.connect(self.canvas.zoom_extents)

        self.act_zoom_in = QAction(self.tr("Ver&größern"), self)
        self.act_zoom_in.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.act_zoom_in.triggered.connect(lambda: self.canvas.set_zoom(self.canvas.zoom() * 1.5))

        self.act_zoom_out = QAction(self.tr("Ver&kleinern"), self)
        self.act_zoom_out.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.act_zoom_out.triggered.connect(lambda: self.canvas.set_zoom(self.canvas.zoom() / 1.5))

        self.act_about = QAction(self.tr("Über {app}").format(app=APP_NAME), self)
        self.act_about.triggered.connect(self._show_about)

    def _create_menus(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu(self.tr("&Datei"))
        file_menu.addAction(self.act_quit)

        view_menu = bar.addMenu(self.tr("&Ansicht"))
        view_menu.addAction(self.act_zoom_in)
        view_menu.addAction(self.act_zoom_out)
        view_menu.addAction(self.act_zoom_extents)
        view_menu.addSeparator()
        view_menu.addAction(self.act_grid)

        help_menu = bar.addMenu(self.tr("&Hilfe"))
        help_menu.addAction(self.act_about)

    def _create_status_bar(self) -> None:
        self.lbl_position = QLabel()
        self.lbl_zoom = QLabel()
        self.lbl_layer = QLabel(self.tr("Ebene: {name}").format(name="0"))
        status = self.statusBar()
        status.addWidget(self.lbl_position, 1)
        status.addPermanentWidget(self.lbl_layer)
        status.addPermanentWidget(self.lbl_zoom)
        self._show_cursor_position(QPointF(0.0, 0.0))

    # -- slots --------------------------------------------------------------

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

    def _save_settings(self) -> None:
        settings = QSettings()
        settings.setValue("main_window/geometry", self.saveGeometry())
        settings.setValue("main_window/state", self.saveState())
        settings.setValue("view/grid_visible", self.act_grid.isChecked())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not getattr(self, "_initial_view_done", False):
            self._initial_view_done = True
            self.canvas.zoom_extents()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_settings()
        super().closeEvent(event)
