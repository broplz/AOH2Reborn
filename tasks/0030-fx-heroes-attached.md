---
id: 0030
title: core/fx migration, heroes attached batch — destroyed-but-unreleased modifier particles in naga sword dance, bloodseeker rampage, shadow demon dark trance, huskar life break, dark seer ion shell
status: ready
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0030-fx-heroes-attached
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/naga_siren_custom_sword_dance.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/bloodseeker_custom_rampage.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/shadow_demon_dark_trance.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/huskar_custom_life_break.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/dark_seer_custom_ion_shell.lua
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
Heroes attached batch of the backlog-0018 follow-up: modifiers that create a long-lived particle in
OnCreated and call `DestroyParticle` in OnDestroy without `ReleaseParticleIndex` (handle leak per
cast), plus huskar's two unreleased one-shots. Move them to `core/fx.lua` (0018) so every path ends
in destroy + release. No behaviour change: same particle, attach, owner, controls, destroy timing.

## Definition of Done
1. `grep -c "ParticleManager:CreateParticle"` prints `0` for naga_siren_custom_sword_dance.lua,
   bloodseeker_custom_rampage.lua, shadow_demon_dark_trance.lua, huskar_custom_life_break.lua, and
   `1` for dark_seer_custom_ion_shell.lua (the already-released :90 site stays).
2. `grep -c "ParticleManager:DestroyParticle" <each of the 5 allowed files>` prints `0` for every file
   (all go through `fx.stop`).
3. `grep -c "require(\"core/fx\")" <each of the 5 allowed files>` prints `1`; `grep -n "^fx *="` is empty.
4. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
5. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
6. `python3 scripts/agents/aoh_lint.py 0030` passes.
7. `git diff --stat feat/p0-foundation` lists only the 5 allowed files plus this task file.
8. [human] In a local lobby: Naga Sword Dance (both effects), Bloodseeker Rampage, Shadow Demon Dark
   Trance, Dark Seer Ion Shell show while the buff lasts and vanish when it ends; Huskar Life Break
   channel ring grows during the channel, vanishes at the end, and both end bursts show.

## Notes from teamlead
Sites (verified 2026-10-30; all creates sit inside `if IsServer() then` blocks):
- naga_siren_custom_sword_dance.lua:70 `self.particle`, :84 `self.particle2` (PATTACH_POINT + ent
  controls with PATTACH_POINT_FOLLOW); destroyed :102-103 with `false` in OnDestroy.
- bloodseeker_custom_rampage.lua:45 `self.particle` (ABSORIGIN_FOLLOW + ent control); destroyed :63 `false`.
- shadow_demon_dark_trance.lua:60 `self.particle` (PATTACH_POINT + ent control); destroyed :93 `false`.
- huskar_custom_life_break.lua:64 `self.particle` (channel, PATTACH_POINT, self.caster; ent CP1 =
  self.parent / POINT_FOLLOW / attach_hitloc); :82 OnIntervalThink sets CP1 on it every tick — keep that
  call on the returned index; destroyed :127 with `true` → `fx.stop(self.particle, true)`.
  :128 and :142 are one-shots (inner_fire_ring_b CP0, life_break_end CP1; ent = self.parent /
  PATTACH_ABSORIGIN / "attach_absorigin") → `fx.once`. Two `local particle` in a row today; both go.
- dark_seer_custom_ion_shell.lua:39 `self.particle2` (PATTACH_POINT + ent control); destroyed :68 `true`.
  :90 is a released per-tick one-shot — leave it unchanged. The file's global `cast_ion_shell`
  (datadriven RunScript entry point) stays a global; do not touch it.

Rules:
- `local fx = require("core/fx")` once at the top (pattern: modifier_boss.lua:39). API:
  `fx.attach(name, attach, owner, controls)` → index, `fx.stop(index, immediate)`,
  `fx.once(...)`; controls `{ [cp] = Vector }` or `{ [cp] = { ent, attach, point } }` (always
  `ent:GetAbsOrigin()`, `true`). A SetParticleControlEnt with another origin/flag keeps its original
  call on the index returned by `fx.attach`.
- Use `fx.attach` + `fx.stop`, NOT `fx.bind`: bind's AddParticle always destroys non-immediately,
  and huskar/dark seer destroy with `true`. Keep each site's `immediate` flag exactly.
- Out of scope: KV numbers, globals, timers, FindUnitsInRadius per tick, any other particle.

## Handoff

## Result

## Review

## QA
