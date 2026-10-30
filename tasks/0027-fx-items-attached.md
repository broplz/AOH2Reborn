---
id: 0027
title: core/fx migration, items batch C — attached particles in devil's seal, suicidal mask, infinite rapier
status: done
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
sessions: 1
blocked_reason: 
reviewed_sha: 1d1496086214f904d36e452ef1c927f2ef97d062
qa_sha: 1d1496086214f904d36e452ef1c927f2ef97d062
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
Round 1: devils_seal, suicidal_mask, custom_rapier moved to `core/fx` (`require` once each, no raw
CreateParticle/DestroyParticle left).
- devils_seal: `fx.attach` + `fx.stop(fx2, false)` in the existing timer.
- suicidal_mask: lifesteal flash → `fx.once`. The ribbon is created inside `OnIntervalThink`, i.e. it
  runs every tick (more than once per modifier), so I added `fx.stop(self.particle, true)` before each
  create (previously leaked all but the last); OnDestroy uses `fx.stop(..., true)`.
- rapier: used `fx.attach` + `fx.stop(…, true)` instead of `fx.bind`, because bind passes
  immediate=false and the task forbids changing the `true` flag.
Verified: check.sh lua OK, test.sh fx OK, aoh_lint 0 fail (NEEDS APPROVAL due to [human] item).
Playtest (DoD 8): seal glow vanishes after `delay`; mask flash/ribbon vanish when debuff ends;
rapier shell + smoke appear on pickup and vanish on removal.

## Review
APPROVE
1. Spec: all 3 files now `local fx = require("core/fx")` once, with no raw CreateParticle/DestroyParticle left
   (DoD 1-3, checked against the diff). The `immediate` flags are kept (seal `false`, mask `true`, rapier `true`).
   The seal timer is kept. Choosing `fx.attach`+`fx.stop` over `fx.bind` for the rapier is correct:
   fx.lua:46 `AddParticle(idx, false, …)` would change the destroy to non-immediate.
2. Scope: the diff touches only the 3 allowed files. No tests were touched.
3. Conventions: the only new local is `fx`. No new globals, KV numbers or LinkLuaModifier changes. Lint: 0 fail, 0 warn
   (NEEDS APPROVAL because of the [human] DoD item 8).
4. Correctness: each control table matches the original SetParticleControlEnt args (fx.lua:12 adds
   `ent:GetAbsOrigin(), true`). item_suicidal_mask.lua:143: the ribbon is created on every think, so the
   `fx.stop` before each create is the case the teamlead asked for (fx.stop is nil-safe, fx.lua:36). The lifesteal
   flash goes through `fx.once`, which releases it.
5. KV: not touched.
6. Result: the claims match the diff and lint. I did not re-run check/test; qa will. DoD 8 is listed for the owner and is not claimed as done.
7. Hygiene: clean. Existing issues outside this scope, not blocking: global `count_modifier` at
   item_suicidal_mask.lua:116, and `self.parent` used in the seal timer without an `IsNull` check.

## QA
PASS
1. DoD 1-2: grep of CreateParticle/DestroyParticle/`^fx *=` gives 0 in all 3 files.
2. DoD 3: `require("core/fx")` count is 1 in each file.
3. DoD 4-5: check.sh lua is OK (logs/check-20261030-172941.log); test.sh fx is OK (6 passed, 0 failed).
4. DoD 6: aoh_lint has 0 fail and 0 warn. It exits with NEEDS APPROVAL only because of the [human] item.
5. DoD 7: `git diff --stat feat/p0-foundation` lists only the 3 allowed files plus this task file.

For the human (DoD 8), in a local lobby:
- Devil's Seal: the debuff glow appears and disappears after `delay`.
- Suicidal Mask: the lifesteal flash shows. The bloodbath ribbon vanishes when the debuff ends and does not stack up while it is active.
- Infinite Rapier: the shell and smoke appear on pickup and vanish when the effect modifier is removed.
