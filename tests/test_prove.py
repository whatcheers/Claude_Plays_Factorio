from fx import judge, pole_points


def ent(i, typ, status, tile=(0, 0), **kw):
    return dict({"index": i, "name": typ, "type": typ, "ghost": False, "tile": list(tile), "status": status}, **kw)


def test_majority_rule_passes_intermittent_furnace():
    samples = [[ent(1, "furnace", s)] for s in ("working", "no_ingredients", "working", "working")]
    lines, bad = judge(samples)
    assert bad == []
    assert any("ok in 3/4" in l for l in lines)


def test_mostly_idle_fails():
    samples = [[ent(1, "lab", s)] for s in ("no_power", "no_power", "working")]
    _, bad = judge(samples)
    assert bad and "ok 1/3" in bad[0]


def test_new_types_have_ok_sets():
    for typ in ("boiler", "generator", "offshore-pump", "lab"):
        _, bad = judge([[ent(1, typ, "working")]])
        assert bad == [], typ
        _, bad = judge([[ent(1, typ, "no_fuel")]])
        assert bad, typ


def test_fed_container_must_end_non_empty():
    ins = ent(1, "inserter", "working", tile=(0, 0), drop=[1.5, 0.5])
    chest = ent(2, "container", None, tile=(1, 0))
    _, bad = judge([[ins, chest]])
    assert any("empty" in b for b in bad)
    chest["contents"] = {"iron-plate": 3}
    _, bad = judge([[ins, chest]])
    assert bad == []


def test_pole_points_spacing_and_corner():
    pts = pole_points(0, 0, 20, -15)
    assert pts[0] == (0, 0) and pts[-1] == (20, -15)
    assert (20, 0) in pts
    for a, b in zip(pts, pts[1:]):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) <= 7
        assert a[0] == b[0] or a[1] == b[1]


def test_pole_points_single():
    assert pole_points(3, 3, 3, 3) == [(3, 3)]
