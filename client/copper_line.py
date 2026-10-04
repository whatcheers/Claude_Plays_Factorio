"""Build the burner smelter stamp on copper ore. The first copper plate unlocks Electronics."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402
from play import PlayFail, gather, gather_wood, inv, must, place_on_ore, withdraw  # noqa: E402

TAG = "copper"
IRON_CHEST = (-90.5, 41.5)


def main():
    with Bridge() as b:
        must("spawn")
        need_plates = 24 - inv(b).get("iron-plate", 0)
        if need_plates > 0:
            got = withdraw(b, *IRON_CHEST, "iron-plate", need_plates)
            if got < need_plates:
                raise PlayFail(f"iron chest only had {got} plates")
        furnaces_needed = 4 - inv(b).get("stone-furnace", 0)
        if furnaces_needed > 0:
            gather(b, "stone", 5 * furnaces_needed)
            must("craft", "stone-furnace", furnaces_needed)
        gather_wood(b, 2)
        must("craft", "iron-gear-wheel", 8)
        must("craft", "burner-mining-drill", 2)
        must("craft", "burner-inserter", 2)
        must("craft", "wooden-chest", 1)
        gather(b, "coal", 14)

        X, Y = place_on_ore(b, "burner-iron", "copper-ore", TAG, near=(-80, 5))
        must("build", TAG)
        gather(b, "copper-ore", 10)
        must("walk", X + 3.5, Y + 5.5, "--radius", 1)
        for cx in (X + 1, X + 6):
            must("put", cx, Y + 1, "coal", 3)
            must("put", cx, Y + 3, "coal", 2)
            must("put", cx, Y + 3, "copper-ore", 5)
        must("put", X + 2.5, Y + 3.5, "coal", 1)
        must("put", X + 4.5, Y + 3.5, "coal", 1)
        if must("prove", TAG, 600) is None:
            print(f"COPPER LINE UP at {X},{Y}")


if __name__ == "__main__":
    try:
        main()
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
