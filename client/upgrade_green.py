"""After Automation 2: upgrade the green-flask assembler (the bottleneck, 12 s
per flask) to an assembling-machine-2 (8 s). Steel comes from Claude's own
stone furnace ("steelworks"), loaded by hand like any player would. Resumable.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fx  # noqa: E402
from bridge import Bridge  # noqa: E402
from play import ChatInterrupt, PlayFail, gather, inv, must, run, withdraw  # noqa: E402
from power_run import tag_state  # noqa: E402
from scale_run import top_up  # noqa: E402
from science_run import IRON_CHEST  # noqa: E402

FURNACE = (-91, 51)            # top-left of the steelworks furnace (off the ore)
G = (-68, 36)                  # green-flask assembler, top-left tile
TARGETS = [G]


def assembler_name(b, x, y):
    s = b.call("scan", {"area": [x, y, x, y]})
    return next((e["name"] for e in s["entities"] if e["type"] == "assembling-machine"), None)


def steel(b, want):
    if inv(b).get("steel-plate", 0) >= want:
        return
    fx_tile = FURNACE
    if tag_state(b, "steelworks") != "built":
        if inv(b).get("stone-furnace", 0) < 1:
            gather(b, "stone", 5)
            must("craft", "stone-furnace", 1)
        if tag_state(b, "steelworks") is None:
            must("walk", fx_tile[0] + 1, fx_tile[1] + 3, "--radius", 2)
            must("plan", "furnace", fx_tile[0], fx_tile[1], 0, "--tag", "steelworks")
        x1, y1 = fx_tile
        must("look", x1 - 1, y1 - 1, x1 + 2, y1 + 2)
        must("shot", x1 + 1, y1 + 1, 1)
        must("lint", "steelworks")
        must("build", "steelworks")
    need = want - inv(b).get("steel-plate", 0)
    top_up(b, *IRON_CHEST, "iron-plate", 5 * need)
    gather(b, "coal", 3)
    cx, cy = fx_tile[0] + 1, fx_tile[1] + 1
    must("walk", cx, cy + 2, "--radius", 2)
    run("put", cx, cy, "coal", 3)
    must("put", cx, cy, "iron-plate", 5 * need)
    # 16 s of furnace time per steel plate
    b.run_ticks(60 * 17 * need + 120)
    must("take", cx, cy, "steel-plate", need)


def main():
    with Bridge() as b:
        must("spawn")
        todo = [t for t in TARGETS if assembler_name(b, *t) == "assembling-machine-1"]
        if not todo:
            print("nothing to upgrade")
            return
        if b.lua("rcon.print(tostring(game.forces.player.technologies['automation-2'].researched))").strip() != "true":
            raise PlayFail("Automation 2 is not researched yet")
        steel(b, 2 * len(todo))
        for t in todo:
            if inv(b).get("assembling-machine-2", 0) < 1:
                top_up(b, *IRON_CHEST, "iron-plate", 25)
                must("craft", "copper-cable", 5)
                must("craft", "electronic-circuit", 3)
                must("craft", "iron-gear-wheel", 5)
                if inv(b).get("assembling-machine-1", 0) < 1:
                    must("craft", "iron-gear-wheel", 5)
                    must("craft", "copper-cable", 5)
                    must("craft", "electronic-circuit", 3)
                    must("craft", "assembling-machine-1", 1)
                must("craft", "assembling-machine-2", 1)
            must("walk", t[0] + 1.5, t[1] + 4.5, "--radius", 2)
            must("upgrade", t[0], t[1], "assembling-machine-2")
        if run("prove", "green", 1800):
            raise PlayFail("green prove failed after the upgrade")
        must("say", "Green assembler upgraded to an assembler 2: green science is 50% faster.")
        print("UPGRADE PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
