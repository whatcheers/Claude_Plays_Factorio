"""More iron (the player asked): two more columns on the east end of elec-iron.
Coal comes from the existing row-49 coal belt (already runs to x=-67); plates
join the row-48 plate belt, which now starts further east. Resumable."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402
from green_run import place  # noqa: E402
from play import ChatInterrupt, PlayFail, must, run  # noqa: E402

UNITS = [-73, -70]


def layout():
    g = {}
    for X in UNITS:
        for dx in range(3):
            for dy in range(3):
                g[(X + dx, 42 + dy)] = "Mv"
        for dx in (1, 2):
            for dy in (45, 46):
                g[(X + dx, dy)] = "F."
        g[(X, 46)] = "p."
        g[(X + 1, 47)] = "J^"
        g[(X + 2, 47)] = "Iv"
    for x in range(-73, -67):
        g[(x, 48)] = "b<"
    return g


def main():
    with Bridge() as b:
        must("spawn")
        place(b, "elec-iron-ext", layout(), walk=(-70, 51))
        b.run_ticks(3600)
        if run("prove", "elec-iron-ext", 3600):
            raise PlayFail("elec-iron-ext prove failed")
        print("IRON EXT PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
