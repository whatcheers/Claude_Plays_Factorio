"""After Automation 2: upgrade the green-flask assembler (the bottleneck, 12 s
per flask) to an assembling-machine-2 (8 s). Steel comes from the player's
steelworks. Resumable.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fx  # noqa: E402
from bridge import Bridge  # noqa: E402
from play import ChatInterrupt, PlayFail, inv, must, run, withdraw  # noqa: E402
from scale_run import top_up  # noqa: E402
from science_run import COPPER_CHEST, IRON_CHEST  # noqa: E402

PLAYER_STEELWORKS = (-94, 32)  # the player's steel furnace (2x2, centred on this corner)
G = (-68, 36)                  # green-flask assembler, top-left tile
TARGETS = [G, (-105, 20)]   # green assemblers of blocks 1 and 2


def assembler_name(b, x, y):
    s = b.call("scan", {"area": [x, y, x, y]})
    return next((e["name"] for e in s["entities"] if e["type"] == "assembling-machine"), None)


def steel(b, want):
    """Steel comes from the player's steelworks (a stone furnace at -94,32);
    they asked me not to build my own."""
    if inv(b).get("steel-plate", 0) >= want:
        return
    got = withdraw(b, *PLAYER_STEELWORKS, "steel-plate", want - inv(b).get("steel-plate", 0))
    if inv(b).get("steel-plate", 0) < want:
        raise PlayFail(f"need {want} steel, have {inv(b).get('steel-plate', 0)} (took {got} from the steelworks)")


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
                top_up(b, *IRON_CHEST, "iron-plate", 60)
                top_up(b, *COPPER_CHEST, "copper-plate", 10)
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
        if run("prove", "green", 1800) or run("prove", "green2", 1800):
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
