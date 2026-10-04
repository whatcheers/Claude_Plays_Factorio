"""Labs 6 and 7, chained east off lab B (-72..-70, 12..14): lab B -> (-69,13) ->
lab 6 (-68..-66) -> (-65,13) -> lab 7 (-64..-62). Resumable."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402
from green_run import place  # noqa: E402
from play import ChatInterrupt, PlayFail, must, run  # noqa: E402


def layout():
    g = {}
    for dx in range(3):
        for dy in range(3):
            g[(-68 + dx, 12 + dy)] = "L."
            g[(-64 + dx, 12 + dy)] = "L."
    g[(-69, 13)] = "I>"
    g[(-65, 13)] = "I>"
    g[(-69, 11)] = "p."
    g[(-65, 11)] = "p."
    return g


def main():
    with Bridge() as b:
        must("spawn")
        place(b, "labs67", layout(), walk=(-66, 9))
        b.run_ticks(1800)
        if run("prove", "labs67", 1800):
            raise PlayFail("labs67 prove failed")
        print("LABS67 PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
