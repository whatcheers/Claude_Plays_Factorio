# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

No code yet. This folder is for a planned project: Claude playing Factorio. Update this file with build/run/test commands and architecture once code lands.

## Environment (verified 2026-10-04)

- Factorio 2.0.77, Steam build, vanilla (no `mods/` folder).
  - Executable: `C:\Program Files (x86)\Steam\steamapps\common\Factorio\bin\x64\factorio.exe`
  - User data: `%APPDATA%\Factorio` (`config\config.ini`, `saves\`, `factorio-current.log`)
- RCON is not configured: `local-rcon-socket` / `local-rcon-password` in `config.ini` are commented out.
- This folder is not its own git repo. `git` here resolves to a repo rooted at the user's home directory, so run `git init` here before committing anything.

## Intended approach (discussed, not built)

- Talk to the game over RCON, using `/silent-command` Lua for state queries and actions. Pause with `game.tick_paused` for turn-based play (same model as the user's pz-bot project for Project Zomboid).
- Go through a "fair play" tool layer (walk, mine, craft, place, insert/take) that enforces reach, inventory, and crafting time, rather than raw god-mode `surface.create_entity`.
- Lua commands permanently disable achievements on a save. Use a fresh map and never touch the user's existing saves in `%APPDATA%\Factorio\saves`.
