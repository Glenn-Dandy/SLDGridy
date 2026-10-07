from sldgridy.model.container import EntityContainer
from sldgridy.model.entities import Line
from sldgridy.model.geometry import Point


def line(i: str) -> Line:
    return Line(id=i, p1=Point(0, 0), p2=Point(1, 0))


def test_lookups_stay_right_after_inserts_and_removals():
    c = EntityContainer([line("a"), line("b"), line("c")])
    c.add(line("x"), index=1)  # a x b c
    assert [e.id for e in c] == ["a", "x", "b", "c"]
    assert c.index_of("b") == 2 and "x" in c
    assert c.remove("a") == (0, line("a"))
    assert c.index_of("c") == 2 and "a" not in c
    c.remove("c")  # last one
    c.add(line("d"))
    assert [c.index_of(i) for i in ("x", "b", "d")] == [0, 1, 2]
    c.replace(Line(id="b", p1=Point(5, 5), p2=Point(6, 6)))
    assert c.get("b").p1 == Point(5, 5) and c.index_of("b") == 1
