"""Shared helpers for tests that need the hosted game with claude-bridge."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "client"))

from bridge import Bridge  # noqa: E402


def fx(*args, timeout=900):
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "client", "fx.py"), *map(str, args)],
        capture_output=True, text=True, timeout=timeout, cwd=ROOT,
    )
    return p.returncode, p.stdout + p.stderr


def bridge():
    return Bridge()


def char_pos(b):
    b.call("spawn")
    return b.call("status")["character"]


def find_clear(b, w, h, near=None, start=12, ore=False):
    """Top-left tile of a w*h area (plus a 1-tile margin) with no entities,
    no water, and (unless ore=True) no resources."""
    cx, cy = near or char_pos(b)
    cx, cy = int(cx), int(cy)
    for r in range(start, 120, 4):
        for dx, dy in ((r, 0), (0, r), (-r, 0), (0, -r), (r, r), (-r, r), (r, -r), (-r, -r)):
            x, y = cx + dx, cy + dy
            snap = b.call("scan", {"area": [x - 1, y - 1, x + w, y + h]})
            if any(e["type"] != "character" for e in snap["entities"]):
                continue
            if snap["water"] or (snap["resources"] and not ore):
                continue
            return x, y
    raise RuntimeError("no clear area found")


def write_stamp(tmp_path, text, name="s.txt"):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def grid_rows(out):
    return [l.split("|", 1)[1] for l in out.splitlines() if "|" in l]
