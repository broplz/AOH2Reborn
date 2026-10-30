---
id: 0039
title: dark_seer_custom_ion_shell damage_flags 0 → DOTA_DAMAGE_FLAG_NONE (0011 leftover)
status: ready
epic: p1
prefix: p1
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0039-dark-seer-flag-enum
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/dark_seer_custom_ion_shell.lua
checks: lua
tests: []
needs_approval: false
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
---

## Goal
Leftover of task 0011 (aoh-rules 4, audit §Legacy 8; "Found by agents" line from 0011): the ion
shell damage table sets `damage_flags = 0`, a magic number. Use the enum `DOTA_DAMAGE_FLAG_NONE`
(value 0), so the 0011 DoD-1 grep has no remaining hit. Behaviour-identical.

## Definition of Done
1. `grep -n "damage_flags = 0" game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/dark_seer_custom_ion_shell.lua` is empty.
2. `grep -c "damage_flags = DOTA_DAMAGE_FLAG_NONE" game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/dark_seer_custom_ion_shell.lua` prints `1`.
3. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
4. `python3 scripts/agents/aoh_lint.py 0039` passes (exit 0).
5. `git diff --stat feat/p0-foundation` lists only the allowed file plus this task file, 1 line changed in the Lua file.

## Notes from teamlead
- Site (verified 2026-10-30): `dark_seer_custom_ion_shell.lua:54`
  `self.damage_table.damage_flags = 0` → `self.damage_table.damage_flags = DOTA_DAMAGE_FLAG_NONE`.
  (The backlog line says :62; the file was reformatted since — trust :54.)
- `DOTA_DAMAGE_FLAG_NONE` is a known engine global (.luacheckrc read_globals); it is already used in
  abilities/bosses/boss_lone_druid_spirit_bear.lua:119.
- One-line change only. Nothing else in the file (fx calls, sounds, interval) is in scope.

## Handoff

## Result

## Review

## QA
