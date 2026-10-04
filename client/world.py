"""Helpers over a scan snapshot (the dict the bridge's `scan` returns)."""
import math

from layout import DIR_DCHAR, STEP

BELT_TYPES = {"transport-belt", "underground-belt", "splitter", "loader", "loader-1x1"}
MACHINE_TYPES = {"furnace", "assembling-machine"}


def tile_of(pos):
    return (math.floor(pos[0]), math.floor(pos[1]))


def footprint(e):
    x, y = e["tile"]
    return [(x + dx, y + dy) for dy in range(e["h"]) for dx in range(e["w"])]


def occupancy(snap):
    occ = {}
    for e in snap["entities"]:
        if e["type"] == "character":
            continue
        for t in footprint(e):
            occ[t] = e
    return occ


def is_belt(e):
    return e is not None and e["type"] in BELT_TYPES


def side_of(src_tile, pos):
    """dchar for the unit step from src_tile toward pos, or None."""
    tx, ty = tile_of(pos)
    d = (tx - src_tile[0], ty - src_tile[1])
    if 0 in d:  # straight line of any length (a long-handed inserter reaches 2 tiles)
        d = tuple((v > 0) - (v < 0) for v in d)
    for c, s in STEP.items():
        if s == d:
            return c
    return None


def dchar(e):
    return DIR_DCHAR.get(e["direction"], "?")
