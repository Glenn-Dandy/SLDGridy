"""Dialog for entering or editing a text entity."""

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QPlainTextEdit,
    QVBoxLayout,
)

from sldgridy.model.entities import DEFAULT_TEXT_HEIGHT, TEXT_HEIGHTS
from sldgridy.ui.styles import mm_label


class TextDialog(QDialog):
    def __init__(self, parent=None, text: str = "", height: float | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Text"))

        self.edit = QPlainTextEdit(text)
        self.edit.setPlaceholderText(self.tr("Mehrere Zeilen mit Enter trennen"))
        self.height_box = QComboBox()
        for h in TEXT_HEIGHTS:
            self.height_box.addItem(mm_label(h), h)
        wanted = DEFAULT_TEXT_HEIGHT if height is None else height
        index = self.height_box.findData(wanted)
        self.height_box.setCurrentIndex(index if index >= 0 else 0)

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
        return float(self.height_box.currentData())
