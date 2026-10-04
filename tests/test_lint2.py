from fakeworld import entity, from_stamp, snapshot
from lint import lint

POWER = """\
....E^E^E^
....E^E^E^
....E^E^E^
....E^E^E^
....E^E^E^
....B^B^B^
O>x.B^B^B^
"""


def run(text, X=0, Y=0, rot=0, extra=()):
    ents, codes = from_stamp(text, X, Y, rot)
    return lint(snapshot([X - 50, Y - 50, X + 60, Y + 60], list(ents) + list(extra)), codes)


def rules(found):
    return sorted((f.tile, f.rule) for f in found)


def test_power_block_is_clean_in_every_rotation():
    for rot in (0, 90, 180, 270):
        assert run(POWER, 7, -3, rot) == [], rot


def test_rotated_boiler_sabotage():
    # boiler steam output pointing east instead of up into the engine: wrong
    # footprint shape for that facing, so build the sabotage at entity level
    ents, codes = from_stamp(POWER)
    boiler = next(e for e in ents if e["name"] == "boiler")
    ents.remove(boiler)
    turned = entity("boiler", (2, 4), direction=4, w=2, h=3)
    ents.append(turned)
    codes = {k: v for k, v in codes.items() if v[0] != "B"}
    codes[(2, 4)] = ("B", ">")
    found = rules(lint(snapshot([-10, -10, 20, 20], ents), codes))
    assert ((2, 4), "fluid-open") in found or ((2, 4), "fluid-isolated") in found


def test_pump_pointing_away_is_open():
    found = rules(run(POWER.replace("O>x.", "O<x.")))
    assert ((0, 6), "fluid-isolated") in found


def test_missing_pipe_isolates():
    found = rules(run(POWER.replace("O>x.", "O>..")))
    assert ((0, 6), "fluid-isolated") in found
    assert ((2, 5), "fluid-open") in found  # boiler has no water input


def test_engine_without_boiler_is_isolated():
    assert ((0, 0), "fluid-isolated") in rules(run("E^E^E^\nE^E^E^\nE^E^E^\nE^E^E^\nE^E^E^\n"))


# --- power network
def test_lab_on_pole_chain_to_engine_ok():
    # engine with a pole next to it, chain of poles 7 apart, lab under the last
    engine = entity("steam-engine", (0, 0), w=3, h=5, ghost=False)
    poles = [entity("small-electric-pole", (3 + 7 * i, 2), ghost=False) for i in range(4)]
    assert run("L.L.L.\nL.L.L.\nL.L.L.\n", X=22, Y=3, extra=[engine] + poles) == []


def test_lab_on_pole_chain_with_gap_has_no_source():
    engine = entity("steam-engine", (0, 0), w=3, h=5, ghost=False)
    poles = [entity("small-electric-pole", (3, 2), ghost=False), entity("small-electric-pole", (20, 2), ghost=False)]
    found = rules(run("L.L.L.\nL.L.L.\nL.L.L.\n", X=19, Y=3, extra=[engine] + poles))
    assert found == [((19, 3), "no-power-source")]


def test_built_powered_pole_counts_as_source():
    p = entity("small-electric-pole", (5, 0), ghost=False)
    p["powered"] = True
    assert run("L.L.L.\nL.L.L.\nL.L.L.\n", X=3, Y=1, extra=[p]) == []


def test_lab_with_no_pole_is_power_rule_not_source_rule():
    assert rules(run("L.L.L.\nL.L.L.\nL.L.L.\n")) == [((0, 0), "power")]
