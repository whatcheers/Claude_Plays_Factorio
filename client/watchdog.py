"""Maintenance watchdog (the player's idea): once a minute, check every machine
in Claude's tags plus power headroom. Anything outside its OK set for STREAK
checks in a row is reported once (stdout for Claude's monitor, plus game chat),
and again when it recovers. Run it in the background."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fx  # noqa: E402
from world import side_of  # noqa: E402
from bridge import Bridge  # noqa: E402

STREAK = 5
PERIOD = 60
POWER_LUA = (
    "local used, cap = 0, 0"
    " for _, e in pairs(game.surfaces[1].find_entities_filtered{type='generator'}) do"
    "  used = used + e.energy_generated_last_tick * 60 cap = cap + e.prototype.get_max_energy_production() * 60 end"
    " rcon.print(string.format('%.0f %.0f', used / 1000, cap / 1000))"
)
SKIP_TAGS = {"acA", "team-chest"}
PLAIN = {
    "no_power": "has no power", "low_power": "is short on power", "no_fuel": "is out of fuel",
    "no_ingredients": "has nothing to smelt", "item_ingredient_shortage": "is starved of parts",
    "missing_science_packs": "is missing science packs", "no_minable_resources": "has run out of ore",
    "waiting_for_space_in_destination": "is backed up", "full_output": "is backed up",
    "no_recipe": "has no recipe set", "no_input_fluid": "has no water", "disabled_by_script": "is switched off",
}


def plain(e):
    what = e["name"].replace("-", " ").replace("assembling machine", "assembler")
    return f"the {what} at ({e['tile'][0]}, {e['tile'][1]})"


def say(b, text):
    print(f"[Maintenance Crew] {text}", flush=True)
    try:
        b.call("say", {"text": "[Maintenance Crew] " + text}, check=False)
    except Exception:
        pass


OUTPUT_LUA = ("local e = game.surfaces[1].find_entities_filtered{area={{%s, %s}, {%s, %s}}, type='assembling-machine'}[1]"
              " rcon.print(e and #e.get_inventory(defines.inventory.assembling_machine_output).get_contents() or 0)")


def has_output(b, e):
    x, y = e["tile"]
    try:
        return int(b.lua(OUTPUT_LUA % (x + 0.2, y + 0.2, x + 0.8, y + 0.8)).strip() or 0) > 0
    except Exception:
        return False


def reversed_inserter(e, codes):
    """An inserter whose engine drop side disagrees with the stamp (e.g. replaced
    facing the wrong way): it starves what it should feed and looks 'waiting'."""
    if e.get("type") != "inserter" or not e.get("drop"):
        return False
    want = codes.get(tuple(e["tile"]))
    if not want or want[0] not in ("i", "I", "J"):
        return False
    return side_of(tuple(e["tile"]), e["drop"]) not in (want[1], None)


def check(b, streaks, alerted):
    for tag, t in fx.load_state()["tags"].items():
        if tag in SKIP_TAGS:
            continue
        try:
            ents = fx.tag_entities(b, tag)
        except Exception:
            continue
        codes = {(c[0], c[1]): (c[2], c[3]) for c in t.get("codes") or []}
        for e in ents:
            if e.get("invalid") or e.get("ghost"):
                continue
            if reversed_inserter(e, codes):
                key = (tag, tuple(e["tile"]), "reversed")
                if key not in alerted:
                    alerted.add(key)
                    say(b, f"{plain(e)} is facing the wrong way (it drops {side_of(tuple(e['tile']), e['drop'])}, "
                           f"the plan says {codes[tuple(e['tile'])][1]}). Claude, please turn it around.")
                continue
            ok = fx.MACHINE_OK.get(e.get("type"))
            if ok is None:
                continue
            key = (tag, tuple(e["tile"]), e["name"])
            if e.get("status") == "item_ingredient_shortage" and has_output(b, e):
                # finished products waiting: it is paced by demand downstream, not starved
                e = dict(e, status=None)
            if e.get("status") in ok or e.get("status") is None:
                streaks.pop(key, None)
                if key in alerted:
                    alerted.discard(key)
                    say(b, f"{plain(e)} is running again")
                continue
            streaks[key] = streaks.get(key, 0) + 1
            if streaks[key] >= STREAK and key not in alerted:
                alerted.add(key)
                say(b, f"{plain(e)} {PLAIN.get(e['status'], e['status'].replace('_', ' '))} ({streaks[key]} min so far)")
    used, cap = map(float, b.lua(POWER_LUA).split())
    key = ("power",)
    if cap and used > 0.9 * cap:
        if key not in alerted:
            alerted.add(key)
            say(b, f"the power plant is near its limit ({used / 1000:.1f} of {cap / 1000:.1f} MW); we need more steam")
    elif key in alerted and used < 0.8 * cap:
        alerted.discard(key)


def main():
    streaks, alerted = {}, set()
    down = False  # report an outage once, not every minute
    print("[Maintenance Crew] on shift", flush=True)
    while True:
        try:
            with Bridge() as b:
                check(b, streaks, alerted)
            if down:
                print("[Maintenance Crew] checks working again", flush=True)
                down = False
        except Exception as e:  # game reloading etc.
            if not down:
                print(f"[Maintenance Crew] check failed: {e}", flush=True)
                down = True
        time.sleep(PERIOD)


if __name__ == "__main__":
    main()
