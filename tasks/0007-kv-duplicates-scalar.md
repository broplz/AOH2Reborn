---
id: 0007
title: KV duplicates, part 1 — remove the 6 duplicated entries and 19 duplicated scalar keys (last copy wins)
status: ready
epic: p1
prefix: p1
kind: code
size: M
role: developer
base: feat/p0-foundation
branch: task/0007-kv-duplicates-scalar
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/npc/npc_abilities_custom.txt
  - game/dota_addons/attackcopy/scripts/npc/npc_abilities_override.txt
  - game/dota_addons/attackcopy/scripts/npc/npc_items_custom.txt
  - game/dota_addons/attackcopy/scripts/npc/npc_units_custom.txt
  - game/dota_addons/attackcopy/scripts/npc/npc_heroes_custom.txt
  - tools/kvcheck.baseline
checks: kv
tests: []
needs_approval: true
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
---

## Goal
Audit §A6 / ADR-0002 §KV ("без дублей ключей и записей"). tools/kvcheck.baseline lists 6
duplicated top-level entries and 48 duplicated keys. The engine keeps one copy, and per the owner
(backlog 0007) that is the LAST one. This task deletes the earlier copy for every duplicated
entry and for every duplicated **scalar** key, so the engine sees the same data as before. The
29 list-like duplicates (AbilitySpecial numbering, datadriven actions, ControlPointEntities,
wearables, precache, OffensiveAbilities) are left alone: whether the engine iterates all of them
is unverified (docs/reports/decisions-needed.md, 2026-10-29).

## Definition of Done
B = tools/kvcheck.baseline
1. `grep -c "duplicated entry" B` → `0`.
2. `grep -c -E "duplicate key '(AbilityTextureName|AttributeAgilityGain|ItemCost|ItemDisplayCharges|ItemInitialCharges|ItemKillable|ItemPurchasable|ItemQuality|ItemSellable|ItemShopTags|AttackCapabilities|BaseClass|CombatClassAttack|CombatClassDefend|HasInventory|vscripts)'" B` → `0`.
3. `grep -c "duplicate key" B` → `29` (the list-like ones, untouched).
4. `grep -c "riki_custom_dagger" B` → `1` (not a duplicate; out of scope).
5. `python3 tools/kvcheck.py` → no FAIL outside the baseline (`CHECK RESULT: OK (kv)` via
   `scripts/agents/check.sh kv`).
6. For each of the 25 fixed sites, `python3 tools/kvcheck.py --show <entry>` shows the
   key/entry exactly once, with the value of the former LAST copy. ## Result has a table
   `entry | key | kept value | dropped value`, and duplicated entries list the differing keys or "identical".
7. `git diff --stat feat/p0-foundation...HEAD` → only allowed_paths + this task file; `git diff`
   shows deletions only in KV files (no `+` line except baseline edits).
8. [human] Local lobby. Confirm the "last copy wins" rule on visible values: the shop shows
   `item_assault_temp` at the kept ItemCost, and `item_pocket_rax` purchasability matches the kept
   ItemPurchasable. `item_great_manta` and its recipe build as before. Marci's agility gain per level
   equals the kept AttributeAgilityGain. The Clockwerk rush boss and the Shredder boss spawn and act
   as before. No KV/Lua errors appear in the console at load.

## Notes from teamlead
- The 25 sites, all named in B:
  - Duplicated entries (6): npc_abilities_override.txt `legion_commander_press_the_attack`,
    `pangolier_swashbuckle`, `shadow_shaman_voodoo`, `special_bonus_unique_nyx_2`;
    npc_items_custom.txt `item_great_manta`, `item_recipe_great_manta` → delete the FIRST block
    (whole entry, braces included).
  - Scalar keys (19): `AbilityTextureName` in boss_aghanim_spell_swap and boss_aghanim_summon_portals;
    `AttributeAgilityGain` in npc_dota_hero_marci; `ItemCost` item_assault_temp; `ItemDisplayCharges`
    and `ItemInitialCharges` item_dark_bloodstone; `ItemKillable` item_bag_of_gold; `ItemPurchasable`
    item_pocket_rax and item_pocket_rax_ranged; `ItemQuality` and `ItemShopTags` item_plain_perma;
    `ItemSellable` item_player_unstoppable; `AttackCapabilities` npc_boss_luna; `BaseClass` and
    `HasInventory` npc_boss_shredder; `HasInventory` npc_boss_aghanim; `CombatClassAttack` and
    `CombatClassDefend` npc_courier_replacement; `vscripts` npc_boss_clockwerk_rush → delete the
    FIRST line, keep the last.
- Do NOT touch: any `duplicate key '0N'` in AbilitySpecial, RunScript/FireEffect/DelayedAction/
  SpawnUnit/ApplyModifier/AttachEffect, CASTER/TARGET in ControlPointEntities, Wearable5,
  particle_folder, Ability2 in OffensiveAbilities.
- Baseline: remove exactly the fixed lines by hand (Edit). Never run `--update-baseline`. Lines have no
  line numbers, so other lines stay valid.
- Find sites with `python3 tools/kvcheck.py --no-baseline --entries <name>` (it prints file:line), then
  Read with offset/limit ≤ 400. Never Read a KV file whole.
- Count note: backlog says "4 entries / 55 keys"; the repo baseline has 6 / 48 (+1 ScriptFile).
  Go by the baseline.
- If a kept value looks like an obvious typo, keep it anyway (behaviour-identical) and add one line under
  "Found by agents" in tasks/backlog.md.

## Handoff

## Result

## Review

## QA
