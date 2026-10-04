# Game state and plan (handoff for the next session)

Last updated 2026-10-04. **Update this file whenever something is built or the plan changes.** It is the only record of the game state outside the game itself.

## How to resume
1. Read `CLAUDE.md` (commands, architecture) and `docs/conventions.md` (measured engine facts).
2. Re-arm the chat watcher with the Monitor tool: `cd ~/playground/factory && python -u client/chatwatch.py`, timeout 30 min, re-armed on every expiry. Answer the player in game with `python client/fx.py say ...`.
3. Run `python client/fx.py status` and `python client/fx.py tech`.
4. Check the last background run: `/tmp/power_run.log`.

## Working with the player (ColonClean)
- **Their role:** they keep the burner drills fuelled with coal. Nothing else. They don't want gathering tasks.
- **No approvals:** they said "dont ask for approval just play the game". Never offer option menus; pick one fix and do it. I lead.
- **Chat is how they direct me.** Answer within seconds, which means:
  - long scripts run with `run_in_background`;
  - the player wants Claude's own short findings + next-step lines in game chat (post them with `fx.py say` as you work), not mechanical step logs. Script narration is off by default (`FX_NARRATE=1` turns it on).
  - background scripts no longer stop on chat (2026-10-04, the player asked). The chatwatch monitor reports chat; answer with `fx.py say` while the script runs. Don't issue walk/build/craft commands while a script is driving the character. `FX_CHAT_INTERRUPT=1` restores the old stop-on-chat.
- **Mod changes need a reload:** after editing `bridge/control.lua`, ask them in chat for Esc → Save, quit to menu, Multiplayer → Host saved game.

## Goal
Automated red science feeding labs, with research running continuously. Phase-2 ACs 14–23 are in `.build/SPEC.md`. The pipeline is at stage `build`, tasks 15–16 of `.build/PLAN.md`. Tasks 9–14 are done; their live tests pass.

## What's built (tags in `.fx_state.json`; mod tags in game storage)
| Tag | Where (bbox) | What | Notes |
|---|---|---|---|
| `e2e` | -94,38 .. -88,41 | Burner iron smelter: 2 drills → 2 furnaces → inserters → chest at (-91,41) | Iron-plate source (hundreds of plates). The player fuels the drills |
| `copper` | -81,7 .. -75,10 | Same stamp on copper; chest at (-78,10) | Copper-plate source |
| `team-chest` | -86,44 | Wooden chest | Unused now |
| `power` | 45,34 .. 51,40 | Offshore pump (51,34) → pipe → boiler (47,34) → steam engine (47,36), pole (46,36), burner inserter (46,35) feeding the boiler from a coal chest (45,35) | Built and fuelled (boiler 5 coal, chest ~55) |
| `lab` | -68,22 .. -65,24 | Lab + pole (-65,22) | Built and proven; researching. The player built the pole (fx resolves player-built ghosts by tile) |
| (player's line) | (46.5,36.5) to (-64.5,22.5) | 18 small poles along y=22.5, then diagonally to the engine | Built by the player, not a tag. Lint follows pole wires past its scan edge to find the engine |
| `science` | -91,11 .. -69,40 | Red science line 1: inserter out of the iron chest -> belt (x=-91 north, y=26 east) -> gear assembler (-76,22); inserter out of the copper chest -> belt (x=-78 south, y=20 east) -> flask assembler (-72,22) -> lab (`lab` tag). 8 poles off the lab pole | `client/science_run.py`; proven: 4 flasks/min, research rising |
| `science2` | -76,12 .. -70,21 | Lines 2-3: the gear assembler also drops gears onto the copper belt (north lane); flask assemblers (-76,16), (-72,16) take copper + gears from it, each feeding a lab (-76,12), (-72,12) | `client/scale_run.py`; proven: 6 flasks each/min. The player built the labs |
| `engine2` | 46,41 .. 49,45 | Second steam engine chained below the first, pole (46,42) | 1.8 MW total. Proven |
| `elec-iron` | -103,42 .. -74,49 | 4 electric drills (x -85..-74, y 42..44) -> stone furnaces (y 45..46); long-handed inserters fuel them from a coal belt (row 49) fed by an electric drill on coal at (-103,46); inserters put plates on row 48 -> up x=-91 -> inserter into the iron chest from the south | `client/elec_iron_run.py`. Proven 60/60 (the first prove failed only on coal start-up lag) |
| (player's coal line) | coal field (-106..-99, 31..32) -> belt row 28 -> boiler chest (45,35) | Burner drills on coal, belt to the boiler; the boiler is fed by an electric inserter (46,35) | Built by the player. The boiler no longer needs hand coal |
| `elec-iron2` | -79,30 .. -57,56 | Mirror of elec-iron on rows 50..56 sharing its coal belt (extended east on row 49). Plates: row 50 east -> up x=-57 -> belt M west along row 30 (iron on M's south lane) | `client/green_run.py`. Proven (furnaces may sit output-full; M backs up) |
| `green` | -73,20 .. -58,40 | Green science: M loops down x=-73 and back east on row 40. Row 1 (rows 32-34, fed from M): gear (-72,32), gear (-64,32), cable (-60,32). Row 2 (rows 36-38, fed from row 40): belt asm (-72,36), GREEN (-68,36), inserter asm (-64,36), circuit (-60,36). Flasks go up x=-67 by underground into lab 1 via (-67,25). Filtered inserter (-70,20) takes copper only off the red copper/gear belt | Proven. The original copper column at x=-63 is retired (`fx retire`) |
| `green-cu` | -63,20 .. -57,29 | Copper from the filtered inserter east on row 20, down x=-57, underground past the coal belt, into M's corner (-57,30) from the north (copper on M's north lane, upstream of every consumer) | Proven via `prove green` |
| `power2` | 35,34 .. 46,50 | Boiler 2 (36,39) + 2 steam engines (36,41),(36,46). Water from boiler 1's west port (46,34) along row 34, down x=39, under the coal belt by pipe-to-ground (39,36)/(39,38). Coal: inserter (37,38) straight off the player's coal belt | `client/power2_run.py`. Proven. 3.6 MW total |
| `brick-sink` | -59,41 .. -59,42 | Inserter filtered to stone-brick at the end of the green row-40 belt, into a chest | Stopgap. The cause (elec-iron2's west unit reaching stone) is retired |
| `elec-iron-ext` | -73,42 .. -68,48 | Two more elec-iron columns (drills -73,42 and -70,42) on the existing coal (row 49) and plate (row 48) belts | `client/elec_iron_ext_run.py`. Proven 60/60 |
| `labs67` | -69,11 .. -62,14 | Labs 6 (-68,12) and 7 (-64,12) chained east off lab B by (-69,13) and (-65,13) | `client/labs67_run.py`. Proven |
| `labs45` | -65,22 .. -58,26 | Lab 4 (-64,22) fed from lab 1 by (-65,23); lab 5 (-60,24) fed from lab 4 by (-61,24). Lab-to-lab inserters pass red + green | `client/labs_run.py`. Proven 30/30 |
| `green2` | -110,4 .. -71,41 | Green Block 2: Green Block 1 mirrored by (-37,-16). Iron from the iron chest's west side (-92,41) up x=-94 (underground under the player's steelworks furnace and coal belt); copper from the copper chest's north side (-78,9) west on row 5, down x=-94. Flasks north, east on row 4, down x=-71 into lab B; (-73,12) passes them lab B -> lab A | `client/green2_run.py`. Proven (first prove failed on copper start-up lag) |
| `acA` | 30,10 | Stone furnace left by the acceptance tester | Ignore |

- **Inventory:** all 10 red flasks are in the lab; I hold 39 small poles, 50 coal, 60 iron and 14 copper plates.
- **Research:** green flasks flow into lab 1 only; the keeper now picks red+green techs (Automation 2 first). Every useful red-only tech is done (the keeper also wasted some on gun turret/military/stone wall before the combat filter); the rest need green.  Automation and Logistics are researched. `client/research_keeper.py` runs in the background (log `/tmp/research_keeper.log`) and queues the next red-only tech whenever research is idle. Restart it on resume.
- **Resources:**
  - iron around (-80,40);
  - copper around (-80,0);
  - coal around (-120,30);
  - stone around (-90,60);
  - water: the lake around (40..80, -20..20);
  - trees: north-east around (80,-40).

## Next steps
1. Task 15 is done (2026-10-04): the lab and the power block both pass `prove`.
2. Task 16 is done (2026-10-04), and red science is scaled to 3 assemblers + 3 labs (player asked). `prove` OK sets now also accept an inserter waiting for space and an assembler with full output; **record both in SPEC AC-23 (reopen spec) before code review**.
   - Bottlenecks next: iron/copper smelting (2 burner drills each) and boiler coal.
3. Boiler coal is solved by the player's coal line. Next work is in `docs/PLAN-next.md`: green science, then electric copper.
4. **Then:** code review (Codex + Sonnet) and acceptance for phase 2, as `crosscheck-build` describes.

## Throughput (2026-10-04)
- Green: both green-flask assemblers are assembler 2 (8 s/flask): ~15/min max. Red: 3 assembler-1 lines, ~18/min max.
- Steel comes from the player's steelworks (stone furnace at -94,32); don't build our own. I hold 8 steel and 639 belts (the player crafted them).
- Build queue (player, 2026-10-04): 1) finish steel furnaces on the iron columns (`client/iron_steel_run.py`, reruns as steel arrives), 2) copper expansion: 2 more copper drills + furnaces (PM: ~45 copper/min needed vs 60 capacity). Copper chest has no free side; route the new copper so it doesn't mix into the gear lane of the red copper/gear belt.
- Next: blue science is "down the line" (player). Research order is set in research_keeper.py; nearest crude oil ~(159,319).

## Background helpers (restart on resume)
- `client/research_keeper.py` (log `/tmp/research_keeper.log`): queues the next research when idle.
- Chat voices are factory-themed (the player wants a game, not a coding project): [Maintenance Crew] = watchdog.py, [Lab Director] = research_keeper.py, [Foreman] = a build script starting/finishing (job names in `play.JOBS`), [QA Inspector] = qa_inspector.py (every 20-40 min one picky remark from live data; log `/tmp/qa_inspector.log`), [Production Manager] = production_manager.py (every 10 min: stats + one suggestion; log `/tmp/production_manager.log`).
- `client/watchdog.py` (log `/tmp/watchdog.log`): once a minute, reports any tag machine stuck 5 checks running, and power above 90%. Watch it with a Monitor on `tail -F /tmp/watchdog.log | grep --line-buffered "Maintenance Crew"`.

## Known issues
- The old iron smelter's west electric drill (-95..-93, 37..39; the player upgraded it) also mines coal; the coal fills its furnace's fuel slot and jams it. I took 45 coal out on 2026-10-04; it will re-jam. Move or remove that drill.
- All 5 labs get green (labs A/B from Green Block 2, labs 1/4/5 from Green Block 1).

## Gotchas learned the hard way
- **One basic inserter moves at most ~50 items/min.** Everything elec-iron makes enters the iron chest through (-91,42); as a basic inserter it capped the chest at ~50 iron/min no matter how many furnaces. Now a fast inserter (~138/min). Check every single-inserter handoff when adding capacity.
- **An upgraded inserter can come back reversed.** The copper smelter's furnace->chest inserters were replaced facing the wrong way: they pulled plates out of the chest and tried to put them into the furnaces, so copper production was 0 while the chest drained (found and fixed 2026-10-04 by rotating both). A reversed inserter looks like a healthy 'waiting' one; the Maintenance Crew now compares every inserter's drop side with its stamp.
- **Drills mine everything under their 5x5 area.** Stone or coal at the edge of an ore patch ends up in the furnace (bricks on the iron belt, coal jamming the fuel slot). Check the drill's whole mining area, not just its 3x3 footprint.
- **Trigger techs** (craft-item, build-entity, mine-entity) only count real players. The mod now credits Claude's own crafts, builds and mines (`credit()` in `control.lua`). `automation-science-pack` was flipped by script after Claude's lab craft.
- **`can_place_entity`** without `build_check_type = manual` says yes to an offshore pump on dry land.
- **Steam engines** are axis-only: the engine reports a south-facing engine as north.
- **Errors in an `on_tick` handler** kill the hosted game. Keep handlers `pcall`-wrapped.
- **`research` refuses** trigger techs and techs with missing prerequisites. Don't switch away from Automation by accident.
