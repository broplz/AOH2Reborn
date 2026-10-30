---
id: 0037
title: core/fx migration, Aghanim — release every destroyed particle (staff beams, shard attack, spell swap, summon portals)
status: ready
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0037-fx-aghanim-stop
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_aghanim_staff_beams.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_aghanim_shard_attack.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_aghanim_spell_swap.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_aghanim_summon_portals.lua
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
Aghanim batch of the backlog-0018 follow-up (audit §Производительность). These 4 files destroy
long-lived particles (channel FX, beams, projectile FX, portal FX) with `DestroyParticle` and never
call `ReleaseParticleIndex`, so each cast leaks indices. Replace every such destroy with
`fx.stop` from `core/fx.lua` (destroy + release). The creation sites stay raw: their entity controls
use custom origins, `nil` points and `false` lock flags that `fx.attach` cannot express. No
behaviour change: same particles, same destroy timing, same `immediate` flag.

## Definition of Done
1. `grep -c "DestroyParticle" <each of the 4 allowed files>` prints `0` for every file.
2. `grep -c "fx.stop(" <file>` prints: staff_beams `4`, shard_attack `2`, spell_swap `2`, summon_portals `2`.
3. `grep -c "require(\"core/fx\")" <each of the 4 allowed files>` prints `1` for every file.
4. `grep -n "fx.stop(nFXIndex, true)" game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_aghanim_spell_swap.lua` prints exactly one line (the beam loop keeps `immediate = true`).
5. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
6. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`.
7. `python3 scripts/agents/aoh_lint.py 0037` has 0 fail.
8. `git diff --stat feat/p0-foundation` lists only the 4 allowed files plus this task file.
9. [human] In a local lobby, fight Aghanim through every ability: Staff Beams (warning rings vanish
   at cast, beams vanish at channel end, linger burn patches vanish), Shard Attack (spiral shards vanish
   on hit, channel glow ends), Spell Swap (beams and channel FX end with the channel), Summon Portals
   (channel FX ends, portals vanish when they close). No Lua errors in the console.

## Notes from teamlead
Sites (verified 2026-10-30 against the current files):
- boss_aghanim_staff_beams.lua: :109 `DestroyParticle(enemy.nWarningFXIndex, false)`; :218
  `DestroyParticle(self.nChannelFX, false)`; :224 `DestroyParticle(v.nFXIndex, false)` (loop over
  self.Projectiles); :361 `DestroyParticle(self.nFXIndex, false)` (linger thinker OnDestroy).
- boss_aghanim_shard_attack.lua: :62 `DestroyParticle(self.nChannelFX, false)`; :336
  `DestroyParticle(info.nFXIndex, false)`.
- boss_aghanim_spell_swap.lua: :76 `DestroyParticle(self.nChannelFX, false)`; :79
  `DestroyParticle(nFXIndex, true)` in the `self.nBeamFXIndices` loop.
- boss_aghanim_summon_portals.lua: :134 `DestroyParticle(self.nChannelFX, false)`; :697
  `DestroyParticle(self.nPortalFX, false)`.

Rules:
- Each site becomes one line: `fx.stop(x)` for `false`, `fx.stop(x, true)` for `true`. Do not add
  a separate `ReleaseParticleIndex` — fx.stop already releases; `fx.stop(nil)` is a no-op.
- `local fx = require("core/fx")` once at the top of each file, after the existing `require` lines
  (staff_beams/crystal files start with `require("lib/warning")`). None of these 4 files has a legacy
  local named `fx` at file scope; staff_beams :72 `local fx = aoe_particle(...)` inside
  OnAbilityPhaseStart shadows the module and is unused → drop the `local fx =` and keep the call
  (`aoe_particle(...)` as a statement).
- Out of scope: the `CreateParticle` sites (all already destroyed or released), the one-shot sites
  that already call ReleaseParticleIndex, sounds, `modifier_cooldown_locked`, KV, the cast queue,
  boss_aghanim_crystal_attack.lua (task 0038) and boss_aghanim_spear (escalated, backlog 0008).

## Handoff

## Result

## Review

## QA
