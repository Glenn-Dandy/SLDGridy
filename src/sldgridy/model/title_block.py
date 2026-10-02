"""Built-in title block after DIN EN ISO 7200 and its field tags."""

from sldgridy.model.blocks import BlockDefinition
from sldgridy.model.container import EntityContainer
from sldgridy.model.entities import AttributeDefinition, Line, Rectangle, Text
from sldgridy.model.geometry import Point

TITLE_BLOCK_NAME = "Schriftfeld"
TITLE_BLOCK_WIDTH = 180.0
TITLE_BLOCK_HEIGHT = 36.0

# Field tags filled automatically in title blocks on sheets.
DOCUMENT_FIELDS = ("PROJEKT", "FIRMA", "BEARBEITER")
SHEET_FIELDS = ("TITEL", "ZEICHNUNGSNR", "DATUM", "GEPRUEFT", "AENDERUNG")
COMPUTED_FIELDS = ("BLATT", "FORMAT")
ALL_FIELDS = DOCUMENT_FIELDS + SHEET_FIELDS + COMPUTED_FIELDS

FIELD_LABELS = {
    "PROJEKT": "Projekt",
    "FIRMA": "Firma",
    "BEARBEITER": "Bearbeiter",
    "TITEL": "Titel",
    "ZEICHNUNGSNR": "Zeichnungsnummer",
    "DATUM": "Datum",
    "GEPRUEFT": "Geprüft",
    "AENDERUNG": "Änderungsindex",
    "BLATT": "Blatt",
    "FORMAT": "Format",
}

LABEL_HEIGHT = 1.8
VALUE_HEIGHT = 3.5
OUTER = 0.7
INNER = 0.35

# Cells (left, top, right, bottom, tag, value height) relative to the bottom
# right corner, which is the base point.
_CELLS = (
    (-180, -36, -120, -18, "FIRMA", 5.0),
    (-180, -18, -120, -9, "BEARBEITER", VALUE_HEIGHT),
    (-180, -9, -120, 0, "GEPRUEFT", VALUE_HEIGHT),
    (-120, -36, -40, -27, "PROJEKT", VALUE_HEIGHT),
    (-120, -27, -40, -9, "TITEL", 5.0),
    (-120, -9, -40, 0, "ZEICHNUNGSNR", VALUE_HEIGHT),
    (-40, -36, 0, -27, "AENDERUNG", VALUE_HEIGHT),
    (-40, -27, 0, -18, "DATUM", VALUE_HEIGHT),
    (-40, -18, 0, -9, "BLATT", VALUE_HEIGHT),
    (-40, -9, 0, 0, "FORMAT", VALUE_HEIGHT),
)


def title_block_definition() -> BlockDefinition:
    entities = [
        Rectangle(id="frame", p1=Point(-180, -36), p2=Point(0, 0), lineweight=OUTER),
        Line(id="v1", p1=Point(-120, -36), p2=Point(-120, 0), lineweight=INNER),
        Line(id="v2", p1=Point(-40, -36), p2=Point(-40, 0), lineweight=INNER),
    ]
    for n, (left, top, right, bottom, tag, height) in enumerate(_CELLS):
        if bottom < 0:
            entities.append(
                Line(id=f"h{n}", p1=Point(left, bottom), p2=Point(right, bottom), lineweight=INNER)
            )
        entities.append(
            Text(
                id=f"label_{tag.lower()}",
                position=Point(left + 1.0, top + 1.0 + LABEL_HEIGHT),
                text=FIELD_LABELS[tag],
                height=LABEL_HEIGHT,
            )
        )
        entities.append(
            AttributeDefinition(
                id=f"att_{tag.lower()}",
                tag=tag,
                prompt=FIELD_LABELS[tag],
                position=Point(left + 1.5, (top + bottom) / 2 + 1.5),
                height=height,
                valign="middle",
            )
        )
    return BlockDefinition(
        name=TITLE_BLOCK_NAME,
        base_point=Point(0, 0),
        entities=EntityContainer(entities),
        category="Rahmen",
        description="Schriftfeld nach DIN EN ISO 7200, 180 mm breit",
    )
