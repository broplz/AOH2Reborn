---
id: 0036
title: core/fx migration, bosses batch D — soul release, thundercall, arctic field, underlord certain death, beastmaster hawk
status: ready
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0036-fx-bosses-mixed
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_soul_release.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_storm_spirit_thundercall.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_arctic_field.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_abyssal_underlord_certain_death.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_beastmaster_hawk.lua
checks: lua
tests: [fx]
needs_approval: true
returns: 0
sessions: 0
blocked_reason: 
---

## Goal
Bosses batch D of the backlog-0018 follow-up (audit §Производительность). Each of these 5 files has
at least one particle that is never released (one-shots) or destroyed without ReleaseParticleIndex
(attached). Move every particle in them to `core/fx.lua` (`fx.once` / `fx.attach` + `fx.stop`).
No behaviour change: same particle, attach type, owner, control points, same destroy timing and
`immediate` flag.

## Definition of Done
1. `grep -c "ParticleManager:" <each of the 5 allowed files>` prints `0` for every file.
2. `grep -c "require(\"core/fx\")" <each of the 5 allowed files>` prints `1` for every file.
3. `grep -n "local fx = ParticleManager" <each of the 5 allowed files>` is empty.
4. `grep -c "fx.stop(" boss_abyssal_underlord_certain_death.lua` prints `2`; `grep -c "fx.stop(" boss_beastmaster_hawk.lua` prints `1`; `grep -c "fx.stop(" custom_arctic_field.lua` prints `1`.
5. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
6. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
7. `python3 scripts/agents/aoh_lint.py 0036` passes.
8. `git diff --stat feat/p0-foundation` lists only the 5 allowed files plus this task file.
9. [human] In a local lobby: Soul Release warning circles + shadowrazes, Storm Spirit Thundercall
   warning + bolts, Arctic Field pre-vortex (disappears after the delay) + nova, Underlord Certain
   Death smoke + maul overhead (both gone when the behaviour ends), Beastmaster hawk circle (gone
   when the hawk dies) + arc lightning on its target still show. No Lua errors in the console.

## Notes from teamlead
Sites (verified 2026-10-30):
- custom_soul_release.lua:23-28 `local fx` aoe_warning (already released) → `fx.once("particles/custom/aoe_warning.vpcf",
  PATTACH_WORLDORIGIN, caster, { [0] = point_loc, [1] = Vector(damage_radius, 1, 1), [2] = Vector(explosion_delay, 1, 1), [3] = Vector(200, 10, 10) })`.
  :30 `local particleIndex` = `particle` (shadowraze, :3), PATTACH_ABSORIGIN, dummy, no controls, never released → `fx.once`.
- boss_storm_spirit_thundercall.lua:30-35 `local fx` aoe_warning (released) → `fx.once`, controls CP0 point_loc,
  CP1 Vector(aoe_radius, 1, 1), CP2 Vector(delay, 1, 1), CP3 Vector(200, 10, 10).
  :38-41 `local particleIndex` = `particle`, PATTACH_WORLDORIGIN, caster; CP0 = point_loc + Vector(0, 0, 1000),
  CP1 = point_loc, CP2 = point_loc; never released → `fx.once`.
- custom_arctic_field.lua:54-56 `local preFX` = `particle_pre`, PATTACH_ABSORIGIN, pre_dummy; CP1, CP5 =
  Vector(damage_radius, 0, 0); destroyed at :60 with `false`, never released → `local preFX = fx.attach(...)`
  and `fx.stop(preFX)` at :60. :65-67 `particleFX` (released) → `fx.once`, CP3 = Vector(damage_radius, 0, 0).
- boss_abyssal_underlord_certain_death.lua:28-33 `local fx` aoe_warning (released) → `fx.once`, CP0 =
  caster:GetAbsOrigin(), CP1 = Vector(800, 1, 1), CP2 = Vector(delay, 1, 1), CP3 = Vector(200, 10, 10).
  :86-116 modifier OnCreated: `self.fx` = certain_death_smoke.vpcf, PATTACH_POINT_FOLLOW, self.parent; CP3 ent =
  self.parent. `self.fx2` = bear_maul.vpcf, PATTACH_OVERHEAD_FOLLOW, self.parent; CP0 ent = self.parent,
  CP1 ent = self.target, CP2 = Vector(duration KV, 1, 0). All ent controls PATTACH_POINT_FOLLOW,
  "attach_hitloc". → `fx.attach` for both; OnDestroy :147-148 `DestroyParticle(x, false)` → `fx.stop(self.fx)`,
  `fx.stop(self.fx2)` (adds the missing release).
- boss_beastmaster_hawk.lua:40-51 `self.fx` = follow_circle.vpcf, PATTACH_ABSORIGIN_FOLLOW, self.parent; CP0 ent =
  self.parent, PATTACH_ABSORIGIN_FOLLOW, "attach_hitloc"; CP1 = Vector(self.radius, 1, 1) → `fx.attach`;
  OnDestroy :108-109 Destroy(true)+Release → `fx.stop(self.fx, true)` (keep `true`; not fx.bind, which
  destroys non-immediately). :78-100 `local fx` = zuus_arc_lightning_.vpcf, PATTACH_POINT, self.parent;
  CP0 ent = self.parent, CP1 ent = enemy, both PATTACH_POINT_FOLLOW, "attach_hitloc"; never released → `fx.once`.

Rules:
- `local fx = require("core/fx")` once at the top of each file (after existing requires/LinkLuaModifier).
  API: `fx.once(name, attach, owner, controls)`, `fx.attach(...)` returns the index, `fx.stop(index, immediate)`.
  Entity controls use NAMED keys `{ ent = unit, attach = PATTACH_*, point = "attach_hitloc" }`;
  fx.apply uses `ent:GetAbsOrigin()` and `true`, which every ent site above already passes.
- The legacy locals named `fx` shadow the module: they must disappear (rename to nothing — use fx.once directly).
- Out of scope: globals `SoulReleaseOuter`/`b`/`x`/`y` in soul release and other datadriven entry points,
  sounds, timers, KV, the boss cast queue.

## Handoff

## Result

## Review

## QA
