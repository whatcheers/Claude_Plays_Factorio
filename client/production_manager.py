"""[Production Manager] (front office, the player's idea): every 10 minutes,
read the production statistics and machine states, find the bottleneck, and
post one short report with a suggestion. Repeats a suggestion at most every
30 minutes. Run it in the background (log /tmp/production_manager.log)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402

PERIOD = 600
REPEAT = 1800
ITEMS = ["iron-plate", "copper-plate", "steel-plate", "iron-gear-wheel", "electronic-circuit",
         "automation-science-pack", "logistic-science-pack"]

STATS_LUA = r"""
local s = game.forces.player.get_item_production_statistics(game.surfaces[1])
local out = {}
for _, n in ipairs({%s}) do
  local made = s.get_flow_count{name=n, category='input', precision_index=defines.flow_precision_index.ten_minutes, count=true} / 10
  local used = s.get_flow_count{name=n, category='output', precision_index=defines.flow_precision_index.ten_minutes, count=true} / 10
  out[#out+1] = n .. '=' .. string.format('%%.1f', made) .. '/' .. string.format('%%.1f', used)
end
local names = {} for k, v in pairs(defines.entity_status) do names[v] = k end
local labs = {}
for _, e in pairs(game.surfaces[1].find_entities_filtered{type='lab'}) do
  local k = names[e.status] or '?' labs[k] = (labs[k] or 0) + 1
  if e.status == defines.entity_status.missing_science_packs then
    local inv = e.get_inventory(defines.inventory.lab_input)
    for _, p in ipairs({'automation-science-pack', 'logistic-science-pack'}) do
      if inv.get_item_count(p) == 0 then labs['lacks:' .. p] = (labs['lacks:' .. p] or 0) + 1 end
    end
  end
end
for k, v in pairs(labs) do out[#out+1] = 'lab:' .. k .. '=' .. v end
local starved = {}
for _, e in pairs(game.surfaces[1].find_entities_filtered{type='assembling-machine'}) do
  if e.status == defines.entity_status.item_ingredient_shortage and e.get_recipe() then
    local r = e.get_recipe().name starved[r] = (starved[r] or 0) + 1
  end
end
for k, v in pairs(starved) do out[#out+1] = 'starved:' .. k .. '=' .. v end
local used, cap = 0, 0
for _, e in pairs(game.surfaces[1].find_entities_filtered{type='generator'}) do
  used = used + e.energy_generated_last_tick * 60 cap = cap + e.prototype.get_max_energy_production() * 60 end
out[#out+1] = string.format('power=%%.2f/%%.2f', used / 1e6, cap / 1e6)
local f = game.forces.player
out[#out+1] = 'research=' .. (f.current_research and f.current_research.name or 'none') .. ':' .. string.format('%%.0f', 100 * (f.research_progress or 0))
rcon.print(table.concat(out, ';'))
"""


def read(b):
    raw = b.lua(STATS_LUA % ",".join(f"'{i}'" for i in ITEMS)).strip()
    made, labs, starved, extra = {}, {}, {}, {}
    for part in raw.split(";"):
        k, _, v = part.partition("=")
        if k.startswith("lab:"):
            labs[k[4:]] = int(v)
        elif k.startswith("starved:"):
            starved[k[8:]] = int(v)
        elif k in ("power", "research"):
            extra[k] = v
        else:
            m, u = v.split("/")
            made[k] = (float(m), float(u))
    return made, labs, starved, extra


def advise(made, labs, starved, extra):
    """One headline number line plus the single most useful suggestion."""
    red = made.get("automation-science-pack", (0, 0))[0]
    green = made.get("logistic-science-pack", (0, 0))[0]
    iron = made.get("iron-plate", (0, 0))[0]
    copper = made.get("copper-plate", (0, 0))[0]
    used, cap = (float(x) for x in extra.get("power", "0/0").split("/"))
    head = f"last 10 min: {red:.0f} red and {green:.0f} green flasks/min, {iron:.0f} iron and {copper:.0f} copper plates/min"
    missing = labs.get("missing_science_packs", 0)
    working = labs.get("working", 0)
    if cap and used > 0.85 * cap:
        tip = f"the power plant is at {used:.1f} of {cap:.1f} MW; build more boilers and steam engines before anything else"
    elif "logistic-science-pack" in starved or any(r in starved for r in ("inserter", "transport-belt", "electronic-circuit")):
        parts = ", ".join(r.replace("-", " ") for r in starved)
        tip = f"green science is starved ({parts} short of inputs); check its iron and copper supply"
    elif missing:
        no_green = labs.get("lacks:logistic-science-pack", 0)
        no_red = labs.get("lacks:automation-science-pack", 0)
        if no_green >= no_red:
            tip = (f"{no_green} lab(s) sit idle without green flasks; more green assemblers, and a way to get "
                   "green to those labs, would put them to work (more red would not help)")
        else:
            tip = f"{no_red} lab(s) sit idle without red flasks; more red assemblers would put them to work"
    elif working and red and green:
        tip = "every lab is busy; more labs would speed research up"
    elif iron < 60:
        tip = "iron is thin; another electric smelting column would help"
    else:
        tip = "production looks balanced"
    return head, tip


def main():
    last_tip, last_time = None, 0.0
    print("[Production Manager] in the office", flush=True)
    while True:
        try:
            with Bridge() as b:
                head, tip = advise(*read(b))
                now = time.time()
                if tip != last_tip or now - last_time >= REPEAT:
                    msg = f"[Production Manager] {head}. Suggestion: {tip}."
                    print(msg, flush=True)
                    b.call("say", {"text": msg}, check=False)
                    last_tip, last_time = tip, now
        except Exception as e:  # game reloading etc.
            print(f"[Production Manager] couldn't read the books: {e}", flush=True)
        time.sleep(PERIOD)


if __name__ == "__main__":
    main()
