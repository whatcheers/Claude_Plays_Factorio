"""Stopgap until a coal line exists: hand-mine coal and top up the boiler's coal chest."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402
from play import ChatInterrupt, PlayFail, gather, inv, must  # noqa: E402

BOILER_CHEST = (45.5, 35.5)


def main(n=150):
    with Bridge() as b:
        gather(b, "coal", n)
        must("walk", BOILER_CHEST[0], BOILER_CHEST[1] + 2, "--radius", 1.5)
        must("put", BOILER_CHEST[0], BOILER_CHEST[1], "coal", inv(b).get("coal", 0))
        print("COAL FERRY DONE")


if __name__ == "__main__":
    try:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else 150)
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
