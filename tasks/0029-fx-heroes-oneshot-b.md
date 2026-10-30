---
id: 0029
title: core/fx migration, heroes batch B — one-shot particles with entity controls in nyx vendetta, disruptor, obsidian mana amp, clinkz death pact, terrorblade reflection
status: done
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0029-fx-heroes-oneshot-b
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/nyx_assassin_custom_vendetta.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/disruptor_custom_ion_hammer.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/obsidian_destroyer_custom_mana_amp.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/clinkz_custom_death_pact.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/terrorblade_custom_reflection.lua
checks: lua
tests: [fx]
needs_approval: true
returns: 0
sessions: 1
blocked_reason: 
reviewed_sha: 2025e56a45c656e7fe9369425eb74ca338b873c9
qa_sha: 2025e56a45c656e7fe9369425eb74ca338b873c9
---

## Goal
Second heroes batch of the backlog-0018 follow-up (unreleased fire-and-forget particles leak a
handle per cast). Replace the 5 unreleased `ParticleManager:CreateParticle` calls in these 5 files
with `core/fx.lua` (0018). Each site sets at least one control point with SetParticleControlEnt.
No behaviour change: same particle, attach type, owner and control points.

## Definition of Done
1. `grep -c "ParticleManager:CreateParticle" <each of the 5 allowed files>` prints `0` for every file.
2. `grep -c "require(\"core/fx\")" <each of the 5 allowed files>` prints `1` for every file.
3. `grep -n "^fx *=" <each of the 5 allowed files>` is empty; `grep -n "local fx = Particle"` in
   the 5 files is empty (no legacy local shadows the module).
4. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
5. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
6. `python3 scripts/agents/aoh_lint.py 0029` passes.
7. `git diff --stat feat/p0-foundation` lists only the 5 allowed files plus this task file.
8. [human] In a local lobby: Nyx Vendetta glare, Disruptor Ion Hammer silence burst, Obsidian
   Destroyer Mana Amp essence flash, Clinkz Death Pact beam, Terrorblade Reflection cast effect
   each still show at the same spot as before.

## Notes from teamlead
Sites (verified 2026-10-30, none stored or destroyed later):
- nyx_assassin_custom_vendetta.lua:153 `local fx = CreateParticle("particles/custom/glare_edge.vpcf", POINT_FOLLOW, target)`;
  :154 ent CP0 = target / PATTACH_POINT / "attach_hitloc" / target:GetAbsOrigin(). The legacy local
  `fx` shadows the module — it must go.
- disruptor_custom_ion_hammer.lua:52 `silencer_global_silence.vpcf`, ABSORIGIN_FOLLOW, target; :57 ent CP1.
- obsidian_destroyer_custom_mana_amp.lua:11 `obsidian_destroyer_essence_effect.vpcf`, ABSORIGIN_FOLLOW, caster; :16 ent CP0.
- clinkz_custom_death_pact.lua:18 `local fx = CreateParticle(clinkz_death_pact.vpcf, POINT_FOLLOW, caster)`;
  :23 ent CP0 (+ check for more control calls after it). Legacy local `fx` shadows the module.
- terrorblade_custom_reflection.lua:39 `CreateParticle(particleName, POINT_FOLLOW, caster)`; :40
  CP3 = Vector(1, 0, 0); :42 ent CP0 = caster / PATTACH_POINT_FOLLOW.

Rules:
- `local fx = require("core/fx")` once at the top of each file (pattern: modifier_boss.lua:39).
  API: `fx.once(name, attach, owner, controls)`; controls `{ [cp] = Vector }` or
  `{ [cp] = { ent = unit, attach = PATTACH_*, point = "attach_x" } }`.
- fx's ent control always passes `ent:GetAbsOrigin()` and `true`. Read each SetParticleControlEnt
  in full: if its 6th arg is not `<same ent>:GetAbsOrigin()` or its 7th is not `true`, do NOT use the
  controls table for it: `local idx = fx.attach(...)`, keep the original SetParticleControlEnt call on
  `idx`, then `ParticleManager:ReleaseParticleIndex(idx)`. Say in ## Result which sites took that path.
- Out of scope: any other change in these files (KV numbers, globals, sounds, timers, other particles).

## Handoff

## Result
Round 1: the 5 `ParticleManager:CreateParticle` sites now go through `core/fx`. Each file has one `local fx = require("core/fx")`, and the two legacy local `fx` variables (nyx, clinkz) are gone.
- nyx, disruptor, obsidian, clinkz: `fx.once` with a controls table. Every ent control already passed `<same ent>:GetAbsOrigin()` and `true`.
- terrorblade_custom_reflection.lua took the `fx.attach` path. Its CP0 passes `caster` as the ent but `target:GetAbsOrigin()` as the origin. CP3 (Vector) and CP1 (target) go in the controls table, the original CP0 `SetParticleControlEnt` call is kept, then `ReleaseParticleIndex`. CP0 is now set after CP1 and CP3 instead of between them.

Verified: `check.sh lua` OK, `test.sh fx` OK, `aoh_lint.py 0029` 0 fail (it ends NEEDS APPROVAL because of the [human] item). `git diff --stat` shows only the 5 files and this task file. I did not run the grep commands from DoD items 1-3 by hand.

Owner playtest (DoD 8): cast or trigger each of the five effects in a local lobby. Each should appear where it did before, and there should be no Lua errors in the console.

## Review
APPROVE
1. Spec: all 5 `CreateParticle` sites are migrated with the same name, attach type, owner and CPs. In nyx, disruptor, obsidian and clinkz, every ent control passed `<same ent>:GetAbsOrigin(), true`, so `fx.once` is exact (core/fx.lua:12). terrorblade_custom_reflection.lua:42-55 uses `fx.attach` and keeps the original CP0 call (caster ent + target origin), followed by `ReleaseParticleIndex`, as the notes require. CP0 is now set after CP1/CP3. The handle is still created and released in the same frame, so this is harmless. Nothing extra was changed.
2. Scope: only the 5 allowed files are touched and no tests are affected.
3. Conventions: one `local fx = require("core/fx")` per file. The legacy `local fx` in nyx and clinkz is removed. No new globals: the `ReflectionCast` global predates this task and is out of scope.
4. Correctness: every created particle is released and no handles are kept. The surrounding guards are unchanged.
5. KV: not touched.
6. Verification: aoh_lint gives 0 fail, 0 warn, NEEDS APPROVAL (expected because of the [human] DoD 8). The diff stat matches DoD 7. DoD 1-3 hold when read from the diff, and qa re-runs check/test. DoD 8 is listed for the owner and not claimed as done.
7. Hygiene: no prints, TODOs or dead code. The stale `-- unknown` comments in nyx were dropped along with the call they annotated.

## QA
PASS
1. DoD 1: `grep -c "ParticleManager:CreateParticle"` prints 0 for all 5 files.
2. DoD 2: `grep -c 'require("core/fx")'` prints 1 for all 5 files.
3. DoD 3: the grep for `^fx *=` and `local fx = Particle` is empty.
4. DoD 4: `check.sh lua` prints CHECK RESULT: OK (log: logs/check-20261030-173653.log).
5. DoD 5: `test.sh fx` prints TEST RESULT: OK (6 passed, 0 failed).
6. DoD 6: `aoh_lint.py 0029` has 0 fail and 0 warn. It exits NEEDS APPROVAL only because of the [human] item.
7. DoD 7: `git diff --stat` lists the 5 allowed files plus this task file.
8. I read the clinkz diff. Both control points use the same ent with `GetAbsOrigin()` and `true`, so `fx.once` is equivalent.

For the human:
- DoD 8: in a local lobby, trigger each effect and check it appears where it did before, with no Lua errors in the console.
  - Nyx Vendetta glare
  - Disruptor Ion Hammer silence burst
  - Obsidian Destroyer Mana Amp essence flash
  - Clinkz Death Pact beam
  - Terrorblade Reflection cast effect
