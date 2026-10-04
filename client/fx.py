"""fx: Claude's Factorio command line. See CLAUDE.md for the workflow.

plan -> look + shot + lint -> build -> prove. Build refuses until all three
checks have seen the current state of the tag's area.
"""
import argparse
import hashlib
import math
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import ROOT, Bridge, BridgeError  # noqa: E402
from layout import CODES, Placed, StampError, load_stamp, place, rotate  # noqa: E402
from lint import lint  # noqa: E402
from render import render  # noqa: E402

STATE = os.path.join(ROOT, ".fx_state.json")
SCRIPT_OUTPUT = os.path.join(os.environ.get("APPDATA", ""), "Factorio", "script-output")
PAD = 4  # fingerprint margin (SPEC AC-8)
LINT_PAD = 40  # lint margin: undergrounds (5) and pole networks (SPEC AC-17: bbox + 40)
MACHINE_OK = {
    "furnace": {"working", "full_output"},  # output backed up: downstream is the bottleneck
    "assembling-machine": {"working", "full_output"},  # output backed up: downstream is the bottleneck
    "mining-drill": {"working", "waiting_for_space_in_destination"},
    "inserter": {"working", "waiting_for_source_items", "waiting_for_space_in_destination"},  # a full destination is judged on its own
    "boiler": {"working"},
    "generator": {"working"},
    "offshore-pump": {"working"},
    "lab": {"working"},
}
SAMPLE_TICKS = 60


class Fail(Exception):
    pass


# ---------------------------------------------------------------- local state
def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {"tags": {}}


def save_state(st):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1)


def get_tag(st, tag):
    if tag not in st["tags"]:
        raise Fail(f"unknown tag {tag!r} (known: {', '.join(st['tags']) or 'none'})")
    return st["tags"][tag]


def padded(bbox, pad=PAD):
    x1, y1, x2, y2 = bbox
    return [x1 - pad, y1 - pad, x2 + pad, y2 + pad]


def _in(area, x, y):
    return area[0] <= x <= area[2] and area[1] <= y <= area[3]


def fingerprint(snap, area):
    """What a check saw inside `area`: every non-character entity (ghost or
    built is the same layout), water, and which tiles hold which resource.
    Resource amounts are ignored; a tile running dry changes the print."""
    def touches(e):
        x, y = e["tile"]
        return x <= area[2] and x + e["w"] - 1 >= area[0] and y <= area[3] and y + e["h"] - 1 >= area[1]

    ents = sorted(
        (e["name"], tuple(e["tile"]), e["w"], e["h"], e["direction"], e.get("belt_type") or "")
        for e in snap["entities"]
        if e["type"] != "character" and touches(e)
    )
    water = sorted(tuple(w) for w in snap.get("water", []) if _in(area, *w))
    res = sorted((r["name"], tuple(r["tile"])) for r in snap.get("resources", []) if _in(area, *r["tile"]))
    return hashlib.sha1(json.dumps([ents, water, res]).encode()).hexdigest()


def tag_fp(b, t):
    area = padded(t["bbox"])
    return fingerprint(b.call("scan", {"area": area}), area)


def union(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def covers(area, bbox):
    return area[0] <= bbox[0] and area[1] <= bbox[1] and area[2] >= bbox[2] and area[3] >= bbox[3]


def codes_of(t):
    return {(x, y): (c, d) for x, y, c, d in t["codes"]}


# ---------------------------------------------------------------- commands
def cmd_status(b, a):
    s = b.call("status")
    ch = s.get("character")
    print(f"bridge {s['version']}  tick {s['tick']}  paused {str(s['paused']).lower()}")
    print(f"character {ch[0]:.2f},{ch[1]:.2f}" if ch else "character none (run spawn)")
    if s.get("job"):
        print(f"job {s['job']}")


def cmd_spawn(b, a):
    r = b.call("spawn")
    ch = r["character"]
    if r["created"]:
        print(f"created character at {ch[0]:.2f},{ch[1]:.2f}; starting kit: {r.get('kit')}")
    else:
        print(f"character already exists at {ch[0]:.2f},{ch[1]:.2f}")


def cmd_look(b, a):
    area = [a.x1, a.y1, a.x2, a.y2]
    st = load_state()
    covered = [name for name, t in st["tags"].items() if covers(area, t["bbox"])]
    # one scan feeds both the picture and the fingerprints, so the recorded
    # check is exactly what was shown
    scan_area = area
    for name in covered:
        scan_area = union(scan_area, padded(st["tags"][name]["bbox"]))
    snap = b.call("scan", {"area": scan_area})
    print(render(dict(snap, area=area)))
    for name in covered:
        t = st["tags"][name]
        t.setdefault("checks", {})["look"] = fingerprint(snap, padded(t["bbox"]))
        print(f"(look covers tag {name})")
    save_state(st)


def stamp_path(name):
    for p in (name, os.path.join(ROOT, "stamps", name), os.path.join(ROOT, "stamps", name + ".txt")):
        if os.path.isfile(p):
            return p
    raise Fail(f"no stamp {name!r}")


def cmd_plan(b, a):
    st = load_state()
    stamp = load_stamp(stamp_path(a.stamp))
    tag = a.tag or f"t{int(time.time())}"
    if tag in st["tags"]:
        raise Fail(f"tag {tag} already exists; unplan it first")
    placed = place(stamp, a.x, a.y, a.rot)
    rs = rotate(stamp, a.rot)
    bbox = [a.x, a.y, a.x + rs.w - 1, a.y + rs.h - 1]
    plan_placed(b, st, tag, placed, bbox, {"stamp": a.stamp, "x": a.x, "y": a.y, "rot": a.rot})


def plan_placed(b, st, tag, placed, bbox, meta):
    items = [
        {"name": p.name, "position": list(p.position), "direction": p.direction, "belt_type": p.belt_type, "tile": list(p.tile), "w": p.w, "h": p.h, "size": max(p.w, p.h), "recipe": p.recipe}
        for p in placed
    ]
    r = b.call("plan", {"tag": tag, "items": items})
    print(f"tag: {tag}")
    bad = []
    for want, got in zip(placed, r["placed"]):
        mark = "ok" if tuple(got["tile"]) == want.tile and got["direction"] == want.direction else "MISMATCH"
        if mark != "ok":
            bad.append(want)
        print(f"  {want.tile[0]},{want.tile[1]} {want.code}{want.dchar} {want.name} -> engine {got['tile'][0]},{got['tile'][1]} dir {got['direction']} {mark}")
    st["tags"][tag] = dict(meta, bbox=bbox, codes=[[p.tile[0], p.tile[1], p.code, p.dchar] for p in placed], checks={})
    save_state(st)
    print(f"bbox {bbox[0]},{bbox[1]} .. {bbox[2]},{bbox[3]}")
    if bad:
        raise Fail(f"{len(bad)} ghost(s) landed somewhere other than the stamp says")


def pole_points(x1, y1, x2, y2, step=7):
    """Tiles along an L path (x first, then y), no two consecutive more than `step` apart."""
    def span(a, b):
        n = max(1, -(-abs(b - a) // step))
        return [a + round((b - a) * i / n) for i in range(n + 1)]

    pts = [(x, y1) for x in span(x1, x2)] + [(x2, y) for y in span(y1, y2)][1:]
    out = []
    for p in pts:
        if p not in out:
            out.append(p)
    return out


def cmd_poles(b, a):
    st = load_state()
    tag = a.tag or f"poles{int(time.time())}"
    if tag in st["tags"]:
        raise Fail(f"tag {tag} already exists; unplan it first")
    pts = pole_points(a.x1, a.y1, a.x2, a.y2)
    if a.skip_ends:  # both ends are existing poles: only plan the ones between
        pts = pts[1:-1]
        if not pts:
            raise Fail("ends are within one wire reach; no poles needed")
    placed = [Placed("p", "small-electric-pole", 1, 1, p, (p[0] + 0.5, p[1] + 0.5), 0, ".", None) for p in pts]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    plan_placed(b, st, tag, placed, [min(xs), min(ys), max(xs), max(ys)], {"stamp": "poles"})
    print(f"{len(pts)} poles")


def cmd_unplan(b, a):
    st = load_state()
    r = b.call("unplan", {"tag": a.tag}, check=False)
    known_locally = st["tags"].pop(a.tag, None) is not None
    save_state(st)
    if r.get("error"):
        if not known_locally:
            raise Fail(r["error"])
        print(f"{a.tag}: the game has no such tag (re-hosted?); dropped it from local state")
        return
    print(f"removed {r['removed']} ghosts of {a.tag}")




def tag_entities(b, tag):
    """The tag's entities. A ghost someone else built (the player) leaves an invalid
    reference; resolve it to the built entity of the same name on the planned tile."""
    ents = b.call("tag", {"tag": tag})["entities"]
    t = load_state()["tags"].get(tag, {})
    codes = t.get("codes") or []
    retired = set(t.get("retired") or [])
    ents = [e for i, e in enumerate(ents) if e.get("index", i + 1) not in retired]
    for i, e in enumerate(ents):
        if not e.get("invalid") or not 0 < e.get("index", 0) <= len(codes):
            continue
        x, y, code, _ = codes[e["index"] - 1]
        name = CODES[code][0]
        snap = b.call("scan", {"area": [x, y, x + 1, y + 1]})
        hit = next((s for s in snap["entities"] if s["name"] == name and not s.get("ghost") and tuple(s["tile"]) == (x, y)), None)
        if hit:
            ents[i] = dict(hit, index=e["index"])
    return ents


def lint_scan(b, bbox):
    """Scan bbox + LINT_PAD, then follow pole wires past the edge (scanning around
    each outlying pole) so a far-away generator still counts as a power source."""
    snap = b.call("scan", {"area": padded(bbox, LINT_PAD)})
    seen = {tuple(e["position"]) for e in snap["entities"]}
    todo = [e for e in snap["entities"] if e.get("supply") and not e.get("ghost")]
    done, scans = set(), 0
    while todo and scans < 300:
        p = todo.pop()
        key = tuple(p["position"])
        if key in done:
            continue
        done.add(key)
        if any(e["type"] == "generator" for e in snap["entities"]):
            break
        r = (p.get("wire") or 7.5) + 1
        x, y = p["position"]
        extra = b.call("scan", {"area": [math.floor(x - r), math.floor(y - r), math.ceil(x + r), math.ceil(y + r)]})
        scans += 1
        for e in extra["entities"]:
            if e["type"] not in ("electric-pole", "generator") or tuple(e["position"]) in seen:
                continue
            seen.add(tuple(e["position"]))
            snap["entities"].append(e)
            if e.get("supply") and not e.get("ghost"):
                todo.append(e)
    return snap

def cmd_lint(b, a):
    st = load_state()
    t = get_tag(st, a.tag)
    snap = lint_scan(b, t["bbox"])
    found = lint(snap, codes_of(t))
    for f in found:
        print(f)
    if found:
        t.get("checks", {}).pop("lint", None)
        save_state(st)
        raise Fail(f"{len(found)} finding(s)")
    t.setdefault("checks", {})["lint"] = fingerprint(snap, padded(t["bbox"]))
    save_state(st)
    print(f"lint {a.tag}: clean")


def cmd_shot(b, a):
    rel = f"claude/shot-{int(time.time() * 1000)}.png"
    st = load_state()
    half_w, half_h = a.w / (32 * a.zoom) / 2, a.h / (32 * a.zoom) / 2
    area = [a.x - half_w, a.y - half_h, a.x + half_w - 1, a.y + half_h - 1]
    covered = {name: t for name, t in st["tags"].items() if covers(area, t["bbox"])}
    before = {name: tag_fp(b, t) for name, t in covered.items()}
    b.call("shot", {"x": a.x, "y": a.y, "zoom": a.zoom, "w": a.w, "h": a.h, "path": rel})
    full = os.path.join(SCRIPT_OUTPUT, *rel.split("/"))
    deadline = time.time() + 15
    while not os.path.exists(full) and time.time() < deadline:
        time.sleep(0.1)
    if not os.path.exists(full):
        raise Fail(f"screenshot not written: {full}")
    print(full)
    # the picture is only credited if nothing changed around it while it was taken
    for name, t in covered.items():
        after = tag_fp(b, t)
        if after == before[name]:
            t.setdefault("checks", {})["shot"] = after
            print(f"(shot covers tag {name})")
        else:
            print(f"(area of tag {name} changed during the shot; not credited)")
    save_state(st)


def gate(b, t):
    checks = t.get("checks", {})
    missing = [k for k in ("lint", "look", "shot") if k not in checks]
    if missing:
        raise Fail("build refused: not yet done since plan: " + ", ".join(missing))
    now = tag_fp(b, t)
    stale = [k for k in ("lint", "look", "shot") if checks[k] != now]
    if stale:
        raise Fail("build refused: area changed since checks (" + ", ".join(stale) + "); rerun them")


def cmd_build(b, a):
    st = load_state()
    t = get_tag(st, a.tag)
    gate(b, t)
    fresh = lint(lint_scan(b, t["bbox"]), codes_of(t))
    if fresh:
        for f in fresh:
            print(f)
        raise Fail(f"build refused: fresh lint has {len(fresh)} finding(s)")
    ents = tag_entities(b, a.tag)
    ghosts = [e for e in ents if not e.get("invalid") and e["ghost"]]
    inv = b.call("inv")["items"]
    built, missing, unreachable, blocked = [], [], [], []
    pos = b.call("status")["character"]
    while ghosts:
        ghosts.sort(key=lambda e: (e["position"][0] - pos[0]) ** 2 + (e["position"][1] - pos[1]) ** 2)
        g = ghosts.pop(0)
        where = f"{g['tile'][0]},{g['tile'][1]} {g['name']}"
        if inv.get(g.get("item"), 0) < 1:
            missing.append(where)
            continue
        r = b.call("revive", {"tag": a.tag, "index": g["index"]}, check=False)
        if r.get("unreachable"):
            j = b.run_job("walk", {"x": g["position"][0], "y": g["position"][1], "radius": 6})
            if j["state"] != "done":
                unreachable.append(where)
                continue
            pos = j["result"]["position"]
            r = b.call("revive", {"tag": a.tag, "index": g["index"]}, check=False)
        if r.get("error"):
            # most often Claude is standing on the footprint: step off and retry once
            j = b.run_job("walk", {"x": g["position"][0] + g["w"] / 2 + 2.5, "y": g["position"][1], "radius": 1})
            if j["state"] == "done":
                pos = j["result"]["position"]
            r = b.call("revive", {"tag": a.tag, "index": g["index"]}, check=False)
        if r.get("built"):
            built.append(where)
            inv[g["item"]] -= 1
        elif r.get("missing"):
            missing.append(where)
        elif r.get("unreachable"):
            unreachable.append(where)
        else:
            blocked.append(f"{where} ({r.get('error')})")
    for w in built:
        print(f"built {w}")
    for w in missing:
        print(f"missing {w}")
    for w in unreachable:
        print(f"unreachable {w}")
    for w in blocked:
        print(f"blocked {w}")
    if missing or unreachable or blocked:
        raise Fail(f"{len(missing) + len(unreachable) + len(blocked)} ghost(s) not built")


def cmd_walk(b, a):
    j = b.run_job("walk", {"x": a.x, "y": a.y, "radius": a.radius})
    if j["state"] != "done":
        print(j.get("msg") or "unreachable")
        raise Fail("unreachable")
    p = j["result"]["position"]
    print(f"at {p[0]:.2f},{p[1]:.2f}")


def cmd_mine(b, a):
    j = b.run_job("mine", {"x": a.x, "y": a.y, "n": a.n})
    if j["state"] != "done":
        raise Fail(j.get("msg") or "mining failed")
    r = j["result"]
    print(f"mined {r['mined']}" + (f" ({r['msg']})" if r.get("msg") else ""))
    if r.get("msg") == "inventory full":
        raise Fail("inventory full")


def cmd_retire(b, a):
    """Mine a built entity of a tag on purpose (a layout change). The tag keeps
    the record but `prove` skips it from now on."""
    st = load_state()
    t = get_tag(st, a.tag)
    codes = t.get("codes") or []
    idx = next((i + 1 for i, c in enumerate(codes) if (c[0], c[1]) == (a.x, a.y)), None)
    if idx is None:
        raise Fail(f"tag {a.tag} has nothing planned at {a.x},{a.y}")
    if idx not in t.setdefault("retired", []):
        name = CODES[codes[idx - 1][2]][0]
        snap = b.call("scan", {"area": [a.x, a.y, a.x, a.y]})
        e = next((s for s in snap["entities"] if s["name"] == name and tuple(s["tile"]) == (a.x, a.y)), None)
        if e is not None:
            j = b.run_job("mine", {"x": e["position"][0], "y": e["position"][1], "n": 1})
            if j["state"] != "done" or not j["result"].get("mined"):
                raise Fail(j.get("msg") or (j.get("result") or {}).get("msg") or "mining failed")
        t["retired"].append(idx)
        save_state(st)
    print(f"retired {a.x},{a.y} from {a.tag}")


def cmd_craft(b, a):
    j = b.run_job("craft", {"item": a.item, "n": a.n})
    if j["state"] != "done":
        raise Fail(j.get("msg") or "crafting failed")
    print(f"crafted {a.n} {a.item}")


def cmd_put(b, a):
    r = b.call("put", {"x": a.x, "y": a.y, "item": a.item, "n": a.n})
    print(f"put {r['moved']} {a.item} into {r['into']}")


def cmd_take(b, a):
    r = b.call("take", {"x": a.x, "y": a.y, "item": a.item, "n": a.n})
    print(f"took {r['moved']} {a.item} from {r['from']}")


def cmd_inv(b, a):
    r = b.call("inv")
    p = r["position"]
    print(f"at {p[0]:.2f},{p[1]:.2f}")
    for name, n in sorted(r["items"].items()):
        print(f"  {n:5d} {name}")


def judge(samples):
    """samples: list of `tag` entity lists taken every SAMPLE_TICKS. An entity
    passes if its status is OK in at least half the samples; containers fed by
    tag inserters must end non-empty; the final sample decides ghosts/gone."""
    final = samples[-1]
    lines, bad = prove_report(final, check_status=False)
    for i, e in enumerate(final):
        if e.get("invalid") or e.get("ghost"):
            continue
        ok = MACHINE_OK.get(e["type"])
        if ok is None:
            continue
        good = sum(1 for s in samples if i < len(s) and s[i].get("status") in ok)
        where = f"{e['tile'][0]},{e['tile'][1]} {e['name']}"
        lines.append(f"  {where}: ok in {good}/{len(samples)} samples")
        if good * 2 < len(samples):
            bad.append(f"{where} ({e.get('status')}; ok {good}/{len(samples)})")
    return lines, bad


def prove_report(ents, check_status=True):
    """Statuses, plus: every container a tag inserter drops into must have
    received something (the output actually arrived)."""
    lines, bad = [], []
    sink_tiles = set()
    for e in ents:
        if not e.get("invalid") and e.get("type") == "inserter" and e.get("drop"):
            sink_tiles.add((math.floor(e["drop"][0]), math.floor(e["drop"][1])))
    for e in ents:
        if e.get("invalid"):
            lines.append("  (entity gone)")
            bad.append("gone")
            continue
        where = f"{e['tile'][0]},{e['tile'][1]} {e['name']}"
        if e["ghost"]:
            lines.append(f"  {where}: still a ghost")
            bad.append(where)
            continue
        status = e.get("status")
        extra = f" {e['contents']}" if e.get("contents") else ""
        lines.append(f"  {where}: {status}{extra}")
        ok = MACHINE_OK.get(e["type"])
        if check_status and ok is not None and status not in ok:
            bad.append(f"{where} ({status})")
        if e["type"] == "container" and tuple(e["tile"]) in sink_tiles and not e.get("contents"):
            bad.append(f"{where} (output container is empty)")
    return lines, bad


def cmd_prove(b, a):
    samples = []
    for _ in range(max(1, a.ticks // SAMPLE_TICKS)):
        b.run_ticks(SAMPLE_TICKS)
        samples.append(tag_entities(b, a.tag))
    lines, bad = judge(samples)
    print(f"after {a.ticks} ticks ({len(samples)} samples):")
    print("\n".join(lines))
    if bad:
        raise Fail("not working: " + "; ".join(bad))
    print("all working")


def cmd_research(b, a):
    r = b.call("research", {"name": a.name})
    print(f"current research: {r['current']}")


def cmd_tech(b, a):
    r = b.call("tech")
    cur = r.get("current")
    print(f"current: {cur or 'none'}" + (f"  {100 * (r.get('progress') or 0):.0f}%" if cur else ""))
    for t in r.get("available", []):
        how = f"trigger: {t['trigger']}" if t.get("trigger") else f"{t.get('units')} x {'+'.join(t.get('ingredients') or [])}"
        print(f"  {t['name']}  ({how})")


def cmd_recipe(b, a):
    r = b.call("set_recipe", {"x": a.x, "y": a.y, "recipe": a.recipe})
    print(f"recipe set: {r['recipe']}")


def cmd_say(b, a):
    r = b.call("say", {"text": " ".join(a.text)})
    print(f"said: {r['said']}")


def cmd_chat(b, a):
    r = b.call("chat_read", {"after": a.after})
    for m in r["msgs"]:
        print(f"#{m['id']} {m['from']}: {m['text']}")
    if not r["msgs"]:
        print(f"(no messages after #{a.after})")


def main(argv=None):
    p = argparse.ArgumentParser(prog="fx")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("spawn")
    s = sub.add_parser("look")
    for n in ("x1", "y1", "x2", "y2"):
        s.add_argument(n, type=int)
    s = sub.add_parser("plan")
    s.add_argument("stamp")
    s.add_argument("x", type=int)
    s.add_argument("y", type=int)
    s.add_argument("rot", type=int, choices=(0, 90, 180, 270))
    s.add_argument("--tag")
    for name in ("unplan", "lint", "build"):
        sub.add_parser(name).add_argument("tag")
    s = sub.add_parser("shot")
    s.add_argument("x", type=float)
    s.add_argument("y", type=float)
    s.add_argument("zoom", type=float)
    s.add_argument("--w", type=int, default=1280)
    s.add_argument("--h", type=int, default=960)
    s = sub.add_parser("walk")
    s.add_argument("x", type=float)
    s.add_argument("y", type=float)
    s.add_argument("--radius", type=float, default=1.0)
    s = sub.add_parser("mine")
    s.add_argument("x", type=float)
    s.add_argument("y", type=float)
    s.add_argument("n", type=int, nargs="?", default=1)
    s = sub.add_parser("retire")
    s.add_argument("tag")
    s.add_argument("x", type=int)
    s.add_argument("y", type=int)
    s = sub.add_parser("craft")
    s.add_argument("item")
    s.add_argument("n", type=int)
    for name in ("put", "take"):
        s = sub.add_parser(name)
        s.add_argument("x", type=float)
        s.add_argument("y", type=float)
        s.add_argument("item")
        s.add_argument("n", type=int)
    sub.add_parser("inv")
    s = sub.add_parser("poles")
    for n in ("x1", "y1", "x2", "y2"):
        s.add_argument(n, type=int)
    s.add_argument("--tag")
    s.add_argument("--skip-ends", action="store_true", help="the end points are existing poles")
    sub.add_parser("research").add_argument("name")
    sub.add_parser("tech")
    s = sub.add_parser("recipe")
    s.add_argument("x", type=float)
    s.add_argument("y", type=float)
    s.add_argument("recipe")
    sub.add_parser("say").add_argument("text", nargs="+")
    sub.add_parser("chat").add_argument("--after", type=int, default=0)
    s = sub.add_parser("prove")
    s.add_argument("tag")
    s.add_argument("ticks", type=int)
    a = p.parse_args(argv)
    try:
        with Bridge() as b:
            globals()["cmd_" + a.cmd](b, a)
    except (Fail, BridgeError, StampError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
