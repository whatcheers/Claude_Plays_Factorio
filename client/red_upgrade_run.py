"""Red choke point: the three red assemblers are working flat out (assembler 1,
10 s/flask). Upgrade them to assembler 2 and make both iron-chest outputs fast
inserters (red needs ~54 iron/min at 27 flasks/min; a basic inserter moves ~50).
Each assembler 2 is crafted from the assembler 1 it replaces. Resumable."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402
from play import ChatInterrupt, PlayFail, inv, must, run  # noqa: E402
from scale_run import top_up  # noqa: E402
from science_run import COPPER_CHEST, IRON_CHEST  # noqa: E402

RED = [(-72, 22), (-76, 16), (-72, 16)]          # red flask assemblers (top-left tiles)
FAST = [(-91, 40), (-92, 41)]                    # iron chest -> red line, iron chest -> Green Block 2


def name_at(b, x, y, typ):
    s = b.call("scan", {"area": [x, y, x, y]})
    return next((e["name"] for e in s["entities"] if e["type"] == typ), None)


def circuits(b, n):
    have = inv(b).get("electronic-circuit", 0)
    if have < n:
        top_up(b, *COPPER_CHEST, "copper-plate", 2 * (n - have))
        must("craft", "copper-cable", (3 * (n - have) + 1) // 2)
        must("craft", "electronic-circuit", n - have)


def main():
    with Bridge() as b:
        must("spawn")
        todo = [t for t in RED if name_at(b, *t, "assembling-machine") == "assembling-machine-1"]
        fast = [t for t in FAST if name_at(b, *t, "inserter") == "inserter"]
        if len(todo) * 2 > inv(b).get("steel-plate", 0):
            raise PlayFail(f"need {2 * len(todo)} steel for {len(todo)} assemblers")
        top_up(b, *IRON_CHEST, "iron-plate", 20 * len(todo) + 6 * len(fast) + 20)
        for t in todo:
            if inv(b).get("assembling-machine-2", 0) < 1:
                if inv(b).get("assembling-machine-1", 0) < 1:
                    circuits(b, 3)
                    must("craft", "iron-gear-wheel", 5)
                    must("craft", "assembling-machine-1", 1)
                circuits(b, 3)
                must("craft", "iron-gear-wheel", 5)
                must("craft", "assembling-machine-2", 1)
            must("walk", t[0] + 1.5, t[1] + 4.5 if t[1] == 22 else t[1] - 1.5, "--radius", 2)
            must("upgrade", t[0], t[1], "assembling-machine-2")
        for t in fast:
            if inv(b).get("fast-inserter", 0) < 1:
                circuits(b, 2)
                if inv(b).get("inserter", 0) < 1:
                    circuits(b, 1)
                    must("craft", "iron-gear-wheel", 1)
                    must("craft", "inserter", 1)
                must("craft", "fast-inserter", 1)
            must("walk", t[0] + 0.5, t[1] + 2.5, "--radius", 2)
            must("upgrade", t[0], t[1], "fast-inserter")
        b.run_ticks(3600)
        if run("prove", "science", 1800):
            raise PlayFail("red line prove failed")
        must("say", "Red line upgraded: 3 assembler 2s (about 27 red/min max) and fast inserters on the iron chest outputs.")
        print("RED UPGRADE PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
