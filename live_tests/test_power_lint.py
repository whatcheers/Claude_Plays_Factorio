from helpers import bridge, find_clear, fx, write_stamp

SABOTAGE = """\
....E^E^E^
....E^E^E^
....E^E^E^
....E^E^E^
....E^E^E^
....B>B>..
O>x.B>B>..
....B>B>..
"""


def lint_of(stamp, w, h, tag, rot=0):
    with bridge() as b:
        x, y = find_clear(b, w, h)
    fx("unplan", tag)
    code, out = fx("plan", stamp, x, y, rot, "--tag", tag)
    assert code == 0, out
    try:
        return x, y, fx("lint", tag)
    finally:
        fx("unplan", tag)


def test_power_block_fluids_connect_on_land():
    x, y, (code, out) = lint_of("power", 5, 7, "lt-fl")
    assert "fluid-" not in out, out
    assert f"{x},{y + 6} placement" in out  # an offshore pump needs water


def test_rotated_boiler_flagged(tmp_path):
    x, y, (code, out) = lint_of(write_stamp(tmp_path, SABOTAGE), 5, 8, "lt-sab2")
    assert code != 0
    assert "fluid-isolated" in out or "fluid-open" in out, out


def test_lab_on_dead_pole_chain_has_no_source(tmp_path):
    x, y, (code, out) = lint_of(write_stamp(tmp_path, "L.L.L.p.\nL.L.L...\nL.L.L...\n"), 4, 3, "lt-ns")
    assert f"{x},{y} no-power-source" in out, out
