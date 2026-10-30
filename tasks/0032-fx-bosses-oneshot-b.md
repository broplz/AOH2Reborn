---
id: 0032
title: core/fx migration, bosses batch B — one-shot arc particles with entity controls in abyssal underlord cleave
status: ready
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0032-fx-bosses-oneshot-b
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_abyssal_underlord_cleave.lua
checks: lua
tests: [fx]
needs_approval: true
returns: 0
sessions: 0
blocked_reason: 
---

## Goal
Bosses batch B of the backlog-0018 follow-up: the Underlord cleave modifier creates 3 bolt/arc
particles per proc and never releases them (handle leak per attack). Replace them with `fx.once`
from `core/fx.lua`. No behaviour change: same particle, attach type, owner, control points.

## Definition of Done
1. `grep -c "ParticleManager:CreateParticle" boss_abyssal_underlord_cleave.lua` prints `0`.
2. `grep -c "ParticleManager:SetParticleControl" boss_abyssal_underlord_cleave.lua` prints `0`.
3. `grep -c "require(\"core/fx\")" boss_abyssal_underlord_cleave.lua` prints `1`; `grep -n "local fx = ParticleManager"` and `grep -n "^fx *="` are empty.
4. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
5. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
6. `python3 scripts/agents/aoh_lint.py 0032` passes.
7. `git diff --stat feat/p0-foundation` lists only the allowed file plus this task file.
8. [human] In a local lobby against the Abyssal Underlord boss: the fade bolt from the attacked unit to
   cleaved enemies shows, and the arc lightning jumps (to a random point when one enemy is near, to each
   other enemy otherwise). No Lua errors in the console.

## Notes from teamlead
Sites (verified 2026-10-30; all three are named `local fx`, which shadows the module → they disappear):
- :79 `rubick_fade_bolt.vpcf`, PATTACH_POINT, owner `target`; CP0 ent target, CP1 ent enemy.
- :120 `particles/custom/underlord_arc_lightning_.vpcf`, PATTACH_POINT, owner `enemy`; CP0 ent enemy,
  CP1 = `pos` (Vector, :118-119).
- :138 same particle, PATTACH_POINT, owner `enemy`; CP0 ent enemy, CP1 ent next_enemy.
Every SetParticleControlEnt here is `(idx, cp, ent, PATTACH_POINT_FOLLOW, "attach_hitloc", ent:GetAbsOrigin(), true)`,
which is exactly what fx.apply does (core/fx.lua:12), so all controls go into the table.

Rules:
- `local fx = require("core/fx")` once at the top (pattern: modifier_boss.lua:39).
- Ent controls use NAMED keys: `{ [0] = { ent = target, attach = PATTACH_POINT_FOLLOW, point = "attach_hitloc" }, [1] = ... }`
  (core/fx.lua:8-12 reads `v.ent`, `v.attach`, `v.point`; a positional table is silently ignored).
- Vector CP: `[1] = pos`.
- Out of scope: Timers, FindUnitsInRadius, damage, sounds, KV numbers, the modifier's other code.

## Handoff

## Result

## Review

## QA
