"""Stamps: parse, rotate, and place 2-char-per-tile layout templates.

See .build/SPEC.md "Stamp format" and docs/conventions.md.
"""
from dataclasses import dataclass, replace

# Factorio 2.0 16-way direction enum (measured, docs/conventions.md)
DIR = {"north": 0, "east": 4, "south": 8, "west": 12}
DCHAR_DIR = {"^": DIR["north"], ">": DIR["east"], "v": DIR["south"], "<": DIR["west"]}
DIR_DCHAR = {v: k for k, v in DCHAR_DIR.items()}
OPPOSITE = {"^": "v", "v": "^", ">": "<", "<": ">"}
CW = {"^": ">", ">": "v", "v": "<", "<": "^"}
STEP = {"^": (0, -1), ">": (1, 0), "v": (0, 1), "<": (-1, 0)}

# code -> (entity name, (w, h) when facing north, direction rule)
#   "belt": dchar is the entity's facing      "drop": dchar is the drop side
#   "none": dchar must be "."                  "recipe": "." or a recipe key
CODES = {
    "b": ("transport-belt", (1, 1), "belt"),
    "s": ("transport-belt", (1, 1), "belt"),
    "e": ("transport-belt", (1, 1), "belt"),
    "u": ("underground-belt", (1, 1), "belt"),
    "U": ("underground-belt", (1, 1), "belt"),
    "i": ("burner-inserter", (1, 1), "drop"),
    "I": ("inserter", (1, 1), "drop"),
    "F": ("stone-furnace", (2, 2), "none"),
    "D": ("burner-mining-drill", (2, 2), "belt"),
    "M": ("electric-mining-drill", (3, 3), "belt"),
    "J": ("long-handed-inserter", (1, 1), "drop"),
    "A": ("assembling-machine-1", (3, 3), "recipe"),
    "c": ("wooden-chest", (1, 1), "none"),
    "p": ("small-electric-pole", (1, 1), "none"),
    "B": ("boiler", (3, 2), "belt"),
    "E": ("steam-engine", (3, 5), "belt"),  # symmetric: only the axis matters (v -> ^, < -> >)
    "O": ("offshore-pump", (1, 1), "drop"),  # dchar = output side; engine faces the other way
    "x": ("pipe", (1, 1), "none"),
    "L": ("lab", (3, 3), "none"),
}
RECIPE_KEYS = set("abcdefghijklmnopqrstuwxyz")  # lowercase, never "v" (a direction)


class StampError(ValueError):
    def __init__(self, msg, line, col):
        super().__init__(f"line {line} col {col}: {msg}")
        self.line, self.col = line, col


@dataclass(frozen=True)
class StampEntity:
    code: str
    x: int  # top-left tile of footprint, relative to the stamp
    y: int
    dchar: str  # direction char, or recipe key for assemblers
    w: int
    h: int

    @property
    def size(self):
        return self.w if self.w == self.h else None


@dataclass(frozen=True)
class Stamp:
    w: int
    h: int
    entities: tuple
    recipes: tuple = ()  # ((key, recipe-name), ...)


@dataclass(frozen=True)
class Placed:
    code: str
    name: str
    w: int
    h: int
    tile: tuple  # world top-left tile
    position: tuple  # world centre, as Factorio expects
    direction: int  # engine direction (inserters already converted)
    dchar: str  # stamp-notation char (drop side for inserters, recipe key for assemblers)
    belt_type: object  # "input" / "output" for underground belts, else None
    recipe: object = None

    @property
    def size(self):
        return self.w if self.w == self.h else None


def inserter_direction(drop_side):
    """Engine direction for an inserter that should DROP toward drop_side.

    Measured: an inserter's direction is its pickup side.
    """
    return DCHAR_DIR[OPPOSITE[drop_side]]


AXIS_ONLY = {"E"}
AXIS = {"^": "^", "v": "^", ">": ">", "<": ">", ".": "."}


def footprint_size(code, dchar):
    w, h = CODES[code][1]
    return (h, w) if dchar in (">", "<") else (w, h)


def parse_stamp(text):
    rows = []  # (line_no, [(code, dchar)])
    recipes = {}
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip("\r\n").rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("@"):
            parts = line[1:].split()
            if len(parts) != 2 or len(parts[0]) != 1 or parts[0] not in RECIPE_KEYS:
                raise StampError("recipe line must be '@k recipe-name' with k a lowercase letter other than v", line_no, 2)
            recipes[parts[0]] = parts[1]
            continue
        if len(line) % 2:
            raise StampError("odd number of characters; tiles are 2 chars", line_no, len(line))
        tiles = []
        for i in range(0, len(line), 2):
            code, d = line[i], line[i + 1]
            col = i + 1
            if code == "." and d == ".":
                tiles.append(None)
                continue
            if code not in CODES:
                raise StampError(f"unknown entity code {code!r}", line_no, col)
            rule = CODES[code][2]
            if rule == "none" and d != ".":
                raise StampError(f"{code!r} takes no direction, got {d!r}", line_no, col + 1)
            if rule == "recipe" and d != "." and d not in recipes:
                raise StampError(f"{code!r} recipe key {d!r} has no '@{d} recipe' line above", line_no, col + 1)
            if rule in ("belt", "drop") and d not in DCHAR_DIR:
                raise StampError(f"{code!r} needs a direction (^ > v <), got {d!r}", line_no, col + 1)
            if code in AXIS_ONLY:
                d = AXIS[d]
            tiles.append((code, d))
        rows.append((line_no, tiles))
    if not rows:
        raise StampError("empty stamp", 1, 1)
    w = len(rows[0][1])
    for line_no, tiles in rows:
        if len(tiles) != w:
            raise StampError(f"row has {len(tiles)} tiles, expected {w}", line_no, 2 * min(len(tiles), w) + 1)

    h = len(rows)
    seen = set()
    entities = []
    for y in range(h):
        for x in range(w):
            t = rows[y][1][x]
            if t is None or (x, y) in seen:
                continue
            code, d = t
            fw, fh = footprint_size(code, d)
            for dy in range(fh):
                for dx in range(fw):
                    tx, ty = x + dx, y + dy
                    if ty >= h or tx >= w:
                        raise StampError(f"{code!r} needs a full {fw}x{fh} footprint here", rows[y][0], 2 * x + 1)
                    other = rows[ty][1][tx]
                    if other is None or other[0] != code or (tx, ty) in seen:
                        raise StampError(f"incomplete {fw}x{fh} {code!r} footprint", rows[ty][0], 2 * tx + 1)
                    if other[1] != d:
                        raise StampError(f"mixed direction/recipe inside one {code!r} footprint", rows[ty][0], 2 * tx + 1)
                    seen.add((tx, ty))
            entities.append(StampEntity(code, x, y, d, fw, fh))
    return Stamp(w, h, tuple(entities), tuple(sorted(recipes.items())))


def load_stamp(path):
    with open(path, encoding="utf-8") as f:
        try:
            return parse_stamp(f.read())
        except StampError as e:
            raise StampError(f"{path}: {e}", e.line, e.col) from None


def _rot_dchar(code, d):
    if CODES[code][2] in ("none", "recipe") or d == ".":
        return d
    return AXIS[CW[d]] if code in AXIS_ONLY else CW[d]


def rotate(stamp, rot):
    if rot not in (0, 90, 180, 270):
        raise ValueError(f"rotation must be 0/90/180/270, got {rot}")
    s = stamp
    for _ in range(rot // 90):
        # clockwise: tile (x, y) in a W*H grid -> (H-1-y, x); footprints swap w/h
        ents = []
        for e in s.entities:
            ents.append(replace(e, x=s.h - (e.y + e.h), y=e.x, w=e.h, h=e.w, dchar=_rot_dchar(e.code, e.dchar)))
        s = Stamp(s.h, s.w, tuple(ents), s.recipes)
    return s


def place(stamp, X, Y, rot):
    """World placements for a stamp whose rotated top-left tile lands on (X, Y)."""
    recipes = dict(stamp.recipes)
    out = []
    for e in rotate(stamp, rot).entities:
        name, _, rule = CODES[e.code]
        tx, ty = X + e.x, Y + e.y
        recipe = None
        if rule == "drop":
            direction = inserter_direction(e.dchar)
        elif rule == "belt":
            direction = DCHAR_DIR[e.dchar]
        else:
            direction = DIR["north"]
            if rule == "recipe" and e.dchar != ".":
                recipe = recipes[e.dchar]
        belt_type = {"u": "input", "U": "output"}.get(e.code)
        out.append(Placed(e.code, name, e.w, e.h, (tx, ty), (tx + e.w / 2, ty + e.h / 2), direction, e.dchar, belt_type, recipe))
    return out
