"""Dialog for choosing the active object snap modes."""

from PyQt6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QVBoxLayout

from sldgridy.model.snap import SnapMode


class OsnapDialog(QDialog):
    def __init__(self, modes: frozenset[SnapMode], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Objektfang"))
        labels = {
            SnapMode.CONNECTION: self.tr("Anschlusspunkt (hat Vorrang)"),
            SnapMode.ENDPOINT: self.tr("Endpunkt"),
            SnapMode.MIDPOINT: self.tr("Mittelpunkt"),
            SnapMode.INTERSECTION: self.tr("Schnittpunkt"),
            SnapMode.CENTER: self.tr("Zentrum"),
        }
        layout = QVBoxLayout(self)
        self._boxes: dict[SnapMode, QCheckBox] = {}
        for mode, label in labels.items():
            box = QCheckBox(label)
            box.setChecked(mode in modes)
            layout.addWidget(box)
            self._boxes[mode] = box
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def modes(self) -> frozenset[SnapMode]:
        return frozenset(m for m, box in self._boxes.items() if box.isChecked())
