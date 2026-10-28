---
id: 0004
title: fix the 5 `not x == y` sites (luacheck W582) and stop ignoring 582
status: blocked
epic: p0
prefix: p0
kind: code
size: S
role: developer-hard
base: feat/p0-foundation
branch: task/0004-not-eq-negation
depends_on: [0005]
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/aohgameround.lua
  - game/dota_addons/attackcopy/scripts/vscripts/modifiers/modifier_boss.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_aghanim_spell_swap.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_void_spirit_counter.lua
  - tools/gen_luacheckrc.py
  - .luacheckrc
  - tools/luacheck.baseline
checks: lua
tests: []
needs_approval: false
returns: 0
sessions: 1
blocked_reason: 6th W582 site windrunner_force_fire_toggle.lua:89 is outside allowed_paths (hook); needs teamlead decision on the rewrite
reviewed_sha: 
qa_sha: 
---

## Goal
In Lua `not x == y` parses as `(not x) == y`. Fix the 5 legacy sites so they say what they mean,
then remove the `'582'` entry from the luacheck ignore list so new ones fail.

## Definition of Done
V = `game/dota_addons/attackcopy/scripts/vscripts`
1. `grep -rn -E "not [^=~]+ == " V` → no output.
2. `grep -n "if self._lastEnemiesRemaining ~= nEnemiesRemaining then" V/aohgameround.lua` → `132:` …
3. `grep -n "if key == self.open_ticket and self.lockout ~= true then" V/modifiers/modifier_boss.lua` → `56:` …
4. `grep -n -E "and hAbility\.bAgh(Disabled|Dummy) ~= true" V/abilities/bosses/boss_aghanim_spell_swap.lua` → lines `266:` and `267:`.
5. `grep -n "if self.has_procced ~= true then" V/abilities/bosses/boss_void_spirit_counter.lua` → `108:` …
6. `grep -c "582" tools/gen_luacheckrc.py` → `0`; `grep -c "582" .luacheckrc` → `0`.
7. `scripts/agents/check.sh lua` → `CHECK RESULT: OK (lua)`.
8. `scripts/agents/check.sh lua --all-files` → `CHECK RESULT: OK (lua)`.
9. `git diff --stat feat/p0-foundation...HEAD` → only files from allowed_paths + this task file;
   each of the 4 Lua files shows a 1-2 line change (no reformatting).

## Notes from teamlead
- Depends on 0005: without the luacheck ratchet, `check.sh lua` fails on the legacy warnings of
  these whole files (e.g. W111 class globals), not on this change.
- Exact rewrites (all flags below are only ever assigned true/false/nil — grep of assignments
  2026-10-29 — so `x ~= true` is behaviour-identical to today's `(not x) == true`):
  - modifier_boss.lua:56 `not self.lockout == true` → `self.lockout ~= true`
  - boss_aghanim_spell_swap.lua:266 `not hAbility.bAghDisabled == true` → `hAbility.bAghDisabled ~= true`
  - boss_aghanim_spell_swap.lua:267 `not hAbility.bAghDummy == true` → `hAbility.bAghDummy ~= true`
  - boss_void_spirit_counter.lua:108 `not self.has_procced == true` → `self.has_procced ~= true`
  - aohgameround.lua:132 `not self._lastEnemiesRemaining == nEnemiesRemaining` →
    `self._lastEnemiesRemaining ~= nEnemiesRemaining`. This one is NOT `~= true` (the backlog line
    was wrong for it): today `(not n) == number` is always false, so the block never runs. After
    the fix it runs once per change of the enemy count; the block only stores the count and calls
    `debug_print` (lib/my.lua:3), so no gameplay effect.
- Backlog says role developer; set to developer-hard because aohgameround.lua and modifier_boss.lua
  are core files (teamlead rule). Touch nothing else in them.
- 582 removal: in tools/gen_luacheckrc.py:76 delete the `"  '582', -- error-prone negation …"` list
  element; in .luacheckrc delete line 10 (the same text). Hand-editing the generated .luacheckrc is
  allowed here only because the generator needs the network; the two edits must match exactly.
- If `check.sh lua` reports W582 elsewhere (a site the grep missed), fix it the same way and list it
  in ## Result; if it reports "fixed" baseline entries, run `python3 tools/luacheck_ratchet.py --prune`
  (never --update-baseline).

## Handoff
Session 1 (commit 48fd8c2). Blocked: DoD 8 needs a file outside allowed_paths (guard_paths hook).

Done:
- The 5 sites rewritten exactly as in the notes (aohgameround.lua:132, modifier_boss.lua:56,
  boss_aghanim_spell_swap.lua:266-267, boss_void_spirit_counter.lua:108). One line each, no reformatting.
- `'582'` entry removed from tools/gen_luacheckrc.py:76 and .luacheckrc:10 (identical text).
- DoD 1-6 hold; DoD 7 `check.sh lua` → `CHECK RESULT: OK (lua)`.
- No lib/ helper or modifier_boss API changed (only the condition inside QueryTicket), so no callers to migrate.

Failing: DoD 8 `check.sh lua --all-files` → FAIL, ratchet: 1 new, 4341 known, 0 fixed:
`abilities/heroes/windrunner_force_fire_toggle.lua:89:8 (W582)` —
`and not target:GetTeam() ~= self.parent:GetTeam()`. The DoD-1 grep misses it because it is `not x ~= y`.
Today `(not team) ~= team` is `false ~= number` → always true, so the clause is a no-op and auto
focus-fire triggers on any attack target, allies (denies) included.

Tried: editing that file → blocked by guard_paths (not in allowed_paths). Did not hand-add the
warning to tools/luacheck.baseline: that hides a real bug and the notes forbid growing the baseline.

Next (teamlead): add `game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/windrunner_force_fire_toggle.lua`
to allowed_paths and pick the rewrite:
- intent (recommended): `and target:GetTeam() ~= self.parent:GetTeam()` — gameplay change: no
  auto focus-fire on allied targets; `[human]` check: toggle on, deny an allied creep → Focus Fire not cast;
  attack an enemy → Focus Fire cast.
- behaviour-identical: delete the clause.
Then rerun `scripts/agents/check.sh lua --all-files`. Also consider widening DoD 1 to
`grep -rn -E "not [^=~]+ (==|~=) " V`. Logged in tasks/backlog.md under Found by agents.

## Result

## Review

## QA
