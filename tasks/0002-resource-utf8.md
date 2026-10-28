---
id: 0002
title: resource/addon_russian.txt UTF-16 LE → UTF-8 (no BOM, LF) via tools/normalize_text.py
status: blocked
epic: p0
prefix: p0
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0002-resource-utf8
depends_on: []
allowed_paths:
  - tools/normalize_text.py
  - game/dota_addons/attackcopy/resource/addon_russian.txt
  - game/dota_addons/attackcopy/resource/addon_english.txt
  - game/dota_addons/attackcopy/resource/addon_schinese.txt
checks: kv
tests: []
needs_approval: true
returns: 0
sessions: 0
blocked_reason: owner: keep addon_russian.txt on disk as UTF-16LE BOM CRLF (Dota UTF-8 support unverified, no source); store UTF-8 in git via .gitattributes working-tree-encoding UTF-16LE-BOM eol crlf (owner test: fresh checkout is byte-identical to base); revert the file conversion, drop tools/normalize_text.py unless still needed; DoD: cmp of a fresh checkout vs the base blob, git diff shows text
reviewed_sha: 6eb99bd2215946894e41b9ce58660d824b5efd90
qa_sha: 6eb99bd2215946894e41b9ce58660d824b5efd90
---

## Goal
All three localization files are UTF-8 without BOM with LF line endings, produced by a small
re-runnable tool that also has a `--check` mode, so diffs and grep work on the Russian file.

## Definition of Done
1. `python3 tools/normalize_text.py --check` on the base branch state would fail; on the task branch it → exit 0, last line `OK: 3 file(s) UTF-8, no BOM, LF`.
2. `file game/dota_addons/attackcopy/resource/addon_russian.txt` → contains `UTF-8` and does not contain `UTF-16` or `CRLF`.
3. `wc -l game/dota_addons/attackcopy/resource/addon_russian.txt` → `3142` (same line count as before).
4. `grep -c -E '^\s*"[^"]+"\s+"' game/dota_addons/attackcopy/resource/addon_russian.txt` → `2626` (same key-line count as before).
5. `head -c 3 game/dota_addons/attackcopy/resource/addon_russian.txt` → `"la` (no BOM; file starts with `"lang"`).
6. Running `python3 tools/normalize_text.py` a second time → exit 0, prints `unchanged:` for all 3 files; `git status --short` shows nothing new.
7. `scripts/agents/check.sh kv` → `CHECK RESULT: OK (kv)` (regression only — kvcheck does not read resource/).
8. `git diff --stat feat/p0-foundation...HEAD` lists only `tools/normalize_text.py`, `addon_russian.txt` and this task file (english/schinese are already clean and must not change).
9. [human] Dota client language Russian: hero/ability tooltips of the addon show Russian text (not `#DOTA_Tooltip_…` keys); console has no `Failed to load` / localization parse error for addon_russian.txt.

## Notes from teamlead
- Finding being fixed (audit §KV): `addon_russian.txt` is UTF-16 LE with CRLF; english and schinese are already UTF-8, no BOM, LF (checked 2026-10-28 with `file`, `head -c 3`, CRLF count 0).
- Tool contract, `tools/normalize_text.py` (stdlib only, argparse, ≤ 80 lines):
  - Default targets: `game/dota_addons/attackcopy/resource/addon_*.txt` (glob from repo root, resolved from `__file__`); optional positional paths override.
  - Decode by BOM: `FF FE` → utf-16-le, `FE FF` → utf-16-be, `EF BB BF` → utf-8-sig, else strict utf-8 (a decode error → print `error: <path>: <reason>`, exit 1, write nothing).
  - Normalize `\r\n` and lone `\r` to `\n`; write utf-8 without BOM; print `converted: <path> (<from-encoding>, crlf=<n>)` or `unchanged: <path>`.
  - `--check`: write nothing; print `bad: <path> (<reason>)` per offender, exit 1 if any, else the OK line from DoD 1.
  - One table of BOMs → codecs and one loop; no per-file branches.
- Run it as `python3 tools/normalize_text.py` (iconv cannot write files here — no redirects allowed).
- Do not edit any string content; the only diff in addon_russian.txt is encoding + line endings. Git will show the whole file as changed — that is expected, it is generated output and does not count toward the S cap.
- Wiring `--check` into scripts/agents/check.sh is out of scope (pipeline file); put one line under "Found by agents" in tasks/backlog.md instead.
- DoD 9 is a playtest item (decisions-needed: playtest machine); write the exact steps in ## Result.

## Handoff

## Result
Round 1
- Added `tools/normalize_text.py` (BOM table + one loop, `--check`, optional paths). Ran it: only addon_russian.txt converted (utf-16-le, crlf=3142); english/schinese unchanged.
- Verified: `--check` before → `bad: …addon_russian.txt (utf-16-le, crlf=3142)` exit 1; after → `OK: 3 file(s) UTF-8, no BOM, LF`. `file` → UTF-8 text. `wc -l` 3142, key lines 2626. Second run → `unchanged:` ×3, no new git changes. `check.sh kv` → OK.
- DoD 5 note: the file starts with 4 spaces of indentation before `"lang"` (as in the original), so `head -c 3` prints spaces, not `"la`. No BOM present; the literal in DoD 5 is a spec slip, content unchanged.
- Backlog: one line added under "Found by agents" for wiring `--check` into check.sh.
- Owner playtest (DoD 9): launch Dota with language Russian, load the addon, open hero/ability/item tooltips → Russian text, no `#DOTA_Tooltip_…` keys; console has no `Failed to load` / localization parse error for addon_russian.txt.

## Review
APPROVE

Checklist:
1. Spec: the tool follows the contract. It has one BOM table and one loop, `--check`, optional positional paths, and a glob resolved from `__file__`. Strict utf-8 is the fallback. On a decode error it prints `error:`, exits 1 and writes nothing, because every file is read before any write. Output strings match. The diff of addon_russian.txt is encoding and line endings only: the tool only decodes and replaces line endings. The line count (3142) and key-line count (2626) match the base. I re-ran DoD 4 and got 2626.
2. Scope: changed files are tools/normalize_text.py, addon_russian.txt, the task file and tasks/backlog.md. DoD 8 does not list backlog.md, but the teamlead notes require that backlog line, so it is the protocol-sanctioned exception. english/schinese are unchanged. No tests were touched.
3. Conventions: N/A (no Lua/KV). aoh_lint: 0 fail, 0 warn, NEEDS APPROVAL (DoD 9 is `[human]`).
4. Dota correctness: N/A.
5. KV: N/A. kvcheck does not read resource/, and qa runs check.sh.
6. Verification: I re-ran `--check` and got `OK: 3 file(s) UTF-8, no BOM, LF`. `file` reports UTF-8 text with no CRLF. `wc -l` gives 3142. The backlog line exists. The DoD 5 claim is correct: the file starts with `    "lang"` (4 spaces, same as the original) and has no BOM, so the `"la` literal in the DoD is a spec slip, not a defect. DoD 9 is listed for the owner and not claimed.
7. Hygiene: no secrets, no debug output, no TODO, all English.

Non-blocking nits (fix only if the file is touched again):
1. tools/normalize_text.py:16,35: the table maps the BOM to `"utf-8-sig"`, then line 35 strips `-sig` again. Store the plain codec in the table and print a label instead. That removes the round-trip.
2. tools/normalize_text.py:34: `crlf = text.count("\r")` counts CR characters, not CRLF pairs. That is fine for the report, but the name is misleading.
3. tools/normalize_text.py:14: the comment "order matters only for distinct prefixes, all are unique" is confusing. Drop it.

## QA
PASS

1. DoD 1: `--check` → `OK: 3 file(s) UTF-8, no BOM, LF`, exit 0.
2. DoD 2: `file` → UTF-8 text, no UTF-16/CRLF.
3. DoD 3: `wc -l` → 3142. DoD 4: key-line count → 2626.
4. DoD 5: no BOM; file starts with 4 spaces then `"lang"` (original indentation). The literal `"la` in the DoD is a spec slip, as the developer noted. Accepted.
5. DoD 6: second run printed `unchanged:` for all 3 files; `git status --short` is clean.
6. DoD 7: `check.sh kv` → `CHECK RESULT: OK (kv)`.
7. DoD 8: the diff stat lists normalize_text.py, addon_russian.txt and the task file. It also lists tasks/backlog.md, the one line the teamlead notes require. english/schinese unchanged. Accepted.

For the human:
- DoD 9: launch Dota 2 with language Russian and load the addon. Open hero, ability and item tooltips and check that they show Russian text rather than `#DOTA_Tooltip_…` keys. Check that the console has no `Failed to load` or localization parse error for addon_russian.txt.
