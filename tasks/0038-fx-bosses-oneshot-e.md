---
id: 0038
title: core/fx migration, bosses batch E — solar strike, spirit bear, crystal attack, undead cannon one-shots
status: ready
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0038-fx-bosses-oneshot-e
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_invoker_solar_strike.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_lone_druid_spirit_bear.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_aghanim_crystal_attack.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_abyssal_underlord_undead_cannon.lua
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
Bosses batch E of the backlog-0018 follow-up (audit §Производительность). Each file has one-shot
particles that are never released. Move them to `fx.once` from `core/fx.lua`, and remove the legacy
locals named `fx` that shadow the module. Attached particles that are already destroyed and released
stay as they are, except the one `OnDestroy` pair listed below. No behaviour change: same particle,
attach type, owner and control points.

## Definition of Done
1. `grep -c "require(\"core/fx\")" <each of the 4 allowed files>` prints `1` for every file.
2. `grep -n "local fx =" <each of the 4 allowed files>` is empty (no locals shadowing the module).
   Note: lines that start with `ParticleManager:CreateParticle(` after a wrapped `self.fxN =` are
   legitimate (stylua line breaks), so the bare-create sites are proven by DoD 3, not by a grep.
3. `grep -c "fx.once(" <file>` prints at least: solar_strike `3`, spirit_bear `4`, crystal_attack `1`, undead_cannon `2`.
4. `grep -c "fx.stop(self.fx, true)" game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_lone_druid_spirit_bear.lua` prints `1`.
5. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
6. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
7. `python3 scripts/agents/aoh_lint.py 0038` has 0 fail.
8. `git diff --stat feat/p0-foundation` lists only the 4 allowed files plus this task file.
9. [human] In a local lobby: Invoker Solar Strike (frost-nova on the caster, warning circles, flare hits),
   Lone Druid spirit bear (spawn/respawn FX, maul burst + maul overhead that disappears with the
   debuff, degen blood and lifesteal FX), Aghanim Crystal Attack (warning circles, self-damage pulse),
   Underlord Undead Cannon (line warning, beam + explosions) still show. No Lua errors in the console.

## Notes from teamlead
API: `local fx = require("core/fx")` once at the top of each file, after existing `require` lines
(spirit_bear has none → line 1 after the header comment). `fx.once(name, attach, owner, controls)`;
controls are `{ [cp] = Vector }` or `{ [cp] = { ent = unit, attach = PATTACH_*, point = "attach_hitloc" } }`
(NAMED keys; `point` may be omitted for nil). fx.apply passes `ent:GetAbsOrigin()` and `true`.

Sites (verified 2026-10-30):
- boss_invoker_solar_strike.lua
  - :8-13 `local fx` aoe_warning.vpcf, PATTACH_WORLDORIGIN, target; CP0 pos, CP1 Vector(radius, 1, 1),
    CP2 Vector(delay, 1, 1), CP3 Vector(200, 10, 10); released → `fx.once`.
  - :16-23 `local fx` custom_mystic_flare_ambient_hit.vpcf, PATTACH_ABSORIGIN, target; CP0 pos,
    CP1 Vector(radius, 0, 0); released → `fx.once`.
  - :60-64 `local particle` lich_frozenchains_frostnova_g2.vpcf, PATTACH_ABSORIGIN_FOLLOW, caster; no
    controls; never released or destroyed → `fx.once(...)` (drop the unused local).
- boss_lone_druid_spirit_bear.lua
  - :20-24 `local particle` lone_druid_bear_spawn.vpcf, PATTACH_ABSORIGIN_FOLLOW, caster.bear; never released → `fx.once`.
  - :28-42 `local fx` vengeful_nether_swap.vpcf: CP1 ent uses `caster.bear:GetOrigin()` and lock `false`
    → keep it raw (already released); only rename the local to `swap_fx`.
  - :62-67 `local particle` versus_explosion_burst_rings.vpcf, PATTACH_ABSORIGIN_FOLLOW, caster.bear;
    CP0 = caster.bear:GetAbsOrigin(); never released → `fx.once`.
  - :109-113 bare create ls_ti9_open_wounds_blood_soft.vpcf, PATTACH_ABSORIGIN_FOLLOW, self.parent → `fx.once`.
  - :131-135 bare create generic_lifesteal.vpcf, PATTACH_ABSORIGIN_FOLLOW, self.caster → `fx.once`.
  - modifier_maul: :187-210 creation of `self.fx` stays raw; OnDestroy :225-226 Destroy(true)+Release
    → `fx.stop(self.fx, true)`.
- boss_aghanim_crystal_attack.lua
  - :126 `local fx = aoe_particle(...)` is unused and shadows the module → keep the call as a statement.
  - :325-348 `local nFXIndex` aghanim_self_dmg.vpcf, PATTACH_CUSTOMORIGIN, self:GetParent(); CP0 ent
    parent PATTACH_POINT_FOLLOW "attach_hitloc"; CP1 ent parent PATTACH_ABSORIGIN_FOLLOW, nil point;
    CP2 Vector(pulse_radius ×3); never released → `fx.once` with CP0/CP1 as named ent controls.
- boss_abyssal_underlord_undead_cannon.lua
  - :204-211 `local fx` line_aoe_warning.vpcf, PATTACH_WORLDORIGIN, self.parent; CP0/CP1 parent origin,
    CP2 target origin, CP3 Vector(beam_radius, beam_radius, 1), CP4 Vector(beam_delay, 1, 1); released → `fx.once`.
  - :230-244 `local fx` custom_abyssal_underlord_beam.vpcf, PATTACH_POINT, self.parent; CP9 ent parent
    PATTACH_POINT_FOLLOW "attach_hitloc"; CP1 = target origin + Vector(0, 0, 150); never released → `fx.once`.
  - :53-176 self.fx..fx4 (destroyed + released in OnDestroy) and :245-266 explosions (released): out of scope.

Out of scope: globals `SpiritBearSpawn`/`Maul` (datadriven entry points), the `caster` / `point`
undefined-global bugs (backlog 0023), sounds, timers, KV, the cast queue.

## Handoff

## Result

## Review

## QA
