"""Maintenance watchdog (the player's idea): once a minute, check every machine
in Claude's tags plus power headroom. Anything outside its OK set for STREAK
checks in a row is reported once (stdout for Claude's monitor, plus game chat),
and again when it recovers. Run it in the background."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fx  # noqa: E402
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


def say(b, text):
    print(f"[maintenance] {text}", flush=True)
    try:
        b.call("say", {"text": "[maintenance] " + text}, check=False)
    except Exception:
        pass


def check(b, streaks, alerted):
    for tag in fx.load_state()["tags"]:
        if tag in SKIP_TAGS:
            continue
        try:
            ents = fx.tag_entities(b, tag)
        except Exception:
            continue
        for e in ents:
            if e.get("invalid") or e.get("ghost"):
                continue
            ok = fx.MACHINE_OK.get(e.get("type"))
            if ok is None:
                continue
            key = (tag, tuple(e["tile"]), e["name"])
            if e.get("status") in ok or e.get("status") is None:
                streaks.pop(key, None)
                if key in alerted:
                    alerted.discard(key)
                    say(b, f"{tag}: {e['name']} at {e['tile'][0]},{e['tile'][1]} is working again")
                continue
            streaks[key] = streaks.get(key, 0) + 1
            if streaks[key] >= STREAK and key not in alerted:
                alerted.add(key)
                say(b, f"{tag}: {e['name']} at {e['tile'][0]},{e['tile'][1]} stuck on {e['status']} for {streaks[key]} min")
    used, cap = map(float, b.lua(POWER_LUA).split())
    key = ("power",)
    if cap and used > 0.9 * cap:
        if key not in alerted:
            alerted.add(key)
            say(b, f"power at {used:.0f} of {cap:.0f} kW: time for more steam")
    elif key in alerted and used < 0.8 * cap:
        alerted.discard(key)


def main():
    streaks, alerted = {}, set()
    print("[maintenance] started", flush=True)
    while True:
        try:
            with Bridge() as b:
                check(b, streaks, alerted)
        except Exception as e:  # game reloading etc.
            print(f"[maintenance] check failed: {e}", flush=True)
        time.sleep(PERIOD)


if __name__ == "__main__":
    main()
