---
id: 0014
title: bosses/_shared/telegraph.lua — ability_lua telegraph base that submits jobs to modifier_boss
status: ready
epic: p2
prefix: p2
kind: code
size: M
role: developer-hard
base: feat/p0-foundation
branch: task/0014-telegraph-base
depends_on: [0013]
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/bosses/_shared/telegraph.lua
  - tests/test_telegraph.lua
  - tests/dota_stub.lua
checks: lua
tests: [telegraph]
needs_approval: false
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
---

## Goal
ADR-0002 §Решение 5 (+ §4 Lua 10): the `generic_*` RunScript functions in abilities/other/generic.lua
poll Timers and the ticket API. This task adds the replacement: one module that builds an
`ability_lua` class for a boss "wrapper" ability whose OnSpellStart builds a boss_queue job and
calls `modifier_boss:Submit(job)`. No wrapper is migrated here (Juggernaut = task 0024); generic.lua
and the KV are untouched.

## Definition of Done
V = `game/dota_addons/attackcopy/scripts/vscripts`
1. `scripts/agents/test.sh telegraph` → `TEST RESULT: OK`; tests/test_telegraph.lua covers at least:
   a. `kind = "no_target"`: OnSpellStart calls `Submit` once on the caster's modifier_boss; `job.telegraph(job)` returns `delay - spell cast point`; `job.cast(job)` issues `CastAbilityNoTarget` on the target spell;
   b. `kind = "point"` with `is_line = 1`: cast issues `CastAbilityOnPosition` at the cursor point; difficulty 2 (`_G.AOHGameMode._difficulty = 2`) → job.iterations = iterations + 1 and telegraph returns `delay*0.8 - cast point`;
   c. `kind = "unit_target"`: difficulty 2 → delay ×0.8, iterations unchanged; cast issues `CastAbilityOnTarget` on the target;
   d. the confirm modifier: once the spell's `IsCooldownReady()` is false it calls `modifier_boss:Confirm()` exactly once and is destroyed;
   e. `job.on_cancel(job)` removes `modifier_anim` from the caster and kills a spawned `npc_target` dummy if one exists;
   f. no modifier_boss on the caster → OnSpellStart does nothing and does not error.
2. `grep -c "Timers" V/bosses/_shared/telegraph.lua` → `0`; `grep -c -E "RequestTicket|QueryTicket|ReleaseTicket|OnAbilityExecuted" V/bosses/_shared/telegraph.lua` → `0`.
3. `grep -c "LinkLuaModifier" V/bosses/_shared/telegraph.lua` → `1` (only the confirm modifier).
4. `grep -n -E "StartIntervalThink\(0\.0" V/bosses/_shared/telegraph.lua` → empty.
5. `scripts/agents/check.sh lua` → `CHECK RESULT: OK (lua)`.
6. `python3 scripts/agents/aoh_lint.py 0014` → 0 fail.
7. `git diff --stat feat/p0-foundation...HEAD` → only allowed_paths + this task file.

## Notes from teamlead
- Public API (keep exactly): `local telegraph = require("bosses/_shared/telegraph")`;
  `boss_x_wrapper = telegraph.class({ kind = "no_target"|"point"|"unit_target", spell = "<target ability name>" })`
  returns a `class({})` with `OnSpellStart`. Numbers come from the wrapper's own KV via
  `self:GetSpecialValueFor`: `delay`, `radius`, `iterations` (0/absent → 1), `is_line`, `line_length`,
  `initial_radius`, `maximum_distance` (0/absent → 475). No `ability_index` — the spell name replaces it.
- Behaviour to port 1:1 from generic.lua (read it, don't copy the Timers): `generic_aoe_notarget`
  :351-403, `generic_aoe` :231-349, `generic_target` :405-528.
  - telegraph(job): `caster:Stop()`, FaceTowards, `EmitSoundOn("Hero_Mars.Spear.Cast", caster)`,
    warning particle via lib/warning.lua globals (`aoe_particle`, `aoe_line_particle`, `line_to_point`;
    unit_target: `particles/custom/aoe_warning_target.vpcf` + `modifier_target_delay` on the target),
    `modifier_anim` for `delay - cast_point`, StartAnimation `ACT_DOTA_CAST_ABILITY_1` with
    `rate = 1 / (delay - cast_point)` (generic.lua has the precedence bug `1 / delay - cp`; the new
    code is correct). Returns `delay - cast_point`.
  - point kind, iteration 2+: retarget to a random enemy hero/basic within the spell's cast range
    (range 0 → 1000), FIND_FARTHEST, as generic_aoe :269-288; first iteration uses the cursor point.
  - cast(job): `spell:EndCooldown()`, face the point, issue the order (player id
    `caster:GetPlayerOwnerID()` for point, `-1` otherwise), unit_target: spawn `npc_target` dummy
    + `modifier_dummy` when the target moved more than `maximum_distance` (generic_target :485-499).
    Adds the confirm modifier; returns true. Target dead/null → return false.
  - `cast_timeout` = `spell:GetCastPoint() + 1.0`; `deadline` = 6 (queue default); `prio` = 0.
- Confirm: a hidden modifier `modifier_telegraph_confirm` (owned by telegraph.lua, linked once) on
  the caster, duration = cast_timeout, think 0.1 s: if `not spell:IsCooldownReady()` → find
  modifier_boss, `:Confirm()`, add `modifier_weak` 0.5 s on the last iteration, then Destroy; elif
  `caster:GetCurrentActiveAbility() == nil and not caster:IsSilenced()` → reissue the order (this
  replaces generic.lua's retry loop). Target abilities are mostly vanilla BaseClass, so they cannot
  call Confirm from OnSpellStart — that is why this modifier exists. OnDestroy stops the think.
- `modifier_anim`, `modifier_weak`, `modifier_dummy`, `modifier_target_delay` are owned and linked by
  abilities/other/generic.lua (:631-879): `require("abilities/other/generic")` at the top, never a
  second LinkLuaModifier. In the test, set `package.loaded["abilities/other/generic"] = true` and
  `package.loaded["lib/warning"]` stubs before requiring the module.
- No globals besides the classes `telegraph.class` returns (assigned by the caller) and
  `modifier_telegraph_confirm`. No `print`.
- tests/dota_stub.lua: add only what the tests need (ability stub with GetSpecialValueFor /
  GetCastPoint / IsCooldownReady / EndCooldown, cast-order recorders on Unit, ParticleManager no-ops).
- Out of scope: generic.lua, KV, every wrapper migration (0024 Juggernaut first).

## Handoff

## Result

## Review

## QA
