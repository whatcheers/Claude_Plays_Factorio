"""Green Block 2 (the huddle's play): the proven green block, mirrored by
(-37, -16) into the free land west of the copper field, fed straight from the
full iron and copper chests. Its flasks go into lab B; an inserter passes them
on to lab A, so the two idle red-only labs get green. Resumable."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402
from green_run import KEYS, layout_green, layout_iron2, place  # noqa: E402
from play import ChatInterrupt, PlayFail, must, run  # noqa: E402

DX, DY = -37, -16
TAG = "green2"


def layout():
    g = {}
    # the block itself: green block 1 from row 30 down (belt M, its loop, assemblers, inserters)
    src = {k: v for k, v in layout_iron2().items() if k[1] == 30}          # belt M and its corner
    src.update({k: v for k, v in layout_green().items() if k[1] >= 30})   # loop, assemblers, inserters
    for (x, y), v in src.items():
        g[(x + DX, y + DY)] = v
    g[(-72 + DX, 30 + DY)] = "b<"   # in block 1 this was belt M's end; here it feeds the loop
    # green flasks: north from the block (underground under belt M2), east on row 4, down into lab B
    g[(-104, 11)] = "U^"
    for y in range(5, 11):
        g[(-104, y)] = "b^"
    g[(-104, 4)] = "b>"
    for x in range(-103, -71):
        g[(x, 4)] = "b>"
    g[(-71, 4)] = "bv"
    for y in range(5, 10):
        g[(-71, y)] = "bv"
    g[(-71, 10)] = "ev"
    g[(-71, 11)] = "Iv"        # green -> lab B (-72..-70, 12..14)
    g[(-73, 12)] = "I<"        # lab B -> lab A (passes red and green)
    # copper: copper chest north side -> row 5 west -> down x=-94 into M2's corner from the north
    g[(-78, 9)] = "I^"
    for y in (6, 7, 8):
        g[(-78, y)] = "b^"
    g[(-78, 5)] = "b<"
    for x in range(-93, -78):
        g[(x, 5)] = "b<"
    g[(-94, 5)] = "bv"
    for y in range(6, 13):
        g[(-94, y)] = "bv"
    g[(-94, 13)] = "sv"        # sideloads M2's corner (-94,14): copper on the north lane
    # iron: iron chest west side -> up x=-94, under the player's coal belt (row 28), into the corner from the south
    g[(-92, 41)] = "I<"
    g[(-93, 41)] = "b<"
    g[(-94, 41)] = "b^"
    for y in range(30, 41):
        g[(-94, y)] = "b^"
    g[(-94, 29)] = "u^"
    g[(-94, 27)] = "U^"
    for y in range(15, 27):
        g[(-94, y)] = "b^"
    return g


def main():
    with Bridge() as b:
        must("spawn")
        place(b, TAG, layout(), KEYS, walk=(-100, 26))
        b.run_ticks(3600)
        if run("prove", TAG, 3600):
            raise PlayFail("green2 prove failed")
        must("say", "Green Block 2 is running: double green, and labs A and B finally get green.")
        print("GREEN2 PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
