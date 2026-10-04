import os

from helpers import ROOT, bridge, find_clear, fx, write_stamp

BURNER_IRON = open(os.path.join(ROOT, "stamps", "burner-iron.txt")).read()


def test_sabotaged_burner_iron_flagged_at_reversed_inserter(tmp_path):
    bad = BURNER_IRON.replace("i>c.", "i<c.")
    assert bad != BURNER_IRON
    with bridge() as b:
        x, y = find_clear(b, 7, 4, ore=True)
    fx("unplan", "lt-sab")
    code, out = fx("plan", write_stamp(tmp_path, bad), x, y, 0, "--tag", "lt-sab")
    try:
        assert code == 0, out
        code, out = fx("lint", "lt-sab")
        assert code != 0
        assert f"{x + 2},{y + 3} dead-end" in out, out
    finally:
        fx("unplan", "lt-sab")


def test_clean_layout_lints_clean(tmp_path):
    with bridge() as b:
        x, y = find_clear(b, 3, 1)
    fx("unplan", "lt-clean")
    code, out = fx("plan", write_stamp(tmp_path, "c.i>c.\n"), x, y, 0, "--tag", "lt-clean")
    try:
        assert code == 0, out
        code, out = fx("lint", "lt-clean")
        assert code == 0 and "clean" in out, out
    finally:
        fx("unplan", "lt-clean")


def test_build_gate_requires_lint_look_shot_and_fresh_area(tmp_path):
    with bridge() as b:
        x, y = find_clear(b, 3, 1)
    fx("unplan", "lt-gate")
    fx("unplan", "lt-intruder")
    code, out = fx("plan", write_stamp(tmp_path, "c.i>c.\n"), x, y, 0, "--tag", "lt-gate")
    assert code == 0, out
    try:
        code, out = fx("build", "lt-gate")
        assert code != 0 and "lint" in out and "look" in out and "shot" in out, out
        assert fx("lint", "lt-gate")[0] == 0
        code, out = fx("build", "lt-gate")
        assert code != 0 and "look" in out and "shot" in out and "lint," not in out, out
        assert fx("look", x - 1, y - 1, x + 3, y + 1)[0] == 0
        code, out = fx("build", "lt-gate")
        assert code != 0 and "shot" in out, out
        code, out = fx("shot", x + 1.5, y + 0.5, 1)
        assert code == 0 and "covers tag lt-gate" in out, out

        # something new within 4 tiles invalidates every check
        code, out = fx("plan", write_stamp(tmp_path, "c.\n", "one.txt"), x, y + 2, 0, "--tag", "lt-intruder")
        assert code == 0, out
        code, out = fx("build", "lt-gate")
        assert code != 0 and "area changed since checks" in out, out
    finally:
        fx("unplan", "lt-gate")
        fx("unplan", "lt-intruder")
