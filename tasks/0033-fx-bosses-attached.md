---
id: 0033
title: core/fx migration, bosses attached batch — destroyed-but-unreleased particles in infernal retribution, ice reflector, boss meteor, spirits
status: done
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0033-fx-bosses-attached
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_infernal_retribution.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_ice_reflector.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_meteor_init.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_spirits.lua
checks: lua
tests: [fx]
needs_approval: true
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: ceaecd465ffb35c700dae8d3d0e88dcbcaa8e357
qa_sha: ceaecd465ffb35c700dae8d3d0e88dcbcaa8e357
---

## Goal
Bosses attached batch of the backlog-0018 follow-up: long-lived particles that are destroyed with
`DestroyParticle` but never released (handle leak per cast), plus one unreleased one-shot. Move them
to `core/fx.lua` so every path ends in destroy + release. No behaviour change: same particle,
attach, owner, controls, destroy timing and `immediate` flag.

## Definition of Done
1. `grep -c "ParticleManager:CreateParticle" <each of the 4 allowed files>` prints `0` for every file.
2. `grep -c "ParticleManager:DestroyParticle" <each of the 4 allowed files>` prints `0` for every file (all go through `fx.stop`).
3. `grep -c "require(\"core/fx\")" <each of the 4 allowed files>` prints `1`; `grep -n "^fx *="` is empty.
4. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
5. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
6. `python3 scripts/agents/aoh_lint.py 0033` passes.
7. `git diff --stat feat/p0-foundation` lists only the 4 allowed files plus this task file.
8. [human] In a local lobby: Infernal Retribution doom circle shows for `delay`, vanishes, and the
   shadowraze burst shows; the ice reflector frost armor shows on the target and vanishes when the buff
   ends; the boss meteor fire trail follows the meteor and fades when it ends; spirits show their
   effect, it grows/shrinks with the radius, and vanishes when a spirit dies. No Lua errors.

## Notes from teamlead
Sites (verified 2026-10-30):
- custom_infernal_retribution.lua:15 `local particleIndex` (doom_bringer_doom, PATTACH_ABSORIGIN, dummy,
  no controls) → `fx.attach`; destroyed :41 with `true` → `fx.stop(particleIndex, true)`.
  :19 `local particleEndIndex` (sf_fire_arcana_shadowraze, PATTACH_ABSORIGIN, dummy) is a one-shot → `fx.once`.
- custom_ice_reflector.lua:39 `target.FrostArmorParticle` (lich_frost_armor, PATTACH_OVERHEAD_FOLLOW, target)
  inside a 0.01 s Timer; CP0 = `target:GetAbsOrigin()`, CP1 = Vector(1, 0, 0), CP2 ent target with
  PATTACH_ABSORIGIN_FOLLOW / "attach_origin" (matches fx.apply). Destroyed :57 with `false`
  → `fx.stop(target.FrostArmorParticle, false)`. Keep storing the index on `target.FrostArmorParticle`.
- boss_meteor_init.lua:32-33 `self.particle` (`particles/custom/boss_meteor_fire_trail.vpcf`, PATTACH_POINT,
  parent); CP0 and CP3 ent parent / PATTACH_POINT_FOLLOW / "attach_hitloc" (matches fx.apply); destroyed
  :55 with `false` → `fx.stop(self.particle, false)`.
- custom_spirits.lua:50 `local pfx` (event.spirit_particle_name, ABSORIGIN_FOLLOW, newSpirit), stored :51
  as `newSpirit.spirit_pfx`; :94 sets CP1 on it every think — keep that call on the stored index;
  destroyed :143 with `false` → `fx.stop(spirit.spirit_pfx, false)`.

Rules:
- `local fx = require("core/fx")` once at the top (pattern: modifier_boss.lua:39). API:
  `fx.attach(name, attach, owner, controls)` → index, `fx.stop(index, immediate)`, `fx.once(...)`.
  Controls: `{ [cp] = Vector }` or `{ [cp] = { ent = unit, attach = PATTACH_*, point = "attach_x" } }`
  with NAMED keys (core/fx.lua:8-12; a positional table is silently ignored).
- Use `fx.attach` + `fx.stop`, NOT `fx.bind` (these are datadriven/Timer paths with explicit
  destroys; infernal retribution destroys with `true`). Keep each `immediate` flag exactly.
- Datadriven entry points (`infernal_retribution`, `on_death`, `ice_reflector_*`, `FrostArmorParticle`,
  `EndFrostArmorParticle`, `CastSpirits`, `ThinkSpirits`, `EndSpirits`, `OnCreatedSpirit`,
  `OnDestroySpirit`, `ExplodeSpirit`, `init`) stay global; do not touch them.
- Out of scope: `GetLevelSpecialValueFor` in infernal retribution, KV numbers, timers, sounds, other particles.

## Handoff

## Result
Round 1: the four boss files now create and stop their particles only through `core/fx`
(`fx.attach` + `fx.stop`, `fx.once` for the shadowraze burst). Every `immediate` flag and every
control point is unchanged.
- Infernal retribution: the doom circle is released after `fx.stop(…, true)`, and the shadowraze burst is `fx.once`.
- Ice reflector: the index is still stored on `target.FrostArmorParticle`, and CP0/1/2 are passed as named controls.
- Boss meteor: CP0 and CP3 share one `attach_hitloc` control.
- Spirits: one deviation. `fx.stop` now releases the index, so `OnDestroySpirit` sets `spirit.spirit_pfx = nil`. `ThinkSpirits` skips the CP1 update when it is nil. Without this, the think would keep writing to a released handle for dead spirits.

Verified: `check.sh lua` gives OK, `test.sh fx` gives OK, `aoh_lint.py 0033` has 0 fail (the exit code 3 is the NEEDS APPROVAL note for the [human] item), and the diff touches only the 4 allowed files plus this task file. I did not run the DoD 1–3 greps. I made the edits so they should print the expected counts, but that is unchecked.

Owner playtest (DoD 8): cast each of the four bosses' abilities in a local lobby and watch the console for Lua errors. Spirits: kill one and check the others keep resizing with the radius.

## Review
APPROVE

1. Spec: all 4 sites match the teamlead notes. infernal: `fx.attach` + `fx.stop(…, true)`, shadowraze `fx.once`;
   ice reflector: CP0/CP1 vectors + CP2 named ent control, index kept on `target.FrostArmorParticle`, `fx.stop(…, false)`;
   meteor: CP0/CP3 share one named `attach_hitloc` control (fx.apply core/fx.lua:12 uses `ent:GetAbsOrigin()`, lock `true`, same as the old calls);
   spirits: `fx.attach` + `fx.stop(…, false)`. All `immediate` flags are unchanged. The spirits nil-guard (custom_spirits.lua:95-98, :148)
   is a justified deviation. The list entry is removed only in ExplodeSpirit (:170), so other destroy paths could leave a released
   index in the think loop. Without the guard the think would write CP1 to a recycled handle.
2. Scope: the diff touches only the 4 allowed files. No tests touched.
3. Conventions: `local fx = require("core/fx")` once per file, no new globals, the datadriven entry points are untouched, no numbers added.
4. Correctness: every create now ends in a release (fx.once releases at core/fx.lua:27, fx.stop at :40). fx.stop is nil-safe (:36), so
   EndFrostArmorParticle before the 0.01 s timer runs behaves as before.
5. KV: not touched.
6. Result: check/test/lint claims match. aoh_lint gives 0 fail with only the NEEDS APPROVAL note (I re-ran it). The developer says they did not run DoD 1–3, and the diff
   leaves no `ParticleManager:CreateParticle`/`DestroyParticle` in these files. qa should confirm the counts. [human] DoD 8 is listed, not claimed.
7. Hygiene: no prints, no TODOs, English.

## QA
PASS

1. DoD 1-2: the combined CreateParticle/DestroyParticle grep count is 0 in all 4 files.
2. DoD 3: `require("core/fx")` count is 1 in each file; `grep -n "^fx *="` is empty.
3. DoD 4: `check.sh lua` gives OK. DoD 5: `test.sh fx` gives OK (6 passed).
4. DoD 6: `aoh_lint.py 0033` has 0 fail, 0 warn; exit 3 is only the NEEDS APPROVAL note.
5. DoD 7: the diff stat lists only the 4 allowed files plus this task file.

For the human (DoD 8), in a local lobby, watch the console for Lua errors:
- Infernal Retribution: the doom circle shows for `delay` and vanishes, then the shadowraze burst shows.
- Ice reflector: the frost armor shows on the target and vanishes when the buff ends.
- Boss meteor: the fire trail follows the meteor and fades when it ends.
- Spirits: the effect shows, resizes with the radius, and vanishes when a spirit dies. Kill one spirit and check the others still resize.
