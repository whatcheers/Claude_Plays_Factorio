from helpers import bridge, find_clear, fx


def test_tech_lists_current_and_available():
    code, out = fx("tech")
    assert code == 0 and out.startswith("current:"), out


def test_research_refusals_and_switch():
    code, out = fx("research", "no-such-tech")
    assert code != 0 and "no such tech" in out
    code, out = fx("research", "electronics")
    assert code != 0 and "already researched" in out
    code, out = fx("research", "steel-axe")
    assert code != 0 and "first" in out, out
    code, before = fx("tech")
    cur = before.splitlines()[0].split()[1]
    code, out = fx("research", "logistics")
    assert code == 0 and "logistics" in out, out
    if cur != "none":
        assert fx("research", cur)[0] == 0


def test_poles_plans_a_spaced_line():
    with bridge() as b:
        x, y = find_clear(b, 1, 1, start=20)
    fx("unplan", "lt-poles")
    code, out = fx("poles", x, y, x + 20, y + 14, "--tag", "lt-poles")
    try:
        assert code == 0 and "MISMATCH" not in out, out
        n = int([l for l in out.splitlines() if l.endswith(" poles")][0].split()[0])
        assert n >= 6
        code, out = fx("lint", "lt-poles")
        assert "power" not in out
    finally:
        fx("unplan", "lt-poles")


def test_recipe_refuses_without_assembler():
    with bridge() as b:
        x, y = b.call("status")["character"]
    code, out = fx("recipe", x + 1, y + 1, "iron-gear-wheel")
    assert code != 0 and ("no assembler" in out or "not unlocked" in out), out
