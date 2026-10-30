---
id: 0026
title: core/fx migration, items batch B — one-shot particles in stat change, glare edge, warrior's seal, dev tools
status: ready
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
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
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

## Review

## QA
