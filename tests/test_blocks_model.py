import pytest
from PyQt6.QtGui import QUndoStack

from blocks_fixtures import blocks, fuse
from sldgridy.commands.blocks import AddBlockCommand, ReplaceBlockCommand, SetBasePointCommand
from sldgridy.fileio.json_format import (
    block_signature,
    document_from_dict,
    document_to_dict,
    entity_from_dict,
    entity_to_dict,
    library_from_dict,
    library_to_dict,
)
from sldgridy.model.blocks import (
    BlockDefinition,
    BlockError,
    dependencies,
    expand,
    explode,
    readable,
    world_connections,
    would_create_cycle,
)
from sldgridy.model.container import EntityContainer
from sldgridy.model.document import Document
from sldgridy.model.entities import (
    AttributeDefinition,
    BlockReference,
    Circle,
    ConnectionPoint,
    Line,
    Text,
)
from sldgridy.model.geometry import Point


def ref(**kw) -> BlockReference:
    return BlockReference(id="r", name="Sicherung", insert=Point(100, 50), **kw)


def lines(entities):
    return [e for e in entities if isinstance(e, Line)]


def test_expand_plain_reference():
    parts = expand(ref(attributes=(("BMK", "F7"),)), blocks())
    (line,) = lines(parts)
    assert (line.p1, line.p2) == (Point(100, 50), Point(100, 60))
    (text,) = [e for e in parts if isinstance(e, Text)]
    assert text.text == "F7" and text.position == Point(105, 55)
    assert not any(isinstance(e, ConnectionPoint) for e in parts)


def test_attribute_default_used_when_missing():
    (text,) = [e for e in expand(ref(), blocks()) if isinstance(e, Text)]
    assert text.text == "F1"


def test_expand_rotated_reference():
    (line,) = lines(expand(ref(rotation=90), blocks()))
    # Local (0, 10) points down; rotated 90 counter-clockwise it points right.
    assert (line.p1, line.p2) == (Point(100, 50), Point(110, 50))


def test_expand_mirrored_reference_with_base_point():
    definition = fuse()
    definition.base_point = Point(0, 10)
    parts = expand(ref(mirrored_x=True), {"Sicherung": definition})
    (line,) = lines(parts)
    assert {line.p1, line.p2} == {Point(100, 40), Point(100, 50)}
    (text,) = [e for e in parts if isinstance(e, Text)]
    assert text.position == Point(95, 45)


@pytest.mark.parametrize(("rotation", "expected"), [(0, 0), (90, 90), (180, 0), (270, 90)])
def test_attribute_text_stays_readable(rotation, expected):
    (text,) = [e for e in expand(ref(rotation=rotation), blocks()) if isinstance(e, Text)]
    assert text.rotation == expected


def test_readable_flips_alignment():
    t = Text(id="t", position=Point(0, 0), text="X", rotation=180, halign="left")
    r = readable(t)
    assert (r.rotation, r.halign, r.position) == (0, "right", Point(0, 0))


def test_invisible_attribute_not_shown():
    definition = fuse()
    att = definition.entities.get("a")
    from dataclasses import replace

    definition.entities.replace(replace(att, visible=False))
    assert not [e for e in expand(ref(), {"Sicherung": definition}) if isinstance(e, Text)]


def test_layer_zero_entities_inherit_reference_style():
    parts = expand(ref(layer="Schutz", color="#ff0000"), blocks())
    assert all(p.layer == "Schutz" and p.color == "#ff0000" for p in parts)


def test_nested_expansion():
    parts = expand(BlockReference(id="p", name="Feld", insert=Point(0, 0)), blocks())
    circles = sorted((c.center.x, c.center.y) for c in parts if isinstance(c, Circle))
    assert circles == [(-5, 5), (5, 5)]


def test_world_connections_follow_transform():
    conns = world_connections(ref(rotation=90), blocks())
    assert {(c.name, c.position, c.direction) for c in conns} == {
        ("1", Point(100, 50), 180),
        ("2", Point(110, 50), 0),
    }


def test_explode_one_level_with_new_ids():
    parts = explode(BlockReference(id="p", name="Feld", insert=Point(0, 0)), blocks())
    assert sorted(type(p).__name__ for p in parts) == ["BlockReference", "BlockReference", "Line"]
    assert {p.id for p in parts}.isdisjoint({"bus", "f1", "f2"})


def test_cycle_detection():
    b = blocks()
    assert would_create_cycle(
        "Sicherung", [BlockReference(id="x", name="Feld", insert=Point(0, 0))], b
    )
    assert not would_create_cycle(
        "Neu", [BlockReference(id="x", name="Feld", insert=Point(0, 0))], b
    )
    b["Sicherung"].entities.add(BlockReference(id="loop", name="Feld", insert=Point(0, 0)))
    with pytest.raises(BlockError):
        expand(BlockReference(id="p", name="Feld", insert=Point(0, 0)), b)


def test_dependencies():
    assert dependencies("Feld", blocks()) == ["Feld", "Sicherung"]


def test_reference_mirror_and_rotate_compose():
    r = ref(rotation=90)
    m = r.mirrored(Point(100, 0), horizontal=False)
    assert (m.rotation, m.mirrored_x) == (270, True)
    h = r.mirrored(Point(0, 50), horizontal=True)
    assert (h.rotation, h.mirrored_x) == (90, True)
    # Mirroring geometry of the reference equals mirroring its expanded parts.
    parts = sorted((p.p1, p.p2) for p in lines(expand(h, blocks())))
    expected = sorted(
        (q.p1, q.p2) for q in (e.mirrored(Point(0, 50), True) for e in lines(expand(r, blocks())))
    )
    assert [sorted(pair, key=lambda p: (p.x, p.y)) for pair in parts] == [
        sorted(pair, key=lambda p: (p.x, p.y)) for pair in expected
    ]


@pytest.mark.parametrize(
    "entity",
    [
        BlockReference(
            id="r",
            name="X",
            insert=Point(1, 2),
            rotation=270,
            mirrored_x=True,
            attributes=(("BMK", "Q1"), ("TYP", "NH00")),
        ),
        AttributeDefinition(
            id="a",
            tag="BMK",
            prompt="p",
            default="d",
            position=Point(1, 1),
            visible=False,
            halign="center",
        ),
        ConnectionPoint(id="c", name="L1", position=Point(3, 4), direction=180),
        Text(id="t", position=Point(0, 0), text="x", halign="right", valign="middle"),
    ],
    ids=lambda e: type(e).__name__,
)
def test_new_entity_roundtrip(entity):
    assert entity_from_dict(entity_to_dict(entity)) == entity


def test_document_with_blocks_roundtrip():
    doc = Document.new("Blatt 1")
    doc.blocks.update(blocks())
    doc.model_space.add(ref())
    data = document_to_dict(doc)
    again = document_from_dict(data)
    assert document_to_dict(again) == data
    assert {"Sicherung", "Feld"} <= set(again.blocks)


def test_library_roundtrip_and_signature():
    lib = library_to_dict(list(blocks().values()), "Test")
    name, loaded = library_from_dict(lib)
    assert name == "Test" and [b.name for b in loaded] == ["Sicherung", "Feld"]
    a, b = fuse(), fuse()
    assert block_signature(a) == block_signature(b)
    copy = BlockDefinition(
        "Sicherung", Point(0, 0), EntityContainer([e.with_new_id() for e in a.entities]), "Schalten"
    )
    assert block_signature(copy) == block_signature(a)


def check(doc, command):
    stack = QUndoStack()
    before = document_to_dict(doc)
    stack.push(command)
    after = document_to_dict(doc)
    assert after != before
    stack.undo()
    assert document_to_dict(doc) == before
    stack.redo()
    assert document_to_dict(doc) == after


def test_block_commands():
    doc = Document.new("Blatt 1")
    check(doc, AddBlockCommand(doc, fuse(), "add"))
    changed = fuse()
    changed.entities.remove("c")
    check(doc, ReplaceBlockCommand(doc, changed, "replace"))


def test_set_base_point_command():
    d = fuse()
    stack = QUndoStack()
    stack.push(SetBasePointCommand(d, Point(1, 2), "base"))
    assert d.base_point == Point(1, 2)
    stack.undo()
    assert d.base_point == Point(0, 0)


def test_block_in_use_and_layer_usage_inside_blocks():
    doc = Document.new("Blatt 1")
    doc.blocks.update(blocks())
    assert doc.block_in_use("Sicherung")  # used inside "Feld"
    assert not doc.block_in_use("Feld")
