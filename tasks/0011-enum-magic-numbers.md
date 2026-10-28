---
id: 0011
title: Magic numbers → enums (damage flags via bit.band, damage type, ability type, order type)
status: ready
epic: p1
prefix: p1
kind: code
size: M
role: developer
base: feat/p0-foundation
branch: task/0011-enum-magic-numbers
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/spectre_custom_dispersion.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/centaur_custom_return.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/ogre_magi_custom_multicast.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/zuus_custom_thundergods_wrath.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/other/global_damage_effects.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/other/hero_attribute_fix.lua
  - game/dota_addons/attackcopy/scripts/vscripts/lib/illusion.lua
  - game/dota_addons/attackcopy/scripts/vscripts/items/item_custom_octarine_core.lua
  - game/dota_addons/attackcopy/scripts/vscripts/items/item_custom_ballista.lua
  - game/dota_addons/attackcopy/scripts/vscripts/modifiers/modifier_tier_5.lua
  - tools/luacheck.baseline
checks: lua
tests: []
needs_approval: true
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
---

## Goal
ADR-0002 §Решение 4 Lua rule 4 / audit §Legacy 8: replace numeric literals for engine enums with
the enum names, and test the damage-flag bitmask with `bit.band` instead of `== 16` / `~= 16`
(an exact compare misses reflected damage that carries any second flag, so reflection can loop).
14 sites in 10 files, one or two lines each.

## Definition of Done
V = `game/dota_addons/attackcopy/scripts/vscripts`
1. `grep -rn -E "damage_flags ?[~=]?= ?[0-9]|damage_type ?[~=]= ?[0-9]|order_type ?[~=]= ?[0-9]|GetAbilityType\(\) ?[~=]= ?[0-9]" V` → no output.
2. `grep -rn "bit.band(.*DOTA_DAMAGE_FLAG_REFLECTION" V` → exactly 4 lines: spectre_custom_dispersion.lua, centaur_custom_return.lua, global_damage_effects.lua, item_custom_octarine_core.lua.
3. `grep -rn -c "DOTA_ABILITY_TYPE_ULTIMATE" V/abilities/heroes/ogre_magi_custom_multicast.lua V/abilities/heroes/zuus_custom_thundergods_wrath.lua V/lib/illusion.lua` → `1` for each file.
4. `grep -n -E "DOTA_UNIT_ORDER_MOVE_TO_POSITION|DOTA_UNIT_ORDER_HOLD_POSITION" V/abilities/other/hero_attribute_fix.lua` → 2 lines (the former `== 1` at ~:298 and `== 10` at ~:314).
5. `scripts/agents/check.sh lua` → `CHECK RESULT: OK (lua)`.
6. `python3 scripts/agents/aoh_lint.py 0011` → 0 fail (NEEDS APPROVAL expected).
7. `git diff --stat feat/p0-foundation...HEAD` → only allowed_paths + this task file; each Lua file changes ≤ 3 lines.
8. [human] Local game with Spectre (Dispersion) and Centaur (Retaliate) taking boss damage, and a hero holding Octarine Core: damage is reflected/returned once per hit, no freeze or damage loop; Ogre Multicast and Zeus ultimate still skip ultimates as before; blink-movement modifier still ends on hold (H); console has no Lua error from the 10 files.

## Notes from teamlead
Exact replacements (values from Valve's enums; do not re-derive):
| file:line (approx.) | now | becomes |
|---|---|---|
| spectre_custom_dispersion.lua:161 | `event.damage_flags ~= 16` | `bit.band(event.damage_flags, DOTA_DAMAGE_FLAG_REFLECTION) == 0` |
| centaur_custom_return.lua:60 | `keys.damage_flags ~= 16` | `bit.band(keys.damage_flags, DOTA_DAMAGE_FLAG_REFLECTION) == 0` |
| centaur_custom_return.lua:72 | `damage_flags = 16,` | `damage_flags = DOTA_DAMAGE_FLAG_REFLECTION,` |
| global_damage_effects.lua:39 | `keys.damage_flags ~= 16` | `bit.band(keys.damage_flags, DOTA_DAMAGE_FLAG_REFLECTION) == 0` |
| global_damage_effects.lua:85 | `keys.damage_type ~= 1` | `keys.damage_type ~= DAMAGE_TYPE_PHYSICAL` |
| item_custom_octarine_core.lua:64 | `keys.damage_flags ~= 16 and keys.damage_type ~= 1` | `bit.band(keys.damage_flags, DOTA_DAMAGE_FLAG_REFLECTION) == 0 and keys.damage_type ~= DAMAGE_TYPE_PHYSICAL` |
| item_custom_ballista.lua:105 | `damage_flags = 16,` | `damage_flags = DOTA_DAMAGE_FLAG_REFLECTION,` |
| modifier_tier_5.lua:67 | `damage_flags = 16,` | `damage_flags = DOTA_DAMAGE_FLAG_REFLECTION,` |
| ogre_magi_custom_multicast.lua:88, zuus_custom_thundergods_wrath.lua:52, lib/illusion.lua:15 | `GetAbilityType() ~= 1` | `GetAbilityType() ~= DOTA_ABILITY_TYPE_ULTIMATE` |
| hero_attribute_fix.lua:298 | `keys.order_type == 1` | `keys.order_type == DOTA_UNIT_ORDER_MOVE_TO_POSITION` |
| hero_attribute_fix.lua:314 | `keys.order_type == 10` | `keys.order_type == DOTA_UNIT_ORDER_HOLD_POSITION` |
- Backlog says "×13" for `damage_flags ~= 16`; the repo has 4 compares + 3 literal assignments (grep 2026-10-29). The table above is the full scope.
- `damage_type` is a single value per damage instance (not a mask) → plain `~=` with the enum is correct.
- The engine always fills `damage_flags` in damage events: no `or 0` guard. The bit.band expression stays inline (it is the rule-4 idiom itself); no new helper, no lib/my.lua change.
- No other edits in these files (legacy globals are baselined). If check.sh reports "fixed" baseline entries, run `python3 tools/luacheck_ratchet.py --prune`, never `--update-baseline`.
- Out of scope: GetItemInSlot numbers (0009), DOTA_ATTRIBUTE_ALL (0010), DOTA_UNIT_TARGET_FLAGS_NONE (0023).

## Handoff

## Result

## Review

## QA
