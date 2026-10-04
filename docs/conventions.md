# Factorio 2.0.77 grid conventions (measured, not assumed)

Measured 2026-10-04 by `client/spike.py` against a live hosted game. Rerun it after any game update.

## Coordinates
- y grows **downward** (south is +y).
- Tile (x,y) covers [x, x+1) × [y, y+1).
- Odd-sized entities (1x1, 3x3) centre on tile centres. A belt asked at (40,40) snapped to (40.5,40.5). An assembler at (50.5,45.5) occupies tiles 49..51 × 44..46.
- Even-sized entities (2x2) centre on tile corners. A stone furnace at (45,45) occupies tiles 44..45 × 44..45.
- Splitter (1×2): asked for east at (55,45), it snapped to (55.5,45.0). For east/west it is 1 tile wide and 2 tall, centred on the tile edge between the two lanes.
- Bounding boxes are inset 0.1–0.3 from the tile edges. Don't use them for tile math; use position + footprint.

## Directions (16-way enum)
north=0, east=4, south=8, west=12. The odd values and 2/6/10/14 are diagonals, unused by belts and inserters. **This is not the 1.1 scheme (0/2/4/6).**

## Inserters: direction = the PICKUP side
| direction | pickup offset | drop offset |
|---|---|---|
| north | (0,-1) | (0,+1.2) |
| east  | (+1,0) | (-1.2,0) |
| south | (0,+1) | (0,-1.2) |
| west  | (-1,0) | (+1.2,0) |

An inserter "facing north" takes from the north and drops south. Never reason about this from the name. Stamps declare *drop side*, and the code converts that with `direction = opposite(drop_side)`.

## Underground belts
Ghost spec `{type="input"|"output"}`. Read the type back with `belt_to_ground_type` (on a ghost it's also exposed as `ghost_type`). For an east-going pair, both halves have direction east, with the input on the west end.

## RCON
- `rcon.print` takes exactly one argument, so concatenate first.
- The first `/silent-command` in a fresh game is swallowed by the achievements-disable confirmation. Send a throwaway command first.
- Errors come back as `Cannot execute command. Error: ...` in the response text.

## Screenshots
- `game.take_screenshot{surface=, position=, resolution=, zoom=, path=, show_entity_info=true}` writes to `%APPDATA%\Factorio\script-output\<path>` and **renders while `tick_paused=true`**.
- At zoom 1 (32 px/tile), ghost belts and inserters are visible, but their facing is not readable. Use zoom ≥ 2 for direction checks, and treat the ASCII view built from engine data as the source of truth.

## can_place_entity needs a build_check_type
Without `build_check_type`, `surface.can_place_entity` returns true for an offshore pump on dry land. Always pass `build_check_type = defines.build_check_type.manual` to get the rules a player is held to (measured 2026-10-04 at 0,19, with no water within 2 tiles).
