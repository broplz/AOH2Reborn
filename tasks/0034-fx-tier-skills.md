---
id: 0034
title: core/fx migration, modifiers/skills batch — one-shot particles in modifier_tier_5 (luck), modifier_tier_3 (flames), skill_transfusion, skill_trident
status: ready
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0034-fx-tier-skills
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/modifiers/modifier_tier_5.lua
  - game/dota_addons/attackcopy/scripts/vscripts/modifiers/modifier_tier_3.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/skills/skill_transfusion.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/skills/skill_trident.lua
checks: lua
tests: [fx]
needs_approval: true
returns: 0
sessions: 0
blocked_reason: 
---

## Goal
Backlog-0018 follow-up (audit §Производительность: CreateParticle sites that never call
ReleaseParticleIndex leak a handle per cast/proc). Replace the 8 unreleased fire-and-forget
`ParticleManager:CreateParticle` calls in these 4 files with `fx.once` from `core/fx.lua`.
No behaviour change: same particle, attach type, owner, control points.

## Definition of Done
1. `grep -c "ParticleManager:CreateParticle" <each of the 4 allowed files>` prints `0` for every file.
2. `grep -c "require(\"core/fx\")" <each of the 4 allowed files>` prints `1` for every file.
3. `grep -nE "local fx2? = ParticleManager|local fx =$" <each of the 4 allowed files>` is empty.
4. `grep -c "ParticleManager:SetParticleControl" <each of the 4 allowed files>` prints `0` for every file.
5. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
6. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
7. `python3 scripts/agents/aoh_lint.py 0034` passes.
8. `git diff --stat feat/p0-foundation` lists only the 4 allowed files plus this task file.
9. [human] In a local lobby: the Luck skill round-up flash (overhead clover + str/agi/int levelup
   flash), the Flames skill proc on attack, Transfusion (green beam on an ally with lower HP%, red on
   an enemy) and the Trident hit (+ crit blur on a target with `modifier_anim`) still show.
   No Lua errors in the console.

## Notes from teamlead
Sites (verified 2026-10-30; none is stored, destroyed or given controls later, except transfusion CP15):
- modifier_tier_5.lua:225-230 `local fx` = `particles/custom/modifier_luck.vpcf`, PATTACH_OVERHEAD_FOLLOW,
  self.parent; CP1 = Vector(4, 0, 4).
  :234/:250/:266 `local fx2` = `hero_levelup_ti6/ti8/ti7_flash_hit_magic.vpcf` (one per rand branch),
  PATTACH_ABSORIGIN_FOLLOW, self.parent; CP0 ent = self.parent, PATTACH_POINT_FOLLOW, "attach_hitloc".
- modifier_tier_3.lua:174-184 `local fx` = `particles/custom/skill_flames.vpcf`, PATTACH_POINT_FOLLOW,
  self.parent; CP3 ent = damage_victim, PATTACH_POINT, "attach_hitloc".
- skill_transfusion.lua:12-34 `local fx` = terrorblade_sunder_ti8.vpcf, PATTACH_POINT_FOLLOW, caster;
  CP1 ent = caster, PATTACH_POINT, "attach_hitloc"; CP0 ent = target, PATTACH_POINT, "attach_hitloc";
  CP15 set later: Vector(0, 255, 0) at :45 (ally branch, only when target HP% < caster HP%),
  Vector(255, 0, 0) at :55 (enemy branch), unset otherwise.
  Shape: a `local color` (nil by default) assigned in those two places, and ONE `fx.once(...)` after the
  if/else with controls `{ [0] = {...target...}, [1] = {...caster...}, [15] = color }` (a nil value
  is simply not set — same as today). Same server frame, so moving the call is not a visible change.
- skill_trident.lua:71-81 `local fx` = `particles/custom/skill_trident_hit.vpcf`, PATTACH_POINT_FOLLOW,
  caster; CP0 ent = hTarget, PATTACH_POINT, "attach_hitloc".
  :86-99 `local fx` = wk_arc_weapon_style2_blur_critical.vpcf, PATTACH_POINT_FOLLOW, caster; CP0 ent =
  hTarget, PATTACH_POINT, "attach_hitloc".

Rules:
- `local fx = require("core/fx")` once at the top of each file (after existing requires/LinkLuaModifier
  lines; pattern: modifier_boss.lua). API: `fx.once(name, attach, owner, controls)`; Vector controls
  `{ [cp] = Vector }`, entity controls with NAMED keys `{ [cp] = { ent = unit, attach = PATTACH_*, point = "attach_hitloc" } }`.
  fx.apply uses `ent:GetAbsOrigin()` and `true` — every site above already passes exactly that.
- The legacy locals named `fx`/`fx2` shadow the module: they must disappear.
- Out of scope (do not fix here): global `damageTable` at skill_trident.lua:102, `self.target` at
  skill_transfusion.lua:47, the `print(total)` at :40, duplicate `modifier_skill_flames:OnDestroy`
  / `modifier_skill_trident:IsHidden` in modifier_tier_3, globals, sounds, KV.

## Handoff

## Result

## Review

## QA
