---
id: 0002
title: resource/addon_russian.txt UTF-16 LE → UTF-8 (no BOM, LF) via tools/normalize_text.py
status: ready
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
blocked_reason:
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

## Review

## QA
