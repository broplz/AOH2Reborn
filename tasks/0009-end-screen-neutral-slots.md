---
id: 0009
title: End screen reads neutral items via DOTA_ITEM_NEUTRAL_*_SLOT, stash no longer overwrites slot 9
status: done
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
reviewed_sha: b65db0b9e45ed2ced165263c569697adeaa32d33
qa_sha: b65db0b9e45ed2ced165263c569697adeaa32d33
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
Round 1: lib/end_screen.lua now reads inventory+backpack (DOTA_ITEM_SLOT_1..9 → items[0..8]) and the
neutral slots by enum through one key→slot table (items[9] active, items[10] passive); stash dropped.
Verified: check.sh lua OK. Not run: aoh_lint. Playtest: DoD item 7 [human].

## Review
APPROVE
1. Spec: matches DoD 1-3 and the teamlead's target shape. The loop runs DOTA_ITEM_SLOT_1..9 (0..8) into items[0..8], items[9] is the active neutral and items[10] the passive one, both read by enum through one key→slot table. Stash is dropped, so the Panorama contract (items[0..9]) still holds.
2. Scope: only lib/end_screen.lua plus the task file. No Panorama, no baseline change, no tests touched.
3. Conventions: the new code adds no globals (`payload_slots` is local), uses enums instead of magic numbers, and keeps the legacy globals baselined as instructed. aoh_lint: 0 fail, 0 warn, NEEDS APPROVAL (expected).
4. Dota correctness: runs server-side at game end with no timers, particles or events, so nothing to release or guard beyond the existing `if item`. Iterating with `pairs` is fine because the order of the keys doesn't matter.
5. KV: not touched.
6. Verification: Result says check.sh lua passed and that aoh_lint was not run; qa reruns check.sh. DoD 7 [human] is listed for the owner, not claimed.
7. Hygiene: no print calls, no leftover TODO, English only.
Non-blocking nit: end_screen.lua:96-99 rebuilds `payload_slots` for every player. It could be a file-level `local` built once, but that is optional.

## QA
PASS
1. DoD 1: grep count 0. DoD 2: count 2. DoD 3: one line (end_screen.lua:100).
2. DoD 4: check.sh lua → CHECK RESULT: OK (lua) (logs/check-20261029-023316.log).
3. DoD 5: aoh_lint 0 fail, 0 warn, NEEDS APPROVAL (expected).
4. DoD 6: diff touches only lib/end_screen.lua and this task file; no Panorama.

For the human:
- DoD 7: play a local game to the end with a hero holding 6 inventory items, 1 backpack item, a stash item, an active neutral and an enchantment. The end screen must show the 6+1 items and the active neutral in the neutral box (not the stash item). The console must show no Lua error from end_screen.lua.
