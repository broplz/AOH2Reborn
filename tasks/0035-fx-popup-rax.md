---
id: 0035
title: core/fx migration — lib/popup create_popup and rax_behavior ping release their particles
status: ready
epic: p4
prefix: p4
kind: code
size: S
role: developer-hard
base: feat/p0-foundation
branch: task/0035-fx-popup-rax
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/lib/popup.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/other/rax_behavior.lua
checks: lua
tests: [fx]
needs_approval: true
returns: 0
sessions: 0
blocked_reason: 
---

## Goal
Backlog-0018 follow-up (audit §Производительность). `create_popup` (lib/popup.lua, called on every
damage/heal popup by many abilities and modifiers) creates a particle and never releases it — one
leaked handle per popup. Same for the rax ping in rax_behavior.lua. Replace both with `fx.once`
from `core/fx.lua`. No behaviour change: same particle, attach, owner, control points; the
`create_popup(data)` signature and its global name stay as they are.

## Definition of Done
1. `grep -c "ParticleManager:" game/dota_addons/attackcopy/scripts/vscripts/lib/popup.lua` prints `0`.
2. `grep -c "ParticleManager:" game/dota_addons/attackcopy/scripts/vscripts/abilities/other/rax_behavior.lua` prints `0`.
3. `grep -c "require(\"core/fx\")" <each of the 2 allowed files>` prints `1` for each.
4. `grep -n "^function create_popup(data)" game/dota_addons/attackcopy/scripts/vscripts/lib/popup.lua` prints one line.
5. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
6. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
7. `python3 scripts/agents/aoh_lint.py 0035` passes.
8. `git diff --stat feat/p0-foundation` lists only the 2 allowed files plus this task file.
9. [human] In a local lobby: damage/heal popup numbers (e.g. the Flames or Transfusion skill) still
   appear with the same colour and size; the barracks ping waypoint still shows. No Lua errors.

## Notes from teamlead
Sites (verified 2026-10-30):
- lib/popup.lua:35-40 `local particle` = `"particles/msg_fx/msg_" .. type .. ".vpcf"`, PATTACH_ROOTBONE_FOLLOW,
  target; CP0 = offset, CP1 = Vector(pre, value, pos) (pre/pos may be nil — pass the same Vector call),
  CP2 = Vector(duration, size, 0), CP3 = color. Becomes one `fx.once(particle_path, PATTACH_ROOTBONE_FOLLOW, target, { [0] = offset, [1] = ..., [2] = ..., [3] = color })`.
- abilities/other/rax_behavior.lua:39-46 `local fx` = `particles/ui_mouseactions/ping_waypoint.vpcf`,
  PATTACH_WORLDORIGIN, self.owner; CP0 = self.target (a Vector, set at :34/:38), CP5 = Vector(3, 0, 0),
  CP7 = Vector(10, 255, 10). The legacy local `fx` shadows the module: it must disappear.

Rules:
- `local fx = require("core/fx")` once near the top of each file (popup.lua: after the header comment,
  before `function create_popup`). API: `fx.once(name, attach, owner, controls)`, controls `{ [cp] = Vector }`.
- role developer-hard: popup.lua is required by many abilities (`require("lib/popup")`); a load error
  there breaks every one of them. Keep the global `create_popup` (callers use it as a global) — the
  rename to a module is a separate task.
- Out of scope: the `type` local shadowing Lua's `type` builtin in popup.lua (rename only if luacheck
  demands it), globals, sounds.

## Handoff

## Result

## Review

## QA
