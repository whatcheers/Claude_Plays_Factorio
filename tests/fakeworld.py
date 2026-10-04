"""Build synthetic scan snapshots (same shape the bridge returns) from stamps.

Inserter pickup/drop offsets follow the measured table in docs/conventions.md:
pickup is 1 tile toward the direction, drop is 1.2 tiles away from it.
"""
from layout import DIR_DCHAR, STEP, parse_stamp, place

INVENTORY_TYPES = {"furnace", "container", "mining-drill", "assembling-machine"}
TYPES = {
    "transport-belt": "transport-belt",
    "underground-belt": "underground-belt",
    "burner-inserter": "inserter",
    "inserter": "inserter",
    "stone-furnace": "furnace",
    "burner-mining-drill": "mining-drill",
    "assembling-machine-1": "assembling-machine",
    "wooden-chest": "container",
    "small-electric-pole": "electric-pole",
}


def entity(name, tile, size=1, direction=0, ghost=True, belt_type=None, can_place=True, typ=None):
    typ = typ or TYPES.get(name, "simple-entity")
    cx, cy = tile[0] + size / 2, tile[1] + size / 2
    e = {
        "name": name,
        "type": typ,
        "ghost": ghost,
        "tile": list(tile),
        "w": size,
        "h": size,
        "direction": direction,
        "position": [cx, cy],
        "pickup": None,
        "drop": None,
        "belt_type": belt_type,
        "has_inventory": typ in INVENTORY_TYPES,
        "needs_power": typ in {"inserter", "assembling-machine"} and name != "burner-inserter",
        "supply": None,
        "can_place": can_place if ghost else None,
        "max_distance": 5 if name == "underground-belt" else None,
    }
    if typ == "inserter":
        pdx, pdy = STEP[DIR_DCHAR[direction]]
        e["pickup"] = [cx + pdx, cy + pdy]
        e["drop"] = [cx - 1.2 * pdx, cy - 1.2 * pdy]
    if typ == "mining-drill":
        vx, vy = -0.3, -1.3  # north-facing drop vector; rotate clockwise
        for _ in range(direction // 4):
            vx, vy = -vy, vx
        e["drop"] = [cx + vx, cy + vy]
    if typ == "electric-pole":
        e["supply"] = [cx - 2.5, cy - 2.5, cx + 2.5, cy + 2.5]
    return e


def from_stamp(text, X=0, Y=0, rot=0, **kw):
    placed = place(parse_stamp(text), X, Y, rot)
    ents = [entity(p.name, p.tile, p.size, p.direction, belt_type=p.belt_type, **kw) for p in placed]
    codes = {tuple(p.tile): (p.code, p.dchar) for p in placed}
    return ents, codes


def snapshot(area, entities=(), resources=(), water=()):
    return {
        "area": list(area),
        "entities": list(entities),
        "resources": [{"name": n, "tile": list(t)} for n, t in resources],
        "water": [list(t) for t in water],
    }
