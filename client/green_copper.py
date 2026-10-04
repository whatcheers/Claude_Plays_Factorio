"""Fix for the green block's copper feed. Copper sideloaded into belt M at
x=-63, but M flows west and the cable assembler picks up at x=-59, upstream of
that, so it never saw copper. Copper now runs east along row 20 to x=-57 and
down into M's corner (-57,30) from the north: iron enters that corner from the
south, so each keeps its own lane, upstream of every consumer. Resumable.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fx  # noqa: E402
from bridge import Bridge  # noqa: E402
from green_run import place  # noqa: E402
from play import ChatInterrupt, PlayFail, must, run  # noqa: E402

OLD = [(-63, y) for y in range(20, 28)] + [(-63, 29)]


def layout():
    g = {}
    for x in range(-63, -57):
        g[(x, 20)] = "b>"
    g[(-57, 20)] = "bv"
    for y in range(21, 27):
        g[(-57, y)] = "bv"
    g[(-57, 27)] = "uv"
    g[(-57, 29)] = "Wv"        # into M's corner from the north: copper on the north lane
    return g


def main():
    with Bridge() as b:
        retired = set(fx.load_state()["tags"]["green"].get("retired") or [])
        codes = fx.load_state()["tags"]["green"]["codes"]
        left = [(x, y) for x, y in OLD if next(i + 1 for i, c in enumerate(codes) if (c[0], c[1]) == (x, y)) not in retired]
        for x, y in left:
            must("walk", x + 0.5, y + 0.5, "--radius", 3)
            must("retire", "green", x, y)
        place(b, "green-cu", layout(), walk=(-60, 24))
        b.run_ticks(3600)
        code = run("prove", "green", 3600)
        if code:
            raise PlayFail("green prove failed")
        print("GREEN COPPER PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
