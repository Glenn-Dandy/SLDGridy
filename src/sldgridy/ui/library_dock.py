"""Dock with block previews from the drawing and from library files."""

import json
from pathlib import Path
from typing import Protocol

from PyQt6.QtCore import QMimeData, QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sldgridy.fileio.files import LIBRARY_SUFFIX, load_library
from sldgridy.fileio.json_format import FileFormatError
from sldgridy.fileio.paths import system_library_dir, user_library_dir
from sldgridy.i18n import library_text
from sldgridy.model.blocks import BlockDefinition
from sldgridy.model.document import Document
from sldgridy.view.canvas import BLOCK_MIME
from sldgridy.view.thumbnails import block_icon

DOCUMENT_SOURCE = ""
ALL_LIBRARIES = "*"
ALL_CATEGORIES = "*"
ROLE_PATH = Qt.ItemDataRole.UserRole
ROLE_NAME = Qt.ItemDataRole.UserRole + 1
ROLE_CATEGORY = Qt.ItemDataRole.UserRole + 3


class LibraryHost(Protocol):
    document: Document

    def message(self, text: str) -> None: ...


class _BlockList(QListWidget):
    def mimeTypes(self) -> list[str]:
        return [BLOCK_MIME]

    def mimeData(self, items) -> QMimeData:
        data = QMimeData()
        if items:
            item = items[0]
            payload = {"path": item.data(ROLE_PATH), "name": item.data(ROLE_NAME)}
            data.setData(BLOCK_MIME, json.dumps(payload).encode("utf-8"))
        return data


class Library:
    def __init__(self, path: Path, title: str, blocks: dict[str, BlockDefinition], shipped: bool):
        self.path = path
        self.title = title
        self.blocks = blocks
        self.shipped = shipped


def library_files() -> list[tuple[Path, bool]]:
    """(path, shipped) of all library files, shipped ones first."""
    result: list[tuple[Path, bool]] = []
    for directory, shipped in ((system_library_dir(), True), (user_library_dir(), False)):
        if directory.is_dir():
            result += [(p, shipped) for p in sorted(directory.glob(f"*{LIBRARY_SUFFIX}"))]
    return result


class LibraryDock(QDockWidget):
    # (source path, block name); an empty path means the drawing itself.
    insert_requested = pyqtSignal(str, str)
    edit_requested = pyqtSignal(str, str)
    delete_requested = pyqtSignal(str, str)
    # Name of a block of the drawing.
    save_requested = pyqtSignal(str)

    def __init__(self, host: LibraryHost, parent=None) -> None:
        super().__init__(self.tr("Bibliothek"), parent)
        self.setObjectName("dock_library")
        self._host = host
        self.libraries: dict[str, Library] = {}
        self._icons: dict[tuple[str, str], object] = {}

        self.source = QComboBox()
        self.category = QComboBox()
        self.category.setToolTip(self.tr("Kategorie"))
        self.search = QLineEdit()
        self.search.setPlaceholderText(self.tr("Suchen …"))
        self.search.setClearButtonEnabled(True)
        self.btn_reload = QToolButton()
        self.btn_reload.setText("↻")
        self.btn_reload.setToolTip(self.tr("Bibliotheken neu laden"))
        self.list = _BlockList()
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setIconSize(QSize(56, 56))
        self.list.setGridSize(QSize(96, 92))
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setWordWrap(True)
        self.list.setDragEnabled(True)
        self.list.setDragDropMode(QListWidget.DragDropMode.DragOnly)

        self.source.currentIndexChanged.connect(lambda _i: self._fill())
        self.category.currentIndexChanged.connect(lambda _i: self._apply_filter(self.search.text()))
        self.search.textChanged.connect(self._apply_filter)
        self.btn_reload.clicked.connect(self.reload)
        self.list.itemDoubleClicked.connect(self._on_double_click)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context_menu)

        top = QHBoxLayout()
        top.addWidget(self.source, 1)
        top.addWidget(self.btn_reload)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(top)
        layout.addWidget(self.category)
        layout.addWidget(self.search)
        layout.addWidget(self.list)
        self.setWidget(widget)
        self.reload()

    # -- data ---------------------------------------------------------------

    def library(self, path: str) -> dict[str, BlockDefinition]:
        if path == DOCUMENT_SOURCE:
            return self._host.document.blocks
        lib = self.libraries.get(path)
        return lib.blocks if lib else {}

    def reload(self) -> None:
        self.libraries.clear()
        self._icons.clear()
        for path, shipped in library_files():
            try:
                title, blocks = load_library(path)
            except (OSError, FileFormatError) as exc:
                self._host.message(
                    self.tr("Bibliothek {name} ist fehlerhaft: {error}").format(
                        name=path.name, error=exc
                    )
                )
                continue
            self.libraries[str(path)] = Library(
                path, title or path.stem, {b.name: b for b in blocks}, shipped
            )
        current = self.source.currentData()
        self.source.blockSignals(True)
        self.source.clear()
        self.source.addItem(self.tr("Alle Bibliotheken"), ALL_LIBRARIES)
        self.source.addItem(self.tr("Blöcke der Zeichnung"), DOCUMENT_SOURCE)
        for key, lib in self.libraries.items():
            self.source.addItem(library_text(lib.title), key)
        index = self.source.findData(current) if current is not None else 0
        self.source.setCurrentIndex(max(index, 0))
        self.source.blockSignals(False)
        self._fill()

    def refresh_document(self) -> None:
        for key in [k for k in self._icons if k[0] == DOCUMENT_SOURCE]:
            del self._icons[key]
        if self.source.currentData() == DOCUMENT_SOURCE:
            self._fill()

    # -- list ---------------------------------------------------------------

    def _entries(self) -> list[tuple[str, BlockDefinition]]:
        source = self.source.currentData()
        if source == DOCUMENT_SOURCE:
            return [(DOCUMENT_SOURCE, b) for b in self._host.document.blocks.values()]
        libs = self.libraries.values() if source == ALL_LIBRARIES else [self.libraries[source]]
        return [(str(lib.path), b) for lib in libs for b in lib.blocks.values()]

    def _fill_categories(self, entries: list[tuple[str, BlockDefinition]]) -> None:
        current = self.category.currentData()
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem(self.tr("Alle Kategorien"), ALL_CATEGORIES)
        names = sorted({d.category for _, d in entries if d.category}, key=str.casefold)
        for name in names:
            self.category.addItem(library_text(name), name)
        if any(not d.category for _, d in entries):
            self.category.addItem(self.tr("Ohne Kategorie"), "")
        index = self.category.findData(current) if current is not None else 0
        self.category.setCurrentIndex(max(index, 0))
        self.category.blockSignals(False)

    def _fill(self) -> None:
        self.list.clear()
        entries = sorted(self._entries(), key=lambda e: (e[1].category, e[1].name.casefold()))
        self._fill_categories(entries)
        for path, definition in entries:
            key = (path, definition.name)
            if key not in self._icons:
                self._icons[key] = block_icon(definition.name, self.library(path))
            item = QListWidgetItem(self._icons[key], library_text(definition.name))
            item.setData(ROLE_PATH, path)
            item.setData(ROLE_NAME, definition.name)
            tip = library_text(definition.name)
            if definition.category:
                tip += f"\n{library_text(definition.category)}"
            if definition.description:
                tip += f"\n{library_text(definition.description)}"
            item.setToolTip(tip)
            item.setData(Qt.ItemDataRole.UserRole + 2, tip.casefold())
            item.setData(ROLE_CATEGORY, definition.category)
            self.list.addItem(item)
        self._apply_filter(self.search.text())

    def _apply_filter(self, text: str) -> None:
        needle = text.casefold().strip()
        category = self.category.currentData()
        for i in range(self.list.count()):
            item = self.list.item(i)
            haystack = item.data(Qt.ItemDataRole.UserRole + 2) or ""
            hidden = bool(needle) and needle not in haystack
            if category not in (None, ALL_CATEGORIES):
                hidden = hidden or (item.data(ROLE_CATEGORY) or "") != category
            item.setHidden(hidden)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        self.insert_requested.emit(item.data(ROLE_PATH), item.data(ROLE_NAME))

    def editable(self, path: str) -> bool:
        """Blocks of the drawing and of user libraries can be changed, shipped ones not."""
        if path == DOCUMENT_SOURCE:
            return True
        lib = self.libraries.get(path)
        return lib is not None and not lib.shipped

    def _on_context_menu(self, pos: QPoint) -> None:
        item = self.list.itemAt(pos)
        if item is None:
            return
        path, name = item.data(ROLE_PATH), item.data(ROLE_NAME)
        menu = QMenu(self)
        menu.addAction(self.tr("Einfügen"), lambda: self.insert_requested.emit(path, name))
        if self.editable(path):
            menu.addSeparator()
            menu.addAction(
                self.tr("Eigenschaften bearbeiten …"), lambda: self.edit_requested.emit(path, name)
            )
            if path == DOCUMENT_SOURCE:
                menu.addAction(
                    self.tr("In Benutzerbibliothek speichern"),
                    lambda: self.save_requested.emit(name),
                )
                text = self.tr("Aus Zeichnung löschen")
            else:
                text = self.tr("Aus Bibliothek löschen")
            menu.addAction(text, lambda: self.delete_requested.emit(path, name))
        else:
            menu.addSeparator()
            hint = menu.addAction(self.tr("Mitgelieferte Bibliothek: nicht änderbar"))
            hint.setEnabled(False)
        menu.exec(self.list.viewport().mapToGlobal(pos))
