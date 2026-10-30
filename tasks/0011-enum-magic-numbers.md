---
id: 0011
title: Magic numbers → enums (damage flags via bit.band, damage type, ability type, order type)
status: done
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
reviewed_sha: 0c8f9581c030bac694c296246a8b4559b803ffb0
qa_sha: 0c8f9581c030bac694c296246a8b4559b803ffb0
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
Round 1
- Changed: all 14 sites from the teamlead table. Reflection compares now use `bit.band(..., DOTA_DAMAGE_FLAG_REFLECTION) == 0`; literal `16` assignments use the enum; `damage_type ~= DAMAGE_TYPE_PHYSICAL`; hero_attribute_fix uses `DOTA_UNIT_ORDER_MOVE_TO_POSITION` / `DOTA_UNIT_ORDER_HOLD_POSITION`. Stylua forced multi-line `if` in 3 files (octarine_core, centaur_return, ogre_multicast), so those exceed 3 changed lines.
- DEVIATION from the table / DoD 3: ultimate checks use `ABILITY_TYPE_ULTIMATE`, not `DOTA_ABILITY_TYPE_ULTIMATE`. The DOTA_ name is not a Lua global (luacheck W113 via dota-data; `.luacheckrc` only has `ABILITY_TYPE_*`). In-game it would be nil, so `~= nil` is always true and ultimates would no longer be skipped. DoD 3 (`grep -c DOTA_ABILITY_TYPE_ULTIMATE`) therefore gives 0; the teamlead should fix the DoD/rule text.
- DoD 1 grep still prints `dark_seer_custom_ion_shell.lua:62: damage_flags = 0` (file not in allowed_paths; out of scope). Backlog line below.
- Verified: `scripts/agents/check.sh lua` → OK. aoh_lint not run by me.
- Owner playtest: DoD 8.

## Review
APPROVE
1. Spec: all 14 sites in the teamlead table are replaced exactly as listed, with no other logic changes. The `ABILITY_TYPE_ULTIMATE` deviation is correct. The Lua global is `ABILITY_TYPE_ULTIMATE` (.luacheckrc:22). `DOTA_ABILITY_TYPE_ULTIMATE` is only the KV string, so it would be nil in Lua and the ultimate filter would stop working. DoD 3 is wrong and gives 0; the teamlead should fix DoD 3 and the aoh-rules rule 4 text (already in backlog, tasks/backlog.md:38).
2. Scope: only allowed_paths, this task file and one backlog line are touched. DoD 7's "≤ 3 lines" is exceeded in centaur_custom_return.lua:60-64, ogre_magi_custom_multicast.lua:88-92 and item_custom_octarine_core.lua:64-67. Stylua forced the multi-line `if` wrapping there, so I accept it.
3. Conventions: no new globals or numbers, and `bit.band` is used inline as the Notes ask. aoh_lint shows 3 FAILs, and all 3 are false positives in the linter, not in this code:
   - centaur_custom_return.lua:61: `unit == self.parent` is a comparison on a continuation line of a multi-line `if`, not an assignment.
   - item_custom_ballista.lua:105 and modifier_tier_5.lua:67: `damage_flags = …` is a field inside an `ApplyDamage({…})` table, not a global. The same line in centaur_custom_return.lua:76 is not flagged.
   The developer cannot fix this, because scripts/agents/ is outside allowed_paths. DoD 6 will therefore show 3 fails. QA/teamlead: treat these 3 as known false positives, or fix aoh_lint (table fields and `if` continuation lines) in a separate task.
4. Dota correctness: the semantics hold. `bit.band(flags, REFLECTION) == 0` is the correct replacement for `~= 16`. The enum values match the old numbers: DAMAGE_TYPE_PHYSICAL=1, ORDER_MOVE_TO_POSITION=1, HOLD_POSITION=10, ABILITY_TYPE_ULTIMATE=1. No new handles, timers or particles. One pre-existing issue, out of scope: the octarine particle at item_custom_octarine_core.lua:69 is never released.
5. KV: not touched.
6. Verification: check.sh OK is claimed (qa re-runs it). The Result honestly says aoh_lint was not run. The backlog line it mentions exists (tasks/backlog.md:38). DoD 8 is listed as [human] and not claimed.
7. Hygiene: no prints, TODOs or dead code; all English.

## QA
PASS
1. DoD 5: `check.sh lua` → CHECK RESULT: OK (luacheck 0, stylua 0).
2. DoD 1: grep prints only `dark_seer_custom_ion_shell.lua:62: damage_flags = 0`. That file is outside allowed_paths and `0` is not an enum site in the table, so it is accepted as out of scope (backlog line exists).
3. DoD 2: exactly 4 lines, in centaur_custom_return.lua:63, spectre_custom_dispersion.lua:161, global_damage_effects.lua:39 and item_custom_octarine_core.lua:65. OK.
4. DoD 3 (literal): `DOTA_ABILITY_TYPE_ULTIMATE` count is 0. The code uses `ABILITY_TYPE_ULTIMATE` (one per file in ogre_magi_custom_multicast.lua:91, zuus_custom_thundergods_wrath.lua:52, lib/illusion.lua:15). The Lua global is `ABILITY_TYPE_ULTIMATE`, so I accept this as a spec error. The teamlead should correct the DoD text.
5. DoD 4: 2 lines (hero_attribute_fix.lua:298 and :314). OK.
6. DoD 6: aoh_lint reports 3 FAIL. They are the false positives the reviewer described: `unit == self.parent` in centaur_custom_return.lua, and `damage_flags =` table fields in item_custom_ballista.lua and modifier_tier_5.lua. They are not real global assignments. The linter should be fixed in a separate task.
7. DoD 7: only allowed_paths, the task file and tasks/backlog.md changed. Three files exceed 3 lines (centaur_custom_return.lua +8/-2, ogre_magi_custom_multicast.lua, item_custom_octarine_core.lua) because stylua wraps the `if` conditions. Accepted.

For the human (DoD 8):
- Play locally with Spectre (Dispersion) and Centaur (Retaliate) taking boss damage, and a hero holding Octarine Core. Check that damage is reflected once per hit, with no freeze or loop.
- Cast Ogre Multicast and Zeus ultimate, and check that ultimates are still skipped.
- Use the blink-movement modifier, then press H (hold). The modifier should end.
- Check that the console shows no Lua errors from the 10 files.
