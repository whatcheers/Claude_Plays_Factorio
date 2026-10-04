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
  - `client/play.py` raises `ChatInterrupt` (exit 3) at the next step when they speak. Answer, then rerun the script; scripts are resumable.
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
| `acA` | 30,10 | Stone furnace left by the acceptance tester | Ignore |

- **Inventory:** all 10 red flasks are in the lab; I hold 39 small poles, 50 coal, 60 iron and 14 copper plates.
- **Research:** Automation is researched (2026-10-04). Nothing else can run until flasks are automated (task 16).
- **Resources:**
  - iron around (-80,40);
  - copper around (-80,0);
  - coal around (-120,30);
  - stone around (-90,60);
  - water: the lake around (40..80, -20..20);
  - trees: north-east around (80,-40).

## Next steps
1. Task 15 is done (2026-10-04): the lab and the power block both pass `prove`.
2. **Task 16** (`client/science_run.py`, not written yet), after Automation is researched:
   - assemblers: iron plates → gear assembler (`@g iron-gear-wheel`) → red-flask assembler (`@r automation-science-pack`, copper fed in) → inserters → labs;
   - electric inserters; plates by belt or inserter from the smelter chests; poles from the lab's pole;
   - queue the next research (`fx.py research ...`).
3. **The boiler needs a steady coal supply.** For now I refill its chest; a coal drill line comes later.
4. **Then:** code review (Codex + Sonnet) and acceptance for phase 2, as `crosscheck-build` describes.

## Gotchas learned the hard way
- **Trigger techs** (craft-item, build-entity, mine-entity) only count real players. The mod now credits Claude's own crafts, builds and mines (`credit()` in `control.lua`). `automation-science-pack` was flipped by script after Claude's lab craft.
- **`can_place_entity`** without `build_check_type = manual` says yes to an offshore pump on dry land.
- **Steam engines** are axis-only: the engine reports a south-facing engine as north.
- **Errors in an `on_tick` handler** kill the hosted game. Keep handlers `pcall`-wrapped.
- **`research` refuses** trigger techs and techs with missing prerequisites. Don't switch away from Automation by accident.
