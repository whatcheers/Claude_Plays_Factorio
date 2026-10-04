import os
import re

from helpers import bridge, find_clear, fx, grid_rows, write_stamp


def plan(stamp, x, y, rot, tag):
    fx("unplan", tag)
    return fx("plan", stamp, x, y, rot, "--tag", tag)


def test_plan_places_ghosts_where_stamp_says(tmp_path):
    with bridge() as b:
        x, y = find_clear(b, 3, 3)
    s = write_stamp(tmp_path, "b>i>c.\n")
    code, out = plan(s, x, y, 90, "lt-rot")
    try:
        assert code == 0, out
        assert "tag: lt-rot" in out and "MISMATCH" not in out
        assert f"{x},{y} bv" in out and f"{x},{y + 1} iv" in out and f"{x},{y + 2} c." in out
        code, out = fx("look", x, y, x, y + 2)
        assert code == 0, out
        assert grid_rows(out) == ["bv", "iv", "c."]
        ghost_line = [l for l in out.splitlines() if l.startswith("?")]
        assert ghost_line and f"{x},{y}" in ghost_line[0]
        with bridge() as b:
            snap = b.call("scan", {"area": [x, y, x, y + 2]})
        assert all(e["ghost"] for e in snap["entities"] if e["type"] != "character")
    finally:
        fx("unplan", "lt-rot")


def test_inserter_drop_east_renders_east(tmp_path):
    with bridge() as b:
        x, y = find_clear(b, 1, 1)
    code, out = plan(write_stamp(tmp_path, "i>\n"), x, y, 0, "lt-ins")
    try:
        assert code == 0, out
        code, out = fx("look", x, y, x, y)
        assert grid_rows(out) == ["i>"], out
    finally:
        fx("unplan", "lt-ins")


def test_tag_reuse_and_overlap_refused_and_unplan_exact(tmp_path):
    with bridge() as b:
        x, y = find_clear(b, 4, 1)
    s = write_stamp(tmp_path, "c.c.\n")
    code, out = plan(s, x, y, 0, "lt-a")
    assert code == 0, out
    try:
        code, out = fx("plan", s, x + 10, y, 0, "--tag", "lt-a")
        assert code != 0 and "already exists" in out
        code, out = fx("plan", s, x + 1, y, 0, "--tag", "lt-b")
        assert code != 0 and "already holds" in out
        code, out = plan(s, x + 2, y, 0, "lt-b")
        assert code == 0, out
        code, out = fx("unplan", "lt-a")
        assert code == 0 and "removed 2" in out, out
        code, out = fx("look", x, y, x + 3, y)
        assert grid_rows(out) == ["....c.c."], out
    finally:
        fx("unplan", "lt-a")
        fx("unplan", "lt-b")


def test_shot_while_paused():
    with bridge() as b:
        was = b.paused()
        b.set_paused(True)
        x, y = b.call("spawn")["character"]
    try:
        code, out = fx("shot", x, y, 1)
        assert code == 0, out
        path = out.strip().splitlines()[0]
        assert re.search(r"script-output[\\/]claude[\\/].+\.png$", path), path
        assert os.path.getsize(path) > 1000
        with bridge() as b:
            assert b.paused()
    finally:
        with bridge() as b:
            b.set_paused(was)
