---
id: 0006
title: CustomGameEvent handlers read keys.PlayerID, dash checks unit ownership
status: done
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
reviewed_sha: 514bcfdd75e0c7a8b6cc931870bd20ba4cb75f5b
qa_sha: 514bcfdd75e0c7a8b6cc931870bd20ba4cb75f5b
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
Round 1 (commit 514bcfd)
- Changes: `local playerID = keys.PlayerID` is now the first line of DifficultyClicked, SettingsUpdate
  (aohgamemode.lua), CreditsClicked, Transaction and SkillSelected (aohgameskills.lua). Every
  `keys.id` became `playerID`. The outgoing field `id = playerID` keeps its name.
  In DifficultyClicked the update_type=1 payload is now built in a local `update` table that fits
  on one line. As a multi-line table, aoh_lint misread the field `id = playerID,` as a global
  assignment (false positive).
- dashmanager.lua: new local guard `DashableHero(unit, keys)` (nil / IsNull guard, then
  `GetPlayerOwnerID() ~= keys.PlayerID`, then the existing IsHero/HasModifier check). The loop over
  `keys.units` is kept. The leaked global `hero` is now local. Dota's Lua 5.1 has no `goto`, so
  the guard lives in a helper instead of a `continue`.
- Callers: these handlers are only registered as CustomGameEvent listeners (aohgamemode.lua
  DifficultyClicked, aohgameskills.lua Init, dashmanager.lua Init). No Lua caller passes `keys`
  directly.
- tools/luacheck.baseline: I ran `luacheck_ratchet.py --prune`, which removed the 4 `hero` global
  entries in dashmanager.lua. I also edited the pre-existing aohgamemode.lua W431 `fx` entry by
  hand: its message includes a line number, which moved from 399 to 397.
- Verified: DoD 1-4 greps hold (0 / 0 / 3 / function+ownership+IsNull lines, no `hero =`).
  `check.sh lua` → CHECK RESULT: OK (lua). `aoh_lint.py 0006` → 0 fail, NEEDS APPROVAL.
  `git diff --stat` holds only allowed_paths + this task file.
- [human] playtest (DoD 8): 2-player local lobby.
  1. Each player votes difficulty and toggles a modifier. The vote panel updates under the right
     player's slot.
  2. Each player clicks credits once: +1 currency each, diamond particle over their own hero.
  3. Buy a perk, then refund it: currency goes −N, then +N.
  4. Dash (builtin blink) with your own hero: it moves. Dash with an allied hero selected: it does
     not move.
  The console must show no `Script Runtime Error` mentioning aohgamemode.lua, aohgameskills.lua or
  dashmanager.lua.

## Review
APPROVE
Round 1 (code head 514bcfd). Checklist:
1. Spec: each of the 6 handlers (DifficultyClicked, SettingsUpdate, CreditsClicked, Transaction,
   SkillSelected, Dash) now reads `keys.PlayerID`. The outgoing `id = playerID` fields keep their
   names. Dash skips nil, IsNull and foreign-owned units, keeps the loop and the
   IsHero/HasModifier check, and `hero` is now local. That matches the DoD and the teamlead notes
   (ADR-0002 Lua rule 5), with nothing extra. Lua 5.1 has no `goto`, so a guard helper
   (`DashableHero`) instead of `continue` is fine.
2. Scope: 4 files, all in allowed_paths, plus this task file. No Panorama file and no test file.
   The baseline was pruned, not `--update-baseline`. The one hand edit
   (aohgamemode.lua W431 `fx`, line 399→397) only follows the line shift. It is acceptable and qa
   re-runs check.sh.
3. Conventions: the change adds no globals (it removes one). No magic numbers. No KV changes.
4. Correctness: ownership is checked against the engine-set PlayerID before any use, and the
   handle IsNull guard comes first. No timers, particles or modifiers are added. Pre-existing nil
   risks (`GetSelectedHeroEntity` with no hero picked, `modifiercount[playerID]` for an
   uninitialised slot) are unchanged and out of scope.
5. KV: not touched.
6. Verification: I grepped and confirmed the DoD 1–4 claims. `keys.id` appears 0 times. `keys.PlayerID` is
   the first line of each handler (aohgameskills.lua:106/115/198, aohgamemode.lua:302/817), with
   the ownership line at dashmanager.lua:15. aoh_lint: 0 fail, 0 warn, NEEDS APPROVAL. The [human]
   DoD 8 is listed for the owner, not claimed.
7. Hygiene: no print, no TODO, no dead code added. English.

## QA
PASS
1. DoD 1: `keys.id` count is 0 in aohgamemode.lua and 0 in aohgameskills.lua.
2. DoD 2: `keys.PlayerID` appears 3 times in aohgameskills.lua.
3. DoD 3: dashmanager.lua has the function line (24), the ownership line (15) and the IsNull line (12).
4. DoD 4: no `hero = ` global assignment remains in dashmanager.lua. `hero` is a local in `DashableHero`.
5. DoD 5: `check.sh lua` → CHECK RESULT: OK (lua). Log: logs/check-20261029-014001.log.
6. DoD 6: `aoh_lint.py 0006` → 0 fail, 0 warn, NEEDS APPROVAL (expected).
7. DoD 7: diff touches only the 3 allowed vscripts, tools/luacheck.baseline and this task file. No Panorama file.

For the human (DoD 8), 2-player local lobby:
- Each player votes difficulty. The vote counter must update for the right player.
- Each player clicks credits once: +1 currency each.
- Buy and refund a perk.
- Dash (builtin blink) with your own hero: it moves. With an allied hero selected, it must not move.
- The console must show no Script Runtime Error from aohgamemode.lua, aohgameskills.lua or dashmanager.lua.
