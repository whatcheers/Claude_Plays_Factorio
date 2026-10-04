"""elec-iron2's west drill (-79,54) reaches a few stone tiles, so its furnace
also makes stone bricks; they ride the iron lane to the end of the green
block's row-40 belt and block iron there. A filtered inserter at the end
(-59,41) moves bricks into a chest (-59,42). Resumable."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402
from green_run import place  # noqa: E402
from play import ChatInterrupt, PlayFail, inv, must, run  # noqa: E402

FILTER_LUA = ("local e = game.surfaces[1].find_entities_filtered{name='inserter', position={-58.5, 41.5}}[1]"
              " if e then e.use_filters = true e.set_filter(1, 'stone-brick') rcon.print(e.get_filter(1).name)"
              " else rcon.print('none') end")


def main():
    with Bridge() as b:
        must("spawn")
        if inv(b).get("wooden-chest", 0) < 1:
            must("craft", "wooden-chest", 1)
        place(b, "brick-sink", {(-59, 41): "Iv", (-59, 42): "c."}, walk=(-57, 43))
        out = b.lua(FILTER_LUA).strip()
        print("brick filter:", out)
        if out != "stone-brick":
            raise PlayFail("could not set the brick filter")
        b.run_ticks(1800)
        if run("prove", "green", 3600):
            raise PlayFail("green prove failed")
        print("BRICK SINK PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
