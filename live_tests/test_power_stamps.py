from helpers import bridge, find_clear, fx, grid_rows

from layout import load_stamp, rotate


def expected_rows(stamp):
    grid = [[".."] * stamp.w for _ in range(stamp.h)]
    for e in stamp.entities:
        for dy in range(e.h):
            for dx in range(e.w):
                grid[e.y + dy][e.x + dx] = e.code + e.dchar
    return ["".join(r) for r in grid]


def test_power_stamp_looks_like_its_tiles_in_every_rotation():
    stamp = load_stamp("stamps/power.txt")
    for rot in (0, 90, 180, 270):
        rs = rotate(stamp, rot)
        with bridge() as b:
            x, y = find_clear(b, rs.w, rs.h)
        tag = f"lt-pw{rot}"
        fx("unplan", tag)
        code, out = fx("plan", "power", x, y, rot, "--tag", tag)
        try:
            assert code == 0 and "MISMATCH" not in out, out
            code, out = fx("look", x, y, x + rs.w - 1, y + rs.h - 1)
            assert grid_rows(out) == expected_rows(rs), (rot, out)
        finally:
            fx("unplan", tag)
