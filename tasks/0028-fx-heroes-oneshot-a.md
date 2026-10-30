---
id: 0028
title: core/fx migration, heroes batch A — Vector-only one-shot particles in pugna, spectre, bloodseeker thirst, undying, obsidian sanity eclipse
status: ready
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0028-fx-heroes-oneshot-a
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/pugna_custom_nether_ward.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/spectre_custom_dispersion.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/bloodseeker_custom_thirst.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/undying_custom_decay.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/obsidian_destroyer_custom_sanity_eclipse.lua
checks: lua
tests: [fx]
needs_approval: true
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
---

## Goal
First heroes batch of the backlog-0018 follow-up (audit §Производительность: CreateParticle sites
that never call ReleaseParticleIndex leak a handle per cast/hit). Replace the 5 unreleased
fire-and-forget `ParticleManager:CreateParticle` calls in these 5 files with `fx.once` from
`core/fx.lua` (merged in 0018). All 5 sites set only Vector control points (no
SetParticleControlEnt). No behaviour change: same particle, attach type, owner, control points.

## Definition of Done
1. `grep -c "ParticleManager:CreateParticle" <each of the 5 allowed files>` prints `0` for every file.
2. `grep -c "require(\"core/fx\")" <each of the 5 allowed files>` prints `1` for every file.
3. `grep -n "^fx *=" <each of the 5 allowed files>` is empty (the module is a `local`).
4. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
5. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
6. `python3 scripts/agents/aoh_lint.py 0028` passes.
7. `git diff --stat feat/p0-foundation` lists only the 5 allowed files plus this task file.
8. [human] In a local lobby: Pugna Nether Ward zap, Spectre Dispersion reflect beam, Bloodseeker
   Thirst blood splash, Undying Decay tombstone, Obsidian Destroyer Sanity's Eclipse damage number
   each still show.

## Notes from teamlead
Sites (verified 2026-10-30, none stored or destroyed later):
- pugna_custom_nether_ward.lua:45 `local attack = CreateParticle(attackName, ABSORIGIN_FOLLOW, unit)`;
  :46 CP1 = `target:GetAbsOrigin()` → `fx.once(attackName, PATTACH_ABSORIGIN_FOLLOW, unit, { [1] = target:GetAbsOrigin() })`.
- spectre_custom_dispersion.lua:191 `local particle = CreateParticle(particle_name, POINT_FOLLOW, self.parent)`;
  :192-194 CP0 = vparent, CP1 = vUnit, CP2 = vparent.
- bloodseeker_custom_thirst.lua:117 unassigned, `ls_ti9_open_wounds_blood_soft.vpcf`, ABSORIGIN_FOLLOW, target, no controls.
- undying_custom_decay.lua:78 unassigned, `undying_pale_tombstone.vpcf`, ABSORIGIN_FOLLOW, target, no controls.
- obsidian_destroyer_custom_sanity_eclipse.lua:14 `local particleIndex = CreateParticle(particle_msg, OVERHEAD_FOLLOW, target)`;
  :15-17 CP1 = Vector(0, damage, 3), CP2 = Vector(lifetime, digits, 0), CP3 = Vector(160, 30, 160).

Rules:
- `local fx = require("core/fx")` once at the top of each file (pattern: modifier_boss.lua:39).
  API: `fx.once(name, attach, owner, controls)`, controls `{ [cp] = Vector }`.
- Keep the control-point values and their order semantics; drop the now-unused local.
- Out of scope: any other change in these files (KV numbers, globals, sounds, timers, other particles).

## Handoff

## Result

## Review

## QA
