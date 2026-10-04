"""Steam power at the lake, a pole line to the base, and a powered lab
researching Automation. Fair play throughout; resumable (each step checks
whether its tag is already built).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fx  # noqa: E402
from bridge import Bridge  # noqa: E402
from layout import load_stamp, rotate  # noqa: E402
from play import ChatInterrupt, PlayFail, checks, gather, gather_wood, inv, must, pos, run, withdraw  # noqa: E402

IRON_CHEST = (-90.5, 41.5)
COPPER_CHEST = (-77.5, 10.5)
LAKE = (45, 5)
BASE = (-70, 22)
POWER, LAB, LINE = "power", "lab", "powerline"

FIND_PUMP = r"""
local s = game.surfaces[1]
local cx, cy, R = %d, %d, %d
local out = {}
for x = cx - R, cx + R do
  for y = cy - R, cy + R do
    for _, d in ipairs({0, 4, 8, 12}) do
      if s.can_place_entity{name="offshore-pump", position={x + 0.5, y + 0.5}, direction=d, force="player", build_check_type=defines.build_check_type.manual} then
        out[#out+1] = x .. "," .. y .. "," .. d
      end
    end
  end
end
rcon.print(table.concat(out, ";"))
"""


def tag_state(b, tag):
    """None (no tag), 'ghost' (some unbuilt) or 'built'."""
    if tag not in fx.load_state()["tags"]:
        return None
    r = b.call("tag", {"tag": tag}, check=False)
    ents = r.get("entities")
    if ents is None:
        return None
    return "built" if all(not e.get("invalid") and not e["ghost"] for e in ents) else "ghost"


def ensure(b, item, n, recipe_n=None):
    have = inv(b).get(item, 0)
    if have < n:
        must("craft", item, recipe_n if recipe_n else n - have)


def materials(b):
    need_iron, need_copper = 60, 14
    if inv(b).get("iron-plate", 0) < need_iron:
        withdraw(b, *IRON_CHEST, "iron-plate", need_iron - inv(b).get("iron-plate", 0))
    if inv(b).get("copper-plate", 0) < need_copper:
        withdraw(b, *COPPER_CHEST, "copper-plate", need_copper - inv(b).get("copper-plate", 0))
    if inv(b).get("stone-furnace", 0) < 1 and inv(b).get("boiler", 0) < 1:
        gather(b, "stone", 5)
        must("craft", "stone-furnace", 1)
    gather_wood(b, 12)
    gather(b, "coal", 60)
    if inv(b).get("offshore-pump", 0) < 1:
        must("craft", "copper-cable", 3)
        must("craft", "electronic-circuit", 2)
    ensure(b, "iron-gear-wheel", 10)
    ensure(b, "pipe", 11)
    ensure(b, "offshore-pump", 1)
    ensure(b, "boiler", 1)
    ensure(b, "steam-engine", 1)
    if inv(b).get("small-electric-pole", 0) < 20:
        must("craft", "copper-cable", 10)
        must("craft", "small-electric-pole", 10)
    ensure(b, "wooden-chest", 1)
    ensure(b, "burner-inserter", 1)


def clear_trees(b, bbox):
    x1, y1, x2, y2 = bbox
    snap = b.call("scan", {"area": [x1 - 1, y1 - 1, x2 + 1, y2 + 1]})
    for e in snap["entities"]:
        if e["type"] in ("tree", "simple-entity"):
            must("walk", e["position"][0], e["position"][1], "--radius", 1.5)
            must("mine", e["position"][0], e["position"][1])


def place_power(b):
    stamp = load_stamp(fx.stamp_path(POWER))
    pump_off = next((e.x, e.y) for e in stamp.entities if e.code == "O")
    raw = b.lua(FIND_PUMP % (LAKE[0], LAKE[1], 45)).strip()
    if not raw:
        raise PlayFail("no offshore-pump spot found near the lake")
    cands = []
    for c in raw.split(";"):
        x, y, d = map(int, c.split(","))
        rot = ((d - 12) % 16) // 4 * 90  # stamp rot 0 has the pump facing west (output east)
        rs = rotate(stamp, rot)
        # where the pump tile lands after rotating the stamp
        (ox, oy), = [(e.x, e.y) for e in rs.entities if e.code == "O"]
        X, Y = x - ox, y - oy
        cands.append((math.hypot(x - BASE[0], y - BASE[1]), X, Y, rot, rs))
    cands.sort()
    for _, X, Y, rot, rs in cands[:25]:
        bbox = [X, Y, X + rs.w - 1, Y + rs.h - 1]
        snap = b.call("scan", {"area": bbox})
        if snap["water"] and len(snap["water"]) > 0:
            continue  # stamp body would sit in the lake
        if any(e["type"] not in ("tree", "simple-entity", "character") for e in snap["entities"]):
            continue
        must("walk", X + rs.w / 2, Y + rs.h + 2, "--radius", 3)
        clear_trees(b, bbox)
        run("unplan", POWER)
        if run("plan", POWER, X, Y, rot, "--tag", POWER) == 0 and checks(POWER, bbox):
            return
    run("unplan", POWER)
    raise PlayFail("no lake site passed lint for the power stamp")


def place_lab(b):
    stamp = load_stamp(fx.stamp_path(LAB))
    from play import find_ore_site  # noqa: F401  (same free-area logic, no ore)
    x0, y0 = BASE
    for r in range(0, 40, 2):
        for X, Y in ((x0 + r, y0), (x0, y0 + r), (x0 - r, y0), (x0, y0 - r)):
            bbox = [X, Y, X + stamp.w - 1, Y + stamp.h - 1]
            snap = b.call("scan", {"area": [X - 1, Y - 1, X + stamp.w, Y + stamp.h]})
            if snap["water"] or snap["resources"] or any(e["type"] != "character" for e in snap["entities"]):
                continue
            must("walk", X + 2, Y + 5, "--radius", 2)
            run("unplan", LAB)
            if run("plan", LAB, X, Y, 0, "--tag", LAB) != 0:
                continue
            # the lab has no power until the line exists: only no-power-source is expected
            must("look", X - 1, Y - 1, X + stamp.w, Y + stamp.h)
            must("shot", X + 2, Y + 1.5, 1)
            return
    raise PlayFail("no free spot for the lab near base")


def pole_tile(b, tag):
    ents = b.call("tag", {"tag": tag})["entities"]
    return next(tuple(e["tile"]) for e in ents if e["name"] == "small-electric-pole")


def main():
    with Bridge() as b:
        must("spawn")
        materials(b)

        if tag_state(b, POWER) != "built":
            if tag_state(b, POWER) is None:
                place_power(b)
            must("build", POWER)
        t = fx.load_state()["tags"][POWER]
        ents = b.call("tag", {"tag": POWER})["entities"]
        chest = next(e for e in ents if e["name"] == "wooden-chest")
        boiler = next(e for e in ents if e["name"] == "boiler")
        must("walk", chest["position"][0], chest["position"][1] + 2, "--radius", 2)
        coal = inv(b).get("coal", 0)
        if coal > 6:
            must("put", boiler["position"][0], boiler["position"][1], "coal", 5)
            must("put", chest["position"][0], chest["position"][1], "coal", coal - 6)
        ins = next(e for e in ents if e["name"] == "burner-inserter")
        if ins.get("status") == "no_fuel" or ins.get("ghost") is False:
            if inv(b).get("coal", 0) == 0:
                withdraw(b, chest["position"][0], chest["position"][1], "coal", 2)
            must("walk", ins["position"][0], ins["position"][1] + 2, "--radius", 2)
            run("put", ins["position"][0], ins["position"][1], "coal", 1)

        if tag_state(b, LAB) is None:
            place_lab(b)
        lab_pole = pole_tile(b, LAB)
        if tag_state(b, LINE) != "built":
            if tag_state(b, LINE) is None:
                start = pole_tile(b, POWER)
                must("poles", start[0], start[1], lab_pole[0], lab_pole[1], "--tag", LINE, "--skip-ends")
                lt = fx.load_state()["tags"][LINE]
                x1, y1, x2, y2 = lt["bbox"]
                must("look", x1 - 1, y1 - 1, x2 + 1, y2 + 1)
                # one zoomed-out shot that covers the whole line (the build gate needs full coverage)
                w_t, h_t = x2 - x1 + 6, y2 - y1 + 6
                zoom = min(1.0, 3840 / (32 * w_t))
                run("shot", (x1 + x2 + 1) / 2, (y1 + y2 + 1) / 2, round(zoom, 3),
                    "--w", 3840, "--h", int(max(h_t * 32 * zoom, 256)))
                if run("lint", LINE) != 0:
                    raise PlayFail("pole line failed lint")
            must("build", LINE)

        if tag_state(b, LAB) != "built":
            lt = fx.load_state()["tags"][LAB]
            x1, y1, x2, y2 = lt["bbox"]
            must("look", x1 - 1, y1 - 1, x2 + 1, y2 + 1)
            must("shot", (x1 + x2 + 1) / 2, (y1 + y2 + 1) / 2, 1)
            if run("lint", LAB) != 0:
                raise PlayFail("lab failed lint after the pole line went in")
            must("build", LAB)

        lab = next(e for e in b.call("tag", {"tag": LAB})["entities"] if e["name"] == "lab")
        must("walk", lab["position"][0], lab["position"][1] + 3, "--radius", 2)
        flasks = inv(b).get("automation-science-pack", 0)
        if flasks:
            must("put", lab["position"][0], lab["position"][1], "automation-science-pack", flasks)
        must("research", "automation") if b.call("tech").get("current") != "automation" else None
        before = b.call("tech").get("progress") or 0
        code = run("prove", LAB, 600)
        after = b.call("tech")
        print(f"automation progress {before:.2f} -> {(after.get('progress') or 0):.2f} (current: {after.get('current')})")
        code2 = run("prove", POWER, 600)
        if code or code2:
            raise PlayFail("prove failed")
        if (after.get("progress") or 0) <= before and after.get("current") == "automation":
            raise PlayFail("research did not progress")
        must("say", "Power is up and the lab is researching Automation!")
        print("POWER RUN PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
