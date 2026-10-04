# Plan: factory layout tooling

How the work is split:
- **Logic in Python, thin mod.** `bridge/` (mod `claude-bridge`) only queries the world and performs timed, reach-checked actions. Parsing, rotation, rendering, lint and the build gate are pure Python in `client/`, so they can be unit-tested offline.
- **Calls.** Python calls the mod with `/silent-command rcon.print(remote.call("claude", <fn>, <json>))`. The mod replies via `helpers.table_to_json`.
- **Ticks.** Tick-dependent actions run as jobs inside the mod's `on_tick`. `fx.py` unpauses, polls the job until it is done or times out, then restores the previous paused state.
- **Gate state.** The tag → bbox mapping and the look/shot/lint flags live in `.fx_state.json`, which is gitignored. The tag → ghost entity refs live in mod `storage`.
- **Password.** The RCON password comes from env `FACTORIO_RCON_PASSWORD`, falling back to a gitignored `.rcon_password` file, so that Verify commands run from cmd.exe can connect.
- **Tests.** Offline tests are in `tests/`. Tests that need the live game are in `live_tests/` and fail, rather than skip, when the game is unreachable.

## Task 1: Stamp parser, rotation, inserter conversion
Covers: AC-1, AC-2
Verify: python -m pytest -q tests/test_stamp.py

## Task 2: ASCII renderer and lint rules (pure)
Covers: AC-1
Verify: python -m pytest -q tests/test_render.py tests/test_lint.py

## Task 3: Mod skeleton, link into mods folder, RCON wrapper, status/spawn
Covers: AC-3
Verify: python -m pytest -q live_tests/test_status.py

## Task 4: look, plan/unplan, shot
Covers: AC-4, AC-5, AC-7
Verify: python -m pytest -q live_tests/test_look_plan_shot.py

## Task 5: Live lint and build gate (incl. sabotage test)
Covers: AC-6, AC-8
Verify: python -m pytest -q live_tests/test_lint_gate.py

## Task 6: Fair-play actions: walk, mine, craft, put, take, inv, build
Covers: AC-9, AC-10
Verify: python -m pytest -q live_tests/test_actions.py

## Task 7: prove command and end-to-end burner-iron (gather, craft, plan, check, build, fuel, prove)
Covers: AC-11, AC-12
Verify: python client/e2e_burner_iron.py

## Task 8: CLAUDE.md setup and command reference
Covers: AC-13
Verify: python -m pytest -q tests/test_docs.py

## Task 9: Non-square footprints, new codes (B E O x L), recipe keys
Covers: AC-14
Verify: python -m pytest -q tests/test_stamp2.py

## Task 10: Fluid-connection and power-network lint (pure)
Covers: AC-14
Verify: python -m pytest -q tests/test_lint2.py

## Task 11: Mod scan uses prototype tile size; reports fluid connections and pole networks
Covers: AC-15
Verify: python -m pytest -q live_tests/test_power_stamps.py

## Task 12: Live fluid and power lint incl. rotated-boiler sabotage
Covers: AC-16, AC-17
Verify: python -m pytest -q live_tests/test_power_lint.py

## Task 13: poles, research, tech, recipe commands
Covers: AC-18, AC-19
Verify: python -m pytest -q live_tests/test_cmds2.py

## Task 14: build re-lints before building; prove samples every 60 ticks
Covers: AC-22, AC-23
Verify: python -m pytest -q live_tests/test_gate2.py tests/test_prove.py

## Task 15: Steam power at the lake, pole line, powered lab researching Automation
Covers: AC-20
Verify: python client/power_run.py

## Task 16: Automated red-science line feeding labs
Covers: AC-21
Verify: python client/science_run.py

## Full offline suite
Covers: AC-1
Verify: python -m pytest -q tests
