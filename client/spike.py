"""Step 0 spike: read grid/direction/inserter conventions back from the engine.

Places ghosts only, in a scratch area, and removes them afterwards.
Usage: FACTORIO_RCON_PASSWORD=... python client/spike.py [scratch_x scratch_y]
"""
import sys

from rcon import Rcon

SX, SY = (int(a) for a in sys.argv[1:3]) if len(sys.argv) >= 3 else (40, 40)

PROBE = r"""
local SX, SY = %d, %d
local s = game.surfaces[1]
local force = game.forces.player
local out = {}
local function p(...) local t = {} for i, v in ipairs({...}) do t[#t+1] = tostring(v) end out[#out+1] = table.concat(t, " ") end
local function pos(v) return v and string.format("(%%.2f,%%.2f)", v.x, v.y) or "nil" end

p("version", script.active_mods.base, "tick", game.tick, "paused", game.tick_paused)
p("players", #game.connected_players)
for name, v in pairs(defines.direction) do p("dir", name, v) end

-- clear scratch area of old probe ghosts
for _, e in pairs(s.find_entities_filtered{area={{SX-2,SY-2},{SX+20,SY+12}}, name="entity-ghost"}) do e.destroy() end

local made = {}
local function ghost(inner, x, y, dir, extra)
  local spec = {name="entity-ghost", inner_name=inner, position={x,y}, direction=dir, force=force}
  if extra then for k, v in pairs(extra) do spec[k] = v end end
  local g = s.create_entity(spec)
  made[#made+1] = g
  return g
end

-- 1x1 placement: ask for exact tile corner and centre, see where it lands
local b1 = ghost("transport-belt", SX, SY, defines.direction.east)
p("belt asked", SX, SY, "-> pos", b1 and pos(b1.position), "dir", b1 and b1.direction)
local b2 = ghost("transport-belt", SX+2.5, SY+0.5, defines.direction.east)
p("belt asked", SX+2.5, SY+0.5, "-> pos", b2 and pos(b2.position))

-- 2x2 (stone furnace) and 3x3 (assembler)
local f = ghost("stone-furnace", SX+5, SY+5)
p("furnace asked", SX+5, SY+5, "-> pos", f and pos(f.position), "bbox", f and pos(f.bounding_box.left_top), f and pos(f.bounding_box.right_bottom))
local a = ghost("assembling-machine-1", SX+10.5, SY+5.5)
p("assembler asked", SX+10.5, SY+5.5, "-> pos", a and pos(a.position), "bbox", a and pos(a.bounding_box.left_top), a and pos(a.bounding_box.right_bottom))

-- inserters: each direction, report pickup/drop relative to centre
for _, d in ipairs({"north", "east", "south", "west"}) do
  local x = SX + ({north=0, east=3, south=6, west=9})[d] + 0.5
  local g = ghost("burner-inserter", x, SY+9.5, defines.direction[d])
  if g then
    local c, pk, dr = g.position, g.pickup_position, g.drop_position
    p("inserter dir", d, "pickup d", pos({x=pk.x-c.x, y=pk.y-c.y}), "drop d", pos({x=dr.x-c.x, y=dr.y-c.y}))
  else
    p("inserter dir", d, "FAILED")
  end
end

-- underground belt pair and splitter
local ui = ghost("underground-belt", SX+14.5, SY+0.5, defines.direction.east, {type="input"})
local uo = ghost("underground-belt", SX+17.5, SY+0.5, defines.direction.east, {type="output"})
p("ug in", ui and pos(ui.position), ui and ui.ghost_type, ui and ui.belt_to_ground_type)
p("ug out", uo and pos(uo.position), uo and uo.belt_to_ground_type)
local sp = ghost("splitter", SX+15, SY+5, defines.direction.east)
p("splitter east asked", SX+15, SY+5, "-> pos", sp and pos(sp.position), "bbox", sp and pos(sp.bounding_box.left_top), sp and pos(sp.bounding_box.right_bottom))

-- screenshot while (possibly) paused
local was_paused = game.tick_paused
game.tick_paused = true
game.take_screenshot{surface=s, position={SX+9, SY+5}, resolution={1024, 768}, zoom=1, path="claude/spike.png", show_entity_info=true, force_render=true}
p("screenshot requested while paused; restore paused=", was_paused)
game.tick_paused = was_paused

storage.claude_spike = made
rcon.print(table.concat(out, "\n"))
"""

CLEANUP = r"""
for _, e in pairs(storage.claude_spike or {}) do if e.valid then e.destroy() end end
storage.claude_spike = nil
rcon.print("cleaned")
"""

if __name__ == "__main__":
    with Rcon() as r:
        if "--cleanup" in sys.argv:
            print(r.lua(CLEANUP))
        else:
            print(r.lua(PROBE % (SX, SY)))
