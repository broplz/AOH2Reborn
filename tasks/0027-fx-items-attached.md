---
id: 0027
title: core/fx migration, items batch C — attached particles in devil's seal, suicidal mask, infinite rapier
status: ready
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0027-fx-items-attached
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/items/item_devils_seal.lua
  - game/dota_addons/attackcopy/scripts/vscripts/items/item_suicidal_mask.lua
  - game/dota_addons/attackcopy/scripts/vscripts/items/item_custom_rapier.lua
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
Third batch of the backlog-0018 follow-up (audit §Производительность). These 3 item files keep
particles alive and call `DestroyParticle` without `ReleaseParticleIndex` (handle leak), plus one
unreleased one-shot. Move them to `core/fx.lua` (0018) so every path ends in destroy + release.

## Definition of Done
1. `grep -c "ParticleManager:CreateParticle" <each of the 3 allowed files>` prints `0` for every file.
2. `grep -c "ParticleManager:DestroyParticle" <each of the 3 allowed files>` prints `0` for every file
   (all go through `fx.stop` or `fx.bind`).
3. `grep -c "require(\"core/fx\")" <each of the 3 allowed files>` prints `1`; `grep -n "^fx *="` is empty.
4. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
5. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
6. `python3 scripts/agents/aoh_lint.py 0027` passes.
7. `git diff --stat feat/p0-foundation` lists only the 3 allowed files plus this task file.
8. [human] In a local lobby: Devil's Seal debuff glow appears and disappears after `delay`; Suicidal
   Mask lifesteal flash shows and the bloodbath ribbon vanishes when the debuff ends; Infinite Rapier
   shell + smoke appear on pickup and vanish when the effect modifier is removed.

## Notes from teamlead
Sites (verified 2026-10-30):
- item_devils_seal.lua:65 `local fx2 = CreateParticle(doom_infernal_blade_debuff, ABSORIGIN_FOLLOW, self.parent)`;
  destroyed at :81 inside `Timers:CreateTimer(self.delay, …)` with `DestroyParticle(fx2, false)` →
  `fx2 = fx.attach(...)` and `fx.stop(fx2, false)` in the timer. Keep the timer (no queue rework here).
- item_suicidal_mask.lua:68 lifesteal flash (unassigned, one-shot) → `fx.once`.
  :144 `self.particle = CreateParticle(bloodbath_ribbon_bigger, ABSORIGIN_FOLLOW, self.parent)`,
  destroyed at :110 in OnDestroy `DestroyParticle(self.particle, true)` → `fx.attach` + `fx.stop(self.particle, true)`.
  :144 sits inside a think/branch — if it can run more than once per modifier, stop the previous
  index before creating a new one (`fx.stop` is nil-safe); say in ## Result which case it was.
- item_custom_rapier.lua:92 shell, :103 smoke (`self.particle`, `self.particle2`, created with
  PATTACH_POINT, CP0 = ent self.parent / PATTACH_POINT_FOLLOW / "attach_hitloc" / GetAbsOrigin / true),
  destroyed at :115-116 with `true` → either `fx.bind(self, ...)` (and drop the OnDestroy destroys) or
  `fx.attach` + `fx.stop(…, true)`. Prefer `fx.bind`: the controls table matches these args exactly.

Rules:
- `local fx = require("core/fx")` once at the top (pattern: modifier_boss.lua:39). API:
  `fx.once/attach/bind(…, controls)`, `fx.stop(idx, immediate)`; controls `{ [cp] = Vector }` or
  `{ [cp] = { ent, attach, point } }` (always `ent:GetAbsOrigin()`, `true`). A site whose
  SetParticleControlEnt differs keeps its original call on the index returned by `fx.attach`.
- Do not change destroy timing or the `immediate` flag of any site.
- Out of scope: KV numbers, globals, timers other than the fx calls inside them, other items.

## Handoff

## Result

## Review

## QA
