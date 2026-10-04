"""Copper capacity: the copper smelter's two drills dig ~60 ore/min but its two
stone furnaces smelt ~37. Steel furnaces are twice as fast: fast-replace both
once Advanced Material Processing is researched (waits for it). Resumable."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402
from play import ChatInterrupt, PlayFail, inv, must, run  # noqa: E402

FURNACES = [(-81, 9), (-76, 9)]   # copper tag, top-left tiles


def furnace_name(b, x, y):
    s = b.call("scan", {"area": [x, y, x, y]})
    return next((e["name"] for e in s["entities"] if e["type"] == "furnace"), None)


def main():
    with Bridge() as b:
        must("spawn")
        todo = [f for f in FURNACES if furnace_name(b, *f) == "stone-furnace"]
        if not todo:
            print("nothing to upgrade")
            return
        while b.lua("rcon.print(tostring(game.forces.player.technologies['advanced-material-processing'].researched))").strip() != "true":
            b.run_ticks(1800)
        short = len(todo) - inv(b).get("steel-furnace", 0)
        if short > 0:
            if inv(b).get("steel-plate", 0) < 6 * short or inv(b).get("stone-brick", 0) < 10 * short:
                raise PlayFail(f"need {6 * short} steel and {10 * short} bricks for {short} steel furnaces")
            must("craft", "steel-furnace", short)
        for x, y in todo:
            must("walk", x + 1, y + 4, "--radius", 2)
            must("upgrade", x, y, "steel-furnace")
        b.run_ticks(3600)
        made = b.lua("local s=game.forces.player.get_item_production_statistics(game.surfaces[1])"
                     " rcon.print(s.get_flow_count{name='copper-plate',category='input',"
                     "precision_index=defines.flow_precision_index.one_minute,count=true})").strip()
        print(f"copper plates in the last minute: {made}")
        if run("prove", "copper", 1800):
            raise PlayFail("copper prove failed")
        must("say", f"Copper smelter has steel furnaces now: {float(made):.0f} copper plates in the last minute.")
        print("COPPER STEEL PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
