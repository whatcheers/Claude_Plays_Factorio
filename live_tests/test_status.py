import re

from helpers import bridge, fx

USER_INV = """
local p = game.connected_players[1]
local inv = p.get_main_inventory()
local t = {}
if inv then for _, it in pairs(inv.get_contents()) do t[#t+1] = it.name .. "=" .. it.count end end
table.sort(t)
rcon.print(p.name .. ":" .. table.concat(t, ","))
"""


def test_status_reports_version_tick_paused():
    code, out = fx("status")
    assert code == 0, out
    assert re.search(r"bridge 0\.1\.0\s+tick \d+\s+paused (true|false)", out), out


def test_spawn_is_idempotent_and_leaves_user_alone():
    with bridge() as b:
        before = b.lua(USER_INV).strip()
    code, out = fx("spawn")
    assert code == 0, out
    code, out = fx("spawn")
    assert code == 0 and "already exists" in out, out
    code, out = fx("status")
    assert re.search(r"character -?\d+\.\d+,-?\d+\.\d+", out), out
    with bridge() as b:
        after = b.lua(USER_INV).strip()
        n = b.lua('local n=0 for _,c in pairs(game.surfaces[1].find_entities_filtered{type="character"}) do n=n+1 end rcon.print(n)').strip()
    assert before == after
    assert int(n) >= 2  # the user's character plus Claude's
