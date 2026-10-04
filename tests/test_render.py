from fakeworld import entity, from_stamp, snapshot
from layout import DIR
from render import render


def grid_rows(text):
    """Grid body rows without rulers: strip the y label and the separator."""
    return [l.split("|", 1)[1] for l in text.splitlines() if "|" in l]


def test_empty_area():
    out = render(snapshot([0, 0, 2, 1]))
    assert grid_rows(out) == ["......", "......"]


def test_rulers_show_coordinates():
    out = render(snapshot([-3, 10, 6, 11]))
    lines = out.splitlines()
    assert "-3" in lines[0] and "0" in lines[0] and "5" in lines[0]
    assert lines[1].lstrip().startswith("10|") or "   10|" in out


def test_terrain_and_resources():
    s = snapshot(
        [0, 0, 3, 0],
        entities=[entity("tree-01", (2, 0), typ="tree", ghost=False), entity("rock-big", (3, 0), typ="simple-entity", ghost=False)],
        resources=[("iron-ore", (0, 0))],
        water=[(1, 0)],
    )
    assert grid_rows(render(s)) == ["'i~~T.R."]


def test_stamp_round_trips_through_render():
    text = "DvDv......DvDv\nDvDv......DvDv\nF.F.......F.F.\nF.F.i>c.i<F.F.\n"
    ents, _ = from_stamp(text, 5, 7)
    out = render(snapshot([5, 7, 11, 10], ents))
    assert grid_rows(out) == text.strip().split("\n")


def test_inserter_drawn_from_drop_position_not_direction():
    # direction says "faces west" (pickup west) -> drops east -> i>
    e = entity("burner-inserter", (0, 0), direction=DIR["west"])
    assert grid_rows(render(snapshot([0, 0, 0, 0], [e]))) == ["i>"]
    # lie about direction but keep engine drop east: render must still say i>
    e["direction"] = DIR["north"]
    assert grid_rows(render(snapshot([0, 0, 0, 0], [e]))) == ["i>"]


def test_rotated_stamp_renders_rotated():
    ents, _ = from_stamp("b>i>c.\n", 0, 0, 90)
    assert grid_rows(render(snapshot([0, 0, 0, 2], ents))) == ["bv", "iv", "c."]


def test_ghosts_listed_built_not():
    g = entity("wooden-chest", (1, 0))
    b = entity("wooden-chest", (0, 0), ghost=False)
    out = render(snapshot([0, 0, 1, 0], [b, g]))
    ghost_lines = [l for l in out.splitlines() if l.startswith("?")]
    assert len(ghost_lines) == 1
    assert "1,0" in ghost_lines[0] and "0,0" not in ghost_lines[0]


def test_underground_and_unknown():
    ents = [
        entity("underground-belt", (0, 0), direction=DIR["east"], belt_type="input"),
        entity("underground-belt", (1, 0), direction=DIR["east"], belt_type="output"),
        entity("steel-chest", (2, 0), typ="container"),
    ]
    assert grid_rows(render(snapshot([0, 0, 2, 0], ents))) == ["u>U>##"]
