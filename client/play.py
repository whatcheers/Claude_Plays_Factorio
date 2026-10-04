"""Reusable fair-play routines built on fx commands (gather, place a stamp on ore, ferry)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fx  # noqa: E402
from layout import load_stamp  # noqa: E402


class PlayFail(Exception):
    pass


class ChatInterrupt(PlayFail):
    """A player spoke: stop at this step boundary so Claude can answer now."""


_chat_seen = None


def _check_chat():
    """Raise ChatInterrupt if anyone has chatted since this script started.
    Off by default: the chatwatch monitor tells Claude about chat on its own,
    and Claude answers with `fx.py say` while the script keeps going.
    Set FX_CHAT_INTERRUPT=1 to stop at the next step instead."""
    global _chat_seen
    if os.environ.get("FX_CHAT_INTERRUPT") != "1":
        return
    from bridge import Bridge

    try:
        with Bridge() as b:
            seq = b.call("chat_read", {"after": 10 ** 9}, check=False).get("seq", 0)
    except Exception:
        return
    if _chat_seen is None:
        _chat_seen = seq
    elif seq > _chat_seen:
        _chat_seen = seq
        raise ChatInterrupt("player spoke in chat; stopping here so Claude can respond")


def run(*args):
    _check_chat()
    print(f"$ fx {' '.join(map(str, args))}", flush=True)
    code = fx.main([str(a) for a in args])
    sys.stdout.flush()
    return code


def must(*args):
    if run(*args) != 0:
        raise PlayFail(f"fx {' '.join(map(str, args))} failed")


def inv(b):
    return b.call("inv")["items"]


def pos(b):
    return b.call("status")["character"]


def nearest_resource(b, name, frm=None):
    x, y = frm or pos(b)
    for r in (16, 40, 80, 150):
        snap = b.call("scan", {"area": [int(x) - r, int(y) - r, int(x) + r, int(y) + r]})
        pool = [t for t in snap["resources"] if t["name"] == name]
        if pool:
            return min(pool, key=lambda t: (t["tile"][0] + 0.5 - x) ** 2 + (t["tile"][1] + 0.5 - y) ** 2)
    raise PlayFail(f"no {name} within 150 tiles")


def gather(b, name, want):
    """Hand-mine until the inventory holds `want` of `name`."""
    while inv(b).get(name, 0) < want:
        t = nearest_resource(b, name)
        px, py = t["tile"][0] + 0.5, t["tile"][1] + 0.5
        must("walk", px, py, "--radius", 1.5)
        n = min(want - inv(b).get(name, 0), 10, t.get("amount", 10))
        must("mine", px, py, n)


def gather_wood(b, want):
    while inv(b).get("wood", 0) < want:
        x, y = pos(b)
        trees = []
        for r in (20, 50, 100, 150):
            snap = b.call("scan", {"area": [int(x) - r, int(y) - r, int(x) + r, int(y) + r]})
            trees = [e for e in snap["entities"] if e["type"] == "tree"]
            if trees:
                break
        if not trees:
            raise PlayFail("no trees within 150 tiles")
        t = min(trees, key=lambda e: (e["position"][0] - x) ** 2 + (e["position"][1] - y) ** 2)
        must("walk", t["position"][0], t["position"][1], "--radius", 1.5)
        must("mine", t["position"][0], t["position"][1])


def withdraw(b, x, y, item, n):
    """Walk to a container and take up to n of item (whatever it holds)."""
    must("walk", x, y + 2, "--radius", 1.5)
    have = 0
    snap = b.call("scan", {"area": [math.floor(x), math.floor(y), math.floor(x), math.floor(y)]})
    for e in snap["entities"]:
        if e.get("contents"):
            have = e["contents"].get(item, 0)
    take = min(n, have)
    if take:
        must("take", x, y, item, take)
    return take


def checks(tag, bbox):
    x1, y1, x2, y2 = bbox
    must("look", x1 - 1, y1 - 1, x2 + 1, y2 + 1)
    must("shot", (x1 + x2 + 1) / 2, (y1 + y2 + 1) / 2, 1)
    return run("lint", tag) == 0


def find_ore_site(b, stamp, ore, near=None, radius=150):
    """Top-lefts (nearest first) where every drill footprint sits on `ore` and
    the stamp area plus a 1-tile margin is free of entities and water."""
    drills = [(e.x, e.y, e.w, e.h) for e in stamp.entities if e.code == "D"]
    x, y = near or pos(b)
    snap = b.call("scan", {"area": [int(x) - radius, int(y) - radius, int(x) + radius, int(y) + radius]})
    tiles = {tuple(t["tile"]) for t in snap["resources"] if t["name"] == ore}
    blocked = set()
    for e in snap["entities"]:
        if e["type"] != "character":
            for dx in range(e["w"]):
                for dy in range(e["h"]):
                    blocked.add((e["tile"][0] + dx, e["tile"][1] + dy))
    blocked |= {tuple(t) for t in snap["water"]}
    out = []
    dx0, dy0, _, _ = drills[0]
    for (ox, oy) in tiles:
        X, Y = ox - dx0, oy - dy0
        if all((X + dx + i, Y + dy + j) in tiles for dx, dy, w, h in drills for i in range(w) for j in range(h)):
            if not any((X + i, Y + j) in blocked for i in range(-1, stamp.w + 1) for j in range(-1, stamp.h + 1)):
                out.append((math.hypot(X - x, Y - y), X, Y))
    return [(X, Y) for _, X, Y in sorted(out)]


def place_on_ore(b, stamp_name, ore, tag, near=None, tries=10):
    path = fx.stamp_path(stamp_name)
    stamp = load_stamp(path)
    for X, Y in find_ore_site(b, stamp, ore, near)[:tries]:
        run("unplan", tag)
        if run("plan", path, X, Y, 0, "--tag", tag) == 0 and checks(tag, [X, Y, X + stamp.w - 1, Y + stamp.h - 1]):
            return X, Y
    run("unplan", tag)
    raise PlayFail(f"no {ore} site passed lint for {stamp_name}")
