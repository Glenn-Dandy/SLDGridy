"""Shared choices for colours, line widths and line types in the UI."""

from PyQt6.QtCore import QCoreApplication, QLocale
from PyQt6.QtGui import QColor, QIcon, QPixmap

from sldgridy.model.layers import LINETYPES, LINEWEIGHTS

BY_LAYER = "__bylayer__"
MIXED = "__mixed__"
OTHER_COLOR = "__other__"

_LOCALE = QLocale(QLocale.Language.German, QLocale.Country.Germany)


def tr(text: str) -> str:
    return QCoreApplication.translate("styles", text)


def standard_colors() -> list[tuple[str, str]]:
    return [
        (tr("Schwarz"), "#000000"),
        (tr("Rot"), "#e00000"),
        (tr("Orange"), "#f08000"),
        (tr("Grün"), "#008000"),
        (tr("Cyan"), "#00a0b0"),
        (tr("Blau"), "#0000e0"),
        (tr("Magenta"), "#c000c0"),
        (tr("Grau"), "#808080"),
    ]


def linetype_names() -> dict[str, str]:
    names = {
        "continuous": tr("durchgezogen"),
        "dashed": tr("gestrichelt"),
        "dashdot": tr("strichpunktiert"),
    }
    assert set(names) == set(LINETYPES)
    return names


def lineweight_label(value: float) -> str:
    return f"{_LOCALE.toString(value, 'f', 2)} mm"


def lineweight_items() -> list[tuple[str, float]]:
    return [(lineweight_label(w), w) for w in LINEWEIGHTS]


def color_icon(color: str, size: int = 14) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)
