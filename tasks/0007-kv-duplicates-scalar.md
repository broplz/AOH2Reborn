---
id: 0007
title: KV duplicates, part 1 — remove the 6 duplicated entries and 19 duplicated scalar keys (last copy wins)
status: done
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
reviewed_sha: 6a8ec86a1da89e77c554cc11e7963bdce25b6100
qa_sha: 6a8ec86a1da89e77c554cc11e7963bdce25b6100
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
Round 1. Deleted the earlier copy of 6 duplicated entries and 19 duplicated scalar keys (last copy
wins) and removed exactly those 25 lines from tools/kvcheck.baseline by hand.

Verified: `scripts/agents/check.sh kv` → `CHECK RESULT: OK (kv)`. Baseline greps: duplicated entry 0,
scalar-key regex 0, `duplicate key` 29, riki_custom_dagger 1. `git diff -U0` shows deletions only,
with one exception: in npc_courier_replacement the whitespace-only line (4 tabs) after
CombatClassDefend became an empty line (the Edit tool strips whitespace-only lines); no KV effect.
I spot-checked `--show item_plain_perma` only; the other sites are covered by kvcheck failing on any
remaining duplicate that is not in the baseline.

| entry | key | kept value | dropped value |
|---|---|---|---|
| legion_commander_press_the_attack | (entry) | duration 5.5, hp_regen 30 45 60 75 (no 02) | duration 5.0, attack_speed 30 60 90 120, hp_regen 30 40 50 70 |
| pangolier_swashbuckle | (entry) | damage 32 63 90 117, strikes 6 7 8 9 (no cooldown/04) | AbilityCooldown 12 10 8 6, attack_interval 0.05, damage 10 20 30 40, strikes 9 10 11 12 |
| shadow_shaman_voodoo | (entry) | AbilityCooldown 18 | AbilitySpecial movespeed 100, duration 1.25 1.6 1.95 2.3 |
| special_bonus_unique_nyx_2 | (entry) | value 280 + ad_linked_ability | value 1000 |
| item_great_manta | (entry) | identical | identical |
| item_recipe_great_manta | (entry) | identical | identical |
| boss_aghanim_spell_swap | AbilityTextureName | rubick_spell_steal | aghanim_spell_swap |
| boss_aghanim_summon_portals | AbilityTextureName | aghanim_spears | aghanim_summon_portals |
| npc_dota_hero_marci | AttributeAgilityGain | 2.40000 | 2.700000 |
| item_assault_temp | ItemCost | 9050 | 0 |
| item_dark_bloodstone | ItemInitialCharges | 0 | 0 |
| item_dark_bloodstone | ItemDisplayCharges | 0 | 0 |
| item_bag_of_gold | ItemKillable | 0 | 0 |
| item_pocket_rax | ItemPurchasable | 1 | 1 |
| item_pocket_rax_ranged | ItemPurchasable | 1 | 1 |
| item_plain_perma | ItemQuality | consumable | epic |
| item_plain_perma | ItemShopTags | consumable | regen_health;regen_mana;mana_pool;health_pool |
| item_player_unstoppable | ItemSellable | 0 | 0 |
| npc_boss_luna | AttackCapabilities | DOTA_UNIT_CAP_RANGED_ATTACK | DOTA_UNIT_CAP_MELEE_ATTACK |
| npc_boss_shredder | BaseClass | npc_dota_creature | npc_dota_creature |
| npc_boss_shredder | HasInventory | 1 | 1 |
| npc_boss_aghanim | HasInventory | 1 | 1 |
| npc_courier_replacement | CombatClassAttack | DOTA_COMBAT_CLASS_ATTACK_BASIC | DOTA_COMBAT_CLASS_ATTACK_HERO |
| npc_courier_replacement | CombatClassDefend | DOTA_COMBAT_CLASS_DEFEND_BASIC | DOTA_COMBAT_CLASS_DEFEND_HERO |
| npc_boss_clockwerk_rush | vscripts | bosses/attack_ancient.lua | bosses/attack_move.lua |

Open questions: none blocking. The kept clockwerk_rush vscripts (attack_ancient) and Marci's 2.4 are
what the engine used before ("last wins" per owner); worth a glance at the [human] playtest.

Owner playtest ([human], DoD 8): shop shows item_assault_temp at 9050; item_pocket_rax purchasable;
item_great_manta + recipe build; Marci agility gain 2.4/level; Clockwerk rush and Shredder bosses
spawn and act; no KV errors in the console at load.

## Review
APPROVE

1. Spec: I checked all 25 sites against the `feat/p0-foundation` base by line number. The FIRST copy is the one deleted in each case: assault_temp 6780 (9050 kept at 6785), dark_bloodstone 9724/9725, pocket_rax 10072, pocket_rax_ranged 10122, bag_of_gold 3714, player_unstoppable 10015, plain_perma, marci, luna, shredder BaseClass 4482 and HasInventory 4492 (4526 kept), aghanim HasInventory 6553 (6632 kept), clockwerk_rush vscripts 3825 (attack_ancient 3871 kept), courier 7242/7243 (7261/7262 kept), and the 4 override entries. For great_manta, git displays the deletion as the second pair (base 5033/5046). The two pairs are adjacent and byte-identical (I checked `--show` against the deleted hunk), so deleting either gives the same file. This matches "identical" in the table.
2. Scope: only allowed_paths are touched. No tests are touched.
3/4. Conventions and Dota correctness: not applicable, because there is no Lua. aoh_lint reports 0 fail and 0 warn. It needs approval only because npc_heroes_custom.txt changed and DoD 8 is a [human] item. Both are expected.
5. KV: the change only deletes lines, so no new keys or localization are needed. qa re-runs kvcheck.
6. Verification: the table values match the base file at every site I checked. The only `+` line is at npc_units_custom.txt:7237: a whitespace-only line became empty. ## Result discloses this, and it has no KV effect. I accept it as the documented exception to DoD 7.
7. Hygiene: nothing to report. DoD 8 [human] is listed for the owner and not claimed.

## QA
PASS

1. `scripts/agents/check.sh kv` → `CHECK RESULT: OK (kv)` (log logs/check-20261029-022126.log).
2. DoD 1-4: baseline greps return 0 / 0 / 29 / 1 as required.
3. DoD 6: `--show` on item_assault_temp (ItemCost 9050 once), npc_boss_clockwerk_rush (vscripts attack_ancient once), legion_commander_press_the_attack (one entry, duration 5.5) match the Result table. The diff of the other sites shows the first copy deleted at each site.
4. DoD 7: diff stat touches only allowed_paths plus this task file. The diff has deletions only, except the whitespace-only line in npc_units_custom.txt (npc_courier_replacement) that became empty. It is disclosed in ## Result and has no KV effect.

For the human (DoD 8), in a local lobby:
- Shop: item_assault_temp costs 9050. item_pocket_rax and item_pocket_rax_ranged are purchasable.
- item_great_manta and its recipe build as before.
- Marci gains 2.4 agility per level.
- The Clockwerk rush boss (attack_ancient.lua) and the Shredder boss spawn and act as before.
- The console shows no KV or Lua errors at load.
