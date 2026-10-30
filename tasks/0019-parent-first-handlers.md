---
id: 0019
title: Parent-first guards in the octarine, mars spear checker and zuus wrath event handlers
status: ready
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0019-parent-first-handlers
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/items/item_custom_octarine_core.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/mars_spear_of_mars_lua.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/zuus_custom_thundergods_wrath.lua
checks: lua
tests: []
needs_approval: false
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
---

## Goal
Modifier event handlers fire for every unit on the map (ADR-0002 §Lua, aoh-rules rule 8). Three
handlers call the engine API before checking that the event is about their parent, so they do
work — and in zuus' case can error — on every cast/damage instance in the game. Make the parent
comparison the first statement (early return), with no behaviour change. This is the
"parent-first filters" half of backlog 0019; the `global_damage_effects` → damage-filter half is
escalated (docs/reports/decisions-needed.md, 2026-10-30).

## Definition of Done
1. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
2. The first statement inside each handler is the parent guard; verify with
   `grep -n -A1 "function modifier_item_custom_octarine_core:OnTakeDamage\|function modifier_mars_spear_of_mars_lua_checker:OnTakeDamage\|function modifier_zuus_custom_thundergods_wrath:OnAbilityExecuted" <the three files>`
   — every second line is `if keys.attacker ~= self.parent then` (octarine) or
   `if keys.unit ~= self:GetParent() then` (mars, zuus), followed by `return` / `end`.
3. `grep -n "HasModifier(\"modifier_item_custom_octarine_core\")" game/dota_addons/attackcopy/scripts/vscripts/items/item_custom_octarine_core.lua` is empty.
4. `grep -n -A4 "CreateParticle(self.particle_name" game/dota_addons/attackcopy/scripts/vscripts/items/item_custom_octarine_core.lua`
   shows the index assigned to a local and passed to `ParticleManager:ReleaseParticleIndex`.
5. In zuus_custom_thundergods_wrath.lua, `used_ability:GetCursorPosition()` and both
   `GetSpecialValueFor` calls appear after the guard and after the `used_ability` nil check.
6. `python3 scripts/agents/aoh_lint.py 0019` passes.
7. `git diff --stat feat/p0-foundation` lists only the three allowed files plus this task file.

## Notes from teamlead
Exact sites (read them at these lines, they were current on 2026-10-30):
- items/item_custom_octarine_core.lua:61-73 `OnTakeDamage`: today
  `if keys.attacker:HasModifier("modifier_item_custom_octarine_core")` → `if self.parent == keys.attacker and keys.unit ~= self.parent`.
  The HasModifier test is implied by `self.parent == keys.attacker` (this modifier sits on its
  parent) → drop it. New shape: guard `if keys.attacker ~= self.parent then return end`, then the
  `keys.unit ~= self.parent`, REFLECTION-flag and damage-type conditions unchanged. Line 69's
  `CreateParticle` is never released (rule 7) → `local fx = …` + `ParticleManager:ReleaseParticleIndex(fx)`.
  Do not use core/fx.lua (task 0018, not merged).
- abilities/heroes/mars_spear_of_mars_lua.lua:542-549 `modifier_mars_spear_of_mars_lua_checker:OnTakeDamage`:
  guard `if keys.unit ~= self:GetParent() then return end` first, then
  `if keys.inflictor and keys.inflictor:GetAbilityName() == "mars_arena_of_blood" then self:Destroy() end`.
- abilities/heroes/zuus_custom_thundergods_wrath.lua:36-54 `OnAbilityExecuted`: today calls
  `keys.ability:GetCursorPosition()` (crashes when `keys.ability` is nil) and two
  `GetSpecialValueFor` before checking `keys.unit == parent`. Order: guard on `keys.unit`, then
  `local used_ability = keys.ability` + nil/IsItem/ultimate/`zuus_cloud` early returns, then cursor
  and specials, then the unchanged Timers body. Keep `ABILITY_TYPE_ULTIMATE` (the Lua global; not
  `DOTA_ABILITY_TYPE_ULTIMATE`).
- items/echo_wand.lua is NOT in scope: both handlers (:175, :205) already compare `keys.unit` /
  `keys.attacker` with `self.parent` as the first operand — the audit row is stale.
- Guards are positive-form early returns (owner rule: no inverted conditions inside the main
  branch; negatives only as guard/return). No other refactors in these files.
