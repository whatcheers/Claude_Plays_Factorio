"""[QA Inspector] (the player's idea): wanders down every 20-40 minutes, makes
one picky, slightly annoying observation drawn from live game data, and leaves.
Run it in the background (log /tmp/qa_inspector.log)."""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402

FACTS_LUA = r"""
local s = game.surfaces[1]
local names = {} for k, v in pairs(defines.entity_status) do names[v] = k end
local out = {}
local idle, total = 0, 0
for _, e in pairs(s.find_entities_filtered{type='assembling-machine'}) do
  total = total + 1
  if e.status ~= defines.entity_status.working then idle = idle + 1 end
end
out[#out+1] = 'asm=' .. idle .. '/' .. total
out[#out+1] = 'belts=' .. s.count_entities_filtered{type='transport-belt'}
out[#out+1] = 'poles=' .. s.count_entities_filtered{type='electric-pole'}
out[#out+1] = 'inserters=' .. s.count_entities_filtered{type='inserter'}
local waiting = 0
for _, e in pairs(s.find_entities_filtered{type='inserter'}) do
  if e.status == defines.entity_status.waiting_for_source_items then waiting = waiting + 1 end
end
out[#out+1] = 'waiting=' .. waiting
local used, cap = 0, 0
for _, e in pairs(s.find_entities_filtered{type='generator'}) do
  used = used + e.energy_generated_last_tick * 60 cap = cap + e.prototype.get_max_energy_production() * 60 end
out[#out+1] = string.format('power=%.2f/%.2f', used / 1e6, cap / 1e6)
local fullest, where = 0, ''
for _, e in pairs(s.find_entities_filtered{type='container'}) do
  local inv = e.get_inventory(defines.inventory.chest)
  local used_slots = #inv - inv.count_empty_stacks()
  if #inv > 0 and used_slots / #inv > fullest then fullest = used_slots / #inv where = math.floor(e.position.x) .. ',' .. math.floor(e.position.y) end
end
out[#out+1] = string.format('chest=%.0f@%s', 100 * fullest, where)
local f = game.forces.player
out[#out+1] = 'research=' .. (f.current_research and f.current_research.name or 'none') .. '@' .. string.format('%.0f', 100 * (f.research_progress or 0))
local c for _, e in pairs(s.find_entities_filtered{name='character'}) do if not e.player then c = e end end
out[#out+1] = 'pockets=' .. (c and (#c.get_main_inventory() - c.get_main_inventory().count_empty_stacks()) or 0)
local labs, idle_labs = 0, 0
for _, e in pairs(s.find_entities_filtered{type='lab'}) do labs = labs + 1 if e.status ~= defines.entity_status.working then idle_labs = idle_labs + 1 end end
out[#out+1] = 'labs=' .. idle_labs .. '/' .. labs
rcon.print(table.concat(out, ';'))
"""


def facts(b):
    return dict(p.split("=", 1) for p in b.lua(FACTS_LUA).strip().split(";"))


def remarks(f):
    idle, total = map(int, f["asm"].split("/"))
    used, cap = map(float, f["power"].split("/"))
    pct, where = f["chest"].split("@")
    tech, prog = f["research"].split("@")
    idle_labs, labs = map(int, f["labs"].split("/"))
    out = [
        f"{idle} of {total} assemblers aren't doing anything right now. I counted. Just noting it.",
        f"There are {f['belts']} belts on this map. I walked all of them. Several are not straight, aesthetically.",
        f"{f['waiting']} inserters are standing around waiting for something to pick up. Union rules, I assume.",
        f"We built a {cap:.1f} MW power plant to use {used:.1f} MW. Ambitious.",
        f"{f['poles']} power poles and not one of them is evenly spaced. Not a safety issue. Yet.",
        f"Claude is carrying {f['pockets']} stacks of stuff around in their pockets. That's a warehouse, not a person.",
        f"Research: {tech.replace('-', ' ')} at {prog}%. I've seen glaciers with better throughput.",
    ]
    if int(pct) >= 90:
        out.append(f"The chest at ({where}) is {pct}% full. "
                   + ("It's full. Everyone walked past it." if int(pct) >= 100 else "When it fills up someone will act surprised."))
    if idle_labs:
        out.append(f"{idle_labs} of {labs} labs {'is' if idle_labs == 1 else 'are'} idle. Scientists on break again.")
    return out


FORMS = [
    "Please file form QA-27B (Observation Acknowledgement) in triplicate.",
    "I'll need a 14-C Deviation Report on my desk by end of shift.",
    "This has been logged on form 9-Yellow. The yellow copy is yours. Don't lose it.",
    "Fill out a Corrective Action Request, form CAR-3. The blue one, not the light blue one.",
    "Initial here, here and here. Form QA-1, page 4 of 11.",
    "Form 220-J (Notice of Noticing) has been filed on your behalf. You're welcome.",
    "Please submit form QA-404 (Missing Form Report) if you can't find the form.",
]


def main():
    down = False  # report an outage once, not every round
    print("[QA Inspector] clipboard in hand", flush=True)
    while True:
        time.sleep(random.randint(20 * 60, 40 * 60))
        try:
            with Bridge() as b:
                msg = "[QA Inspector] " + random.choice(remarks(facts(b))) + " " + random.choice(FORMS)
                print(msg, flush=True)
                b.call("say", {"text": msg}, check=False)
            down = False
        except Exception as e:
            if not down:
                print(f"[QA Inspector] lost my clipboard: {e}", flush=True)
                down = True


if __name__ == "__main__":
    main()
