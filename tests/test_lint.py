from fakeworld import entity, from_stamp, snapshot
from layout import DIR
from lint import lint

BURNER_IRON = "DvDv......DvDv\nDvDv......DvDv\nF.F.......F.F.\nF.F.i>c.i<F.F.\n"


def run(text, X=0, Y=0, rot=0, extra=(), **kw):
    ents, codes = from_stamp(text, X, Y, rot, **kw)
    return lint(snapshot([X - 4, Y - 4, X + 20, Y + 20], list(ents) + list(extra)), codes)


def rules(findings):
    return sorted((f.tile, f.rule) for f in findings)


def test_burner_iron_is_clean():
    assert run(BURNER_IRON) == []


def test_burner_iron_clean_in_all_rotations():
    for rot in (0, 90, 180, 270):
        assert run(BURNER_IRON, 3, -2, rot) == [], rot


def test_sabotage_reversed_inserter_flagged_at_its_tile():
    bad = BURNER_IRON.replace("i>c.", "i<c.")
    found = run(bad, 10, 20)
    # both ends still have inventories, so rule (a) can't see it; the
    # inserter now pushes into a furnace that nothing extracts from.
    assert rules(found) == [((12, 23), "dead-end")]


def test_intent_mismatch_when_engine_disagrees_with_stamp():
    ents, codes = from_stamp(BURNER_IRON)
    ins = next(e for e in ents if e["tile"] == [2, 3])
    ins["drop"], ins["pickup"] = ins["pickup"], ins["drop"]  # engine says reversed
    found = lint(snapshot([-4, -4, 20, 20], ents), codes)
    assert ((2, 3), "intent") in rules(found)


def test_inserter_dropping_on_ground():
    assert rules(run("F.F.i>\nF.F...\n")) == [((2, 0), "inserter")]


def test_inserter_into_belt_is_fine():
    assert run("F.F.i>e^\nF.F.....\n") == []


def test_belt_into_nothing():
    assert rules(run("b>b>\n")) == [((1, 0), "belt-end")]


def test_open_output_e_ok():
    assert run("b>e>\n") == []


def test_belt_into_underground_input_ok():
    assert run("b>u>....U>e>\n") == []


def test_belt_head_on():
    assert ((0, 0), "belt-end") in rules(run("b>e<\n"))


def test_curve_is_not_sideload():
    # b> feeding into a belt going down with nothing behind it = a curve
    assert run("b>bv\n..ev\n") == []


def test_sideload_flagged_unless_s():
    text = "..bv\nb>bv\n..ev\n"  # (0,1) feeds side of a straight vertical line
    assert rules(run(text)) == [((0, 1), "sideload")]
    assert run(text.replace("b>bv", "s>bv")) == []


def test_unpowered_electric_entity():
    assert rules(run("I>\n", extra=())) == [((0, 0), "inserter"), ((0, 0), "power")] or \
        ((0, 0), "power") in rules(run("I>\n"))


def test_powered_by_pole_in_range():
    text = "c.I>c.\n......\np.....\n"
    grid = entity("small-electric-pole", (5, 2), ghost=False)
    grid["powered"] = True  # the stamp's pole links to an existing live network
    assert run(text, extra=[grid]) == []


def test_pole_out_of_range():
    text = "c.I>c.\n......\n......\n......\n......\n......\np.....\n"
    assert rules(run(text)) == [((1, 0), "power")]


def test_unplaceable_ghost():
    found = run("c.\n", can_place=False)
    assert rules(found) == [((0, 0), "placement")]


def test_drill_dropping_on_ground():
    assert rules(run("DvDv\nDvDv\n")) == [((0, 0), "drill")]


def test_neighbours_outside_tag_count_as_present():
    chest = entity("wooden-chest", (3, 0), ghost=False)
    assert run("F.F.i>\nF.F...\n", extra=[chest]) == []


def test_findings_format():
    (f,) = run("b>b>\n")
    assert str(f).startswith("1,0 belt-end:")


def test_underground_pair_in_range_ok():
    assert run("b>u>......U>e>\n") == []


def test_underground_pair_too_far():
    found = rules(run("b>u>..........U>e>\n"))  # 6 tiles apart, max is 5
    assert ((1, 0), "underground") in found and ((7, 0), "underground") in found


def test_lonely_underground_input():
    assert rules(run("b>u>\n")) == [((1, 0), "underground")]


def test_underground_wrong_direction_is_not_a_pair():
    assert ((1, 0), "underground") in rules(run("b>u>....U<\n"))


# Electric drill -> stone furnace; a long-handed inserter fuels the furnace from
# the coal belt (row 7) over the plate belt (row 6); an inserter moves plates out.
SMELT_COLUMN = (
    "MvMvMvMvMvMv\n"
    "MvMvMvMvMvMv\n"
    "MvMvMvMvMvMv\n"
    "..F.F...F.F.\n"
    "p.F.F.p.F.F.\n"
    "..J^Iv..J^Iv\n"
    "e<b<b<b<b<b<\n"
    "b>b>b>b>b>e>\n"
)


def test_electric_smelt_column_clean():
    pole_power = entity("steam-engine", (-3, -3), typ="generator", ghost=False, w=1, h=1)
    pole = entity("small-electric-pole", (-2, -2), ghost=False)
    found = [f for f in run(SMELT_COLUMN, extra=[pole_power, pole]) if f.rule not in ("power",)]
    assert found == [], found


def test_long_inserter_renders_drop_side():
    from render import glyph
    ents, _ = from_stamp("J^\n")
    assert glyph(ents[0]) == "J^"


def test_lone_electric_drill_is_not_fluid_isolated():
    ents, codes = from_stamp("MvMvMv\nMvMvMv\nMvMvMv\n..c...\n")
    ents[0]["fluid"] = [{"at": [-1, 1], "to": [-2, 1]}, {"at": [3, 1], "to": [4, 1]}]
    assert "fluid-isolated" not in [f.rule for f in lint(snapshot([-4, -4, 10, 10], ents), codes)]
