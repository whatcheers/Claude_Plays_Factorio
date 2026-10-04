"""Stone bricks for steel furnaces: hand-mine stone, smelt it in two temporary
stone furnaces, collect the bricks, take the furnaces back down. Resumable."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fx  # noqa: E402
from bridge import Bridge  # noqa: E402
from play import ChatInterrupt, PlayFail, gather, inv, must, run  # noqa: E402
from power_run import tag_state  # noqa: E402

WANT = 90
SPOT = (-84, 58)   # off the ore, next to the stone patch (-85..-75, 56..60)


def main():
    with Bridge() as b:
        must("spawn")
        need = WANT - inv(b).get("stone-brick", 0)
        if need <= 0:
            print("enough bricks")
            return
        if tag_state(b, "brickworks") != "built":
            if inv(b).get("stone-furnace", 0) < 2:
                gather(b, "stone", 5 * (2 - inv(b).get("stone-furnace", 0)))
                must("craft", "stone-furnace", 2 - inv(b).get("stone-furnace", 0))
            from green_run import place
            place(b, "brickworks", {(SPOT[0] + dx, SPOT[1] + dy): "F." for dx in range(4) for dy in range(2)},
                  walk=(SPOT[0] + 2, SPOT[1] + 4))
        gather(b, "stone", 2 * need)
        gather(b, "coal", 6)
        for fx_ in (SPOT[0] + 1, SPOT[0] + 3):
            must("walk", fx_, SPOT[1] + 3, "--radius", 2)
            run("put", fx_, SPOT[1] + 1, "coal", 3)
            must("put", fx_, SPOT[1] + 1, "stone", need)
        b.run_ticks(int(60 * 3.2 * (need / 2 + 1)))
        for fx_ in (SPOT[0] + 1, SPOT[0] + 3):
            must("walk", fx_, SPOT[1] + 3, "--radius", 2)
            run("take", fx_, SPOT[1] + 1, "stone-brick", need)
        for x in (SPOT[0], SPOT[0] + 2):
            must("walk", x + 1, SPOT[1] + 3, "--radius", 2)
            must("retire", "brickworks", x, SPOT[1])
        st = fx.load_state()
        st["tags"].pop("brickworks", None)
        fx.save_state(st)
        print(f"bricks now: {inv(b).get('stone-brick', 0)}")
        print("BRICKS PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
