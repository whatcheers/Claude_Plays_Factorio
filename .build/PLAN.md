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

## Full offline suite
Covers: AC-1
Verify: python -m pytest -q tests
