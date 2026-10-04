-- claude-bridge: thin world access + timed, reach-checked actions for Claude's
-- own character. Every function takes one JSON string and returns one JSON
-- string. Logic (stamps, lint, gating) lives in Python under client/.

local VERSION = script.active_mods["claude-bridge"]

local INVENTORY_TYPES = {
  furnace = true, ["assembling-machine"] = true, container = true, ["logistic-container"] = true,
  ["mining-drill"] = true, lab = true, boiler = true, ["rocket-silo"] = true, ["cargo-wagon"] = true,
}

local STATUS_NAME = {}
for name, v in pairs(defines.entity_status) do STATUS_NAME[v] = name end

local function init()
  storage.tags = storage.tags or {}
  storage.job = storage.job or nil
end
script.on_init(init)
script.on_configuration_changed(init)

-- Trigger techs (craft-item / build-entity / mine-entity) only listen to real
-- players. Claude's character has no LuaPlayer, so credit its own actions here.
local function trigger_target(trig)
  local v = trig.item or trig.entity
  if type(v) == "table" then v = v.name end
  return v
end

local function credit(kind, name, count)
  local ok, err = pcall(function()
    storage.trigger_counts = storage.trigger_counts or {}
    local force = game.forces.player
    for tname, tech in pairs(force.technologies) do
      local trig = tech.prototype.research_trigger
      if trig and trig.type == kind and not tech.researched and tech.enabled and trigger_target(trig) == name then
        local ready = true
        for _, pre in pairs(tech.prerequisites) do if not pre.researched then ready = false end end
        if ready then
          local n = (storage.trigger_counts[tname] or 0) + (count or 1)
          storage.trigger_counts[tname] = n
          if n >= (trig.count or 1) then
            tech.researched = true
            game.print("[color=#7fc8ff][Claude][/color] unlocked " .. tname .. " (" .. kind .. " " .. name .. ")")
          end
        end
      end
    end
  end)
  if not ok then log("claude-bridge credit failed: " .. tostring(err)) end
end

local function char()
  local c = storage.char
  if c and c.valid then return c end
  return nil
end

local function xy(p) return { p.x or p[1], p.y or p[2] } end

local function dist(a, b)
  local dx, dy = a.x - b.x, a.y - b.y
  return math.sqrt(dx * dx + dy * dy)
end

local function bbox_dist(p, box)
  local cx = math.max(box.left_top.x, math.min(p.x, box.right_bottom.x))
  local cy = math.max(box.left_top.y, math.min(p.y, box.right_bottom.y))
  return dist(p, { x = cx, y = cy })
end

local function contents(inv)
  local out = {}
  if not inv then return out end
  for _, it in pairs(inv.get_contents()) do out[it.name] = (out[it.name] or 0) + it.count end
  return out
end

-- ---------------------------------------------------------------- status/spawn
local api = {}

function api.status()
  local c = char()
  return {
    version = VERSION, tick = game.tick, paused = game.tick_paused,
    character = c and xy(c.position) or nil,
    job = storage.job and { kind = storage.job.kind, state = storage.job.state, msg = storage.job.msg } or nil,
  }
end

function api.spawn()
  if char() then return { created = false, character = xy(char().position) } end
  local player = game.connected_players[1]
  if not player then return { error = "no connected player to spawn near" } end
  local surface = player.surface
  local pos = surface.find_non_colliding_position("character", { player.position.x + 3, player.position.y }, 20, 0.5)
  if not pos then return { error = "no free spot near the player" } end
  local c = surface.create_entity { name = "character", position = pos, force = player.force }
  storage.char = c
  -- the one exemption: the same starting kit freeplay gives any new player
  local kit = {}
  if remote.interfaces.freeplay and remote.interfaces.freeplay.get_created_items then
    kit = remote.call("freeplay", "get_created_items") or {}
  end
  for name, count in pairs(kit) do c.insert { name = name, count = count } end
  return { created = true, character = xy(c.position), kit = kit }
end

-- ---------------------------------------------------------------- scan
local function footprint(e)
  local b = e.bounding_box
  local x1, y1 = math.floor(b.left_top.x), math.floor(b.left_top.y)
  return x1, y1, math.max(1, math.ceil(b.right_bottom.x) - x1), math.max(1, math.ceil(b.right_bottom.y) - y1)
end

local function describe(e)
  local ghost = e.type == "entity-ghost"
  local name = ghost and e.ghost_name or e.name
  local typ = ghost and e.ghost_type or e.type
  local proto = ghost and e.ghost_prototype or e.prototype
  local x, y, w, h = footprint(e)
  local d = {
    name = name, type = typ, ghost = ghost, tile = { x, y }, w = w, h = h,
    direction = e.direction, position = xy(e.position), unit = e.unit_number,
    has_inventory = INVENTORY_TYPES[typ] or false, needs_power = false,
  }
  if typ == "inserter" then
    d.pickup = xy(e.pickup_position); d.drop = xy(e.drop_position)
  elseif typ == "mining-drill" then
    local ok, p = pcall(function() return e.drop_position end)
    if ok and p then d.drop = xy(p) end
  elseif typ == "underground-belt" then
    d.belt_type = e.belt_to_ground_type
    pcall(function() d.max_distance = proto.max_underground_distance end)
  elseif typ == "electric-pole" then
    local ok, r = pcall(function() return proto.get_supply_area_distance() end)
    if ok and r then
      local p = e.position
      d.supply = { p.x - r, p.y - r, p.x + r, p.y + r }
    end
  end
  pcall(function() d.needs_power = proto.electric_energy_source_prototype ~= nil end)
  if ghost then
    d.can_place = e.surface.can_place_entity {
      name = name, position = e.position, direction = e.direction, force = e.force,
      build_check_type = defines.build_check_type.manual,
    }
  end
  if typ == "container" and not ghost then d.contents = contents(e.get_inventory(defines.inventory.chest)) end
  return d
end

function api.scan(a)
  local surface = game.surfaces[1]
  local x1, y1, x2, y2 = a.area[1], a.area[2], a.area[3], a.area[4]
  local area = { { x1, y1 }, { x2 + 1, y2 + 1 } }
  local out = { area = a.area, entities = {}, resources = {}, water = {} }
  for _, r in pairs(surface.find_entities_filtered { area = area, type = "resource" }) do
    out.resources[#out.resources + 1] = { name = r.name, tile = { math.floor(r.position.x), math.floor(r.position.y) }, amount = r.amount }
  end
  for _, e in pairs(surface.find_entities_filtered { area = area }) do
    if e.type ~= "resource" then out.entities[#out.entities + 1] = describe(e) end
  end
  local ok, tiles = pcall(function() return surface.find_tiles_filtered { area = area, collision_mask = "water_tile" } end)
  if ok then
    for _, t in pairs(tiles) do out.water[#out.water + 1] = { t.position.x, t.position.y } end
  end
  return out
end

-- ---------------------------------------------------------------- plan
local IGNORE_FOR_PLAN = { tree = true, ["simple-entity"] = true, resource = true, character = true, corpse = true }

function api.plan(a)
  local surface = game.surfaces[1]
  if storage.tags[a.tag] then return { error = "tag " .. a.tag .. " already exists; unplan it first" } end
  for _, it in ipairs(a.items) do
    local area = { { it.tile[1] + 0.05, it.tile[2] + 0.05 }, { it.tile[1] + it.w - 0.05, it.tile[2] + it.h - 0.05 } }
    for _, e in pairs(surface.find_entities_filtered { area = area }) do
      if not IGNORE_FOR_PLAN[e.type] then
        return { error = string.format("tile %d,%d already holds %s%s", it.tile[1], it.tile[2],
          e.type == "entity-ghost" and "a ghost of " or "", e.type == "entity-ghost" and e.ghost_name or e.name) }
      end
    end
  end
  local force = game.forces.player
  local made, placed = {}, {}
  for _, it in ipairs(a.items) do
    local spec = { name = "entity-ghost", inner_name = it.name, position = it.position, direction = it.direction, force = force }
    if it.belt_type then spec.type = it.belt_type end
    if it.recipe then spec.recipe = it.recipe end
    local g = surface.create_entity(spec)
    if not g then
      for _, m in pairs(made) do if m.valid then m.destroy() end end
      return { error = "could not create ghost for " .. it.name .. " at " .. it.tile[1] .. "," .. it.tile[2] }
    end
    made[#made + 1] = g
    local x, y = footprint(g)
    placed[#placed + 1] = { name = it.name, tile = { x, y }, position = xy(g.position), direction = g.direction }
  end
  storage.tags[a.tag] = { ents = made }
  return { tag = a.tag, placed = placed }
end

function api.unplan(a)
  local t = storage.tags[a.tag]
  if not t then return { error = "no such tag " .. a.tag } end
  local n = 0
  for _, e in pairs(t.ents) do
    if e.valid and e.type == "entity-ghost" then e.destroy(); n = n + 1 end
  end
  storage.tags[a.tag] = nil
  return { removed = n }
end

function api.tag(a)
  local t = storage.tags[a.tag]
  if not t then return { error = "no such tag " .. a.tag } end
  local out = {}
  for i, e in pairs(t.ents) do
    if e.valid then
      local d = describe(e)
      d.index = i
      d.status = (not d.ghost) and STATUS_NAME[e.status] or nil
      if d.ghost then
        local items = e.ghost_prototype.items_to_place_this
        d.item = items and items[1] and items[1].name or nil
      end
      out[#out + 1] = d
    else
      out[#out + 1] = { index = i, invalid = true }
    end
  end
  return { tag = a.tag, entities = out }
end

-- ---------------------------------------------------------------- screenshot
function api.shot(a)
  game.take_screenshot {
    surface = game.surfaces[1], position = { a.x, a.y }, resolution = { a.w, a.h }, zoom = a.zoom,
    path = a.path, show_entity_info = true, daytime = 0, force_render = true,
  }
  return { path = a.path }
end

-- ---------------------------------------------------------------- instant fair-play actions
function api.inv()
  local c = char()
  if not c then return { error = "no character; run spawn" } end
  return { items = contents(c.get_main_inventory()), position = xy(c.position) }
end

local function entity_at(x, y, filter)
  local surface = game.surfaces[1]
  local found = surface.find_entities_filtered { position = { x, y } }
  local best
  for _, e in pairs(found) do
    if e.type ~= "character" and e.type ~= "entity-ghost" and (not filter or filter(e)) then
      if not best or (best.type == "resource" and e.type ~= "resource") then best = e end
    end
  end
  return best
end

function api.put(a)
  local c = char()
  if not c then return { error = "no character; run spawn" } end
  local e = entity_at(a.x, a.y, function(e) return e.type ~= "resource" end)
  if not e then return { error = "no entity at " .. a.x .. "," .. a.y } end
  if not c.can_reach_entity(e) then return { error = "out of reach" } end
  local have = c.get_item_count(a.item)
  if have < a.n then return { error = string.format("short: have %d %s, need %d", have, a.item, a.n) } end
  local moved = e.insert { name = a.item, count = a.n }
  if moved > 0 then c.remove_item { name = a.item, count = moved } end
  return { moved = moved, into = e.name }
end

function api.take(a)
  local c = char()
  if not c then return { error = "no character; run spawn" } end
  local e = entity_at(a.x, a.y, function(e) return e.type ~= "resource" end)
  if not e then return { error = "no entity at " .. a.x .. "," .. a.y } end
  if not c.can_reach_entity(e) then return { error = "out of reach" } end
  local have = e.get_item_count(a.item)
  if have < a.n then return { error = string.format("short: %s holds %d %s, need %d", e.name, have, a.item, a.n) } end
  local fits = c.get_main_inventory().get_insertable_count(a.item)
  local n = math.min(a.n, fits)
  local moved = 0
  local out_inv = e.get_output_inventory()
  if out_inv and n > 0 then moved = out_inv.remove { name = a.item, count = n } end
  if moved < n then moved = moved + e.remove_item { name = a.item, count = n - moved } end
  if moved > 0 then c.insert { name = a.item, count = moved } end
  return { moved = moved, from = e.name }
end

function api.revive(a)
  local c = char()
  if not c then return { error = "no character; run spawn" } end
  local t = storage.tags[a.tag]
  if not t then return { error = "no such tag " .. a.tag } end
  local g = t.ents[a.index]
  if not (g and g.valid) then return { error = "invalid entry" } end
  if g.type ~= "entity-ghost" then return { built = true, already = true } end
  local items = g.ghost_prototype.items_to_place_this
  local item = items and items[1] and items[1].name
  if not item or c.get_item_count(item) < 1 then return { missing = item or "?" } end
  if bbox_dist(c.position, g.bounding_box) > c.build_distance then return { unreachable = true, distance = dist(c.position, g.position) } end
  c.remove_item { name = item, count = 1 }
  local _, ent = g.revive { raise_revive = true }
  if not ent then
    c.insert { name = item, count = 1 }
    return { error = "revive failed (blocked?)" }
  end
  t.ents[a.index] = ent
  credit("build-entity", ent.name, 1)
  return { built = true, item = item }
end

-- ---------------------------------------------------------------- timed jobs (advance in on_tick)
local function set_job(j)
  j.state = "running"; j.start = game.tick
  storage.job = j
  return { started = j.kind }
end

function api.job()
  local j = storage.job
  if not j then return { state = "none" } end
  return { kind = j.kind, state = j.state, msg = j.msg, result = j.result }
end

function api.cancel_job()
  local c = char()
  if c then c.walking_state = { walking = false, direction = defines.direction.north } end
  storage.job = nil
  return { cancelled = true }
end

function api.walk(a)
  local c = char()
  if not c then return { error = "no character; run spawn" } end
  local id = c.surface.request_path {
    bounding_box = c.prototype.collision_box, collision_mask = c.prototype.collision_mask,
    start = c.position, goal = { a.x, a.y }, force = c.force, radius = a.radius or 0.5,
    entity_to_ignore = c, pathfind_flags = { cache = false, low_priority = false, prefer_straight_paths = true },
  }
  return set_job { kind = "walk", goal = { x = a.x, y = a.y }, radius = a.radius or 0.5, path_id = id, wp = nil, i = 1, timeout = a.timeout or 3600, last_move = game.tick, last_pos = xy(c.position) }
end

local function on_path(ev)
  local j = storage.job
  if not (j and j.kind == "walk" and j.path_id == ev.id) then return end
  if ev.try_again_later then
    j.state = "failed"; j.msg = "unreachable (pathfinder busy)"; return
  end
  if not ev.path then j.state = "failed"; j.msg = "unreachable"; return end
  j.wp = {}
  for _, w in ipairs(ev.path) do j.wp[#j.wp + 1] = { x = w.position.x, y = w.position.y } end
end

script.on_event(defines.events.on_script_path_request_finished, function(ev)
  local ok, err = pcall(on_path, ev)
  if not ok and storage.job then storage.job.state = "failed"; storage.job.msg = "bridge error: " .. tostring(err) end
end)

local DIRS8 = { -- angle sectors -> 16-way enum (east = 0 rad, y grows south)
  defines.direction.east, defines.direction.southeast, defines.direction.south, defines.direction.southwest,
  defines.direction.west, defines.direction.northwest, defines.direction.north, defines.direction.northeast,
}

local function step_walk(j, c)
  if game.tick - j.start > j.timeout then
    c.walking_state = { walking = false, direction = defines.direction.north }
    j.state = "failed"; j.msg = "unreachable (timeout)"; return
  end
  if not j.wp then return end
  local target = j.wp[j.i]
  while target and dist(c.position, target) < 0.25 do
    j.i = j.i + 1; target = j.wp[j.i]
  end
  if not target then
    c.walking_state = { walking = false, direction = defines.direction.north }
    if dist(c.position, j.goal) <= j.radius + 1 then
      j.state = "done"; j.result = { position = xy(c.position) }
    else
      j.state = "failed"; j.msg = "unreachable"
    end
    return
  end
  local ang = math.atan2(target.y - c.position.y, target.x - c.position.x)
  local sector = math.floor((ang / (2 * math.pi)) * 8 + 0.5) % 8
  c.walking_state = { walking = true, direction = DIRS8[sector + 1] }
  if dist(c.position, { x = j.last_pos[1], y = j.last_pos[2] }) > 0.05 then
    j.last_move = game.tick; j.last_pos = xy(c.position)
  elseif game.tick - j.last_move > 120 then
    c.walking_state = { walking = false, direction = defines.direction.north }
    j.state = "failed"; j.msg = "unreachable (stuck)"
  end
end

local function mining_ticks(c, target)
  local speed = c.prototype.mining_speed * (1 + c.force.manual_mining_speed_modifier + c.character_mining_speed_modifier)
  return math.max(1, math.ceil(target.prototype.mineable_properties.mining_time / speed * 60))
end

function api.mine(a)
  local c = char()
  if not c then return { error = "no character; run spawn" } end
  local target = entity_at(a.x, a.y)
  if not target then return { error = "nothing minable at " .. a.x .. "," .. a.y } end
  if not target.minable then return { error = target.name .. " is not minable" } end
  if target.prototype.mineable_properties.required_fluid then
    return { error = target.name .. " needs " .. target.prototype.mineable_properties.required_fluid .. " to mine; not by hand" }
  end
  local reach = target.type == "resource" and c.resource_reach_distance or c.reach_distance
  if bbox_dist(c.position, target.bounding_box) > reach then return { error = "out of reach" } end
  return set_job { kind = "mine", target = target, target_name = target.name, left = a.n or 1, progress = 0, per = mining_ticks(c, target), got = 0 }
end

local function product_count(p)
  if p.amount then return p.amount end
  return math.random(p.amount_min, p.amount_max)
end

local function step_mine(j, c)
  local t = j.target
  if not t.valid then j.state = "done"; j.result = { mined = j.got, msg = "target gone" }; return end
  c.mining_state = { mining = true, position = t.position } -- animation only; progress is ours
  j.progress = j.progress + 1
  if j.progress < j.per then return end
  j.progress = 0
  if t.type == "resource" then
    local inv = c.get_main_inventory()
    local adds = {}
    for _, p in pairs(t.prototype.mineable_properties.products or {}) do
      if p.type == "item" then adds[#adds + 1] = { name = p.name, count = product_count(p) } end
    end
    for _, it in pairs(adds) do
      if inv.get_insertable_count(it.name) < it.count then
        c.mining_state = { mining = false }
        j.state = "done"; j.msg = "inventory full"; j.result = { mined = j.got, msg = "inventory full" }; return
      end
    end
    for _, it in pairs(adds) do c.insert(it) end
    if t.amount <= 1 then t.destroy() else t.amount = t.amount - 1 end
  else
    if not t.mine { inventory = c.get_main_inventory(), raise_destroyed = true } then
      c.mining_state = { mining = false }
      j.state = "done"; j.msg = "inventory full"; j.result = { mined = j.got, msg = "inventory full" }; return
    end
  end
  j.got = j.got + 1
  credit("mine-entity", t.valid and t.name or j.target_name, 1)
  j.left = j.left - 1
  if j.left <= 0 or not t.valid then
    c.mining_state = { mining = false }
    j.state = "done"; j.result = { mined = j.got }
  end
end

function api.craft(a)
  local c = char()
  if not c then return { error = "no character; run spawn" } end
  local recipe = prototypes.recipe[a.item]
  if not recipe then return { error = "no recipe " .. a.item } end
  local can = c.get_craftable_count(a.item)
  if can < a.n then return { error = string.format("missing ingredients: can craft %d of %d", can, a.n) } end
  for _, p in pairs(recipe.products) do
    if p.type == "item" and c.get_main_inventory().get_insertable_count(p.name) < (p.amount or 1) * a.n then
      return { error = "result won't fit in inventory" }
    end
  end
  local started = c.begin_crafting { recipe = a.item, count = a.n, silent = true }
  if started < a.n then return { error = "crafting started only " .. started } end
  return set_job { kind = "craft", item = a.item, n = a.n }
end

local function step_craft(j, c)
  if c.crafting_queue_size == 0 then
    j.state = "done"; j.result = { crafted = j.n, item = j.item }
    local recipe = prototypes.recipe[j.item]
    for _, prod in pairs(recipe and recipe.products or {}) do
      if prod.type == "item" then credit("craft-item", prod.name, (prod.amount or 1) * j.n) end
    end
  end
end

script.on_event(defines.events.on_tick, function()
  local j = storage.job
  if not j or j.state ~= "running" then return end
  local c = char()
  if not c then j.state = "failed"; j.msg = "character gone"; return end
  local step = ({ walk = step_walk, mine = step_mine, craft = step_craft })[j.kind]
  if not step then j.state = "failed"; j.msg = "unknown job " .. tostring(j.kind); return end
  -- never let a job error take the whole game down: fail the job instead
  local ok, err = pcall(step, j, c)
  if not ok then
    pcall(function() c.walking_state = { walking = false, direction = defines.direction.north } end)
    pcall(function() c.mining_state = { mining = false } end)
    j.state = "failed"; j.msg = "bridge error: " .. tostring(err)
  end
end)

-- ---------------------------------------------------------------- chat with the team
-- Players' chat lines are queued for Claude; Claude answers with `say`.
local CHAT_KEEP = 200

script.on_event(defines.events.on_console_chat, function(ev)
  if not ev.player_index then return end -- server/RCON lines (including Claude's own)
  local ok = pcall(function()
    storage.chat = storage.chat or { seq = 0, msgs = {} }
    local ch = storage.chat
    ch.seq = ch.seq + 1
    local p = game.get_player(ev.player_index)
    ch.msgs[#ch.msgs + 1] = { id = ch.seq, tick = ev.tick, from = p and p.name or "?", text = ev.message }
    while #ch.msgs > CHAT_KEEP do table.remove(ch.msgs, 1) end
  end)
end)

function api.chat_read(a)
  local ch = storage.chat or { seq = 0, msgs = {} }
  local out = {}
  for _, m in ipairs(ch.msgs) do
    if m.id > (a.after or 0) then out[#out + 1] = m end
  end
  return { seq = ch.seq, msgs = out }
end

function api.say(a)
  local text = tostring(a.text or ""):sub(1, 500)
  game.print("[color=#7fc8ff][Claude][/color] " .. text)
  local c = char()
  if c then
    pcall(function()
      c.surface.create_entity {
        name = "compi-speech-bubble", position = c.position, source = c,
        text = text, lifetime = math.min(600, 120 + #text * 4),
      }
    end)
  end
  return { said = text }
end

-- ---------------------------------------------------------------- remote interface
local wrapped = {}
for name, fn in pairs(api) do
  wrapped[name] = function(json)
    local args = (json and json ~= "") and helpers.json_to_table(json) or {}
    local ok, res = pcall(fn, args)
    if not ok then res = { error = tostring(res) } end
    return helpers.table_to_json(res)
  end
end
remote.add_interface("claude", wrapped)
