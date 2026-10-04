# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Resuming? Read `docs/STATE.md` first.** It has the live game state, what is built where, the plan, and how to work with the player.

## What this is
This project lets Claude play vanilla Factorio 2.0.77 through its **own second character**, over RCON, under fair-play rules:
- it has reach limits;
- it uses real mining and crafting time;
- every entity is built from an item in its inventory.

The core problem it solves is placing belts and inserters by coordinate without seeing the screen. Layouts are drafted as ghosts and checked three ways before anything is built:
- a text map read back from the engine;
- a screenshot;
- lint.

The spec and audit trail live in `.build/`, from the crosscheck-build pipeline. **Read `docs/conventions.md` before touching coordinates or directions.** It holds measured facts, e.g. an inserter's direction is its *pickup* side, and 2.0 uses a 16-way direction enum.

## Setup (once)
1. **Link the mod:** `New-Item -ItemType Junction -Path "$env:APPDATA\Factorio\mods\claude-bridge" -Target "<repo>\bridge"`. Restart Factorio and make sure **Claude Bridge** is enabled under Mods.
2. **Set the RCON settings:** in the main menu, Ctrl+Alt-click **Settings**, open **The rest**, and set `local-rcon-socket=127.0.0.1:27015` and `local-rcon-password=<pw>`.
3. **Host a map:** Multiplayer → Host new game, on a fresh map in peaceful mode. RCON only runs on a hosted game.
4. **Give the client the password:** put it in env `FACTORIO_RCON_PASSWORD` or in `.rcon_password` (gitignored) at the repo root.

Factorio re-reads `bridge/control.lua` every time a map loads, so after editing it, re-host or reload instead of restarting the game. An uncaught error in the mod's event handlers kills the hosted game, so tick and path handlers must stay wrapped in `pcall`.

## Commands
All commands are `python client/fx.py <command>`. Exit code 0 means success.

| Command | What it does |
|---|---|
| `status` | Bridge version, tick, paused state, Claude's character position |
| `spawn` | Create Claude's character next to the first player, once. Its only free items are the freeplay starting kit |
| `look X1 Y1 X2 Y2` | Text map in stamp notation with x/y rulers. Inserters are drawn from the engine's `drop_position`. Marks look-coverage for any tag inside the area |
| `plan STAMP X Y ROT [--tag T]` | Place a stamp as ghosts only; ROT is 0/90/180/270 clockwise. Prints `tag:` and each ghost's engine tile vs. what the stamp expects |
| `unplan T` | Remove exactly that tag's ghosts |
| `lint T` | Rule findings for the tag: inserter, dead-end, intent, belt-end, sideload, power, placement, drill, underground |
| `shot X Y ZOOM [--w --h]` | Screenshot into `%APPDATA%\Factorio\script-output\claude\` and print the path; works while paused. View it with Read |
| `build T` | Refuses unless lint, look and shot have all seen the current area since `plan`, and re-lints a fresh scan right before building. Then walks to each ghost and builds it from inventory, reporting `missing` and `unreachable` |
| `walk X Y [--radius R]` | Pathfind and walk there |
| `mine X Y [N]` | Mine a resource or entity within reach, N times |
| `upgrade X Y NAME` | Fast-replace the built entity at tile X,Y with NAME from Claude's inventory (within reach); keeps the recipe, the old one goes back to the inventory |
| `retire T X Y` | Mine a built entity of tag T at tile X,Y on purpose (a layout change); `prove` skips it from then on |
| `craft ITEM N` | Hand-craft from Claude's own ingredients |
| `put X Y ITEM N` / `take X Y ITEM N` | Move items between Claude's inventory and an entity within reach |
| `inv` | List Claude's inventory |
| `poles X1 Y1 X2 Y2 [--tag T] [--skip-ends]` | Plan small-pole ghosts along an L path (x first, then y), at most 7 tiles apart (`--skip-ends` when both ends are existing poles); then look/shot/lint/build as usual |
| `research NAME` / `tech` | Set the current research (refuses trigger techs and missing prerequisites) / show current research, progress and available techs |
| `recipe X Y RECIPE` | Set a built assembler's recipe (within reach). Ghosts get recipes from stamp keys: `@g iron-gear-wheel` then `Ag` tiles |
| `say TEXT...` | Post in game chat as **[Claude]**, with a speech bubble over Claude's character |
| `chat [--after N]` | Print players' chat messages with id > N |
| `prove T N` | Run N ticks sampling statuses every 60; exit 0 only if every machine is OK in at least half the samples and fed containers end non-empty |

The workflow is always: `plan` → `look` + `shot` + `lint` → `build` → `put` fuel/inputs → `prove`. Commands that need game time unpause the game and restore the previous paused state afterwards.

### Stamps
Stamps live in `stamps/*.txt`. Each tile is 2 characters: an entity code plus a direction char (`^ > v <`, or `.` for none). For inserters the direction char is the **drop side**. Multi-tile entities repeat their code over the whole footprint. The full code table is in `.build/SPEC.md` under "Stamp format".

## Chat with the player
Players type in normal game chat; the mod queues every line (`on_console_chat`). Run `python client/chatwatch.py` under Monitor: it prints one `[chat] name: text` line per new message, remembers its place in `.chat_seq`, and reconnects after a re-host. Answer with `fx.py say`.

## Tests
- `python -m pytest -q tests`: offline (stamps, rotation, renderer, lint). Run a single test with `python -m pytest -q tests/test_lint.py::test_sideload_flagged_unless_s`.
- `python -m pytest -q live_tests/<file>.py`: needs the hosted game. These tests place ghosts, and `test_actions.py` really mines, crafts and builds.
- `python client/e2e_burner_iron.py`: the full fair-play run. It gathers, bootstrap-smelts, crafts, builds `stamps/burner-iron.txt` on iron ore, fuels it, and proves it. It can resume from a built `e2e` tag.

## Architecture
- **`bridge/control.lua`** (mod `claude-bridge`): thin and deliberately logic-free.
  - Exposes `remote.call("claude", fn, json)` → JSON.
  - `scan` describes entities, ghosts, resources and water in an area.
  - `plan`/`unplan`/`tag` own the ghosts for each tag in `storage.tags`.
  - Instant actions: `put`/`take`/`revive`.
  - Timed jobs (`walk`/`mine`/`craft`) advance in `on_tick`. Python polls `job`.
- **`client/`**: all the logic, so it can be tested offline.
  - `layout.py`: stamp parse, rotate and place.
  - `render.py`: the text map.
  - `lint.py`: the rules. It runs on a `scan` snapshot; ghosts and built entities both count.
  - `fx.py`: the CLI and the build gate. The gate state is in `.fx_state.json` (gitignored). Each check stores a fingerprint of the tag's bbox + 4 tiles, and `build` rescans and compares.
  - `bridge.py` / `rcon.py`: transport.
- **`tests/fakeworld.py`**: builds synthetic `scan` snapshots from stamps using the measured inserter offsets. Lint and render tests use it.
