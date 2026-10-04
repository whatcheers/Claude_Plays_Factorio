import pytest

from layout import DIR, StampError, parse_stamp, place, rotate

POWER = """\
# offshore pump -> boiler (steam up) -> steam engine (vertical)
....E^E^E^
....E^E^E^
....E^E^E^
....E^E^E^
....E^E^E^
....B^B^B^
O>x.B^B^B^
"""


def ents(s):
    return sorted((e.code, e.x, e.y, e.dchar, e.w, e.h) for e in s.entities)


def test_boiler_and_engine_footprints():
    s = parse_stamp(POWER)
    assert (s.w, s.h) == (5, 7)
    assert ("B", 2, 5, "^", 3, 2) in ents(s)
    assert ("E", 2, 0, "^", 3, 5) in ents(s)
    assert ("O", 0, 6, ">", 1, 1) in ents(s)
    assert ("x", 1, 6, ".", 1, 1) in ents(s)


def test_horizontal_boiler_is_2_wide_3_tall():
    s = parse_stamp("B>B>\nB>B>\nB>B>\n")
    assert ents(s) == [("B", 0, 0, ">", 2, 3)]


def test_boiler_wrong_shape_for_facing():
    with pytest.raises(StampError):
        parse_stamp("B>B>B>\nB>B>B>\n")  # east-facing boiler must be 2x3


def test_rotate_power_block_all_ways():
    s = parse_stamp(POWER)
    for rot in (90, 180, 270):
        r = rotate(s, rot)
        b = next(e for e in r.entities if e.code == "B")
        e = next(e for e in r.entities if e.code == "E")
        if rot in (90, 270):
            assert (r.w, r.h) == (7, 5)
            assert (b.w, b.h) == (2, 3) and (e.w, e.h) == (5, 3)
        else:
            assert (b.w, b.h) == (3, 2) and (e.w, e.h) == (3, 5)
    r = rotate(s, 90)  # clockwise: steam now points east
    assert next(e for e in r.entities if e.code == "B").dchar == ">"
    # rotate back to start
    r4 = rotate(rotate(rotate(r, 90), 90), 90)
    assert ents(r4) == ents(s)


def test_place_centres_for_rectangles():
    p = {e.code: e for e in place(parse_stamp(POWER), 10, 20, 0)}
    assert p["B"].position == (13.5, 26.0)   # 3x2 at tiles 12..14 x 25..26
    assert p["B"].direction == DIR["north"]
    assert p["E"].position == (13.5, 22.5)   # 3x5 at tiles 12..14 x 20..24
    p90 = {e.code: e for e in place(parse_stamp(POWER), 0, 0, 90)}
    assert p90["E"].direction == DIR["east"]
    assert (p90["E"].w, p90["E"].h) == (5, 3)


def test_recipe_keys():
    s = parse_stamp("@g iron-gear-wheel\n@r automation-science-pack\nAgAgAgArArAr\nAgAgAgArArAr\nAgAgAgArArAr\n")
    p = {e.recipe: e for e in place(s, 0, 0, 0)}
    assert set(p) == {"iron-gear-wheel", "automation-science-pack"}
    assert p["iron-gear-wheel"].tile == (0, 0)
    # recipe keys survive rotation untouched
    p90 = place(s, 0, 0, 90)
    assert {e.recipe for e in p90} == {"iron-gear-wheel", "automation-science-pack"}


def test_unknown_recipe_key_names_line_and_col():
    with pytest.raises(StampError) as ei:
        parse_stamp("@g iron-gear-wheel\nAqAqAq\nAqAqAq\nAqAqAq\n")
    assert (ei.value.line, ei.value.col) == (2, 2)


def test_recipe_key_must_not_be_direction():
    with pytest.raises(StampError):
        parse_stamp("@v iron-gear-wheel\nA.A.A.\nA.A.A.\nA.A.A.\n")


def test_lab_and_plain_assembler():
    s = parse_stamp("L.L.L.A.A.A.\nL.L.L.A.A.A.\nL.L.L.A.A.A.\n")
    assert [(e.code, e.w, e.h) for e in sorted(s.entities, key=lambda e: e.x)] == [("L", 3, 3), ("A", 3, 3)]
