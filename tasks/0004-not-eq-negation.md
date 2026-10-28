---
id: 0004
title: fix the 6 `not x ==/~= y` sites (luacheck W582) and stop ignoring 582
status: done
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
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/heroes/windrunner_force_fire_toggle.lua
  - tools/gen_luacheckrc.py
  - .luacheckrc
  - tools/luacheck.baseline
checks: lua
tests: []
needs_approval: true
returns: 0
sessions: 1
blocked_reason: 
reviewed_sha: 2dfe4edfb9801d7bc657599946a557a66cd0626e
qa_sha: 2dfe4edfb9801d7bc657599946a557a66cd0626e
---

## Goal
In Lua `not x == y` parses as `(not x) == y`. Fix the 5 legacy sites so they say what they mean,
then remove the `'582'` entry from the luacheck ignore list so new ones fail.

## Definition of Done
V = `game/dota_addons/attackcopy/scripts/vscripts`
1. `grep -rn -E "\bnot ([A-Za-z_][A-Za-z0-9_.:]*(\([^()]*\))?) (==|~=) " V` → no output (owner: the old regex also matched `not a:IsIllusion() and b ~= c`, which is correct Lua).
2. `grep -n "if self._lastEnemiesRemaining ~= nEnemiesRemaining then" V/aohgameround.lua` → `132:` …
3. `grep -n "if key == self.open_ticket and self.lockout ~= true then" V/modifiers/modifier_boss.lua` → `56:` …
4. `grep -n -E "and hAbility\.bAgh(Disabled|Dummy) ~= true" V/abilities/bosses/boss_aghanim_spell_swap.lua` → lines `266:` and `267:`.
5. `grep -n "if self.has_procced ~= true then" V/abilities/bosses/boss_void_spirit_counter.lua` → `108:` …
6. `grep -c "582" tools/gen_luacheckrc.py` → `0`; `grep -c "582" .luacheckrc` → `0`.
7. `scripts/agents/check.sh lua` → `CHECK RESULT: OK (lua)`.
8. `scripts/agents/check.sh lua --all-files` → `CHECK RESULT: OK (lua)`.
9. `git diff --stat feat/p0-foundation...HEAD` → only files from allowed_paths + this task file;
   each of the 5 Lua files shows a 1-2 line change (no reformatting).
10. `grep -n "and target:GetTeam() ~= self.parent:GetTeam()" V/abilities/heroes/windrunner_force_fire_toggle.lua` → `89:` …
11. `grep -c "W582" tools/luacheck.baseline` → `0`.
12. [human] Windrunner with the Focus Fire toggle on: attack (deny) an allied creep → Focus Fire is
    NOT cast; attack an enemy → Focus Fire is cast as before.

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
- Re-spec 2026-10-29 (teamlead, after session 1 blocked on the 6th site):
  - The 5 original sites and the 582 removal are already done on the branch (48fd8c2) — do not redo
    them. Remaining work: one line in windrunner_force_fire_toggle.lua, then DoD 1-11.
  - windrunner_force_fire_toggle.lua:89 `and not target:GetTeam() ~= self.parent:GetTeam()` →
    `and target:GetTeam() ~= self.parent:GetTeam()` (the intent rewrite). Today the clause is
    `false ~= number` → always true, so auto Focus Fire also fires on allied (deny) targets. The fix
    is a gameplay change, hence `needs_approval: true` and the [human] DoD 12; list it in ## Result
    as a behaviour change. Do not delete the clause, do not touch any other line of that file.
  - Never add the W582 to tools/luacheck.baseline (DoD 11).
  - This takes the "windrunner `not`" item out of the unplanned p1 one-line-bugs backlog entry;
    whoever plans that batch drops it.

## Handoff
Session 2 (commit 06f7fb9). Blocked only on a spec defect in DoD 1; no code work is left.

Done: windrunner_force_fire_toggle.lua:89 → `and target:GetTeam() ~= self.parent:GetTeam()` (one line).
DoD 2-11 hold (run this session): check.sh lua → OK; check.sh lua --all-files → OK (W582 gone, no
baseline change); `582`/`W582` grep in gen_luacheckrc.py, .luacheckrc, luacheck.baseline → none;
grep lines 2/3/4/5/10 at the expected line numbers; diff --stat shows only allowed_paths + this task
file + tasks/backlog.md (session 1's Found-by-agents line, allowed by the rules); each Lua file 1-2 lines.

Failing: DoD 1 as written prints 2 lines, both correct code outside allowed_paths:
- items/item_unstoppable.lua:35 `if not self.parent:IsIllusion() and self.parent:GetName() ~= "npc_dota_hero_treant" then`
- items/item_plain_ring.lua:17 `if not parent:IsIllusion() and parent:GetUnitLabel() ~= "spirit_bear" then`
`[^=~]+` spans across ` and `; luacheck (DoD 8, the authority for W582) does not flag them.

Next (teamlead): replace the DoD 1 regex with `not [^=~ ]+ (==|~=) ` (no spaces in the operand).
Verified: `git grep -n -E "not [^=~ ]+ (==|~=) " feat/p0-foundation -- V` lists exactly the 6 fixed
sites on base, and `grep -rn -E` with it on this branch prints nothing. Then set status: review
(or ready for a session that only fills ## Result — the draft below is complete).

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
Draft (session 2). Changed: 6 `not x ==/~= y` sites rewritten per the notes (aohgameround.lua:132,
modifier_boss.lua:56, boss_aghanim_spell_swap.lua:266-267, boss_void_spirit_counter.lua:108,
windrunner_force_fire_toggle.lua:89); `'582'` removed from tools/gen_luacheckrc.py and .luacheckrc.
Callers: no lib/ helper or modifier_boss API changed (only the condition inside QueryTicket).
Verified: check.sh lua and check.sh lua --all-files → `CHECK RESULT: OK (lua)`; DoD 2-11 greps as
expected. DoD 1: see Handoff (regex false positives).

Behaviour changes:
- windrunner_force_fire_toggle: auto Focus Fire no longer triggers on allied (deny) targets
  (the old clause was `false ~= number` → always true).
- aohgameround.lua:132 block now runs once per enemy-count change (stores the count, debug_print only).

[human] playtest (DoD 12): Windrunner, Focus Fire toggle on. Attack-deny an allied creep → Focus Fire
is NOT cast (no modifier_windrunner_focusfire on the hero, no Focus Fire cooldown starts). Attack an
enemy → Focus Fire is cast as before (cooldown starts). No console line exists for this path; the
ability cooldown on the HUD is the proof.

## Review
APPROVE

Checklist:
1. Spec: all 6 rewrites match the notes exactly (aohgameround.lua:132, modifier_boss.lua:56,
   boss_aghanim_spell_swap.lua:266-267, boss_void_spirit_counter.lua:108, windrunner_force_fire_toggle.lua:89).
   `'582'` is removed from both tools/gen_luacheckrc.py:76 and .luacheckrc:10, and the text matches. Nothing else changed.
   I ran the respecced DoD 1 grep on this branch and it prints nothing. DoD 2-5 and 10 line numbers match the diff hunks.
2. Scope: the diff touches only allowed_paths, this task file and tasks/backlog.md (one Found-by-agents
   line, which the rules allow). Each Lua file changes 1-2 lines with no reformatting. No tests touched.
3. Conventions: no new globals, numbers, LinkLuaModifier or KV changes. aoh_lint: 0 fail. Its 1 warning
   is the size count (7 files over the S file cap); that comes from the task's shape, not from the dev.
4. Dota correctness: these are condition-only edits inside existing guarded paths (`if IsServer()` blocks).
   Lua semantics hold: the flags are true/false/nil, so `x ~= true` behaves the same as `(not x) == true`.
   The windrunner and aohgameround changes are intended behaviour changes and are listed in ## Result.
5. KV: not touched.
6. Verification: I did not re-run check.sh (qa does). DoD 11 holds because tools/luacheck.baseline is not in the diff.
   The [human] DoD 12 is listed for the owner and not claimed.
7. Hygiene: no debug output was added. The `print` at boss_aghanim_spell_swap.lua:270 was already there before this task.

Non-blocking (qa/owner, no return needed):
1. tasks/0004-not-eq-negation.md:139: the "DoD 1: see Handoff (regex false positives)" sentence in ## Result is
   stale. DoD 1 was respecced and now passes. Also, the Result is still marked "Draft".
2. tasks/backlog.md:36: the Found-by-agents line for the windrunner site was resolved by this task.
   The teamlead should drop it when grooming.
3. aoh_lint shows NEEDS APPROVAL (core files aohgameround.lua/modifier_boss.lua + [human] DoD 12). This matches `needs_approval: true`.

## QA
PASS

1. DoD 1: both the original and the respecced regex print nothing.
2. DoD 2-5, 10: grep hits at 132, 56, 266/267, 108, 89 as specified.
3. DoD 6, 11: "582" count is 0 in gen_luacheckrc.py, .luacheckrc and luacheck.baseline; the diff of the two removals matches.
4. DoD 7, 8: `check.sh lua` and `check.sh lua --all-files` → CHECK RESULT: OK (lua). Logs: logs/check-20261029-002419.log, logs/check-20261029-002421.log.
5. DoD 9: diff --stat shows only allowed_paths, this task file and tasks/backlog.md; each Lua file changes 1-2 lines.
6. Note: the ## Result still says "Draft" and has a stale "DoD 1: see Handoff" sentence (non-blocking).

For the human:
- DoD 12: Windrunner with the Focus Fire toggle on. Attack (deny) an allied creep → Focus Fire is NOT cast (no cooldown starts). Attack an enemy → Focus Fire is cast as before.
- This is a gameplay change (needs_approval: true).
