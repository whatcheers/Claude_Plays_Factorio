"""Craft a lab (unlocks the red-flask recipe) and then 10 red flasks by hand.

Plates come from the smelter chests; waits for copper if the line is still filling.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402
from play import PlayFail, inv, must, withdraw  # noqa: E402

IRON_CHEST = (-90.5, 41.5)
COPPER_CHEST = (-77.5, 10.5)


def top_up(b, chest, item, want, wait_s=180):
    deadline = time.time() + wait_s
    while inv(b).get(item, 0) < want:
        withdraw(b, *chest, item, want - inv(b).get(item, 0))
        if inv(b).get(item, 0) >= want:
            break
        if time.time() > deadline:
            raise PlayFail(f"{item}: chest at {chest} didn't fill in time")
        b.run_ticks(600)


def main():
    with Bridge() as b:
        top_up(b, IRON_CHEST, "iron-plate", 56)
        top_up(b, COPPER_CHEST, "copper-plate", 25)
        must("craft", "copper-cable", 15)        # 30 cable
        must("craft", "electronic-circuit", 10)
        must("craft", "iron-gear-wheel", 22)     # 10 lab + 2 belts + 10 flasks
        must("craft", "transport-belt", 2)       # 4 belts
        must("craft", "lab", 1)
        must("say", "Lab crafted - the red flask recipe should be unlocked now. Hand-crafting the first 10 flasks.")
        must("craft", "automation-science-pack", 10)
        print("LAB + 10 FLASKS READY", inv(b))


if __name__ == "__main__":
    try:
        main()
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
