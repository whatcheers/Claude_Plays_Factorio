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

# code -> (entity name, size, direction rule)
#   "belt": dchar is the belt/output direction   "drop": dchar is the drop side
#   "none": dchar must be "."
CODES = {
    "b": ("transport-belt", 1, "belt"),
    "s": ("transport-belt", 1, "belt"),
    "e": ("transport-belt", 1, "belt"),
    "u": ("underground-belt", 1, "belt"),
    "U": ("underground-belt", 1, "belt"),
    "i": ("burner-inserter", 1, "drop"),
    "I": ("inserter", 1, "drop"),
    "F": ("stone-furnace", 2, "none"),
    "D": ("burner-mining-drill", 2, "belt"),
    "A": ("assembling-machine-1", 3, "none"),
    "c": ("wooden-chest", 1, "none"),
    "p": ("small-electric-pole", 1, "none"),
}


class StampError(ValueError):
    def __init__(self, msg, line, col):
        super().__init__(f"line {line} col {col}: {msg}")
        self.line, self.col = line, col


@dataclass(frozen=True)
class StampEntity:
    code: str
    x: int  # top-left tile of footprint, relative to the stamp
    y: int
    dchar: str
    size: int


@dataclass(frozen=True)
class Stamp:
    w: int
    h: int
    entities: tuple


@dataclass(frozen=True)
class Placed:
    code: str
    name: str
    size: int
    tile: tuple  # world top-left tile
    position: tuple  # world centre, as Factorio expects
    direction: int  # engine direction (inserters already converted)
    dchar: str  # stamp-notation direction (drop side for inserters)
    belt_type: object  # "input" / "output" for underground belts, else None


def inserter_direction(drop_side):
    """Engine direction for an inserter that should DROP toward drop_side.

    Measured: an inserter's direction is its pickup side.
    """
    return DCHAR_DIR[OPPOSITE[drop_side]]


def parse_stamp(text):
    rows = []  # (line_no, [(code, dchar)])
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip("\r\n").rstrip()
        if not line or line.lstrip().startswith("#"):
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
            if rule != "none" and d not in DCHAR_DIR:
                raise StampError(f"{code!r} needs a direction (^ > v <), got {d!r}", line_no, col + 1)
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
            size = CODES[code][1]
            for dy in range(size):
                for dx in range(size):
                    tx, ty = x + dx, y + dy
                    if ty >= h or tx >= w:
                        raise StampError(f"{code!r} needs a full {size}x{size} footprint here", rows[y][0], 2 * x + 1)
                    other = rows[ty][1][tx]
                    if other is None or other[0] != code or (tx, ty) in seen:
                        raise StampError(f"incomplete {size}x{size} {code!r} footprint", rows[ty][0], 2 * tx + 1)
                    if other[1] != d:
                        raise StampError(f"mixed directions inside one {code!r} footprint", rows[ty][0], 2 * tx + 1)
                    seen.add((tx, ty))
            entities.append(StampEntity(code, x, y, d, size))
    return Stamp(w, h, tuple(entities))


def load_stamp(path):
    with open(path, encoding="utf-8") as f:
        try:
            return parse_stamp(f.read())
        except StampError as e:
            raise StampError(f"{path}: {e}", e.line, e.col) from None


def _rot_dchar(d, turns):
    if d == ".":
        return d
    for _ in range(turns):
        d = CW[d]
    return d


def rotate(stamp, rot):
    if rot not in (0, 90, 180, 270):
        raise ValueError(f"rotation must be 0/90/180/270, got {rot}")
    s = stamp
    for _ in range(rot // 90):
        # clockwise: tile (x, y) in a w*h grid -> (h-1-y, x)
        ents = []
        for e in s.entities:
            ents.append(replace(e, x=s.h - (e.y + e.size), y=e.x, dchar=_rot_dchar(e.dchar, 1)))
        s = Stamp(s.h, s.w, tuple(ents))
    return s


def place(stamp, X, Y, rot):
    """World placements for a stamp whose rotated top-left tile lands on (X, Y)."""
    out = []
    for e in rotate(stamp, rot).entities:
        name, size, rule = CODES[e.code]
        tx, ty = X + e.x, Y + e.y
        if rule == "drop":
            direction = inserter_direction(e.dchar)
        elif rule == "belt":
            direction = DCHAR_DIR[e.dchar]
        else:
            direction = DIR["north"]
        belt_type = {"u": "input", "U": "output"}.get(e.code)
        out.append(Placed(e.code, name, size, (tx, ty), (tx + size / 2, ty + size / 2), direction, e.dchar, belt_type))
    return out
