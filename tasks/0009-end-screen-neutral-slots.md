---
id: 0009
title: End screen reads neutral items via DOTA_ITEM_NEUTRAL_*_SLOT, stash no longer overwrites slot 9
status: ready
epic: p1
prefix: p1
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0009-end-screen-neutral-slots
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/lib/end_screen.lua
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
Audit bug 13 / ADR-0002 Lua rule 4: `end_screen_get_data` (lib/end_screen.lua:95-104) loops
`DOTA_ITEM_SLOT_1 .. DOTA_STASH_SLOT_6` (0..14), so stash slot 9 lands in `items[9]`, then reads
the neutral item with the magic number `GetItemInSlot(16)`. Since 7.38 there are two neutral slots
(16 active, 17 passive/enchantment). Read them by enum and stop the stash from colliding with the
key the Panorama end screen uses for the neutral item.

## Definition of Done
V = `game/dota_addons/attackcopy/scripts/vscripts`
1. `grep -c -E "GetItemInSlot\([0-9]+\)|DOTA_STASH_SLOT" V/lib/end_screen.lua` → `0`.
2. `grep -c -E "DOTA_ITEM_NEUTRAL_ACTIVE_SLOT|DOTA_ITEM_NEUTRAL_PASSIVE_SLOT" V/lib/end_screen.lua` → `2`.
3. `grep -n "DOTA_ITEM_SLOT_9" V/lib/end_screen.lua` → one line (the inventory+backpack loop bound).
4. `scripts/agents/check.sh lua` → `CHECK RESULT: OK (lua)`.
5. `python3 scripts/agents/aoh_lint.py 0009` → 0 fail (NEEDS APPROVAL expected).
6. `git diff --stat feat/p0-foundation...HEAD` → only allowed_paths + this task file; no Panorama file.
7. [human] Win or lose a local game with a hero holding 6 inventory items, 1 backpack item, an
   item in the stash, an active neutral and an enchantment: the end screen shows the 6+1 items
   and the active neutral in the neutral box (not the stash item); console has no Lua error
   from end_screen.lua.

## Notes from teamlead
- Panorama contract (content/.../panorama/scripts/end_screen.js, obfuscated, NOT to be edited):
  it reads `items[0..8]` (0-5 inventory, 6-8 backpack) and `items[9]` for the
  `NeutralItemContainer`. Keep those keys.
- Target shape: loop `DOTA_ITEM_SLOT_1 .. DOTA_ITEM_SLOT_9` → `items[slot]`; then
  `items[9]` = name of `GetItemInSlot(DOTA_ITEM_NEUTRAL_ACTIVE_SLOT)`, `items[10]` = name of
  `GetItemInSlot(DOTA_ITEM_NEUTRAL_PASSIVE_SLOT)` (not shown yet; the JS rewrite is task 0021).
  Per the no-duplicates rule, the two neutral reads go through one small table/loop
  (`{ [9] = DOTA_ITEM_NEUTRAL_ACTIVE_SLOT, [10] = DOTA_ITEM_NEUTRAL_PASSIVE_SLOT }`) or one local
  helper shared with the inventory loop, not two copy-pasted blocks.
- Stash items are dropped from the payload on purpose (the JS never showed them).
- Legacy globals in this file (`end_screen_get_data`, `formatted_number`, …) are baselined in
  tools/luacheck.baseline; do not fix them here. If check.sh reports "fixed" entries, run
  `python3 tools/luacheck_ratchet.py --prune`, never `--update-baseline`.
- Out of scope: Panorama, other GetItemInSlot sites (task 0011 handles magic numbers repo-wide).

## Handoff

## Result

## Review

## QA
