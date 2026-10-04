"""ASCII view of a scan snapshot, in stamp notation (2 chars per tile)."""
from world import dchar, footprint, side_of

RESOURCE_GLYPH = {"iron-ore": "'i", "copper-ore": "'c", "coal": "'k", "stone": "'s", "uranium-ore": "'u", "crude-oil": "'o"}
SIMPLE = {"stone-furnace": "F.", "assembling-machine-1": "A.", "wooden-chest": "c.", "small-electric-pole": "p.", "pipe": "x.", "lab": "L."}
INSERTER_CODE = {"burner-inserter": "i", "inserter": "I", "long-handed-inserter": "J"}
TYPE_GLYPH = {"tree": "T.", "simple-entity": "R.", "character": "@@"}


def glyph(e):
    name, typ = e["name"], e["type"]
    if name in SIMPLE:
        return SIMPLE[name]
    if name == "transport-belt":
        return "b" + dchar(e)
    if name == "underground-belt":
        return ("u" if e.get("belt_type") == "input" else "U") + dchar(e)
    if name == "burner-mining-drill":
        return "D" + dchar(e)
    if name == "electric-mining-drill":
        return "M" + dchar(e)
    if name == "boiler":
        return "B" + dchar(e)
    if name == "steam-engine":
        return "E" + dchar(e)
    if name == "offshore-pump":
        # stamp notation is the OUTPUT side; read it from the engine's pipe connection
        for c in e.get("fluid") or []:
            side = side_of(tuple(c["at"]), [c["to"][0] + 0.5, c["to"][1] + 0.5])
            if side:
                return "O" + side
        return "O?"
    if name in INSERTER_CODE:
        # drawn from where the engine says it drops, never from its direction
        side = side_of(tuple(e["tile"]), e["drop"]) if e.get("drop") else None
        return INSERTER_CODE[name] + (side or "?")
    return TYPE_GLYPH.get(typ, "##")


def render(snap):
    x1, y1, x2, y2 = snap["area"]
    w = x2 - x1 + 1
    cells = {}
    for t in snap.get("water", []):
        cells[tuple(t)] = "~~"
    for r in snap.get("resources", []):
        cells[tuple(r["tile"])] = RESOURCE_GLYPH.get(r["name"], "'?")
    ghosts = []
    for e in snap["entities"]:
        g = glyph(e)
        for t in footprint(e):
            cells[t] = g
        if e.get("ghost") and x1 <= e["tile"][0] <= x2 and y1 <= e["tile"][1] <= y2:
            ghosts.append(f"{e['tile'][0]},{e['tile'][1]} {g}")

    ruler = [" "] * (2 * w)
    last_end = -1
    for i in range(w):
        x = x1 + i
        if i == 0 or x % 5 == 0:
            label = str(x)
            if 2 * i <= last_end:
                continue
            for j, ch in enumerate(label):
                if 2 * i + j >= len(ruler):
                    ruler.append(" ")
                ruler[2 * i + j] = ch
            last_end = 2 * i + len(label)
    lines = ["      " + "".join(ruler).rstrip()]
    for y in range(y1, y2 + 1):
        row = "".join(cells.get((x, y), "..") for x in range(x1, x2 + 1))
        lines.append(f"{y:5d}|{row}")
    if ghosts:
        lines.append("? ghosts (top-left tile): " + "; ".join(ghosts))
    return "\n".join(lines)
