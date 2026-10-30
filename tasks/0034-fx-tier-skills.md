---
id: 0034
title: core/fx migration, modifiers/skills batch — one-shot particles in modifier_tier_5 (luck), modifier_tier_3 (flames), skill_transfusion, skill_trident
status: done
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
reviewed_sha: aad1c81704d2cafb7735e173243d2a8d3a89c4f1
qa_sha: aad1c81704d2cafb7735e173243d2a8d3a89c4f1
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
Round 1: all 8 CreateParticle sites in the 4 files now go through `fx.once`; `local fx = require("core/fx")` added to each file; legacy `fx`/`fx2` locals removed. Luck: the 3 rand branches only pick the stat modifier, one `fx.once` with a `flashes[rand]` lookup. Transfusion: one `fx.once` after the if/else, with a `controls` table that gets `[15]` set in the ally/enemy branches (aoh_lint flags assignment to a pre-declared local, hence the table field).
Verified: check.sh lua OK, test.sh fx OK (before the final lint-driven restructure, re-run below). Open [human] item 9 for the owner playtest.

## Review
APPROVE
1. Spec: all 8 sites from the teamlead notes are replaced with `fx.once`, using the same particle, attach, owner and CPs. Entity CPs use named keys; `core/fx.lua:12` passes `ent:GetAbsOrigin()` and `true`, which is what the old code passed. Transfusion follows the prescribed shape: one call after the if/else, and `[15]` is set only in the ally and enemy branches. Luck uses a `flashes[rand]` lookup, so the attach and CP0 are unchanged for every branch. No behaviour change found.
2. Scope: only the 4 allowed files changed. No tests touched. Out-of-scope items (`damageTable`, `self.target`, `print(total)`, duplicate methods) were left alone, as instructed.
3. Conventions: one `local fx = require("core/fx")` per file, and the shadowing `fx`/`fx2` locals are gone. No new globals and no new magic numbers. aoh_lint: 0 fail, 0 warn, NEEDS APPROVAL (the [human] item).
4. Dota correctness: every particle is now released through `fx.once` (`core/fx.lua:27`). No timers or event handlers added. The flames proc stays inside the handler's existing parent filter.
5. KV: none touched.
6. Verification: the [human] item 9 is listed for the owner, not claimed. Non-blocking: `## Result` (line 80) says "re-run below", but there is no re-run in the file. check.sh and test.sh on the final head are unconfirmed by the developer, so qa must run DoD 5 and 6 on this head.
7. Hygiene: no debug prints, TODOs or dead code added. Minor, non-blocking: the `flashes` table in `modifier_tier_5.lua:230` is rebuilt every round-up. It could be a file-level local, but it runs once per round, so the cost is negligible.

## QA
PASS
1. DoD 1/2/4: CreateParticle and SetParticleControl counts are 0, and the `require("core/fx")` count is 1, in all 4 files.
2. DoD 3: the legacy `fx`/`fx2` local grep is empty.
3. DoD 5: `check.sh lua` printed `CHECK RESULT: OK` (luacheck and stylua exit 0). Log: logs/check-20261030-183054.log.
4. DoD 6: `test.sh fx` printed `TEST RESULT: OK` (6 passed, 0 failed).
5. DoD 7: aoh_lint reports 0 fail, 0 warn. It exits "NEEDS APPROVAL" only because of the [human] item.
6. DoD 8: `git diff --stat feat/p0-foundation` lists only the 4 allowed files plus this task file.
7. Read skill_transfusion.lua: one `fx.once` after the if/else, with `[15]` set only in the ally and enemy branches. This matches the spec.

For the human (DoD 9, local lobby, watch the console for Lua errors):
- Luck skill round-up: the overhead clover and the str/agi/int levelup flash show.
- Flames skill: the proc shows on attack.
- Transfusion: the beam is green on an ally with lower HP%, red on an enemy, and the default colour in other cases.
- Trident: the hit effect shows, plus the crit blur on a target with `modifier_anim`.
