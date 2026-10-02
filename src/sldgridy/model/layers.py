"""Layers and line style constants."""

from dataclasses import dataclass

# ISO 128 line widths in mm.
LINEWEIGHTS = (0.18, 0.25, 0.35, 0.5, 0.7)
LINETYPES = ("continuous", "dashed", "dashdot")

DEFAULT_LAYER = "0"


@dataclass
class Layer:
    name: str
    color: str = "#000000"
    lineweight: float = 0.25
    linetype: str = "continuous"
    visible: bool = True
    locked: bool = False
    printable: bool = True
