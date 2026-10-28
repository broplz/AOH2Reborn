---
id: 0006
title: CustomGameEvent handlers read keys.PlayerID, dash checks unit ownership
status: ready
epic: p1
prefix: p1
kind: code
size: S
role: developer-hard
base: feat/p0-foundation
branch: task/0006-playerid-handlers
depends_on: [0005]
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/aohgamemode.lua
  - game/dota_addons/attackcopy/scripts/vscripts/aohgameskills.lua
  - game/dota_addons/attackcopy/scripts/vscripts/dashmanager.lua
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
Audit bug 7 / ADR-0002 §Решение 4 Lua rule 5: client events trust a player id from the payload
(`keys.id`), so any client can vote, take credits or buy perks for another player, and the `dash`
event moves any unit by entity index. Handlers must use `keys.PlayerID` (set by the engine) and the
dash handler must act only on units owned by that player.

## Definition of Done
V = `game/dota_addons/attackcopy/scripts/vscripts`
1. `grep -c -E "keys\.id([^A-Za-z_]|$)" V/aohgamemode.lua` → `0`; same for `V/aohgameskills.lua` → `0`.
2. `grep -c "keys.PlayerID" V/aohgameskills.lua` → ≥ `3` (one per handler: CreditsClicked, Transaction, SkillSelected).
3. `grep -n -E "^function DashManager:Dash|GetPlayerOwnerID\(\) ~= keys\.PlayerID|IsNull\(\)" V/dashmanager.lua` → the function line, one ownership line and one IsNull line.
4. `grep -n -E "^\s+hero = " V/dashmanager.lua` → no output (the leaked global is now `local`).
5. `scripts/agents/check.sh lua` → `CHECK RESULT: OK (lua)`.
6. `python3 scripts/agents/aoh_lint.py 0006` → 0 fail (NEEDS APPROVAL is expected).
7. `git diff --stat feat/p0-foundation...HEAD` → only allowed_paths + this task file; no Panorama file.
8. [human] 2-player local lobby: both players can vote difficulty (vote counter updates for the
   right player), click credits once each (+1 currency each), buy and refund a perk, and dash
   (builtin blink) with their own hero. Console shows no Lua error from these handlers.

## Notes from teamlead
- Handlers in scope (registered in aohgamemode.lua:497, aohgameskills.lua:89-91, dashmanager.lua:6):
  `AOHGameMode:DifficultyClicked` (aohgamemode.lua:301-321), `AOHGameSkills:CreditsClicked`
  (:105), `AOHGameSkills:Transaction` (:113), `AOHGameSkills:SkillSelected` (:195),
  `DashManager:Dash` (dashmanager.lua:9). Also `AOHGameMode:SettingsUpdate` (aohgamemode.lua:818,
  deprecated, not registered): replace its `keys.id` too so DoD 1 holds; do not delete it (dead
  code is task 0020).
- Shape: first line of each handler `local playerID = keys.PlayerID`, then every `keys.id` in that
  handler → `playerID`. Outgoing payload fields keep their names (`id = playerID` at :312/:320) —
  the Panorama side reads them.
- Dash: `local hero = EntIndexToHScript(unit)`; skip (continue via guard) when
  `not hero or hero:IsNull()` or `hero:GetPlayerOwnerID() ~= keys.PlayerID`; the existing
  IsHero/HasModifier check stays. Keep the loop over `keys.units`.
- Out of scope: Panorama sources (still send `id`; the server now ignores it; the JS is obfuscated,
  task 0021), `OnPlayerChat` (`keys.playerid` is engine-set by the player_chat game event),
  validating `keys.tier`/`keys.choice`.
- Base is feat/p0-foundation (the only active feature branch) although the item is phase p1.
- If check.sh reports "fixed" baseline entries (e.g. the old `hero` global), run
  `python3 tools/luacheck_ratchet.py --prune`, never --update-baseline.

## Handoff

## Result

## Review

## QA
