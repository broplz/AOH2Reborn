---
id: 0026
title: core/fx migration, items batch B — one-shot particles in stat change, glare edge, warrior's seal, dev tools
status: done
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0026-fx-items-oneshot-b
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/items/custom_stat_change.lua
  - game/dota_addons/attackcopy/scripts/vscripts/items/glare_edge.lua
  - game/dota_addons/attackcopy/scripts/vscripts/items/item_warriors_seal.lua
  - game/dota_addons/attackcopy/scripts/vscripts/items/dev_tools.lua
checks: lua
tests: [fx]
needs_approval: true
returns: 1
sessions: 1
blocked_reason: 
reviewed_sha: 754b8e0e6565733af9aa23076374a30827ed6504
qa_sha: 754b8e0e6565733af9aa23076374a30827ed6504
---

## Goal
Second batch of the backlog-0018 follow-up (audit §Производительность: unreleased CreateParticle
leaks). Replace the 8 unreleased fire-and-forget `ParticleManager:CreateParticle` calls in these 4
item files with `core/fx.lua` (0018). No behaviour change: same particle, attach, owner, controls.

## Definition of Done
1. `grep -c "ParticleManager:CreateParticle" <each of the 4 allowed files>` prints `0` for every file.
2. `grep -c "require(\"core/fx\")" <each of the 4 allowed files>` prints `1` for every file.
3. `grep -n "^fx *=" <each of the 4 allowed files>` is empty (the module is a `local`).
4. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
5. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
6. `python3 scripts/agents/aoh_lint.py 0026` passes.
7. `git diff --stat feat/p0-foundation` lists only the 4 allowed files plus this task file.
8. [human] In a local lobby: Stat Change (all 3 attribute targets), Glare Edge proc, Warrior's Seal
   stack impact + shield end, dev-tool manafill/damage25 each still show their effect.

## Notes from teamlead
Sites (verified 2026-10-30; none is destroyed or stored past the function):
- custom_stat_change.lua:10, :26, :42 — `local fx2 = CreateParticle(..., PATTACH_ABSORIGIN_FOLLOW, caster)`
  + SetParticleControlEnt (ti6/ti8/ti7 levelup flash).
- glare_edge.lua:110 — `local fx = CreateParticle("particles/custom/glare_edge.vpcf", PATTACH_POINT_FOLLOW, target)`
  + SetParticleControlEnt(cp0, target, PATTACH_POINT, "attach_hitloc", target:GetAbsOrigin(), true).
  The local `fx` shadows the module: rename/drop it.
- item_warriors_seal.lua:91 (shell impact), :112 (shield end) — unassigned.
- dev_tools.lua:3, :24 — unassigned dagon particle; the file defines datadriven RunScript globals
  (`manafill`, `damage25`) — leave those globals as they are; only add `local fx = require("core/fx")`.

Rules:
- `local fx = require("core/fx")` once at the top of each file (pattern: modifier_boss.lua:39).
  API: `fx.once(name, attach, owner, controls)`; `controls` = `{ [cp] = Vector }` or
  `{ [cp] = { ent = unit, attach = PATTACH_*, point = "attach_x" } }`.
- fx's ent control always passes `ent:GetAbsOrigin()` and `true`. If a site's SetParticleControlEnt
  uses another origin or `false`, do NOT use the controls table: `local idx = fx.attach(...)`, keep
  the original SetParticleControlEnt call, then `ParticleManager:ReleaseParticleIndex(idx)`.
- custom_stat_change's 3 branches differ only in particle name; a name-per-attribute table + one
  `fx.once` is allowed (ADR "no dupes") if it stays behaviour-identical; nothing else in the file.
- Out of scope: KV numbers, globals, sounds, timers, any other item.

## Handoff

## Result
Round 2: dev_tools reduced to the minimal change (review item 1): helper and constant dropped; each of manafill/damage25 now uses `fx.attach` + the original SetParticleControlEnt(…, false) and SetParticleControl + `ReleaseParticleIndex`; `function` lines untouched. Verified: check.sh lua OK; aoh_lint 0026: 0 fail, 0 warn (run after commit). Item 2: waiver note removed, none needed.

Round 1: all 8 CreateParticle sites in the 4 files now go through core/fx (`local fx = require("core/fx")`).
- custom_stat_change: name/attribute table + one `fx.once`; behaviour identical (unknown ability name still gives attribute 0, no fx).
- glare_edge, item_warriors_seal: `fx.once` (seal sites have no controls).
- dev_tools: the dagon SetParticleControlEnt used origin-arg `false`, so per the notes it is `fx.attach` + original SetParticleControlEnt + ReleaseParticleIndex. `manafill`/`damage25` stay global.
Verified: grep CreateParticle = 0 in all 4; check.sh lua OK; test.sh fx OK (6 passed).
Playtest [human]: Stat Change str/agi/int flash, Glare Edge proc, Warrior's Seal impact + shield end, dev-tool manafill/damage25 dagon beam.

## Review
APPROVE
1. Round-1 item 1 is fixed. dev_tools.lua:4 and :25 use `fx.attach` and keep the original
   SetParticleControlEnt(…, false) and SetParticleControl(cp2). `ReleaseParticleIndex` is added at
   :16 and :37. The `function manafill`/`function damage25` lines are now unchanged context, and
   aoh_lint reports 0 fail and 0 warn (exit 3 only because the task has [human] items and
   needs_approval).
2. Round-1 item 2 is fixed. The waiver note is gone from ## Result.

Checklist notes:
- Spec: all 8 sites are migrated. custom_stat_change uses the table plus one `fx.once` and behaves
  the same. glare_edge's ent control (origin, `true`) matches fx. warriors_seal uses `fx.once` with
  no controls. dev_tools uses attach + original Ent(false) + Release. Nothing beyond the notes.
- Scope: only the 4 allowed files and the task file. No tests touched.
- Conventions: one `local fx = require("core/fx")` per file. No new globals (manafill and damage25
  were already globals and are kept, as the notes say). No KV changes.
- Correctness: every particle is released (fx.once / explicit Release). No timers or events changed.
- KV/localization: n/a.
- Verification: the Result claims (grep, check.sh lua, test.sh fx, lint) match the diff and my lint
  run. qa re-runs check/test. [human] item 8 is listed, not claimed.
- Hygiene: no prints, TODOs or secrets. English.

---
REQUEST_CHANGES
1. items/dev_tools.lua:22 — DoD 6 fails (`aoh_lint: global function manafill`), and the cause is
   your change, not the task. aoh_lint only checks *added* lines (aoh_lint.py:72-83); the original
   `function manafill(keys)` / `function damage25(keys)` lines were untouched context until the new
   `dagon_effect` helper moved them, so git now reports `function manafill` as an added line. The
   notes for dev_tools say "only add `local fx = require("core/fx")`". The helper and the
   `DAGON_INTENSITY` constant (lines 3-20) go beyond that. Fix: drop the helper. Then in each of the
   two functions, change only the create line to
   `local dagon_particle = fx.attach("particles/items_fx/dagon.vpcf", PATTACH_ABSORIGIN_FOLLOW, keys.caster)`,
   keep the existing SetParticleControlEnt(…, false) and SetParticleControl(cp2) calls, and add
   `ParticleManager:ReleaseParticleIndex(dagon_particle)` after them. Leave the `function` lines
   byte-identical so they stay context. Re-run aoh_lint and confirm 0 fail. If lint still flags a
   global, record that in ## Result; do not claim a waiver.
2. tasks/0026 ## Result:74 — after the fix, remove the "owner or teamlead must waive it" open item.
   No waiver is needed.

Checklist notes:
- Spec: custom_stat_change uses the allowed table plus one `fx.once`. It behaves the same: an unknown
  name gives attribute 0 and no fx, and ent control with origin and `true` matches fx.lua:12.
  glare_edge: origin and `true` match, so `fx.once` with controls is correct, and the shadowing
  `local fx` is gone. warriors_seal: both sites use `fx.once` with no controls, which is correct.
  dev_tools: the effect is correct (attach + kept Ent(false) + Release), but the refactor is out of
  scope (item 1).
- Scope: only the 4 allowed files changed. No tests touched.
- Conventions: `local fx` in every file, and no new globals other than the moved
  manafill/damage25 (item 1). No KV changes.
- Correctness: every particle is now released. `fx.attach` + `ReleaseParticleIndex` is correct in
  dev_tools. No timers or events changed.
- KV/localization: n/a.
- Verification: the grep/check/test claims are consistent with the diff. qa re-runs them.
  [human] item 8 is listed for the owner, not claimed.
- Hygiene: no prints, TODOs or secrets.

## QA
PASS
1. DoD 1: CreateParticle count is 0 in all 4 files.
2. DoD 2: `require("core/fx")` count is 1 in every file.
3. DoD 3: `grep "^fx *="` returns nothing.
4. DoD 4: check.sh lua prints `CHECK RESULT: OK` (log logs/check-20261030-172716.log).
5. DoD 5: test.sh fx prints `TEST RESULT: OK` (6 passed).
6. DoD 6: aoh_lint 0026 reports 0 fail, 0 warn. It exits 3 only because the task has [human] items and needs_approval.
7. DoD 7: the diff stat lists only the 4 allowed files and the task file.

For the human:
- In a local lobby, check Stat Change on str, agi and int. Each should flash its level-up particle.
- Check that a Glare Edge proc shows its particle on the target.
- Check Warrior's Seal: the impact particle on stack impact and the particle when the shield ends.
- Check that dev-tool manafill and damage25 each show the dagon beam.
