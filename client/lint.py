"""Lint a planned tag against a scan snapshot. Built entities and ghosts both count.

`codes` maps each tag entity's top-left tile to its stamp (code, dchar).
"""
from dataclasses import dataclass

from layout import CODES, DCHAR_DIR, OPPOSITE, STEP
from world import MACHINE_TYPES, dchar, footprint, is_belt, occupancy, side_of, tile_of


@dataclass(frozen=True, order=True)
class Finding:
    tile: tuple
    rule: str
    msg: str

    def __str__(self):
        return f"{self.tile[0]},{self.tile[1]} {self.rule}: {self.msg}"


def _add(t, s):
    return (t[0] + s[0], t[1] + s[1])


def _sink_ok(e):
    return e is not None and (e["has_inventory"] or is_belt(e))


def _belt_findings(e, code, occ, out):
    t = tuple(e["tile"])
    d = dchar(e)
    target = occ.get(_add(t, STEP[d]))
    if not is_belt(target):
        if code != "e":
            out.append(Finding(t, "belt-end", f"belt {d} feeds {_add(t, STEP[d])}, which has no belt"))
        return
    td = dchar(target)
    tt = tuple(target["tile"]) if target["w"] == 1 and target["h"] == 1 else _add(t, STEP[d])
    if td == d:
        if target["type"] == "underground-belt" and target.get("belt_type") == "output":
            out.append(Finding(t, "belt-end", "feeds the back of an underground output"))
        elif target["type"] == "transport-belt" or target.get("belt_type") == "input" or target["type"] == "splitter":
            pass
        return
    if td == OPPOSITE[d]:
        if code != "e":
            out.append(Finding(t, "belt-end", f"head-on into a belt going {td}"))
        return
    if target["type"] not in ("transport-belt", "underground-belt"):
        out.append(Finding(t, "belt-end", f"side of a {target['type']}"))
        return
    # perpendicular: a curve unless the target already has a straight feeder
    # or is fed from both sides; otherwise this belt sideloads it
    behind = occ.get(_add(tt, STEP[OPPOSITE[td]]))
    straight_fed = (
        target["type"] == "transport-belt"
        and is_belt(behind)
        and dchar(behind) == td
        and not (behind["type"] == "underground-belt" and behind.get("belt_type") == "input")
    )
    other_side = occ.get(_add(tt, STEP[d]))
    both_sides = is_belt(other_side) and dchar(other_side) == OPPOSITE[d]
    sideload = straight_fed or both_sides or target["type"] == "underground-belt"
    if sideload and code != "s":
        out.append(Finding(t, "sideload", f"sideloads the belt at {tt[0]},{tt[1]} (mark it 's' if intended)"))


def _paired(e, occ):
    """Walk along the underground's line for the first same-name, same-direction
    underground; it pairs only if it is the opposite half."""
    d = dchar(e)
    step = STEP[d] if e.get("belt_type") == "input" else STEP[OPPOSITE[d]]
    want = "output" if e.get("belt_type") == "input" else "input"
    t = tuple(e["tile"])
    for k in range(1, (e.get("max_distance") or 5) + 1):
        o = occ.get((t[0] + k * step[0], t[1] + k * step[1]))
        if o is not None and o["name"] == e["name"] and o["direction"] == e["direction"]:
            return o.get("belt_type") == want
    return False


def _fluid_findings(e, t, conn_at, out):
    """Rule (j): pipe connections must meet a neighbour's facing connection."""
    conns = e.get("fluid") or []
    if not conns or e["type"] == "mining-drill":
        return  # a drill's fluid input is optional (only uranium needs it)

    def matched(c):
        return any(o is not e and c2["to"] == c["at"] for o, c2 in conn_at.get(tuple(c["to"]), []))

    hits = [matched(c) for c in conns]
    if not any(hits):
        out.append(Finding(t, "fluid-isolated", f"{e['name']} has no connected pipe connection"))
        return
    if e["type"] == "offshore-pump" and not all(hits):
        out.append(Finding(t, "fluid-open", "offshore pump output connects to nothing"))
    if e["type"] == "boiler":
        water = [h for c, h in zip(conns, hits) if c.get("fluid") == "water"]
        steam = [h for c, h in zip(conns, hits) if c.get("fluid") == "steam"]
        if water and not any(water):
            out.append(Finding(t, "fluid-open", "boiler has no water input connected"))
        if steam and not any(steam):
            out.append(Finding(t, "fluid-open", "boiler steam output connects to nothing"))


def _overlaps(rect, e):
    x, y = e["tile"]
    return x < rect[2] and x + e["w"] > rect[0] and y < rect[3] and y + e["h"] > rect[1]


def _power_sources(ents):
    """Rule (k): which poles sit on a network that has a generator."""
    poles = [e for e in ents if e.get("supply")]
    gens = [e for e in ents if e["type"] == "generator"]
    src = {id(p) for p in poles if p.get("powered") or any(_overlaps(p["supply"], g) for g in gens)}
    adj = {id(p): [] for p in poles}
    for i, a in enumerate(poles):
        for b in poles[i + 1:]:
            reach = min(a.get("wire") or 7.5, b.get("wire") or 7.5)
            dx, dy = a["position"][0] - b["position"][0], a["position"][1] - b["position"][1]
            if dx * dx + dy * dy <= reach * reach + 1e-9:
                adj[id(a)].append(id(b))
                adj[id(b)].append(id(a))
    live, todo = set(src), list(src)
    while todo:
        for n in adj[todo.pop()]:
            if n not in live:
                live.add(n)
                todo.append(n)
    return poles, live


def lint(snap, codes):
    occ = occupancy(snap)
    ents = snap["entities"]
    extracted = set()  # tiles some inserter picks from
    for e in ents:
        if e["type"] == "inserter" and e.get("pickup"):
            extracted.add(tile_of(e["pickup"]))

    conn_at = {}
    for e in ents:
        for c in e.get("fluid") or []:
            conn_at.setdefault(tuple(c["at"]), []).append((e, c))
    all_poles, live_poles = _power_sources(ents)

    out = []
    for e in ents:
        t = tuple(e["tile"])
        if t not in codes:
            continue
        code, want = codes[t]
        if CODES[code][0] != e["name"]:
            continue

        if e.get("ghost") and e.get("can_place") is False:
            out.append(Finding(t, "placement", f"{e['name']} ghost can't be built here (collision, water or no ore)"))

        if e["type"] == "inserter":
            pick = occ.get(tile_of(e["pickup"]))
            drop = occ.get(tile_of(e["drop"]))
            if not _sink_ok(pick):
                out.append(Finding(t, "inserter", f"nothing to pick up from at {tile_of(e['pickup'])}"))
            if not _sink_ok(drop):
                out.append(Finding(t, "inserter", f"nothing to drop into at {tile_of(e['drop'])}"))
            elif drop["type"] in MACHINE_TYPES and not any(ft in extracted for ft in footprint(drop)):
                out.append(Finding(t, "dead-end", f"drops into a {drop['name']} whose output nothing takes"))
            got = side_of(t, e["drop"])
            if got != want:
                out.append(Finding(t, "intent", f"stamp says drop {want}, engine drops {got}"))
        elif CODES[code][2] == "belt" and DCHAR_DIR[want] != e["direction"]:
            out.append(Finding(t, "intent", f"stamp says {want}, engine direction is {dchar(e)}"))

        if e["type"] == "mining-drill" and e.get("drop") and not _sink_ok(occ.get(tile_of(e["drop"]))):
            out.append(Finding(t, "drill", f"drill outputs onto the ground at {tile_of(e['drop'])}"))

        if e["type"] == "underground-belt" and not _paired(e, occ):
            other = "output ahead" if e.get("belt_type") == "input" else "input behind"
            out.append(Finding(t, "underground", f"no matching {other} within {e.get('max_distance')} tiles"))

        if e["type"] in ("transport-belt",) or (e["type"] == "underground-belt" and e.get("belt_type") == "output"):
            _belt_findings(e, code, occ, out)

        _fluid_findings(e, t, conn_at, out)

        if e.get("needs_power"):
            covering = [p for p in all_poles if _overlaps(p["supply"], e)]
            if not covering:
                out.append(Finding(t, "power", f"{e['name']} is outside every pole's supply area"))
            elif not any(id(p) in live_poles for p in covering):
                out.append(Finding(t, "no-power-source", f"{e['name']}'s poles never reach a steam engine or powered network"))
    return sorted(set(out))
