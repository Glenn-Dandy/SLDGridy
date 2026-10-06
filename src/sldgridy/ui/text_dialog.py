"""Dialog for entering or editing a text entity."""

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QPlainTextEdit,
    QVBoxLayout,
)

from sldgridy.model.entities import DEFAULT_TEXT_HEIGHT
from sldgridy.ui.styles import HeightCombo


class TextDialog(QDialog):
    def __init__(self, parent=None, text: str = "", height: float | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Text"))

        self.edit = QPlainTextEdit(text)
        self.edit.setPlaceholderText(self.tr("Mehrere Zeilen mit Enter trennen"))
        self.height_box = HeightCombo()
        self.height_box.set_height(DEFAULT_TEXT_HEIGHT if height is None else height)

        form = QFormLayout()
        form.addRow(self.tr("Texthöhe:"), self.height_box)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.edit)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.resize(420, 220)
        self.edit.setFocus()

    def text(self) -> str:
        return self.edit.toPlainText()

    def text_height(self) -> float:
        return self.height_box.height() or DEFAULT_TEXT_HEIGHT
