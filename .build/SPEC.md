# Spec: factory layout tooling
Approved-by: user (2026-10-04; phase 2 approved in chat, then standing instruction "dont ask for approval just play the game")

## Goal
Let Claude place belts, inserters and machines in Factorio 2.0.77 without making the coordinate mistakes that come from not seeing the screen. The user's words: "Laying out belts and inserters by coordinates without seeing the screen is where I'll make mistakes. This is what you need to figure out."

Claude works through its own second character and plays fair:
- it has limited reach;
- it needs the items in its inventory;
- no entity or item is ever created from nothing.

Every layout goes through the same sequence:
1. Drafted as ghosts.
2. Checked three ways: an ASCII view read from the engine, a screenshot, and lint.
3. Built.
4. Proven working by entity status.

The conventions this rests on were measured live and are in `docs/conventions.md`.

## Phase 2 goal (added 2026-10-04)
Build steam power and an automated red-science line that feeds labs, so research runs on its own. The user's words: "Your goal is to create red flasks and turn them into research. You will build the process to do that." This needs layouts the phase-1 stamps can't express: non-square entities (boiler 3x2, steam engine 3x5), pipes and fluid connections, assemblers with a recipe, labs, and pole networks that must reach a generator.

## Stamp format
A stamp is a text file in `stamps/`. Lines starting with `#` are comments. A tile is written as **two characters**: an entity code and a direction char.
- Direction chars are `^ > v <` (north/east/south/west). `.` means no direction.
- An empty tile is `..`.

Entity codes:

| Code | Entity | Size | What the direction char means |
|---|---|---|---|
| `b` | transport-belt | 1x1 | belt direction |
| `s` | transport-belt | 1x1 | belt direction; it may sideload into the belt it feeds |
| `e` | transport-belt | 1x1 | belt direction; it may end without feeding anything (an open output) |
| `u` / `U` | underground-belt | 1x1 | `u` is the input half, `U` the output half; the char is belt direction |
| `i` | burner-inserter | 1x1 | the **drop side**; the tool converts it with `direction = opposite(drop side)` (`docs/conventions.md`) |
| `I` | inserter | 1x1 | drop side, same conversion as `i` |
| `F` | stone-furnace | 2x2 | `.` |
| `D` | burner-mining-drill | 2x2 | output side |
| `A` | assembling-machine-1 | 3x3 | `.` |
| `c` | wooden-chest | 1x1 | `.` |
| `p` | small-electric-pole | 1x1 | `.` |
| `B` | boiler | 3x2 (north) | facing: the side its steam output is on |
| `E` | steam-engine | 3x5 (north) | `^`/`v` for a vertical engine, `>`/`<` for a horizontal one |
| `O` | offshore-pump | 1x1 | its facing as the engine reports it (`docs/conventions.md` records which side the water is on) |
| `x` | pipe | 1x1 | `.` |
| `L` | lab | 3x3 | `.` |
| `A` | assembling-machine-1 | 3x3 | `.` or a recipe key (see below) |

Non-square entities are listed at their north-facing size. Facing east or west swaps width and height, and the footprint written in the stamp must match the rotated size.

Recipe keys are lowercase letters (never `^ > v < .`) and are not rotated. A stamp line `@k recipe-name` (e.g. `@g iron-gear-wheel`) lets an assembler write `k` as its second char (`Ag`) on every tile it covers. `plan` gives the ghost that recipe.

Multi-tile entities:
- Write the code on every tile the entity covers.
- Give the same direction char on every one of those tiles.
- The footprint must be a complete, aligned rectangle of the entity's size for its facing (square for square entities).

Placement and rotation:
- `plan <stamp> X Y ROT` maps the stamp's top-left tile to tile (X,Y).
- ROT is 0/90/180/270 clockwise. It rotates both the grid and every direction char.
- After rotating, the grid's top-left tile is again placed at (X,Y).

`mine X Y [N]`: N is the number of mining cycles (one item per cycle for resources), default 1. It stops early when the target is gone or the inventory is full.

Every command that needs ticks to pass (`walk`, `mine`, `craft`, `build`, `prove`) unpauses the game while it runs and restores the previous paused state when it finishes.

## Acceptance criteria
Live criteria need the user's hosted game with the `claude-bridge` mod enabled, RCON on 127.0.0.1:27015, `FACTORIO_RCON_PASSWORD` set, and peaceful mode or a cleared area. Offline criteria need nothing.

- AC-1: [offline] `python -m pytest -q tests` exits 0, with tests covering stamp parsing; rotation by 0/90/180/270 for both positions and direction chars, including the placement of 2x2 and 3x3 footprints; drop-side → direction conversion matching the inserter table in `docs/conventions.md`; the ASCII renderer working on a captured grid; and lint rules working on synthetic grids.
- AC-2: [offline] A malformed stamp fails with an error that names its line and column. Malformed means any of: an unknown code; an odd-length or ragged row; a direction char missing where the table requires one; a multi-tile footprint that is incomplete or misaligned.
- AC-3: [live] `python client/fx.py status` prints the bridge version, the game tick, the paused state, and Claude's character position. `python client/fx.py spawn` creates Claude's character near the first connected player if none exists, and does nothing if one does. On creation, and only then, the new character receives exactly the vanilla freeplay starting items (read from the `freeplay` scenario's `get_created_items` interface), the same kit any new player gets; this is the one exemption from "no item from nothing". The user's character and inventory are never modified.
- AC-4: [live] `python client/fx.py look X1 Y1 X2 Y2` prints a 2-char-per-tile grid in stamp notation, with x and y rulers. Notation beyond the stamp codes: resources `'i` iron, `'c` copper, `'k` coal, `'s` stone, `'u` uranium, `'o` crude oil; `~~` water; `T.` tree; `R.` rock; `@@` character; `##` any other entity. When layers share a tile, an entity (built or ghost) wins over a resource, which wins over water. Ghosts carry a `?` marker line under the grid listing their tiles. Inserters are drawn from the engine's `drop_position`, never from their direction field, so an inserter ghost planned with drop side east renders as `i>`.
- AC-5: [live] `python client/fx.py plan <stamp> X Y ROT [--tag T]` places only ghosts and prints `tag: <T>`, generating a tag if none is given. It refuses, placing nothing, if the tag already exists (unplan it first) or if any footprint tile already holds a ghost or a built entity other than a tree or rock (trees and rocks are reported by lint rule e). The mod records which ghosts belong to which tag. It also prints every ghost's tile and code, which must equal the rotated stamp offset by (X,Y). `python client/fx.py unplan <T>` removes exactly the ghosts from that tag.
- AC-6: [live] `python client/fx.py lint <T>` prints one finding per problem, giving the tile and the rule, and exits nonzero if there are any. Built entities and ghosts both count as present. The rules: (a) an inserter's pickup tile or drop tile has no entity with an inventory and no belt; (b) a belt that is neither `e` nor ends in an underground input feeds into a tile with no belt; (c) a belt feeds sideways into another belt and is not an `s`; (d) an entity that needs electricity is not inside any pole's supply area; (e) a ghost fails `can_place_entity` (collision with a tree/rock/entity, water, or a drill with no ore under it); (f) `dead-end`: an inserter drops into a furnace or assembler that no inserter takes from; (g) `intent`: the engine's drop side (inserters) or direction (belts, drills) disagrees with the stamp; (h) a drill outputs onto a tile with no inventory and no belt; (i) an underground input `u` has no output of the same direction on its line within the prototype's max underground distance, or an output `U` has no such input behind it. A paired input counts as continuing the belt, and the output is checked as a belt under (b) and (c). The sabotage test: planning `stamps/burner-iron.txt` with its output inserter reversed is flagged at that inserter's tile (rule f, since both of its ends still have inventories).
- AC-7: [live] `python client/fx.py shot X Y ZOOM` writes a PNG under `%APPDATA%\Factorio\script-output\claude\` and prints its path, including while the game is paused.
- AC-8: [live] Gate before building: `python client/fx.py build <T>` refuses, with a message saying what is missing, unless all three hold since the tag's last `plan`: `lint <T>` passed with zero findings, a `look` covered the tag's bounding box, and a `shot` covered the tag's bounding box. Each check records a fingerprint of everything in the tag's bounding box plus 4 tiles; `build` rescans first and refuses with `area changed since checks` if that fingerprint no longer matches what lint, look and shot saw.
- AC-9: [live, fair play] `build <T>` walks Claude's character within build reach of each ghost and revives it by removing one matching item from Claude's inventory. A ghost whose item Claude lacks is listed as `missing`, and one Claude can't reach is listed as `unreachable`; neither is built, and the exit code is nonzero if any ghost stays unbuilt. No item is ever created from nothing.
- AC-10: [live, fair play] Supporting actions: `fx.py walk X Y` pathfinds and moves the character, printing the final position, or `unreachable` with a nonzero exit, giving up after 60 s of game time. `fx.py mine X Y [N]` mines a resource or entity within reach, in real mining time, into the inventory, and refuses when out of reach. `fx.py craft ITEM N` hand-crafts from Claude's own ingredients in real crafting time, and refuses when ingredients are missing. `fx.py put X Y ITEM N` and `fx.py take X Y ITEM N` move items between Claude's inventory and an entity within reach, refusing when out of reach or when the source is short. `put` uses the engine's own insert routing (fuel to the fuel slot, ingredients to the source slot); `take` takes from the entity's output inventory first, then any other. Nothing is ever dropped or lost: when the destination can't hold everything, `put`/`take` move what fits and print the moved count; `mine` stops and prints `inventory full`; `craft` refuses if the result won't fit. `fx.py inv` lists the inventory.
- AC-11: [live, end to end] Claude builds `stamps/burner-iron.txt` on an iron-ore patch. The stamp is two burner mining drills, each outputting into a stone furnace, with a burner inserter taking from each furnace into one wooden chest. Everything not in the vanilla freeplay starting inventory is gathered with `mine` and made with `craft`, and fuel goes in with `put`. Then `python client/fx.py prove <T> 600` runs 600 ticks and prints each entity's status; it exits 0 only if every furnace and drill reports `working` (or `waiting_for_space_in_destination` for a drill) and the chest holds at least 1 iron plate.
- AC-12: [live] `python client/fx.py prove <T> N` works for any tag: it runs N ticks and prints each tag entity's status. It exits 0 only if every furnace, drill and assembler reports `working` (drills may also report `waiting_for_space_in_destination`) and every inserter reports `working` or `waiting_for_source_items`, otherwise nonzero naming the entities that failed.
- AC-13: [offline] `CLAUDE.md` documents setup (linking the mod, enabling it, RCON settings) and every `fx.py` command.

- AC-22: [live] `build` re-runs every lint rule against a fresh scan right before building, and refuses on any finding. This also covers power sources and fluids outside the fingerprinted box, which can change without the fingerprint noticing. The fingerprint is defined as entity name, top-left tile, size, direction and belt type; water tiles; and which tiles hold which resource. It excludes characters, inventories, statuses and resource amounts.
- AC-23: [live] `prove <T> N` samples the tag's statuses every 60 ticks. An entity passes if it is in its OK set in at least half the samples. OK sets: furnace, assembler, boiler, steam engine, offshore pump and lab are `working`; a drill may also be `waiting_for_space_in_destination`; an inserter may also be `waiting_for_source_items`. Containers fed by tag inserters must end non-empty. This replaces the single end-of-run snapshot in AC-12.
- AC-14: [offline] `python -m pytest -q tests` covers non-square footprints in every rotation (boiler, steam engine), recipe keys (a parse error names line/col for an unknown key), and fluid and power-network lint on synthetic snapshots.
- AC-15: [live] For every entity, `scan` reports its footprint as the prototype's tile size (swapped for east/west), centred on its position, not as its bounding box. A planned boiler, steam engine and offshore pump each `look` exactly as their stamp tiles in all four rotations.
- AC-16: [live] Fluid lint, rule (j). For each fluid entity in the tag, the mod reports its pipe connection points from the prototype, rotated to the entity's direction, and lint matches each one against a neighbour's facing connection. Findings: `fluid-isolated` (a fluid entity with no matched connection); `fluid-open` (an offshore pump's output or a boiler's steam output is unmatched, or a boiler has no matched water input). The sabotage test: a power stamp with the boiler rotated 90° is flagged.
- AC-17: [live] Power-network lint, rule (k). Poles connect when within the smaller wire reach of the two. An electric consumer in the tag is flagged `no-power-source` unless its covering pole's network contains a pole that covers a steam engine, or a built pole whose live network shows production. The network is traversed over ghost and built poles in a scan of the tag bbox plus 40 tiles. A ghost-only chain that leaves that scan without reaching a powered built pole is flagged. Electric entities with no covering pole remain rule (d) `power`.
- AC-18: [live] `python client/fx.py poles X1 Y1 X2 Y2 [--tag T]` plans small-pole ghosts along an L-shaped path (x first, then y), spaced no more than the wire reach apart, as a tag. The tag goes through look/shot/lint/build like any other.
- AC-19: [live] `python client/fx.py research NAME` sets the force's current research and prints it. It refuses a tech that is unknown, already researched, or has unresearched prerequisites. `python client/fx.py tech` lists the current research with its progress, and every available tech. `python client/fx.py recipe X Y RECIPE` sets the recipe of a built assembler within reach.
- AC-20: [live, end to end] Claude builds steam power at the lake: offshore pump → boiler → steam engine, plus a coal chest with a burner inserter feeding the boiler. A pole line runs from the engine to a lab at the base. Everything is from gathered and crafted items, and the power tags lint clean before build. Then, with red flasks inserted, `prove` shows the steam engine and the lab `working`, and `fx.py tech` shows Automation progress increasing.
- AC-21: [live, end to end] After Automation completes, Claude builds an assembler line with these stamps: iron plates → gear assembler → red-flask assembler (copper plates fed in) → inserters → labs. Plates arrive by belt or inserter from the smelter chests, nothing is hand-fed, and the next research is queued. `prove <tag> 3600` passes under AC-23, the red-flask assembler's `products_finished` rises during the window, and the current research's progress rises.

## Out of scope
- Combat and biters. The test map is peaceful or has a cleared area.
- Long-range strategy: research order, rocket. This build is the layout and action layer only.
- Driving vehicles, trains, oil and other fluids beyond water/steam, and modules.
- Headless server mode. It runs only on the user's hosted client game.
- Any change to the user's saves that predate this project. Live tests and play happen only on the hosted map made for it.
