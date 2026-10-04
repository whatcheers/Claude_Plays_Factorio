"""More labs with green: labs 4 and 5 chained off lab 1 (lab -> inserter -> lab
passes both science packs). Resumable."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402
from green_run import asm, place  # noqa: E402
from play import ChatInterrupt, PlayFail, must, run  # noqa: E402


def layout():
    g = {}
    for dx in range(3):
        for dy in range(3):
            g[(-64 + dx, 22 + dy)] = "L."   # lab 4
            g[(-60 + dx, 24 + dy)] = "L."   # lab 5 (one row down: the player's pole at -58,22)
    g[(-65, 23)] = "I>"   # lab 1 -> lab 4
    g[(-61, 24)] = "I>"   # lab 4 -> lab 5
    g[(-61, 22)] = "p."
    return g


def main():
    with Bridge() as b:
        must("spawn")
        place(b, "labs45", layout(), walk=(-62, 27))
        b.run_ticks(1800)
        if run("prove", "labs45", 1800):
            raise PlayFail("labs45 prove failed")
        must("say", "Labs 4 and 5 are researching with red + green, fed from lab 1.")
        print("LABS PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
