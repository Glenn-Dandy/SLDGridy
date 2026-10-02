"""Conversion between the document model and the versioned JSON structure."""

from collections.abc import Callable
from typing import Any

from sldgridy import __version__
from sldgridy.model.container import EntityContainer
from sldgridy.model.document import Document, ModelSpace, SheetLayout
from sldgridy.model.entities import Arc, Circle, Entity, Line, Polyline, Rectangle, Text
from sldgridy.model.geometry import Point
from sldgridy.model.layers import DEFAULT_LAYER, Layer
from sldgridy.model.paper import Orientation

FORMAT_VERSION = 1

# Migration from version N to N + 1, keyed by N.
MIGRATIONS: dict[int, Callable[[dict], dict]] = {}


class FileFormatError(Exception):
    pass


# -- points ---------------------------------------------------------------


def _pt(p: Point) -> list[float]:
    return [p.x, p.y]


def _to_pt(v: Any) -> Point:
    x, y = v
    return Point(float(x), float(y))


# -- entities -------------------------------------------------------------

_TYPE_NAMES: dict[type, str] = {
    Line: "line",
    Polyline: "polyline",
    Rectangle: "rectangle",
    Circle: "circle",
    Arc: "arc",
    Text: "text",
}


def entity_to_dict(e: Entity) -> dict[str, Any]:
    d: dict[str, Any] = {"type": _TYPE_NAMES[type(e)], "id": e.id, "layer": e.layer}
    for key in ("color", "lineweight", "linetype"):
        value = getattr(e, key)
        if value is not None:
            d[key] = value
    match e:
        case Line() | Rectangle():
            d["p1"], d["p2"] = _pt(e.p1), _pt(e.p2)
        case Polyline():
            d["points"] = [_pt(p) for p in e.points]
            d["closed"] = e.closed
        case Circle():
            d["center"], d["radius"] = _pt(e.center), e.radius
        case Arc():
            d["center"], d["radius"] = _pt(e.center), e.radius
            d["start_angle"], d["end_angle"] = e.start_angle, e.end_angle
        case Text():
            d["position"], d["text"] = _pt(e.position), e.text
            d["height"], d["rotation"] = e.height, e.rotation
    return d


def entity_from_dict(d: dict[str, Any]) -> Entity:
    common = {
        "id": str(d["id"]),
        "layer": str(d.get("layer", DEFAULT_LAYER)),
        "color": d.get("color"),
        "lineweight": d.get("lineweight"),
        "linetype": d.get("linetype"),
    }
    kind = d.get("type")
    match kind:
        case "line":
            return Line(p1=_to_pt(d["p1"]), p2=_to_pt(d["p2"]), **common)
        case "rectangle":
            return Rectangle(p1=_to_pt(d["p1"]), p2=_to_pt(d["p2"]), **common)
        case "polyline":
            return Polyline(
                points=tuple(_to_pt(p) for p in d["points"]),
                closed=bool(d.get("closed", False)),
                **common,
            )
        case "circle":
            return Circle(center=_to_pt(d["center"]), radius=float(d["radius"]), **common)
        case "arc":
            return Arc(
                center=_to_pt(d["center"]),
                radius=float(d["radius"]),
                start_angle=float(d["start_angle"]),
                end_angle=float(d["end_angle"]),
                **common,
            )
        case "text":
            return Text(
                position=_to_pt(d["position"]),
                text=str(d["text"]),
                height=float(d["height"]),
                rotation=int(d.get("rotation", 0)),
                **common,
            )
    raise FileFormatError(f"unknown entity type {kind!r}")


# -- document -------------------------------------------------------------


def _layer_to_dict(layer: Layer) -> dict[str, Any]:
    return {
        "name": layer.name,
        "color": layer.color,
        "lineweight": layer.lineweight,
        "linetype": layer.linetype,
        "visible": layer.visible,
        "locked": layer.locked,
        "printable": layer.printable,
    }


def _layer_from_dict(d: dict[str, Any]) -> Layer:
    return Layer(
        name=str(d["name"]),
        color=str(d.get("color", "#000000")),
        lineweight=float(d.get("lineweight", 0.25)),
        linetype=str(d.get("linetype", "continuous")),
        visible=bool(d.get("visible", True)),
        locked=bool(d.get("locked", False)),
        printable=bool(d.get("printable", True)),
    )


def document_to_dict(doc: Document) -> dict[str, Any]:
    return {
        "format_version": FORMAT_VERSION,
        "application": f"SLDGridy {__version__}",
        "layers": [_layer_to_dict(layer) for layer in doc.layers],
        "blocks": [],
        "model": {"entities": [entity_to_dict(e) for e in doc.model_space]},
        "sheets": [
            {
                "name": s.name,
                "paper": s.paper,
                "orientation": s.orientation.value,
                "entities": [entity_to_dict(e) for e in s.entities],
            }
            for s in doc.sheets
        ],
    }


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    """Bring ``data`` up to FORMAT_VERSION."""
    version = data.get("format_version")
    if not isinstance(version, int) or version < 1:
        raise FileFormatError("missing or invalid format_version")
    if version > FORMAT_VERSION:
        raise FileFormatError(
            f"file format version {version} is newer than supported version {FORMAT_VERSION}"
        )
    while version < FORMAT_VERSION:
        data = MIGRATIONS[version](data)
        version += 1
        data["format_version"] = version
    return data


def document_from_dict(data: dict[str, Any]) -> Document:
    data = migrate(data)
    try:
        layers = [_layer_from_dict(d) for d in data.get("layers", [])]
        if not any(layer.name == DEFAULT_LAYER for layer in layers):
            layers.insert(0, Layer(DEFAULT_LAYER))
        model = ModelSpace(entity_from_dict(d) for d in data["model"]["entities"])
        sheets = [
            SheetLayout(
                name=str(s["name"]),
                paper=str(s["paper"]),
                orientation=Orientation(s["orientation"]),
                entities=EntityContainer(entity_from_dict(d) for d in s.get("entities", [])),
            )
            for s in data["sheets"]
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise FileFormatError(f"invalid drawing data: {exc}") from exc
    return Document(model_space=model, sheets=sheets, layers=layers)
