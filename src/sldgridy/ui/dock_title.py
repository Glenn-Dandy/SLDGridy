"""Own title bar for dock widgets.

Floating docks with the native window frame cannot be docked again under
Wayland (no global window positions). With this title bar the dock keeps
its own buttons: the float button and a double click toggle docking.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDockWidget, QHBoxLayout, QLabel, QStyle, QToolButton, QWidget


class DockTitleBar(QWidget):
    def __init__(self, dock: QDockWidget) -> None:
        super().__init__(dock)
        self._dock = dock
        self.label = QLabel(dock.windowTitle())
        self.label.setStyleSheet("font-weight: bold")
        style = self.style()
        self.btn_float = QToolButton()
        self.btn_float.setAutoRaise(True)
        self.btn_float.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))
        self.btn_float.clicked.connect(self.toggle)
        self.btn_close = QToolButton()
        self.btn_close.setAutoRaise(True)
        self.btn_close.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self.btn_close.setToolTip(self.tr("Schließen"))
        self.btn_close.clicked.connect(dock.close)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 2, 2)
        layout.setSpacing(2)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.btn_float)
        layout.addWidget(self.btn_close)
        dock.windowTitleChanged.connect(self.label.setText)
        dock.topLevelChanged.connect(self._update_tooltip)
        self._update_tooltip(dock.isFloating())

    def _update_tooltip(self, floating: bool) -> None:
        self.btn_float.setToolTip(
            self.tr("Andocken (oder Doppelklick auf den Titel)")
            if floating
            else self.tr("Abdocken (oder Doppelklick auf den Titel)")
        )

    def toggle(self) -> None:
        self._dock.setFloating(not self._dock.isFloating())

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


def install_title_bar(dock: QDockWidget) -> DockTitleBar:
    bar = DockTitleBar(dock)
    dock.setTitleBarWidget(bar)
    return bar
