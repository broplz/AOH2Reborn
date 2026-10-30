---
id: 0035
title: core/fx migration — lib/popup create_popup and rax_behavior ping release their particles
status: done
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
reviewed_sha: 3b71f54f9955253b9d7f19b52febd3c03b0b5167
qa_sha: 3b71f54f9955253b9d7f19b52febd3c03b0b5167
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
Round 1 (commit 3b71f54).
What changed
- lib/popup.lua: `local fx = require("core/fx")` after the header comment; the CreateParticle +
  4× SetParticleControl block became one `fx.once(particle_path, PATTACH_ROOTBONE_FOLLOW, target,
  { [0] = offset, [1] = Vector(pre, value, pos), [2] = Vector(duration, size, 0), [3] = color })`,
  so the index is now released. `function create_popup(data)` stays a global with the same signature.
- abilities/other/rax_behavior.lua: `local fx = require("core/fx")` at the top; the legacy local
  `fx` in OnRefresh is gone, replaced by `fx.once(ping_waypoint, PATTACH_WORLDORIGIN, self.owner,
  { [0] = self.target, [5] = Vector(3,0,0), [7] = Vector(10,255,10) })`.
- Same particles, attach types, owners and CP values. The only difference is that CPs are set in
  `pairs` order rather than 0→3; all are set before the release, so it does not matter.

Callers of create_popup / lib/popup (unchanged, they keep using the global): modifiers/modifier_tier_3.lua,
modifiers/modifier_tier_5.lua, aohgameround.lua, abilities/heroes/{bloodseeker_custom_thirst,
shadow_demon_custom_soul_catcher, bounty_hunter_custom_jinada, nyx_assassin_custom_vendetta,
antimage_custom_speed, templar_assassin_slipstrike}.lua, abilities/skills/{skill_trident,
skill_transfusion}.lua, abilities/other/global_damage_effects.lua, abilities/bosses/{custom_borrowed_time,
custom_aphotic_shield}.lua, items/{high_tech_boots, arcane_staff, echo_wand, glare_edge, dynamo_core,
item_custom_ballista}.lua.

Verified (run this session)
- DoD 1/2: `grep -c "ParticleManager:"` → 0 for both files. DoD 3: `require("core/fx")` count 1 each.
- DoD 4: `function create_popup(data)` still at the start of a line in popup.lua.
- `scripts/agents/check.sh lua` → CHECK RESULT: OK. `scripts/agents/test.sh fx` → TEST RESULT: OK (6 passed).
- `aoh_lint.py 0035` → 0 fail, 0 warn, NEEDS APPROVAL (the [human] item).
- `git diff --stat feat/p0-foundation` → only the 2 allowed files + this task file.

For the owner to playtest ([human] DoD 9)
1. Local lobby, pick a hero with Flames or Transfusion (skill_transfusion), hit a creep/boss: popup
   numbers float above the target with the same colour and size as before.
2. Use a barracks' `custom_rax_behavior` ability: a green ping waypoint appears at the owner's position.
3. Console shows no `Script Runtime Error` mentioning `lib/popup.lua`, `core/fx.lua` or `rax_behavior.lua`
   (a load error in popup.lua would show as `module 'core/fx' not found` when any of the callers above load).

## Review
APPROVE
Reviewed commit 3b71f54. aoh_lint: 0 fail, 0 warn, NEEDS APPROVAL (the [human] DoD 9).
1. Spec: both sites now use `fx.once`, and `core/fx.lua:26-27` releases the index. The particle
   paths, attach types, owners and CP values match the teamlead notes. The `create_popup(data)`
   global keeps its signature (popup.lua:14). The legacy local `fx` in rax_behavior OnRefresh is
   gone, so it no longer shadows the module. Nothing beyond the task was changed.
2. Scope: only the 2 allowed files plus the task file (`git diff --stat` checked). No tests touched.
3. Conventions: `local fx = require("core/fx")` once per file (rax_behavior.lua:2, popup.lua:12).
   No new globals and no magic numbers; the CP indices are particle data, not enums.
4. Dota correctness: no handle lifetime change. Vector is userdata, so the `type(v) == "table"`
   branch in `fx.apply` is not taken and SetParticleControl is called as before. The CP order
   now follows `pairs`, but all CPs are set before the release, so this does not matter.
5. KV: not touched.
6. Verification: the claims in Result match the diff (0 `ParticleManager:` in the changed hunks,
   one require each). qa re-runs check.sh and test.sh. The [human] playtest is listed for the
   owner and not claimed as done.
7. Hygiene: no prints, TODOs or dead code.

## QA
PASS
1. DoD 1/2: `grep -c "ParticleManager:"` gives 0 for popup.lua and rax_behavior.lua.
2. DoD 3: `require("core/fx")` count is 1 in each file.
3. DoD 4: `14:function create_popup(data)` is the only match.
4. DoD 5: `check.sh lua` printed CHECK RESULT: OK (logs/check-20261030-183317.log).
5. DoD 6: `test.sh fx` printed TEST RESULT: OK (6 passed).
6. DoD 7: `aoh_lint.py 0035` reported 0 fail and 0 warn. It exits 3 (NEEDS APPROVAL) only because of the [human] item.
7. DoD 8: `git diff --stat feat/p0-foundation` lists only the 2 allowed files and this task file.

For the human (DoD 9):
- In a local lobby, use a hero with Flames or Transfusion and hit a creep. The popup numbers should show the same colour and size as before.
- Use a barracks `custom_rax_behavior` ability. The green ping waypoint should appear.
- The console should show no `Script Runtime Error` mentioning `lib/popup.lua`, `core/fx.lua` or `rax_behavior.lua`.
