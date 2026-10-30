---
id: 0019
title: Parent-first guards in the octarine, mars spear checker and zuus wrath event handlers
status: done
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
returns: 1
sessions: 0
blocked_reason: 
reviewed_sha: 1e414a7b66c878e583b3975fb7eaf332f9679206
qa_sha: 1e414a7b66c878e583b3975fb7eaf332f9679206
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

## Result
Round 2:
- Review item 1: zuus `OnAbilityExecuted` now starts with `if keys.unit ~= self:GetParent() then return end`;
  `local parent = self:GetParent()` follows it. `check.sh lua` OK.

Round 1:
- octarine `OnTakeDamage`: guard `keys.attacker ~= self.parent` first; dropped the redundant
  HasModifier; particle index stored in `local fx` and released.
- mars checker `OnTakeDamage`: guard `keys.unit ~= self:GetParent()` first, then the inflictor test.
- zuus `OnAbilityExecuted`: guard on `keys.unit`, then nil/IsItem/ultimate/zuus_cloud early returns,
  then cursor + specials, then the unchanged Timers body (dedented one level). Added
  `-- aoh-lint: ok` on `count = count + 1` (lint false positive: upvalue of a declared local).
- Verified: `check.sh lua` OK, `aoh_lint.py 0019` 0 fail. Diff touches only the three files + this task.
- [human] playtest: cast Thundergod's Wrath on Zuus, then a spell; it repeats once. Octarine
  spell damage heals with the particle. Mars spear stops on Arena of Blood damage.

## Review
APPROVE
Round 2 checklist:
1. Spec: round-1 item 1 fixed — zuus_custom_thundergods_wrath.lua:37 now opens with
   `if keys.unit ~= self:GetParent() then` / `return` / `end`, then `local parent`. DoD 2 holds for
   all three handlers (octarine :62, mars :543, zuus :37); DoD 3/4/5 hold in the diff. No behaviour change.
2. Scope: diff --stat lists only the three allowed files; no tests touched.
3. Conventions: no new globals; `ABILITY_TYPE_ULTIMATE` kept per notes; aoh_lint 0 fail, 0 warn.
4. Dota correctness: guards first; octarine particle released; Timers body unchanged (its
   pre-existing missing `IsNull` stays out of scope).
5. KV: not touched.
6. Verification: ## Result claims (check OK, lint OK, guard first) match the diff and lint run;
   `[human]` playtest listed for the owner, not claimed. qa re-runs check.sh.
7. Hygiene: no prints, no TODOs, English.

---
REQUEST_CHANGES
1. zuus_custom_thundergods_wrath.lua:37-38 — DoD 2 fails: the first statement of
   `OnAbilityExecuted` is still `local parent = self:GetParent()`, so the grep `-A1` line is not
   `if keys.unit ~= self:GetParent() then`. Make the guard the first statement exactly as DoD 2
   says (`if keys.unit ~= self:GetParent() then return end`), then `local parent = self:GetParent()`
   below it (the Timers closure still needs `parent`). Nothing else in that file needs to change.

Checklist notes:
- Spec: octarine (guard, HasModifier dropped, fx released) and mars match the notes and DoD 3/4.
  Zuus DoD 5 holds (cursor + specials come after the guard and the nil check); only DoD 2 fails (item 1).
  The unused `caster` local was removed, which is fine.
- Scope: the diff touches only the three allowed files; no tests touched.
- Conventions: no new globals; `ABILITY_TYPE_ULTIMATE` kept as the notes require; `-- aoh-lint: ok`
  on `count = count + 1` is a valid suppression of a known false positive; aoh_lint 0 fail.
- Dota correctness: no behaviour change. The octarine particle is now released. The Timers body is
  unchanged as required (its missing `IsNull` check was already there, so it is out of scope).
- KV: not touched.
- Verification: the ## Result claims check/lint OK; lint confirmed. The claim "first statement is
  the guard" does not hold for zuus (item 1). [human] items are listed for the owner, not claimed.
- Hygiene: no prints, no TODOs, English.

## QA
PASS
1. DoD 1: `check.sh lua` → CHECK RESULT: OK (logs/check-20261030-171744.log).
2. DoD 2: grep -A1/-A2 shows the parent guard first with `return` in all three handlers (octarine :62, mars :543, zuus :37).
3. DoD 3: no `HasModifier("modifier_item_custom_octarine_core")` left. DoD 4: `local fx = CreateParticle(...)` then `ReleaseParticleIndex(fx)` (:71-72).
4. DoD 5: zuus `GetCursorPosition` and both `GetSpecialValueFor` come after the guard and the nil check (:55-57).
5. DoD 6: aoh_lint 0 fail, 0 warn. DoD 7: diff --stat lists only the three allowed files plus this task file.

For the human:
- Cast Thundergod's Wrath on Zuus, then a normal spell: it repeats the casts.
- Octarine Core spell damage still heals, and the particle shows.
- Mars spear stops when Arena of Blood damages the parent.

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
