import pytest

from layout import (
    DIR,
    StampError,
    inserter_direction,
    parse_stamp,
    place,
    rotate,
)


def ents(stamp):
    return sorted((e.code, e.x, e.y, e.dchar) for e in stamp.entities)


def test_parse_simple_row():
    s = parse_stamp("b>b>i>c.\n")
    assert (s.w, s.h) == (4, 1)
    assert ents(s) == [("b", 0, 0, ">"), ("b", 1, 0, ">"), ("c", 3, 0, "."), ("i", 2, 0, ">")]


def test_comments_and_blank_lines_ignored():
    s = parse_stamp("# a comment\n\nb>\n")
    assert (s.w, s.h) == (1, 1)


def test_multitile_footprint_collapses_to_one_entity():
    s = parse_stamp("F.F.\nF.F.\n")
    assert ents(s) == [("F", 0, 0, ".")]
    assert s.entities[0].size == 2


def test_two_adjacent_furnaces():
    s = parse_stamp("F.F.F.F.\nF.F.F.F.\n")
    assert ents(s) == [("F", 0, 0, "."), ("F", 2, 0, ".")]


def test_assembler_3x3():
    s = parse_stamp("A.A.A.\nA.A.A.\nA.A.A.\n")
    assert ents(s) == [("A", 0, 0, ".")]


def test_drill_keeps_output_direction():
    s = parse_stamp("DvDv\nDvDv\n")
    assert ents(s) == [("D", 0, 0, "v")]


@pytest.mark.parametrize(
    "text,line,col",
    [
        ("b>Q>\n", 1, 3),          # unknown code
        ("b>b\n", 1, 3),           # odd length
        ("b>b>\nb>\n", 2, 3),      # ragged row
        ("b.\n", 1, 2),            # belt needs a direction
        ("i.\n", 1, 2),            # inserter needs a drop side
        ("c>\n", 1, 2),            # chest takes no direction
        ("F.F.\nF...\n", 2, 3),    # incomplete furnace
        ("..F.F.\n..F.F.\nF.F...\n", 3, 1),  # misaligned footprint
        ("DvD>\nDvDv\n", 1, 3),    # mixed direction in one footprint
    ],
)
def test_malformed_stamps_name_line_and_col(text, line, col):
    with pytest.raises(StampError) as ei:
        parse_stamp(text)
    assert (ei.value.line, ei.value.col) == (line, col), str(ei.value)
    assert f"line {line}" in str(ei.value) and f"col {col}" in str(ei.value)


# --- inserter: direction = pickup side = opposite of drop side (docs/conventions.md)
@pytest.mark.parametrize(
    "drop,direction",
    [(">", DIR["west"]), ("<", DIR["east"]), ("v", DIR["north"]), ("^", DIR["south"])],
)
def test_inserter_drop_side_to_direction(drop, direction):
    assert inserter_direction(drop) == direction


# --- rotation
def test_rotate_0_is_identity():
    s = parse_stamp("b>i>c.\n")
    assert ents(rotate(s, 0)) == ents(s)


def test_rotate_90_row_becomes_column():
    # b> at (0,0), i> at (1,0)  -- 2 wide, 1 tall
    s = rotate(parse_stamp("b>i>\n"), 90)
    assert (s.w, s.h) == (1, 2)
    assert ents(s) == [("b", 0, 0, "v"), ("i", 0, 1, "v")]


def test_rotate_180_and_270():
    s = parse_stamp("b>i>\n")
    r180 = rotate(s, 180)
    assert (r180.w, r180.h) == (2, 1)
    assert ents(r180) == [("b", 1, 0, "<"), ("i", 0, 0, "<")]
    r270 = rotate(s, 270)
    assert ents(r270) == [("b", 0, 1, "^"), ("i", 0, 0, "^")]


def test_rotate_multitile_footprint():
    # furnace at (0,0) 2x2, belt at (2,0) and (2,1): 3 wide, 2 tall
    s = parse_stamp("F.F.bv\nF.F.bv\n")
    r = rotate(s, 90)  # -> 2 wide, 3 tall; furnace on top, belt row below
    assert (r.w, r.h) == (2, 3)
    assert ents(r) == [("F", 0, 0, "."), ("b", 0, 2, "<"), ("b", 1, 2, "<")]


def test_rotate_assembler_270():
    s = parse_stamp("A.A.A.b>\nA.A.A.b>\nA.A.A.b>\n")
    r = rotate(s, 270)
    assert (r.w, r.h) == (3, 4)
    assert ("A", 0, 1, ".") in ents(r)
    assert ("b", 0, 0, "^") in ents(r)


def test_four_rotations_round_trip():
    s = parse_stamp("F.F.i>c.\nF.F.b^..\n")
    r = s
    for _ in range(4):
        r = rotate(r, 90)
    assert ents(r) == ents(s)


def test_bad_rotation():
    with pytest.raises(ValueError):
        rotate(parse_stamp("b>\n"), 45)


# --- placement into world coordinates
def test_place_positions_and_directions():
    s = parse_stamp("F.F.i>c.\nF.F.....\n")
    p = {e.code: e for e in place(s, 10, -5, 0)}
    assert p["F"].name == "stone-furnace"
    assert p["F"].position == (11.0, -4.0)          # 2x2 centred on tile corner
    assert p["F"].tile == (10, -5)
    assert p["i"].name == "burner-inserter"
    assert p["i"].position == (12.5, -4.5)          # 1x1 centred on tile centre
    assert p["i"].direction == DIR["west"]          # drops east -> faces west
    assert p["c"].position == (13.5, -4.5)


def test_place_3x3_centre_and_rotation():
    s = parse_stamp("A.A.A.\nA.A.A.\nA.A.A.\n")
    (a,) = place(s, 0, 0, 90)
    assert a.position == (1.5, 1.5)


def test_place_underground_types():
    p = place(parse_stamp("u>b>U>\n"), 0, 0, 0)
    assert [(e.name, e.belt_type) for e in p] == [
        ("underground-belt", "input"),
        ("transport-belt", None),
        ("underground-belt", "output"),
    ]
    assert all(e.direction == DIR["east"] for e in p)


def test_load_shipped_stamps():
    import glob
    from layout import load_stamp

    paths = glob.glob("stamps/*.txt")
    assert paths
    for path in paths:
        load_stamp(path)
