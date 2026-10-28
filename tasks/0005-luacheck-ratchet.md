---
id: 0005
title: luacheck baseline ratchet (tools/luacheck_ratchet.py + tools/luacheck.baseline), --all-files green
status: ready
epic: p0
prefix: p0
kind: code
size: M
role: developer
base: feat/p0-foundation
branch: task/0005-luacheck-ratchet
depends_on: []
allowed_paths:
  - tools/luacheck_ratchet.py
  - tools/luacheck.baseline
  - tools/fixtures/luacheck_ratchet/new_global.lua
  - scripts/agents/check.sh
checks: lua
tests: []
needs_approval: false
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
---

## Goal
`scripts/agents/check.sh lua --all-files` reports ~4341 legacy luacheck warnings, so a task that
touches any legacy Lua file (aohgamemode.lua, modifier_boss.lua, …) fails `check.sh lua` on warnings
it did not write. Add a luacheck ratchet like `tools/kvcheck.baseline`: known legacy warnings are
recorded in `tools/luacheck.baseline`, only NEW warnings fail. Both scopes (changed files and
`--all-files`) go through it. Result: `check.sh lua --all-files` is green, new globals still fail.

## Definition of Done
R = `python3 tools/luacheck_ratchet.py`
1. `R --update-baseline` → last line `baseline written: <N> warnings` with N ≥ 4000. (Initial
   generation is this task's job; after merge only the owner runs --update-baseline.)
2. `grep -c -E ':[0-9]+:[0-9]+:' tools/luacheck.baseline` → `0` (no line/column numbers).
3. `head -1 tools/luacheck.baseline` → starts with `# luacheck baseline:`.
4. `R` (no args = default tree) → contains `0 new` and `RATCHET: OK`.
5. `R tools/fixtures/luacheck_ratchet/new_global.lua` → contains a line starting with
   `NEW tools/fixtures/luacheck_ratchet/new_global.lua:` and `(W111)`, plus `1 new` and `RATCHET: FAIL`.
6. `R --prune` → `baseline pruned: 0 removed` (run right after DoD 1).
7. `scripts/agents/check.sh lua --all-files` → `CHECK RESULT: OK (lua)`.
8. `scripts/agents/check.sh lua` → `CHECK RESULT: OK (lua)`.
9. `grep -c "luacheck_ratchet.py" scripts/agents/check.sh` → `1`; `grep -c -E "run luacheck luacheck" scripts/agents/check.sh` → `0`.
10. `git diff --stat feat/p0-foundation...HEAD` lists only the allowed_paths and this task file.

## Notes from teamlead
- Why a ratchet and not `allow_defined_top`: ADR-0001 §Решение 4 says luacheck must catch "new
  globals"; `allow_defined_top` would silence every top-level global, not only engine classes
  (ADR-0002 Lua rule 1). Mirror the kvcheck ratchet (tools/kvcheck.py:122-148) instead.
- tools/luacheck_ratchet.py (Python 3, stdlib only, ≤ ~130 lines):
  - Runs from the repo root: `luacheck --no-color --codes --formatter plain <paths>` via
    `subprocess.run`, cwd = repo root (so `.luacheckrc` applies). Default paths (no args):
    `game/dota_addons/attackcopy/scripts/vscripts tests` — the same as check.sh `--all-files`.
  - luacheck exit 0/1/2 = ok/warnings/errors (all parsed as entries); exit ≥ 3 = fatal → print its
    stderr and `RATCHET: FAIL (luacheck exit <n>)`, exit 1.
  - Normalize each output line `path:line:col: (Wxxx) msg` → `path: (Wxxx) msg` (regex on the first
    `:<digits>:<digits>:`). Baseline is a MULTISET (collections.Counter): one line per occurrence,
    duplicates kept, sorted. Lines starting with `#` are comments.
  - Check mode: `new = current − baseline` (Counter subtraction). Print each new occurrence as
    `NEW <raw luacheck line>` (raw keeps line numbers for the triage). Summary line
    `luacheck ratchet: <a> new, <b> known, <c> fixed` (fixed = baseline entries for linted files
    that no longer occur), then `RATCHET: OK` / `RATCHET: FAIL`; exit 1 iff new > 0.
  - `--update-baseline`: ignores path args, lints the default tree, writes header
    `# luacheck baseline: known legacy warnings (normalized, no line numbers). Shrink with --prune; never add by hand.`
    then the sorted lines; prints `baseline written: <N> warnings`.
  - `--prune`: lints the default tree, writes baseline := baseline ∩ current (Counter `&`), never
    adds; prints `baseline pruned: <k> removed`. Agents fixing legacy warnings run this, not --update-baseline.
- check.sh: replace only line 43 `run luacheck luacheck --no-color -q "${FILES[@]}"` with
  `run luacheck python3 tools/luacheck_ratchet.py "${FILES[@]}"`. Keep the step name `luacheck`.
  Update the header comment (lines 6-9) by one line mentioning the ratchet. Nothing else in check.sh.
- Fixture tools/fixtures/luacheck_ratchet/new_global.lua: exactly `leak_global_for_ratchet_test = 1`
  plus newline. It lives outside vscripts/ and tests/, so neither check.sh scope lints it. Must be
  stylua-clean anyway (tabs, no trailing spaces).
- Do not touch .luacheckrc or tools/gen_luacheckrc.py (W582 stays ignored; task 0004 removes it).
- The guard hook blocks running `luacheck` directly in Bash; calling it from the Python script is
  fine. The baseline is generated output: it does not count toward the M size cap.
- If `--all-files` stays red because of stylua (not luacheck), that is not this task: Handoff with
  the triage lines.

## Handoff

## Result

## Review

## QA
