"""End to end, fair play: gather, smelt a bootstrap batch, craft, plan the
burner-iron stamp on iron ore, check it three ways, build, fuel, prove.

Resumable: if tag `e2e` is already fully built it skips straight to fuel + prove.
Exit 0 only if prove passes and the chest holds at least one iron plate.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fx  # noqa: E402
from bridge import Bridge  # noqa: E402
from layout import load_stamp  # noqa: E402

TAG, BOOT = "e2e", "e2e-boot"
STAMP = os.path.join(fx.ROOT, "stamps", "burner-iron.txt")
BOOT_STAMP = os.path.join(fx.ROOT, "stamps", "furnace.txt")


class E2EFail(Exception):
    pass


def run(*args):
    print(f"$ fx {' '.join(map(str, args))}", flush=True)
    code = fx.main([str(a) for a in args])
    sys.stdout.flush()
    return code


def must(*args):
    if run(*args) != 0:
        raise E2EFail(f"fx {' '.join(map(str, args))} failed")


def inv(b):
    return b.call("inv")["items"]


def nearest_resource(b, name):
    x, y = b.call("status")["character"]
    for r in (16, 40, 80, 150):
        snap = b.call("scan", {"area": [int(x) - r, int(y) - r, int(x) + r, int(y) + r]})
        pool = [t for t in snap["resources"] if t["name"] == name]
        if pool:
            return min(pool, key=lambda t: (t["tile"][0] + 0.5 - x) ** 2 + (t["tile"][1] + 0.5 - y) ** 2)
    raise E2EFail(f"no {name} within 150 tiles")


def gather(b, name, want):
    while inv(b).get(name, 0) < want:
        t = nearest_resource(b, name)
        px, py = t["tile"][0] + 0.5, t["tile"][1] + 0.5
        must("walk", px, py, "--radius", 1.5)
        n = min(want - inv(b).get(name, 0), 10, t.get("amount", 10))
        must("mine", px, py, n)


def gather_wood(b, want):
    while inv(b).get("wood", 0) < want:
        x, y = b.call("status")["character"]
        trees = []
        for r in (20, 50, 100, 150):
            snap = b.call("scan", {"area": [int(x) - r, int(y) - r, int(x) + r, int(y) + r]})
            trees = [e for e in snap["entities"] if e["type"] == "tree"]
            if trees:
                break
        if not trees:
            raise E2EFail("no trees within 150 tiles")
        t = min(trees, key=lambda e: (e["position"][0] - x) ** 2 + (e["position"][1] - y) ** 2)
        must("walk", t["position"][0], t["position"][1], "--radius", 1.5)
        must("mine", t["position"][0], t["position"][1])


def checks(tag, bbox):
    x1, y1, x2, y2 = bbox
    must("look", x1 - 1, y1 - 1, x2 + 1, y2 + 1)
    must("shot", (x1 + x2 + 1) / 2, (y1 + y2 + 1) / 2, 1)
    return run("lint", tag) == 0


def find_site(b, stamp):
    """Top-left where both drill footprints are on iron ore and the stamp area is empty."""
    drills = [(e.x, e.y) for e in stamp.entities if e.code == "D"]
    x, y = b.call("status")["character"]
    best = []
    snap = b.call("scan", {"area": [int(x) - 150, int(y) - 150, int(x) + 150, int(y) + 150]})
    ore = {tuple(t["tile"]) for t in snap["resources"] if t["name"] == "iron-ore"}
    blocked = set()
    for e in snap["entities"]:
        if e["type"] != "character":
            for dx in range(e["w"]):
                for dy in range(e["h"]):
                    blocked.add((e["tile"][0] + dx, e["tile"][1] + dy))
    blocked |= {tuple(t) for t in snap["water"]}
    for (ox, oy) in ore:
        X, Y = ox - drills[0][0], oy - drills[0][1]
        if all((X + dx + i, Y + dy + j) in ore for dx, dy in drills for i in (0, 1) for j in (0, 1)):
            if not any((X + i, Y + j) in blocked for i in range(-1, stamp.w + 1) for j in range(-1, stamp.h + 1)):
                best.append((math.hypot(X - x, Y - y), X, Y))
    if not best:
        raise E2EFail("no free iron-ore site for the stamp within 150 tiles")
    return [(X, Y) for _, X, Y in sorted(best)]


def tag_built(b, tag):
    st = fx.load_state()
    if tag not in st["tags"]:
        return None
    ents = b.call("tag", {"tag": tag}, check=False).get("entities")
    if ents is None:
        return None
    return all(not e.get("invalid") and not e["ghost"] for e in ents)


def bootstrap_plates(b, need):
    """Smelt `need` plates in a temporary furnace from the starting kit, then pick it back up."""
    have = inv(b).get("iron-plate", 0)
    if have >= need:
        return
    n = need - have
    gather(b, "iron-ore", n)
    gather(b, "coal", 2)
    x, y = b.call("status")["character"]
    X, Y = int(x) + 3, int(y) + 3
    for _ in range(20):
        snap = b.call("scan", {"area": [X - 1, Y - 1, X + 2, Y + 2]})
        if not snap["water"] and not any(e["type"] != "character" for e in snap["entities"]):
            break
        X += 3
    run("unplan", BOOT)
    must("plan", BOOT_STAMP, X, Y, 0, "--tag", BOOT)
    if not checks(BOOT, [X, Y, X + 1, Y + 1]):
        raise E2EFail("bootstrap furnace spot failed lint")
    must("build", BOOT)
    must("put", X + 1, Y + 1, "coal", 2)
    must("put", X + 1, Y + 1, "iron-ore", n)
    b.run_ticks(math.ceil(n * 3.2 * 60) + 120)
    must("take", X + 1, Y + 1, "iron-plate", n)
    must("mine", X + 1, Y + 1)  # pick the furnace (and any leftovers) back up
    run("unplan", BOOT)


def main():
    with Bridge() as b:
        must("spawn")
        stamp = load_stamp(STAMP)
        built = tag_built(b, TAG)
        if not built:
            run("unplan", TAG)
            # --- gather and craft: 2 drills, 2 furnaces, 2 burner inserters, 1 chest
            gather(b, "stone", 10)
            gather_wood(b, 2)
            gather(b, "coal", 16)
            gather(b, "iron-ore", 20)
            need_drills = max(0, 2 - inv(b).get("burner-mining-drill", 0))
            need_ins = max(0, 2 - inv(b).get("burner-inserter", 0))
            gears = 3 * need_drills + need_ins
            plates = 2 * gears + 3 * need_drills + need_ins
            bootstrap_plates(b, plates)
            furnaces_needed = 2 + need_drills
            if inv(b).get("stone-furnace", 0) < furnaces_needed:
                gather(b, "stone", 5 * (furnaces_needed - inv(b).get("stone-furnace", 0)))
                must("craft", "stone-furnace", furnaces_needed - inv(b).get("stone-furnace", 0))
            if gears:
                must("craft", "iron-gear-wheel", gears)
            if need_drills:
                must("craft", "burner-mining-drill", need_drills)
            if need_ins:
                must("craft", "burner-inserter", need_ins)
            if inv(b).get("wooden-chest", 0) < 1:
                must("craft", "wooden-chest", 1)

            # --- plan on ore, check three ways, build
            for X, Y in find_site(b, stamp)[:10]:
                run("unplan", TAG)
                if run("plan", STAMP, X, Y, 0, "--tag", TAG) == 0 and checks(TAG, [X, Y, X + stamp.w - 1, Y + stamp.h - 1]):
                    break
            else:
                raise E2EFail("no site passed lint")
            must("build", TAG)

        t = fx.load_state()["tags"][TAG]
        X, Y = t["x"], t["y"]
        # --- fuel and prime (positions from the stamp: drills at 0,0 and 5,0; furnaces below)
        gather(b, "coal", 12)
        gather(b, "iron-ore", 10)
        must("walk", X + 3.5, Y + 5.5, "--radius", 1)
        for cx in (X + 1, X + 6):
            must("put", cx, Y + 1, "coal", 3)
            must("put", cx, Y + 3, "coal", 2)
            must("put", cx, Y + 3, "iron-ore", 5)
        must("put", X + 2.5, Y + 3.5, "coal", 1)
        must("put", X + 4.5, Y + 3.5, "coal", 1)

        code = run("prove", TAG, 600)
        chest = [e for e in b.call("tag", {"tag": TAG})["entities"] if e.get("name") == "wooden-chest"]
        plates = chest[0].get("contents", {}).get("iron-plate", 0) if chest else 0
        print(f"chest holds {plates} iron plate(s)")
        if code != 0 or plates < 1:
            raise E2EFail("prove failed" if code else "no iron plates in the chest")
        print("E2E PASS")


if __name__ == "__main__":
    try:
        main()
    except E2EFail as e:
        print(f"E2E FAIL: {e}", file=sys.stderr)
        sys.exit(1)
