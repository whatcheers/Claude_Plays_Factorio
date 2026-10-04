"""Second boiler + 2 steam engines (3.6 MW total), water from boiler 1's west
port, coal straight off the player's coal belt. Resumable."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fx  # noqa: E402
from bridge import Bridge  # noqa: E402
from green_run import place  # noqa: E402
from layout import load_stamp  # noqa: E402
from play import ChatInterrupt, PlayFail, inv, must, run  # noqa: E402
from power_run import tag_state  # noqa: E402
from scale_run import top_up  # noqa: E402
from science_run import IRON_CHEST  # noqa: E402

TAG = "power2"


def grid():
    st = load_stamp(fx.stamp_path(TAG))
    g = {}
    for e in st.entities:
        for dx in range(e.w):
            for dy in range(e.h):
                g[(35 + e.x + dx, 34 + e.y + dy)] = e.code + e.dchar
    return g


def craft_power(b):
    need = {"steam-engine": 2, "boiler": 1, "pipe": 10, "pipe-to-ground": 2}
    short = {k: max(0, n - inv(b).get(k, 0)) for k, n in need.items()}
    if not any(short.values()):
        return
    ptg = (short["pipe-to-ground"] + 1) // 2
    pipes = short["pipe"] + 10 * ptg + 5 * short["steam-engine"] + 4 * short["boiler"]
    gears = 8 * short["steam-engine"]
    iron = pipes + 2 * gears + 10 * short["steam-engine"] + 5 * ptg + 10
    top_up(b, *IRON_CHEST, "iron-plate", iron)
    if gears:
        must("craft", "iron-gear-wheel", gears)
    if pipes:
        must("craft", "pipe", pipes)
    if ptg:
        must("craft", "pipe-to-ground", ptg)
    if short["steam-engine"]:
        must("craft", "steam-engine", short["steam-engine"])
    if short["boiler"]:
        must("craft", "boiler", short["boiler"])


def main():
    with Bridge() as b:
        must("spawn")
        if tag_state(b, TAG) != "built":
            craft_power(b)
        g = grid()
        # place() regenerates stamps/<tag>.txt from the grid; keep the hand-written header
        with open(fx.stamp_path(TAG), encoding="utf-8") as f:
            header = [line for line in f.read().splitlines() if line.startswith("#")]
        place(b, TAG, g, walk=(40, 44))
        with open(fx.stamp_path(TAG), encoding="utf-8") as f:
            body = [line for line in f.read().splitlines() if not line.startswith("#")]
        with open(fx.stamp_path(TAG), "w", encoding="utf-8") as f:
            f.write("\n".join(header + body) + "\n")
        b.run_ticks(600)
        if run("prove", TAG, 1800):
            raise PlayFail("power2 prove failed")
        must("say", "Second boiler and 2 more steam engines are up: 3.6 MW of capacity.")
        print("POWER2 PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
