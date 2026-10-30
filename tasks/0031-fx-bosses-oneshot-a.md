---
id: 0031
title: core/fx migration, bosses batch A — Vector-only one-shot particles in arena warning, spirit walk warning, ghostship warning, desolation, elder titan shifting quake
status: ready
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0031-fx-bosses-oneshot-a
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_arena_warning.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_spirit_walk_warning.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_ghostship_warning.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_desolation.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_elder_titan_shifting_quake.lua
checks: lua
tests: [fx]
needs_approval: true
returns: 0
sessions: 0
blocked_reason: 
---

## Goal
First bosses batch of the backlog-0018 follow-up (audit §Производительность: CreateParticle sites
that never call ReleaseParticleIndex leak a handle per cast). Replace the 7 unreleased
fire-and-forget `ParticleManager:CreateParticle` calls in these 5 files with `fx.once` from
`core/fx.lua`. All 7 sites have only Vector control points or none. No behaviour change: same particle, attach type,
owner, control points.

## Definition of Done
1. `grep -c "ParticleManager:CreateParticle" <each of the 5 allowed files>` prints `0` for every file.
2. `grep -c "require(\"core/fx\")" <each of the 5 allowed files>` prints `1` for every file.
3. `grep -n "^fx *=" <each of the 5 allowed files>` is empty, and `grep -n "local fx = ParticleManager" custom_ghostship_warning.lua` is empty.
4. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
5. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
6. `python3 scripts/agents/aoh_lint.py 0031` passes.
7. `git diff --stat feat/p0-foundation` lists only the 5 allowed files plus this task file.
8. [human] In a local lobby: the arena boss warning glow and arena ring, the spirit-walk boss frost nova,
   the ghostship boss warning circle and Kunkka marker, the Desolation shadowrazes and the Elder Titan
   Shifting Quake stomps each still show. No Lua errors in the console.

## Notes from teamlead
Sites (verified 2026-10-30; none is stored, given controls later or destroyed):
- custom_arena_warning.lua:16 `local particle` = `sf_fire_arcana_wings_rope_glow.vpcf`, ABSORIGIN_FOLLOW, caster, no controls.
  :26-27 `local particle2` = `particles/custom/custom_arena.vpcf`, ABSORIGIN_FOLLOW, caster, no controls (inside the Timer).
- custom_spirit_walk_warning.lua:11 `local particle` = `lich_frozenchains_frostnova_g2.vpcf`, ABSORIGIN_FOLLOW, caster, no controls.
- custom_ghostship_warning.lua:63 `local fx` = `particles/custom/aoe_warning.vpcf`, PATTACH_WORLDORIGIN, dummy;
  :64-67 CP0 = `dummy:GetAbsOrigin()`, CP1 = Vector(350, 1, 1), CP2 = Vector(4, 1, 1), CP3 = Vector(200, 10, 10).
  :69 `local particleIndex1` = `kunkka_ghostship_marker.vpcf`, ABSORIGIN_FOLLOW, dummy, no controls.
  The legacy local named `fx` shadows the module: it must disappear (the module is `fx`).
- custom_desolation.lua:19 `local particleIndex` = `particle` (nevermore_shadowraze, :13), PATTACH_ABSORIGIN, dummy, no controls.
- boss_elder_titan_shifting_quake.lua:36 `local particleIndex` = `particle` (elder_titan_echo_stomp, :22), PATTACH_ABSORIGIN, dummy, no controls.

Rules:
- `local fx = require("core/fx")` once at the top of each file (after existing requires; pattern:
  modifier_boss.lua:39). API: `fx.once(name, attach, owner, controls)`, controls `{ [cp] = Vector }`.
- Keep the control-point values; drop the now-unused locals (keep `particle` name strings at
  desolation :13 / shifting quake :22, they are the names passed to fx.once).
- Releasing a one-shot does not stop the effect; dummies removed later (desolation :21,
  ghostship :74) behave as today.
- Out of scope: the duplicated `require("lib/timers")` in arena warning, globals (datadriven entry
  points `DesolationPoints`, `shifting_quake*` stay global), KV numbers, sounds, timers, BKB calls.

## Handoff

## Result

## Review

## QA
