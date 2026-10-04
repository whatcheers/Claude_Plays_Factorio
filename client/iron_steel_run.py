"""Steel furnaces on the electric iron columns: each column's drill digs
30 ore/min but a stone furnace smelts ~19. Upgrades as many as the steel and
bricks on hand allow, iron-chest smelter (elec-iron) first. Resumable."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402
from play import ChatInterrupt, PlayFail, inv, must, run  # noqa: E402

# furnace top-left tiles: elec-iron (feeds the iron chest), its extension, then elec-iron2 (green block 1)
FURNACES = [(-84, 45), (-81, 45), (-78, 45), (-75, 45), (-72, 45), (-69, 45),
            (-75, 52), (-72, 52), (-69, 52)]
TAGS = {(-72, 45): "elec-iron-ext", (-69, 45): "elec-iron-ext"}


def furnace_name(b, x, y):
    s = b.call("scan", {"area": [x, y, x, y]})
    return next((e["name"] for e in s["entities"] if e["type"] == "furnace"), None)


def main():
    with Bridge() as b:
        must("spawn")
        todo = [f for f in FURNACES if furnace_name(b, *f) == "stone-furnace"]
        can = min(len(todo), inv(b).get("steel-furnace", 0) + min(inv(b).get("steel-plate", 0) // 6,
                                                                   inv(b).get("stone-brick", 0) // 10))
        if not can:
            print(f"nothing affordable ({len(todo)} left)")
            return
        todo = todo[:can]
        short = can - inv(b).get("steel-furnace", 0)
        if short > 0:
            must("craft", "steel-furnace", short)
        for x, y in todo:
            must("walk", x + 1, y + 3, "--radius", 2)
            must("upgrade", x, y, "steel-furnace")
        b.run_ticks(2400)
        tags = sorted({TAGS.get(f, "elec-iron" if f[1] == 45 else "elec-iron2") for f in todo})
        for t in tags:
            if run("prove", t, 1800):
                raise PlayFail(f"{t} prove failed")
        left = len([f for f in FURNACES if furnace_name(b, *f) == "stone-furnace"])
        must("say", f"{can} iron furnaces upgraded to steel. {left} still to go.")
        print("IRON STEEL PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
