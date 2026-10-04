# Spec: factory layout tooling
Approved-by: user (2026-10-04)

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

Multi-tile entities:
- Write the code on every tile the entity covers.
- Give the same direction char on every one of those tiles.
- The footprint must be a complete, aligned square of the right size.

Placement and rotation:
- `plan <stamp> X Y ROT` maps the stamp's top-left tile to tile (X,Y).
- ROT is 0/90/180/270 clockwise. It rotates both the grid and every direction char.
- After rotating, the grid's top-left tile is again placed at (X,Y).

Every command that needs ticks to pass (`walk`, `mine`, `craft`, `build`, `prove`) unpauses the game while it runs and restores the previous paused state when it finishes.

## Acceptance criteria
Live criteria need the user's hosted game with the `claude-bridge` mod enabled, RCON on 127.0.0.1:27015, `FACTORIO_RCON_PASSWORD` set, and peaceful mode or a cleared area. Offline criteria need nothing.

- AC-1: [offline] `python -m pytest -q tests` exits 0, with tests covering stamp parsing; rotation by 0/90/180/270 for both positions and direction chars, including the placement of 2x2 and 3x3 footprints; drop-side → direction conversion matching the inserter table in `docs/conventions.md`; the ASCII renderer working on a captured grid; and lint rules working on synthetic grids.
- AC-2: [offline] A malformed stamp fails with an error that names its line and column. Malformed means any of: an unknown code; an odd-length or ragged row; a direction char missing where the table requires one; a multi-tile footprint that is incomplete or misaligned.
- AC-3: [live] `python client/fx.py status` prints the bridge version, the game tick, the paused state, and Claude's character position. `python client/fx.py spawn` creates Claude's character near the first connected player if none exists, and does nothing if one does. The user's character and inventory are never modified.
- AC-4: [live] `python client/fx.py look X1 Y1 X2 Y2` prints a 2-char-per-tile grid in stamp notation, with x and y rulers. It shows resources, water, trees and rocks, built entities, and ghosts; ghosts carry a `?` marker line under the grid listing their tiles. Inserters are drawn from the engine's `drop_position`, never from their direction field, so an inserter ghost planned with drop side east renders as `i>`.
- AC-5: [live] `python client/fx.py plan <stamp> X Y ROT [--tag T]` places only ghosts and prints `tag: <T>`, generating a tag if none is given. It also prints every ghost's tile and code, which must equal the rotated stamp offset by (X,Y). `python client/fx.py unplan <T>` removes exactly the ghosts from that tag.
- AC-6: [live] `python client/fx.py lint <T>` prints one finding per problem, giving the tile and the rule, and exits nonzero if there are any. Built entities and ghosts both count as present. The rules: (a) an inserter's pickup tile or drop tile has no entity with an inventory and no belt; (b) a belt that is neither `e` nor ends in an underground input feeds into a tile with no belt; (c) a belt feeds sideways into another belt and is not an `s`; (d) an entity that needs electricity is not inside any pole's supply area; (e) a ghost fails `can_place_entity` (collision with a tree/rock/entity, or water). The sabotage test: planning `stamps/burner-iron.txt` with its output inserter reversed is flagged at that inserter's tile.
- AC-7: [live] `python client/fx.py shot X Y ZOOM` writes a PNG under `%APPDATA%\Factorio\script-output\claude\` and prints its path, including while the game is paused.
- AC-8: [live] Gate before building: `python client/fx.py build <T>` refuses, with a message saying what is missing, unless all three hold since the tag's last `plan`: `lint <T>` passed with zero findings, a `look` covered the tag's bounding box, and a `shot` covered the tag's bounding box.
- AC-9: [live, fair play] `build <T>` walks Claude's character within build reach of each ghost and revives it by removing one matching item from Claude's inventory. A ghost whose item Claude lacks is listed as `missing`, and one Claude can't reach is listed as `unreachable`; neither is built, and the exit code is nonzero if any ghost stays unbuilt. No item is ever created from nothing.
- AC-10: [live, fair play] Supporting actions: `fx.py walk X Y` pathfinds and moves the character, printing the final position, or `unreachable` with a nonzero exit, giving up after 60 s of game time. `fx.py mine X Y [N]` mines a resource or entity within reach, in real mining time, into the inventory, and refuses when out of reach. `fx.py craft ITEM N` hand-crafts from Claude's own ingredients in real crafting time, and refuses when ingredients are missing. `fx.py put X Y ITEM N` and `fx.py take X Y ITEM N` move items between Claude's inventory and an entity within reach, refusing when out of reach or when the source is short. `fx.py inv` lists the inventory.
- AC-11: [live, end to end] Claude builds `stamps/burner-iron.txt` on an iron-ore patch. The stamp is two burner mining drills, each outputting into a stone furnace, with a burner inserter taking from each furnace into one wooden chest. Everything not in the vanilla freeplay starting inventory is gathered with `mine` and made with `craft`, and fuel goes in with `put`. Then `python client/fx.py prove <T> 600` runs 600 ticks and prints each entity's status; it exits 0 only if every furnace and drill reports `working` (or `waiting_for_space_in_destination` for a drill) and the chest holds at least 1 iron plate.
- AC-12: [offline] `CLAUDE.md` documents setup (linking the mod, enabling it, RCON settings) and every `fx.py` command.

## Out of scope
- Combat and biters. The test map is peaceful or has a cleared area.
- Long-range strategy: research order, rocket. This build is the layout and action layer only.
- Driving vehicles, trains, fluids, and modules.
- Headless server mode. It runs only on the user's hosted client game.
- Any change to the user's existing saves.
