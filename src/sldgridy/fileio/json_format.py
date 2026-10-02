"""Conversion between the document model and the versioned JSON structure."""

from collections.abc import Callable
from typing import Any

from sldgridy import __version__
from sldgridy.model.blocks import BlockDefinition
from sldgridy.model.container import EntityContainer
from sldgridy.model.document import Document, ModelSpace, SheetLayout
from sldgridy.model.entities import (
    Arc,
    AttributeDefinition,
    BlockReference,
    Busbar,
    Circle,
    ConnectionPoint,
    Entity,
    Line,
    Polyline,
    Rectangle,
    Text,
    Wire,
)
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
    AttributeDefinition: "attdef",
    ConnectionPoint: "connection",
    BlockReference: "block_ref",
    Wire: "wire",
    Busbar: "busbar",
}


def entity_to_dict(e: Entity) -> dict[str, Any]:
    d: dict[str, Any] = {"type": _TYPE_NAMES[type(e)], "id": e.id, "layer": e.layer}
    for key in ("color", "lineweight", "linetype"):
        value = getattr(e, key)
        if value is not None:
            d[key] = value
    match e:
        case Line() | Rectangle() | Busbar():
            d["p1"], d["p2"] = _pt(e.p1), _pt(e.p2)
        case Wire():
            d["points"] = [_pt(p) for p in e.points]
            if e.label:
                d["label"], d["label_side"], d["label_height"] = (
                    e.label,
                    e.label_side,
                    e.label_height,
                )
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
            if e.halign != "left":
                d["halign"] = e.halign
            if e.valign != "baseline":
                d["valign"] = e.valign
        case AttributeDefinition():
            d["tag"], d["prompt"], d["default"] = e.tag, e.prompt, e.default
            d["position"], d["height"], d["rotation"] = _pt(e.position), e.height, e.rotation
            d["visible"], d["halign"], d["valign"] = e.visible, e.halign, e.valign
        case ConnectionPoint():
            d["name"], d["position"], d["direction"] = e.name, _pt(e.position), e.direction
        case BlockReference():
            d["name"], d["insert"] = e.name, _pt(e.insert)
            d["rotation"], d["mirrored"] = e.rotation, e.mirrored_x
            d["attributes"] = dict(e.attributes)
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
        case "busbar":
            return Busbar(p1=_to_pt(d["p1"]), p2=_to_pt(d["p2"]), **common)
        case "wire":
            return Wire(
                points=tuple(_to_pt(p) for p in d["points"]),
                label=str(d.get("label", "")),
                label_side=1 if int(d.get("label_side", 1)) >= 0 else -1,
                label_height=float(d.get("label_height", 2.5)),
                **common,
            )
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
                halign=str(d.get("halign", "left")),
                valign=str(d.get("valign", "baseline")),
                **common,
            )
        case "attdef":
            return AttributeDefinition(
                tag=str(d["tag"]),
                prompt=str(d.get("prompt", "")),
                default=str(d.get("default", "")),
                position=_to_pt(d["position"]),
                height=float(d.get("height", 2.5)),
                rotation=int(d.get("rotation", 0)),
                visible=bool(d.get("visible", True)),
                halign=str(d.get("halign", "left")),
                valign=str(d.get("valign", "middle")),
                **common,
            )
        case "connection":
            return ConnectionPoint(
                name=str(d["name"]),
                position=_to_pt(d["position"]),
                direction=int(d.get("direction", 0)) % 360,
                **common,
            )
        case "block_ref":
            attributes = d.get("attributes", {})
            if not isinstance(attributes, dict):
                raise FileFormatError("block attributes must be an object")
            return BlockReference(
                name=str(d["name"]),
                insert=_to_pt(d["insert"]),
                rotation=int(d.get("rotation", 0)) % 360,
                mirrored_x=bool(d.get("mirrored", False)),
                attributes=tuple(sorted((str(k), str(v)) for k, v in attributes.items())),
                **common,
            )
    raise FileFormatError(f"unknown entity type {kind!r}")


# -- blocks ---------------------------------------------------------------


def block_to_dict(b: BlockDefinition) -> dict[str, Any]:
    d: dict[str, Any] = {"name": b.name, "base_point": _pt(b.base_point)}
    if b.category:
        d["category"] = b.category
    if b.description:
        d["description"] = b.description
    d["entities"] = [entity_to_dict(e) for e in b.entities]
    return d


def block_from_dict(d: dict[str, Any]) -> BlockDefinition:
    try:
        return BlockDefinition(
            name=str(d["name"]),
            base_point=_to_pt(d.get("base_point", [0, 0])),
            entities=EntityContainer(entity_from_dict(e) for e in d.get("entities", [])),
            category=str(d.get("category", "")),
            description=str(d.get("description", "")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, FileFormatError):
            raise
        raise FileFormatError(f"invalid block definition: {exc}") from exc


def block_signature(b: BlockDefinition) -> dict[str, Any]:
    """Content of a definition without entity ids, for comparing definitions."""
    d = block_to_dict(b)
    d["entities"] = [{k: v for k, v in e.items() if k != "id"} for e in d["entities"]]
    return d


def library_to_dict(blocks: list[BlockDefinition], name: str = "") -> dict[str, Any]:
    return {
        "format_version": FORMAT_VERSION,
        "type": "library",
        "name": name,
        "blocks": [block_to_dict(b) for b in blocks],
    }


def library_from_dict(data: dict[str, Any]) -> tuple[str, list[BlockDefinition]]:
    data = migrate(data)
    if data.get("type") != "library":
        raise FileFormatError("not a library file")
    blocks = data.get("blocks")
    if not isinstance(blocks, list):
        raise FileFormatError("library without blocks")
    return str(data.get("name", "")), [block_from_dict(b) for b in blocks]


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
        "blocks": [block_to_dict(b) for b in doc.blocks.values()],
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
        blocks = {b.name: b for b in (block_from_dict(d) for d in data.get("blocks", []))}
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
    return Document(model_space=model, sheets=sheets, layers=layers, blocks=blocks)
