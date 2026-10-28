---
id: 0008
title: Drop dead overrides for removed vanilla names (beastmaster boar, marci magic-immune talent)
status: ready
epic: p1
prefix: p1
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0008-removed-vanilla-hero-names
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/npc/npc_abilities_override.txt
  - game/dota_addons/attackcopy/scripts/npc/npc_heroes_custom.txt
  - tools/vanilla_diff.baseline
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
ADR-0002 §KV / compatibility traps: two names in our KV no longer exist in Dota build 6968, so
their overrides are dead and Marci's level-20 talent slot points at nothing. Remove the dead
`beastmaster_call_of_the_wild_boar` override, replace Marci's removed talent with its vanilla
successor, and shrink tools/vanilla_diff.baseline by those two lines. Scope is deliberately the
two hero-side names only; `boss_aghanim_spear` and `skeleton_king_vampiric_aura` need an owner
decision (docs/reports/decisions-needed.md) and are NOT part of this task.

## Definition of Done
N = `game/dota_addons/attackcopy/scripts/npc`
1. `grep -c -E "beastmaster_call_of_the_wild_boar|special_bonus_unique_marci_guardian_magic_immune" N/npc_abilities_override.txt` → `0`.
2. `grep -c "special_bonus_unique_marci_guardian_magic_immune" N/npc_heroes_custom.txt` → `0`.
3. `grep -n "special_bonus_unique_marci_guardian_strong_dispel" N/npc_heroes_custom.txt` → exactly one line, `"Ability15"` inside the `npc_dota_hero_marci` block.
4. `grep -c -E "beastmaster_call_of_the_wild_boar|marci_guardian_magic_immune" tools/vanilla_diff.baseline` → `0`; the file still has the `boss_aghanim_spear` and `skeleton_king_vampiric_aura` lines (2 data lines + header).
5. `python3 tools/vanilla_diff.py` → last line `vanilla_diff (...): 0 fail, 2 known, ...`; no line mentions beastmaster_call_of_the_wild_boar or marci_guardian_magic_immune.
6. `scripts/agents/check.sh kv` → `CHECK RESULT: OK (kv)`.
7. `python3 scripts/agents/aoh_lint.py 0008` → 0 fail (NEEDS APPROVAL expected).
8. `git diff --stat feat/p0-foundation...HEAD` → only the 3 allowed_paths + this task file.
9. [human] Local lobby, Marci: the talent tree shows the strong-dispel talent in the level-20
   slot where the magic-immune one used to be; taking it at level 20 gives no console error.
   Beastmaster: Call of the Wild still summons (hawk) and no console error mentions the boar.

## Notes from teamlead
- Entries to delete whole (key line through the matching closing brace), nothing else in the file:
  `npc_abilities_override.txt` `"beastmaster_call_of_the_wild_boar"` (≈ line 2564, only
  `duration 75`) and `"special_bonus_unique_marci_guardian_magic_immune"` (≈ line 920, value 2.0).
  Re-grep the line numbers; 0007 edited this file.
- `npc_heroes_custom.txt` ≈ line 391 in `npc_dota_hero_marci`:
  `"Ability15" "special_bonus_unique_marci_guardian_magic_immune"` →
  `"Ability15" "special_bonus_unique_marci_guardian_strong_dispel"`. That is the vanilla successor
  (tools/vanilla/heroes: Marci Ability17 in vanilla, an `=1` inline talent in
  `marci_guardian`'s AbilityValues); it is not used elsewhere in our Marci block. Keep the
  existing whitespace style of the block. Do not add an override entry for it (stand-alone
  talent overrides are dead since 7.34) and no tooltip (vanilla localization covers it).
- Baseline: delete exactly the two lines; never run `vanilla_diff.py --update-baseline`.
- Out of scope: boss_aghanim_spear, skeleton_king_vampiric_aura / skeleton_king_hidden_skeleton.lua
  (owner decision pending), the 126 talent WARN lines (task 0017), any AbilitySpecial → AbilityValues
  migration.

## Handoff

## Result

## Review

## QA
