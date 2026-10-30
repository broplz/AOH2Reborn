---
id: 0031
title: core/fx migration, bosses batch A — Vector-only one-shot particles in arena warning, spirit walk warning, ghostship warning, desolation, elder titan shifting quake
status: done
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0031-fx-bosses-oneshot-a
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_arena_warning.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_spirit_walk_warning.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_ghostship_warning.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/custom_desolation.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_elder_titan_shifting_quake.lua
checks: lua
tests: [fx]
needs_approval: true
returns: 1
sessions: 0
blocked_reason: 
reviewed_sha: 20a30c575f26d125fca0ca8d623ab26dffc645a8
qa_sha: 20a30c575f26d125fca0ca8d623ab26dffc645a8
---

## Goal
First bosses batch of the backlog-0018 follow-up (audit §Производительность: CreateParticle sites
that never call ReleaseParticleIndex leak a handle per cast). Replace the 7 unreleased
fire-and-forget `ParticleManager:CreateParticle` calls in these 5 files with `fx.once` from
`core/fx.lua`. All 7 sites have only Vector control points or none. No behaviour change: same particle, attach type,
owner, control points.

## Definition of Done
1. `grep -c "ParticleManager:CreateParticle" <each of the 5 allowed files>` prints `0` for every file.
2. `grep -c "require(\"core/fx\")" <each of the 5 allowed files>` prints `1` for every file.
3. `grep -n "^fx *=" <each of the 5 allowed files>` is empty, and `grep -n "local fx = ParticleManager" custom_ghostship_warning.lua` is empty.
4. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
5. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
6. `python3 scripts/agents/aoh_lint.py 0031` passes.
7. `git diff --stat feat/p0-foundation` lists only the 5 allowed files plus this task file.
8. [human] In a local lobby: the arena boss warning glow and arena ring, the spirit-walk boss frost nova,
   the ghostship boss warning circle and Kunkka marker, the Desolation shadowrazes and the Elder Titan
   Shifting Quake stomps each still show. No Lua errors in the console.

## Notes from teamlead
Sites (verified 2026-10-30; none is stored, given controls later or destroyed):
- custom_arena_warning.lua:16 `local particle` = `sf_fire_arcana_wings_rope_glow.vpcf`, ABSORIGIN_FOLLOW, caster, no controls.
  :26-27 `local particle2` = `particles/custom/custom_arena.vpcf`, ABSORIGIN_FOLLOW, caster, no controls (inside the Timer).
- custom_spirit_walk_warning.lua:11 `local particle` = `lich_frozenchains_frostnova_g2.vpcf`, ABSORIGIN_FOLLOW, caster, no controls.
- custom_ghostship_warning.lua:63 `local fx` = `particles/custom/aoe_warning.vpcf`, PATTACH_WORLDORIGIN, dummy;
  :64-67 CP0 = `dummy:GetAbsOrigin()`, CP1 = Vector(350, 1, 1), CP2 = Vector(4, 1, 1), CP3 = Vector(200, 10, 10).
  :69 `local particleIndex1` = `kunkka_ghostship_marker.vpcf`, ABSORIGIN_FOLLOW, dummy, no controls.
  The legacy local named `fx` shadows the module: it must disappear (the module is `fx`).
- custom_desolation.lua:19 `local particleIndex` = `particle` (nevermore_shadowraze, :13), PATTACH_ABSORIGIN, dummy, no controls.
- boss_elder_titan_shifting_quake.lua:36 `local particleIndex` = `particle` (elder_titan_echo_stomp, :22), PATTACH_ABSORIGIN, dummy, no controls.

Rules:
- `local fx = require("core/fx")` once at the top of each file (after existing requires; pattern:
  modifier_boss.lua:39). API: `fx.once(name, attach, owner, controls)`, controls `{ [cp] = Vector }`.
- Keep the control-point values; drop the now-unused locals (keep `particle` name strings at
  desolation :13 / shifting quake :22, they are the names passed to fx.once).
- Releasing a one-shot does not stop the effect; dummies removed later (desolation :21,
  ghostship :74) behave as today.
- Out of scope: the duplicated `require("lib/timers")` in arena warning, globals (datadriven entry
  points `DesolationPoints`, `shifting_quake*` stay global), KV numbers, sounds, timers, BKB calls.

## Handoff

## Result
Round 1: replaced the 7 unreleased `ParticleManager:CreateParticle` calls in the 5 files with `fx.once`
(same particle, attach type, owner, control points); added `local fx = require("core/fx")` to each file;
removed the legacy `local fx` in ghostship warning and the unused particle locals.
Verified: `check.sh lua` OK, `test.sh fx` OK (6 passed), `aoh_lint.py 0031` 0 fail (exit 3 = needs approval only because of the [human] item), diff touches only the 5 files + task file.
For the owner (DoD 8, not run): in a local lobby check the arena glow + ring, spirit-walk frost nova,
ghostship circle + Kunkka marker, Desolation shadowrazes, Elder Titan stomps; the console should show no Lua errors.

## Review
APPROVE
Round 2: item 1 fixed. tasks/0031-fx-bosses-oneshot-a.md:76-77 now lists DoD 8 as a to-do for the
owner ("not run"). The code is unchanged since round 1 (same code head, 20a30c5).
1. Spec: all 7 sites use `fx.once` with the same particle, attach type, owner and CPs. The legacy
   `local fx` in ghostship is gone. Each file has one `local fx = require("core/fx")`. Nothing extra.
2. Scope: only the 5 allowed files and the task file changed. No tests touched.
3. Conventions: no new globals. aoh_lint reports 0 fail and 0 warn. It says NEEDS APPROVAL only
   because of the [human] item.
4. Dota: `fx.once` releases the particle index. The dummy lifetimes are the same as before.
5. KV: not touched.
6. Verification: qa re-runs the check and test claims. The [human] item is listed, not claimed.
7. Hygiene: clean.

---
Round 1:
REQUEST_CHANGES
1. tasks/0031-fx-bosses-oneshot-a.md:75-76 — ## Result states the DoD 8 `[human]` playtest as an
   outcome ("... all still show; no Lua errors in the console"). Nobody can run the game in this
   pipeline; ADR-0001 says agents list `[human]` items and never claim them. Rewrite as a to-do for
   the owner, e.g. "For the owner (DoD 8, not run): in a local lobby check the arena glow + ring,
   spirit-walk frost nova, ghostship circle + Kunkka marker, Desolation shadowrazes, Elder Titan
   stomps; the console should show no Lua errors." No code change needed.

Checklist notes (code is approvable as is):
- Spec: all 7 sites from the teamlead notes are now `fx.once` with the same particle, attach, owner
  and CPs (ghostship CP0–3 kept, as a `{ [cp] = Vector }` table); the legacy `local fx` in ghostship
  is gone; `particle` name locals kept in desolation/shifting quake; one `local fx = require("core/fx")`
  per file. Nothing extra.
- Scope: only the 5 allowed files (+ task file); no tests touched.
- Conventions: no new globals; out-of-scope globals/duplicate require left alone as the task says.
  aoh_lint: 0 fail, 0 warn (NEEDS APPROVAL because of the [human] item).
- Dota correctness: `core/fx.lua:26-27` `M.once` releases the index; one-shots on dummies removed
  later behave as before.
- KV: not touched.
- Verification: check/test claims left for qa to re-run; the only false claim is item 1.
- Hygiene: no prints, TODOs or dead code added.

## QA
PASS
1. DoD 1: CreateParticle count is 0 in all 5 files.
2. DoD 2: `require("core/fx")` count is 1 in every file.
3. DoD 3: no `^fx *=` and no `local fx = ParticleManager` matches.
4. DoD 4: `check.sh lua` gives CHECK RESULT: OK.
5. DoD 5: `test.sh fx` gives TEST RESULT: OK (6 passed).
6. DoD 6: `aoh_lint.py 0031` has 0 fail, 0 warn. Exit 3 is only the [human] approval flag.
7. DoD 7: `git diff --stat` lists the 5 allowed files and this task file only.
8. I read the ghostship diff. CP0-3 values, the attach types and the owner are unchanged.

For the human:
- DoD 8: in a local lobby, check these effects and watch the console for Lua errors:
  - arena boss warning glow and ring
  - spirit-walk boss frost nova
  - ghostship warning circle and Kunkka marker
  - Desolation shadowrazes
  - Elder Titan Shifting Quake stomps
