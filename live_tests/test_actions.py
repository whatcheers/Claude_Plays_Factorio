"""Fair-play actions. Runs in file order; later tests use what earlier ones gathered."""
import math

from helpers import bridge, char_pos, find_clear, fx, write_stamp


def inv():
    with bridge() as b:
        return b.call("inv")["items"]


def nearest(type_, name=None):
    with bridge() as b:
        x, y = char_pos(b)
        for r in (10, 25, 50, 100):
            snap = b.call("scan", {"area": [int(x) - r, int(y) - r, int(x) + r, int(y) + r]})
            pool = snap["resources"] if type_ == "resource" else [e for e in snap["entities"] if e["type"] == type_]
            if name:
                pool = [p for p in pool if p["name"] == name]
            if pool:
                return min(pool, key=lambda p: (p["tile"][0] - x) ** 2 + (p["tile"][1] - y) ** 2)
    raise AssertionError(f"no {type_} {name or ''} within 100 tiles")


def test_inv_lists_items():
    code, out = fx("inv")
    assert code == 0 and out.startswith("at "), out


def test_walk_moves_character():
    with bridge() as b:
        x, y = char_pos(b)
        tx, ty = find_clear(b, 1, 1, start=8)
    code, out = fx("walk", tx + 0.5, ty + 0.5)
    assert code == 0, out
    with bridge() as b:
        nx, ny = b.call("status")["character"]
    assert math.hypot(nx - tx - 0.5, ny - ty - 0.5) < 2.5


def test_walk_unreachable():
    code, out = fx("walk", 1000000, 1000000)
    assert code != 0 and "unreachable" in out, out


def test_mine_out_of_reach_refused():
    with bridge() as b:
        x, y = char_pos(b)
    t = nearest("tree")
    if math.hypot(t["position"][0] - x, t["position"][1] - y) < 12:
        code, out = fx("walk", t["position"][0] + 15, t["position"][1])
    code, out = fx("mine", t["position"][0], t["position"][1])
    assert code != 0 and "out of reach" in out, out


def test_mine_tree_gives_wood():
    t = nearest("tree")
    before = inv().get("wood", 0)
    assert fx("walk", t["position"][0], t["position"][1], "--radius", 1.5)[0] == 0
    code, out = fx("mine", t["position"][0], t["position"][1])
    assert code == 0 and "mined 1" in out, out
    assert inv().get("wood", 0) > before


def test_mine_ore_takes_real_time():
    for ore in ("stone", "coal", "iron-ore", "copper-ore"):
        try:
            r = nearest("resource", ore)
            break
        except AssertionError:
            continue
    px, py = r["tile"][0] + 0.5, r["tile"][1] + 0.5
    assert fx("walk", px, py, "--radius", 1.5)[0] == 0
    with bridge() as b:
        t0 = b.tick()
    before = inv().get(r["name"], 0)
    code, out = fx("mine", px, py, 2)
    assert code == 0 and "mined 2" in out, out
    with bridge() as b:
        t1 = b.tick()
    assert inv().get(r["name"], 0) == before + 2
    assert t1 - t0 >= 2 * 60  # 2 ores at >= 1 s each by hand


def test_craft_refuses_missing_ingredients():
    code, out = fx("craft", "iron-gear-wheel", 5000)
    assert code != 0 and "missing ingredients" in out, out


def test_craft_chest_from_own_wood():
    t = nearest("tree")
    while inv().get("wood", 0) < 4:
        t = nearest("tree")
        fx("walk", t["position"][0], t["position"][1], "--radius", 1.5)
        fx("mine", t["position"][0], t["position"][1])
    before = inv()
    code, out = fx("craft", "wooden-chest", 2)
    assert code == 0, out
    after = inv()
    assert after.get("wooden-chest", 0) == before.get("wooden-chest", 0) + 2
    assert after.get("wood", 0) == before.get("wood", 0) - 4


def test_build_missing_then_build_put_take(tmp_path):
    with bridge() as b:
        x, y = find_clear(b, 2, 1, start=6)
    fx("unplan", "lt-act")
    assert fx("plan", write_stamp(tmp_path, "c.c.c.\n"), x, y, 0, "--tag", "lt-act")[0] == 0
    assert fx("lint", "lt-act")[0] == 0
    assert fx("look", x - 1, y - 1, x + 3, y + 1)[0] == 0
    assert fx("shot", x + 1.5, y + 0.5, 1)[0] == 0
    chests = inv().get("wooden-chest", 0)
    code, out = fx("build", "lt-act")
    built = out.count("built ")
    assert built == min(chests, 3), out
    if chests < 3:
        assert code != 0 and "missing" in out, out
    assert inv().get("wooden-chest", 0) == chests - built   # one item per entity, none created

    # put / take on the first chest (always built: craft test made 2)
    cx, cy = x + 0.5, y + 0.5
    fx("walk", cx, cy + 2, "--radius", 1)
    wood = inv().get("wood", 0)
    if wood == 0:
        t = nearest("tree")
        fx("walk", t["position"][0], t["position"][1], "--radius", 1.5)
        fx("mine", t["position"][0], t["position"][1])
        fx("walk", cx, cy + 2, "--radius", 1)
        wood = inv().get("wood", 0)
    code, out = fx("put", cx, cy, "wood", 1)
    assert code == 0 and "put 1 wood" in out, out
    assert inv().get("wood", 0) == wood - 1
    code, out = fx("take", cx, cy, "wood", 5)
    assert code != 0 and "short" in out, out
    code, out = fx("take", cx, cy, "wood", 1)
    assert code == 0 and "took 1 wood" in out, out
    assert inv().get("wood", 0) == wood

    fx("walk", cx + 20, cy, "--radius", 2)
    code, out = fx("put", cx, cy, "wood", 1)
    assert code != 0 and "out of reach" in out, out
    fx("unplan", "lt-act")
