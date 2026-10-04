"""Build synthetic scan snapshots (same shape the bridge returns) from stamps.

Inserter pickup/drop offsets follow the measured table in docs/conventions.md:
pickup is 1 tile toward the direction, drop is 1.2 tiles away from it.
"""
import math

from layout import DIR_DCHAR, STEP, parse_stamp, place

INVENTORY_TYPES = {"furnace", "container", "mining-drill", "assembling-machine", "lab", "boiler"}
TYPES = {
    "transport-belt": "transport-belt",
    "underground-belt": "underground-belt",
    "burner-inserter": "inserter",
    "inserter": "inserter",
    "stone-furnace": "furnace",
    "burner-mining-drill": "mining-drill",
    "electric-mining-drill": "mining-drill",
    "long-handed-inserter": "inserter",
    "assembling-machine-1": "assembling-machine",
    "wooden-chest": "container",
    "small-electric-pole": "electric-pole",
    "boiler": "boiler",
    "steam-engine": "generator",
    "offshore-pump": "offshore-pump",
    "pipe": "pipe",
    "lab": "lab",
}


def entity(name, tile, size=1, direction=0, ghost=True, belt_type=None, can_place=True, typ=None, w=None, h=None):
    typ = typ or TYPES.get(name, "simple-entity")
    w, h = w or size, h or size
    cx, cy = tile[0] + w / 2, tile[1] + h / 2
    e = {
        "name": name,
        "type": typ,
        "ghost": ghost,
        "tile": list(tile),
        "w": w,
        "h": h,
        "direction": direction,
        "position": [cx, cy],
        "pickup": None,
        "drop": None,
        "belt_type": belt_type,
        "has_inventory": typ in INVENTORY_TYPES,
        "needs_power": (typ in {"inserter", "assembling-machine", "lab"} and name != "burner-inserter") or name == "electric-mining-drill",
        "supply": None,
        "can_place": can_place if ghost else None,
        "max_distance": 5 if name == "underground-belt" else None,
    }
    if typ == "inserter":
        pdx, pdy = STEP[DIR_DCHAR[direction]]
        reach = 2 if name == "long-handed-inserter" else 1
        e["pickup"] = [cx + reach * pdx, cy + reach * pdy]
        e["drop"] = [cx - (reach + 0.2) * pdx, cy - (reach + 0.2) * pdy]
    if typ == "mining-drill":
        vx, vy = (0, -2.0) if name == "electric-mining-drill" else (-0.3, -1.3)  # north-facing drop vector; rotate clockwise
        for _ in range(direction // 4):
            vx, vy = -vy, vx
        e["drop"] = [cx + vx, cy + vy]
    if typ == "electric-pole":
        e["supply"] = [cx - 2.5, cy - 2.5, cx + 2.5, cy + 2.5]
        e["wire"] = 7.5
        e["powered"] = False
    if name in FLUID_DEFS:
        e["fluid"] = fluid_conns(name, (cx, cy), direction)
    return e


def from_stamp(text, X=0, Y=0, rot=0, **kw):
    placed = place(parse_stamp(text), X, Y, rot)
    ents = [entity(p.name, p.tile, direction=p.direction, belt_type=p.belt_type, w=p.w, h=p.h, **kw) for p in placed]
    codes = {tuple(p.tile): (p.code, p.dchar) for p in placed}
    return ents, codes


def snapshot(area, entities=(), resources=(), water=()):
    return {
        "area": list(area),
        "entities": list(entities),
        "resources": [{"name": n, "tile": list(t)} for n, t in resources],
        "water": [list(t) for t in water],
    }


# Measured north-facing pipe connections (client/spike2.py): (fluidbox, kind, fluid, offset from centre, dir)
FLUID_DEFS = {
    "offshore-pump": [(1, "output", None, (0, 0), 8)],
    "boiler": [(1, "input", "water", (-1, 0.5), 12), (1, "input", "water", (1, 0.5), 4), (2, "output", "steam", (0, -0.5), 0)],
    "steam-engine": [(1, "input", "steam", (0, 2), 8), (1, "input", "steam", (0, -2), 0)],
    "pipe": [(1, "none", None, (0, 0), d) for d in (0, 4, 8, 12)],
}
DSTEP = {0: (0, -1), 4: (1, 0), 8: (0, 1), 12: (-1, 0)}


def fluid_conns(name, centre, direction):
    out = []
    for box, kind, fluid, (ox, oy), d in FLUID_DEFS.get(name, []):
        for _ in range(direction // 4):
            ox, oy = -oy, ox
        dd = (d + direction) % 16
        ax, ay = math.floor(centre[0] + ox), math.floor(centre[1] + oy)
        sx, sy = DSTEP[dd]
        out.append({"at": [ax, ay], "to": [ax + sx, ay + sy], "box": box, "kind": kind, "fluid": fluid})
    return out
