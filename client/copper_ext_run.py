"""Copper expansion (PM: copper at its limit): two electric copper columns west
of the red line's copper belt. Coal: an inserter takes it off the player's coal
belt (row 28) at x=-92 (west of the red iron belt) up x=-92 and east along
row 19. Plates go east on row 18 and sideload the red copper belt's column
(x=-78) from the west, onto the copper lane (gears ride the other lane only
after row 20). Resumable."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402
from green_run import place  # noqa: E402
from play import ChatInterrupt, PlayFail, must, run  # noqa: E402

UNITS = [-88, -85]


def layout():
    g = {}
    for X in UNITS:
        for dx in range(3):
            for dy in range(3):
                g[(X + dx, 12 + dy)] = "Mv"
        for dx in (1, 2):
            for dy in (15, 16):
                g[(X + dx, dy)] = "F."
        g[(X, 16)] = "p."
        g[(X + 1, 17)] = "J^"   # coal belt (row 19) -> furnace (row 15)
        g[(X + 2, 17)] = "Iv"   # furnace (row 16) -> plate belt (row 18)
    # plates: east on row 18, sideloading the red copper belt (x=-78) from the west
    for x in range(-87, -79):
        g[(x, 18)] = "b>"
    g[(-79, 18)] = "s>"
    # coal: off the player's coal belt at (-92,28), up x=-92, east on row 19
    g[(-92, 27)] = "I^"
    for y in range(20, 27):
        g[(-92, y)] = "b^"
    g[(-92, 19)] = "b>"
    for x in range(-91, -84):
        g[(x, 19)] = "b>"
    g[(-84, 19)] = "e>"
    g[(-81, 16)] = "p."         # links the units to the red line's pole (-77,16)
    return g


def main():
    with Bridge() as b:
        must("spawn")
        place(b, "copper-ext", layout(), walk=(-86, 22))
        b.run_ticks(3600)
        if run("prove", "copper-ext", 3600):
            raise PlayFail("copper-ext prove failed")
        must("say", "Copper expansion is running: 2 more copper columns feeding the red line's copper belt.")
        print("COPPER EXT PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
