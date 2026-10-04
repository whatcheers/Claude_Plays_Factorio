"""Phase-2 spike: footprints/fluidboxes of power entities, pole reach, ghost
recipes, research API. Ghosts only, removed at the end."""
import sys

from bridge import Bridge

PROBE = r"""
local out = {}
local function p(s) out[#out+1] = s end
local s = game.surfaces[1]
local force = game.forces.player
local st = helpers.json_to_table(remote.call("claude", "status", "{}"))
local c = {position = {x = st.character[1], y = st.character[2]}}
local SX, SY = math.floor(c.position.x) + 30, math.floor(c.position.y) - 30
local made = {}
local function f2(v) return string.format("(%.2f,%.2f)", v.x, v.y) end

for _, name in ipairs({"offshore-pump", "boiler", "steam-engine", "pipe", "lab", "assembling-machine-1", "small-electric-pole", "inserter"}) do
  local proto = prototypes.entity[name]
  local extra = ""
  pcall(function() extra = extra .. " wire=" .. tostring(proto.get_max_wire_distance()) end)
  pcall(function() extra = extra .. " supply=" .. tostring(proto.get_supply_area_distance()) end)
  pcall(function() if proto.electric_energy_source_prototype then extra = extra .. " electric" end end)
  p(name .. " tile " .. proto.tile_width .. "x" .. proto.tile_height .. extra)
  for i, fb in ipairs(proto.fluidbox_prototypes or {}) do
    local conns = {}
    for _, pc in ipairs(fb.pipe_connections or {}) do
      local pos = pc.positions and pc.positions[1] or pc.position
      conns[#conns+1] = string.format("[%s dir=%s pos=%s]", tostring(pc.connection_type), tostring(pc.direction), pos and f2(pos) or "?")
    end
    p("  fluidbox " .. i .. " " .. tostring(fb.production_type) .. " filter=" .. tostring(fb.filter and fb.filter.name) .. " " .. table.concat(conns, " "))
  end
end

-- footprints by direction for non-square entities (ghosts in open space)
local x = SX
for _, name in ipairs({"boiler", "steam-engine", "offshore-pump"}) do
  for _, d in ipairs({"north", "east", "south", "west"}) do
    local g = s.create_entity{name="entity-ghost", inner_name=name, position={x, SY}, direction=defines.direction[d], force=force}
    if g then
      made[#made+1] = g
      local b = g.bounding_box
      p(string.format("%s %s at (%d,%d) -> pos %s bbox %s..%s", name, d, x, SY, f2(g.position), f2(b.left_top), f2(b.right_bottom)))
      local ok, fbs = pcall(function() return g.ghost_prototype.fluidbox_prototypes end)
    else
      p(name .. " " .. d .. " ghost FAILED")
    end
    x = x + 8
  end
end

-- ghost assembler with a recipe
local a = s.create_entity{name="entity-ghost", inner_name="assembling-machine-1", position={SX + 0.5, SY + 10.5}, force=force, recipe="iron-gear-wheel"}
if a then
  made[#made+1] = a
  local ok, r = pcall(function() local rr = a.get_recipe() return rr and rr.name end)
  p("ghost assembler recipe via create_entity: " .. tostring(ok) .. " " .. tostring(r))
end

-- research API
local t = force.technologies["automation"]
p("automation enabled=" .. tostring(t.enabled) .. " researched=" .. tostring(t.researched) .. " unit_count=" .. tostring(t.research_unit_count) .. " energy=" .. tostring(t.research_unit_energy))
for _, ing in ipairs(t.research_unit_ingredients) do p("  ingredient " .. ing.name .. " x" .. ing.amount) end
p("recipes enabled: assembling-machine-1=" .. tostring(force.recipes["assembling-machine-1"].enabled) ..
  " inserter=" .. tostring(force.recipes["inserter"].enabled) .. " lab=" .. tostring(force.recipes["lab"].enabled) ..
  " boiler=" .. tostring(force.recipes["boiler"].enabled) .. " steam-engine=" .. tostring(force.recipes["steam-engine"].enabled) ..
  " offshore-pump=" .. tostring(force.recipes["offshore-pump"].enabled) .. " small-electric-pole=" .. tostring(force.recipes["small-electric-pole"].enabled) ..
  " electronic-circuit=" .. tostring(force.recipes["electronic-circuit"].enabled) .. " automation-science-pack=" .. tostring(force.recipes["automation-science-pack"].enabled))
p("current research=" .. tostring(force.current_research and force.current_research.name))

-- nearest water
local w = s.find_tiles_filtered{position=c.position, radius=200, collision_mask="water_tile", limit=1}
p("water near character: " .. (w[1] and f2(w[1].position) or "none within 200"))

storage.claude_spike2 = made
rcon.print(table.concat(out, "\n"))
"""

CLEANUP = r"""
for _, e in pairs(storage.claude_spike2 or {}) do if e.valid then e.destroy() end end
storage.claude_spike2 = nil
rcon.print("cleaned")
"""

if __name__ == "__main__":
    with Bridge() as b:
        print(b.lua(CLEANUP if "--cleanup" in sys.argv else PROBE))
