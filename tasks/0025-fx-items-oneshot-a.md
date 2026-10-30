---
id: 0025
title: core/fx migration, items batch A — one-shot particles in blast staff, plain ring (+perma), blink, dynamo core
status: done
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0025-fx-items-oneshot-a
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/items/item_blast_staff.lua
  - game/dota_addons/attackcopy/scripts/vscripts/items/item_plain_ring.lua
  - game/dota_addons/attackcopy/scripts/vscripts/items/item_plain_ring_perma.lua
  - game/dota_addons/attackcopy/scripts/vscripts/items/custom_blink.lua
  - game/dota_addons/attackcopy/scripts/vscripts/items/dynamo_core.lua
checks: lua
tests: [fx]
needs_approval: true
returns: 0
sessions: 1
blocked_reason: 
reviewed_sha: db98ed819024801ad051f95d2563486a28b3c879
qa_sha: db98ed819024801ad051f95d2563486a28b3c879
---

## Goal
First batch of the backlog-0018 follow-up (audit §Производительность: CreateParticle sites that
never call ReleaseParticleIndex leak particle handles every cast/attack). Replace the 6 unreleased
fire-and-forget `ParticleManager:CreateParticle` calls in these 5 item files with `core/fx.lua`
(merged in 0018). No behaviour change: same particle, attach type, owner and control points.

## Definition of Done
1. `grep -c "ParticleManager:CreateParticle" <each of the 5 allowed files>` prints `0` for every file.
2. `grep -c "require(\"core/fx\")" <each of the 5 allowed files>` prints `1` for every file.
3. `grep -n "^fx *=" <each of the 5 allowed files>` is empty (the module is a `local`).
4. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
5. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
6. `python3 scripts/agents/aoh_lint.py 0025` passes.
7. `git diff --stat feat/p0-foundation` lists only the 5 allowed files plus this task file.
8. [human] In a local lobby: Blast Staff cast, Plain Ring invincibility proc (both ring items),
   Custom Blink (start + end flash), Dynamo Core mana-steal attack each still show their effect.

## Notes from teamlead
Sites (verified 2026-10-30, all fire-and-forget, none stored or destroyed later):
- item_blast_staff.lua:45 `particles/custom/blast_staff_explosion.vpcf`, ABSORIGIN_FOLLOW, target; CP3 = target origin.
- item_plain_ring.lua:148, item_plain_ring_perma.lua:100 (unassigned CreateParticle).
- custom_blink.lua:12 `blink_dagger_start.vpcf`, :23 `blink_dagger_end.vpcf` (unassigned).
- dynamo_core.lua:88 `particles/custom/dynamo_core.vpcf`, POINT_FOLLOW, attacker; then SetParticleControlEnt.

Rules:
- `local fx = require("core/fx")` once at the top of each file (pattern: modifier_boss.lua:39 uses
  `require("core/boss_queue")`). API: `fx.once(name, attach, owner, controls)`; `controls` =
  `{ [cp] = Vector }` or `{ [cp] = { ent = unit, attach = PATTACH_*, point = "attach_x" } }`.
- fx's ent control always passes `ent:GetAbsOrigin()` and `true`. If a site's SetParticleControlEnt
  uses another origin or `false`, do NOT use the controls table for it: `local idx = fx.attach(...)`,
  keep the original SetParticleControlEnt call, then `ParticleManager:ReleaseParticleIndex(idx)`.
- Remove the now-unused local (`particleIndex`, `fx` shadowing!). A legacy local named `fx` in
  dynamo_core.lua:87 would shadow the module — rename or drop it.
- Out of scope: any other change in these files (KV numbers, globals, sounds, timers). item_conduit.lua
  is NOT here (it has the undefined-`enemy` bug of backlog 0023).

## Handoff

## Result
Round 1: replaced the 6 unreleased `ParticleManager:CreateParticle` calls in the 5 item files with
`fx.once` (`local fx = require("core/fx")` at the top of each file). Same particle, attach type, owner
and control points. In dynamo_core.lua the legacy local `fx` is gone, so the module is not shadowed.
Its CP0 `SetParticleControlEnt` already used `GetAbsOrigin()` and `true`, so it went into the controls table.
Verified: `check.sh lua` OK, `test.sh fx` OK (6 passed), `aoh_lint.py 0025` 0 fail (exit 3 = owner approval needed),
`git diff --stat` lists only the 5 files plus this task file.
Owner playtest (DoD 8): Blast Staff cast, both Plain Ring procs, Custom Blink start and end flash, Dynamo Core
mana-steal attack. Each effect should still show.

## Review
APPROVE
1. Spec: all 6 sites replaced with `fx.once` (fx.lua:26 releases the index). Particle, attach type, owner and CPs are unchanged. Blast staff CP3 = target origin. Dynamo CP0 ent control matches fx.lua:12, which uses `GetAbsOrigin()` and `true`, as the original call did. The legacy local `fx` in dynamo_core is gone. Nothing else changed.
2. Scope: the diff touches only the 5 allowed files. No tests touched.
3. Conventions: each file has one `local fx = require("core/fx")`. No new globals. aoh_lint reports 0 fail and 0 warn (exit 3 = [human] approval only).
4. Correctness: no ParticleManager calls are left in the 5 files. Every particle is released. The existing guards are untouched.
5. KV: not touched.
6. Result claims: the diff and lint results match. I did not rerun check/test (qa does). DoD 8 is listed for the owner and not claimed.
7. Hygiene: no debug prints, TODOs or dead code were added.

## QA
PASS
1. DoD 1: CreateParticle count is 0 in all 5 files.
2. DoD 2: `require("core/fx")` count is 1 in all 5 files.
3. DoD 3: `grep "^fx *="` is empty.
4. DoD 4: `check.sh lua` prints CHECK RESULT: OK.
5. DoD 5: `test.sh fx` prints TEST RESULT: OK (6 passed).
6. DoD 6: `aoh_lint.py 0025` reports 0 fail, 0 warn. Exit 3 is only the owner-approval flag for the [human] item.
7. DoD 7: the diff stat lists only the 5 allowed files plus this task file.

For the human (DoD 8), in a local lobby:
- Cast Blast Staff and check that the explosion particle shows on the target.
- Trigger the invincibility proc of Plain Ring and of Plain Ring Perma. Each should show its effect.
- Use Custom Blink and check that both the start flash and the end flash show.
- Attack with Dynamo Core and check that the mana-steal effect shows.
