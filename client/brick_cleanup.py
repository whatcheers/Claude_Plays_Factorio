"""Stop stone bricks reaching the green block: retire elec-iron2's west unit
(its drill reaches stone), then walk the iron belts picking bricks off by hand
(only belts within Claude's reach, like a player would)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fx  # noqa: E402
from bridge import Bridge  # noqa: E402
from play import ChatInterrupt, PlayFail, must, run  # noqa: E402

WEST_UNIT = [(-79, 54), (-78, 52), (-78, 51), (-77, 51)]   # drill, furnace, long inserter, inserter
STOPS = [(-76, 49), (-68, 48), (-60, 48), (-58, 42), (-58, 35), (-62, 29), (-70, 29),
         (-74, 33), (-74, 38), (-68, 41), (-62, 41)]

PICK_LUA = r"""
local c
for _, e in pairs(game.surfaces[1].find_entities_filtered{name='character'}) do if not e.player then c = e end end
local n = 0
for _, b in pairs(game.surfaces[1].find_entities_filtered{area={{-81, 28}, {-55, 52}}, type={'transport-belt', 'underground-belt'}}) do
  if c.can_reach_entity(b) then
    for i = 1, 2 do
      local line = b.get_transport_line(i)
      local k = line.get_item_count('stone-brick')
      if k > 0 then
        local got = c.insert{name='stone-brick', count=k}
        if got > 0 then line.remove_item{name='stone-brick', count=got} n = n + got end
      end
    end
  end
end
for _, f in pairs(game.surfaces[1].find_entities_filtered{area={{-79, 52}, {-77, 54}}, type='furnace'}) do
  if c.can_reach_entity(f) then
    for _, inv in pairs({f.get_output_inventory(), f.get_inventory(defines.inventory.furnace_source)}) do
      for _, it in pairs(inv.get_contents()) do
        if it.name == 'stone-brick' or it.name == 'stone' then
          local got = c.insert{name=it.name, count=it.count}
          if got > 0 then inv.remove{name=it.name, count=got} n = n + got end
        end
      end
    end
  end
end
rcon.print(n)
"""


def main():
    with Bridge() as b:
        must("spawn")
        retired = set(fx.load_state()["tags"]["elec-iron2"].get("retired") or [])
        codes = fx.load_state()["tags"]["elec-iron2"]["codes"]
        for x, y in WEST_UNIT:
            idx = next(i + 1 for i, c in enumerate(codes) if (c[0], c[1]) == (x, y))
            if idx in retired:
                continue
            must("walk", x + 1, y - 1 if y >= 54 else y + 1, "--radius", 3)
            # pick the unit's stray bricks/stone out first, then take it down
            print("picked", b.lua(PICK_LUA).strip())
            must("retire", "elec-iron2", x, y)
        total = 0
        for _ in range(2):
            for x, y in STOPS:
                must("walk", x, y, "--radius", 2)
                total += int(b.lua(PICK_LUA).strip() or 0)
        print(f"picked {total} bricks off the belts")
        b.run_ticks(1800)
        if run("prove", "green", 3600):
            raise PlayFail("green prove failed")
        print("BRICK CLEANUP PASS")


if __name__ == "__main__":
    try:
        main()
    except ChatInterrupt as e:
        print(f"INTERRUPTED: {e}")
        sys.exit(3)
    except PlayFail as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
