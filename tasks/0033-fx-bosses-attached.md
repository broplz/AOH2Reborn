---
id: 0033
title: core/fx migration, bosses attached batch — destroyed-but-unreleased particles in infernal retribution, ice reflector, boss meteor, spirits
status: ready
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0033-fx-bosses-attached
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_infernal_retribution.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_ice_reflector.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_meteor_init.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_spirits.lua
checks: lua
tests: [fx]
needs_approval: true
returns: 0
sessions: 0
blocked_reason: 
---

## Goal
Bosses attached batch of the backlog-0018 follow-up: long-lived particles that are destroyed with
`DestroyParticle` but never released (handle leak per cast), plus one unreleased one-shot. Move them
to `core/fx.lua` so every path ends in destroy + release. No behaviour change: same particle,
attach, owner, controls, destroy timing and `immediate` flag.

## Definition of Done
1. `grep -c "ParticleManager:CreateParticle" <each of the 4 allowed files>` prints `0` for every file.
2. `grep -c "ParticleManager:DestroyParticle" <each of the 4 allowed files>` prints `0` for every file (all go through `fx.stop`).
3. `grep -c "require(\"core/fx\")" <each of the 4 allowed files>` prints `1`; `grep -n "^fx *="` is empty.
4. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
5. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
6. `python3 scripts/agents/aoh_lint.py 0033` passes.
7. `git diff --stat feat/p0-foundation` lists only the 4 allowed files plus this task file.
8. [human] In a local lobby: Infernal Retribution doom circle shows for `delay`, vanishes, and the
   shadowraze burst shows; the ice reflector frost armor shows on the target and vanishes when the buff
   ends; the boss meteor fire trail follows the meteor and fades when it ends; spirits show their
   effect, it grows/shrinks with the radius, and vanishes when a spirit dies. No Lua errors.

## Notes from teamlead
Sites (verified 2026-10-30):
- custom_infernal_retribution.lua:15 `local particleIndex` (doom_bringer_doom, PATTACH_ABSORIGIN, dummy,
  no controls) → `fx.attach`; destroyed :41 with `true` → `fx.stop(particleIndex, true)`.
  :19 `local particleEndIndex` (sf_fire_arcana_shadowraze, PATTACH_ABSORIGIN, dummy) is a one-shot → `fx.once`.
- custom_ice_reflector.lua:39 `target.FrostArmorParticle` (lich_frost_armor, PATTACH_OVERHEAD_FOLLOW, target)
  inside a 0.01 s Timer; CP0 = `target:GetAbsOrigin()`, CP1 = Vector(1, 0, 0), CP2 ent target with
  PATTACH_ABSORIGIN_FOLLOW / "attach_origin" (matches fx.apply). Destroyed :57 with `false`
  → `fx.stop(target.FrostArmorParticle, false)`. Keep storing the index on `target.FrostArmorParticle`.
- boss_meteor_init.lua:32-33 `self.particle` (`particles/custom/boss_meteor_fire_trail.vpcf`, PATTACH_POINT,
  parent); CP0 and CP3 ent parent / PATTACH_POINT_FOLLOW / "attach_hitloc" (matches fx.apply); destroyed
  :55 with `false` → `fx.stop(self.particle, false)`.
- custom_spirits.lua:50 `local pfx` (event.spirit_particle_name, ABSORIGIN_FOLLOW, newSpirit), stored :51
  as `newSpirit.spirit_pfx`; :94 sets CP1 on it every think — keep that call on the stored index;
  destroyed :143 with `false` → `fx.stop(spirit.spirit_pfx, false)`.

Rules:
- `local fx = require("core/fx")` once at the top (pattern: modifier_boss.lua:39). API:
  `fx.attach(name, attach, owner, controls)` → index, `fx.stop(index, immediate)`, `fx.once(...)`.
  Controls: `{ [cp] = Vector }` or `{ [cp] = { ent = unit, attach = PATTACH_*, point = "attach_x" } }`
  with NAMED keys (core/fx.lua:8-12; a positional table is silently ignored).
- Use `fx.attach` + `fx.stop`, NOT `fx.bind` (these are datadriven/Timer paths with explicit
  destroys; infernal retribution destroys with `true`). Keep each `immediate` flag exactly.
- Datadriven entry points (`infernal_retribution`, `on_death`, `ice_reflector_*`, `FrostArmorParticle`,
  `EndFrostArmorParticle`, `CastSpirits`, `ThinkSpirits`, `EndSpirits`, `OnCreatedSpirit`,
  `OnDestroySpirit`, `ExplodeSpirit`, `init`) stay global; do not touch them.
- Out of scope: `GetLevelSpecialValueFor` in infernal retribution, KV numbers, timers, sounds, other particles.

## Handoff

## Result

## Review

## QA
