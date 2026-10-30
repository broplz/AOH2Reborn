---
id: 0029
title: core/fx migration, heroes batch B — one-shot particles with entity controls in nyx vendetta, disruptor, obsidian mana amp, clinkz death pact, terrorblade reflection
status: ready
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
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
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

## Review

## QA
