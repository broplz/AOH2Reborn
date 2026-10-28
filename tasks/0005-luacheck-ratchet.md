---
id: 0005
title: luacheck baseline ratchet (tools/luacheck_ratchet.py + tools/luacheck.baseline), --all-files green
status: done
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
returns: 2
sessions: 0
blocked_reason: 
reviewed_sha: 247ecc538f7b0cdb8f51afdfc1db07ef250bc30b
qa_sha: 247ecc538f7b0cdb8f51afdfc1db07ef250bc30b
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
Round 3
- QA 1: reworded the check.sh header comment (line 10) so it no longer contains `luacheck_ratchet.py`; `grep -c "luacheck_ratchet.py" scripts/agents/check.sh` → `1`.
- Verified: `check.sh lua --all-files` → `CHECK RESULT: OK (lua)`.

Round 2
- Review 1: removed the `LOC` regex; `normalize` uses `POS.sub(":", line, count=1)` (baseline unchanged: default run `0 new, 4341 known, 0 fixed`).
- Review 2: dropped the lambda and noqa; the in-scope baseline subset is a plain Counter comprehension.
- Verified: default run `RATCHET: OK`; fixture run still reports a new W111.

Round 1
- Added `tools/luacheck_ratchet.py` (check / `--prune` / `--update-baseline`, multiset baseline), `tools/luacheck.baseline` (4341 warnings, no line numbers), fixture `new_global.lua`; `check.sh` luacheck step now runs the ratchet (+1 header comment line).
- Verified: `--update-baseline` → 4341; `--prune` → 0 removed; default run → `0 new`, `RATCHET: OK`; fixture → `NEW …new_global.lua:1:1: (W111)`, `1 new`, `RATCHET: FAIL`; baseline has 0 line:col entries; `check.sh lua --all-files` and `check.sh lua` → `CHECK RESULT: OK (lua)`.
- Open questions: none. Nothing to playtest ([human] none).

## Review
APPROVE

Checklist notes (round 3):
- Spec: since reviewed_sha 34155f0 the only code change is check.sh:10. The header comment now says "luacheck runs through the ratchet: legacy warnings in tools/luacheck.baseline, only NEW ones fail." and no longer names `luacheck_ratchet.py`. The diff shows the string only on check.sh:44 (the call), so QA 1 / DoD 9 hold. The script, baseline and fixture are unchanged from round 2.
- Scope: 4 files, all in allowed_paths, plus the task file. No tests touched and no .claude/replay leak.
- Conventions/Dota correctness/KV: n/a (tooling only). aoh_lint: 0 fail, 1 size warn. The warning comes from the generated baseline, which the notes exempt.
- Verification: the Round 3 claim matches the diff. A hook blocked my DoD 9 grep for the reviewer role, so I read the diff instead. qa re-runs it.
- Hygiene: clean.

---
Checklist notes (round 2):
- Spec: round-1 item 1 fixed — the single `POS` regex (tools/luacheck_ratchet.py:19) handles both filtering (:30) and normalizing (:35, `count=1`); `LOC` is gone. Item 2 fixed — no lambda and no noqa; the in-scope subset is a plain comprehension (:84). Nothing else in the script changed. The behaviour still matches the teamlead notes.
- Scope: the same 4 files, all in allowed_paths; check.sh diff is unchanged from round 1 (line 44 plus one header line); no tests touched; no .claude/replay leak.
- Conventions/Dota correctness: n/a (tooling only). aoh_lint: 0 fail, 1 size warn. The warning comes from the generated baseline, which the notes exempt (the script is 93 lines).
- KV: n/a.
- Verification: the Round 2 claims are consistent with the code. Baseline is unchanged at 4341 entries + header. I did not re-run anything (qa runs it).
- Hygiene: clean, English, no debug output.

---
REQUEST_CHANGES
1. tools/luacheck_ratchet.py:19 and :22 — two near-identical regexes (`POS = r":\d+:\d+:"`, `LOC = r":\d+:\d+: "`) for the same thing (the owner's "no duplicates" rule). Keep one: filter with `POS.search` and normalize with `POS.sub(":", line, count=1)` (`path:1:2: (W111)` → `path: (W111)`, same output, so the baseline stays byte-identical). Delete `LOC` and the extra blank lines at :20-21.
2. tools/luacheck_ratchet.py:86 — a lambda assigned to a name plus `# noqa: E731` to silence the linter about it. Drop the lambda and the noqa: inline the test in the dict comprehension at :87 (`if k.split(":", 1)[0].startswith(scope)`), or use a small `def`.

Checklist notes (round 1):
- Spec: the script matches the teamlead notes: luacheck flags, exit ≥ 3 is fatal, normalization on the first `:d:d:`, Counter multiset, `NEW <raw>`, summary `a new, b known, c fixed`, `--update-baseline`/`--prune` lint the default tree, prune is `&`. check.sh changes only line 44 plus one header comment line (DoD 9 holds). Baseline header OK (DoD 3); 0 line:col entries (DoD 2, re-run by me). Fixture is exactly one line.
- Scope: 4 files, all in allowed_paths; no tests touched; no .claude/replay leak.
- Conventions/Dota correctness: n/a (no game Lua). aoh_lint: 0 fail; 1 size warning, but it comes from the generated baseline, which the notes exempt from the cap (script = 96 lines).
- KV: n/a.
- Verification: the Result claims match the DoD commands; I did not re-run check.sh/the ratchet (that is qa's job).
- Hygiene: no secrets, no debug prints, English. Only items 1-2 above.

## QA
PASS
1. Round 3 re-check: DoD 9 now holds (`grep -c "luacheck_ratchet.py"` → `1`, `run luacheck luacheck` → `0`). All other DoD items re-run and hold; git status clean after the runs.
2. DoD 1: `--update-baseline` → `baseline written: 4341 warnings`. The baseline is byte-identical afterwards (git status clean).
3. DoD 2: grep count `0`. DoD 3: the header is correct.
4. DoD 4: `0 new, 4341 known, 0 fixed` and `RATCHET: OK`.
5. DoD 5: `NEW tools/fixtures/luacheck_ratchet/new_global.lua:1:1: (W111) …`, `1 new`, `RATCHET: FAIL`.
6. DoD 6: `baseline pruned: 0 removed`.
7. DoD 7 and 8: `CHECK RESULT: OK (lua)`. Logs: logs/check-20261029-000837.log and logs/check-20261029-000839.log.
8. DoD 9 second grep (`run luacheck luacheck`) → `0`.
9. DoD 10: the diff lists only allowed_paths and this task file.

For the human: nothing ([human] none).
