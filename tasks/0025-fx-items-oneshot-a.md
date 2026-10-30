---
id: 0025
title: core/fx migration, items batch A — one-shot particles in blast staff, plain ring (+perma), blink, dynamo core
status: ready
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
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
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

## Review

## QA
