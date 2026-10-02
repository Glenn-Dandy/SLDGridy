"""Block definitions and the expansion of block references into plain entities."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace

from sldgridy.model.container import EntityContainer
from sldgridy.model.entities import (
    AttributeDefinition,
    BlockReference,
    ConnectionPoint,
    Entity,
    Text,
)
from sldgridy.model.geometry import Point
from sldgridy.model.layers import DEFAULT_LAYER

MAX_NESTING = 32


@dataclass
class BlockDefinition:
    name: str
    base_point: Point = field(default_factory=lambda: Point(0.0, 0.0))
    entities: EntityContainer = field(default_factory=EntityContainer)
    category: str = ""
    description: str = ""

    def attribute_definitions(self) -> list[AttributeDefinition]:
        return [e for e in self.entities if isinstance(e, AttributeDefinition)]

    def connection_points(self) -> list[ConnectionPoint]:
        return [e for e in self.entities if isinstance(e, ConnectionPoint)]

    def copy(self, name: str | None = None) -> "BlockDefinition":
        return BlockDefinition(
            name=self.name if name is None else name,
            base_point=self.base_point,
            entities=EntityContainer(list(self.entities)),
            category=self.category,
            description=self.description,
        )


class BlockError(ValueError):
    pass


def referenced_names(entities: Iterable[Entity]) -> set[str]:
    return {e.name for e in entities if isinstance(e, BlockReference)}


def dependencies(name: str, blocks: Mapping[str, BlockDefinition]) -> list[str]:
    """All block names ``name`` needs (itself first, then nested), without duplicates."""
    order: list[str] = []
    stack = [name]
    while stack:
        n = stack.pop()
        if n in order:
            continue
        order.append(n)
        definition = blocks.get(n)
        if definition is not None:
            stack.extend(sorted(referenced_names(definition.entities)))
    return order


def would_create_cycle(
    name: str, entities: Iterable[Entity], blocks: Mapping[str, BlockDefinition]
) -> bool:
    """True if a definition ``name`` holding ``entities`` would reference itself."""
    seen: set[str] = set()
    stack = list(referenced_names(entities))
    while stack:
        n = stack.pop()
        if n == name:
            return True
        if n in seen:
            continue
        seen.add(n)
        definition = blocks.get(n)
        if definition is not None:
            stack.extend(referenced_names(definition.entities))
    return False


def to_world(ref: BlockReference, base: Point, e: Entity) -> Entity:
    """Map a definition entity into drawing coordinates of ``ref``."""
    e = e.translated(-base.x, -base.y)
    if ref.mirrored_x:
        e = e.mirrored(Point(0.0, 0.0), horizontal=False)
    e = e.rotated(Point(0.0, 0.0), ref.rotation // 90)
    return e.translated(ref.insert.x, ref.insert.y)


def point_to_world(ref: BlockReference, base: Point, p: Point) -> Point:
    probe = ConnectionPoint(id="", name="", position=p)
    return to_world(ref, base, probe).position


_FLIP_HALIGN = {"left": "right", "right": "left", "center": "center"}


def readable(text: Text) -> Text:
    """Turn upside-down (180) or downward (270) text into 0 or 90 around the same anchor."""
    if text.rotation % 360 not in (180, 270):
        return text
    return replace(
        text, rotation=(text.rotation - 180) % 360, halign=_FLIP_HALIGN.get(text.halign, "left")
    )


def _inherit(ref: BlockReference, e: Entity) -> Entity:
    """Entities on layer 0 take layer and style of the reference."""
    if e.layer != DEFAULT_LAYER:
        return e
    return replace(
        e,
        layer=ref.layer,
        color=e.color if e.color is not None else ref.color,
        lineweight=e.lineweight if e.lineweight is not None else ref.lineweight,
        linetype=e.linetype if e.linetype is not None else ref.linetype,
    )


def explode(
    ref: BlockReference, blocks: Mapping[str, BlockDefinition], keep_ids: bool = False
) -> list[Entity]:
    """One level of a reference as drawing entities.

    Attribute definitions become texts with the reference's values (invisible
    ones are dropped), connection points are dropped, nested references stay.
    """
    definition = blocks.get(ref.name)
    if definition is None:
        return []
    out: list[Entity] = []
    for e in definition.entities:
        if isinstance(e, ConnectionPoint):
            continue
        if isinstance(e, AttributeDefinition):
            if not e.visible:
                continue
            world = to_world(ref, definition.base_point, e)
            text = readable(world.as_text(ref.attribute(e.tag, e.default)))
            out.append(text if keep_ids else text.with_new_id())
            continue
        world = to_world(ref, definition.base_point, e)
        out.append(world if keep_ids else world.with_new_id())
    return [_inherit(ref, e) for e in out]


def expand(
    ref: BlockReference, blocks: Mapping[str, BlockDefinition], depth: int = 0
) -> list[Entity]:
    """All drawing entities of a reference, nested references resolved."""
    if depth > MAX_NESTING:
        raise BlockError(f"block nesting too deep at {ref.name!r}")
    out: list[Entity] = []
    for e in explode(ref, blocks, keep_ids=True):
        if isinstance(e, BlockReference):
            out.extend(expand(e, blocks, depth + 1))
        else:
            out.append(e)
    return out


def world_connections(
    ref: BlockReference, blocks: Mapping[str, BlockDefinition]
) -> list[ConnectionPoint]:
    """Connection points of the reference's own definition in drawing coordinates."""
    definition = blocks.get(ref.name)
    if definition is None:
        return []
    return [to_world(ref, definition.base_point, c) for c in definition.connection_points()]
