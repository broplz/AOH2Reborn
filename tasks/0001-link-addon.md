---
id: 0001
title: scripts/agents/link_addon.sh links game/ and content/ into the Dota 2 install
status: ready
epic: p0
prefix: p0
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0001-link-addon
depends_on: []
allowed_paths:
  - scripts/agents/link_addon.sh
checks: none
tests: []
needs_approval: true
returns: 0
sessions: 0
blocked_reason:
---

## Goal
One idempotent shell script that links this repo's addon folders into the Dota 2 install so the
Workshop Tools open the `attackcopy` addon straight from the repo (macOS and Windows/Git Bash).

## Definition of Done
1. `scripts/agents/link_addon.sh` exists; first lines are a usage comment in the style of
   `scripts/agents/check.sh` (usage line, what it links, exit codes).
2. `mkdir -p logs/fake_dota` then `bash scripts/agents/link_addon.sh --dota-dir logs/fake_dota`
   → exit 0; prints exactly two `linked: <link> -> <target>` lines (game, content).
3. `ls -l logs/fake_dota/game/dota_addons logs/fake_dota/content/dota_addons` → each shows
   `attackcopy -> /…/AOH2Reborn/game/dota_addons/attackcopy` and
   `attackcopy -> /…/AOH2Reborn/content/dota_addons/attackcopy` (absolute targets).
4. Running the command from item 2 a second time → exit 0; prints two `ok: already linked: <link>` lines, changes nothing.
5. `mkdir -p logs/fake_conflict/game/dota_addons/attackcopy` then
   `bash scripts/agents/link_addon.sh --dota-dir logs/fake_conflict` → exit 1; prints
   `conflict: <path> exists and is not a link to <target>`; the directory is still there (`ls logs/fake_conflict/game/dota_addons/attackcopy` succeeds).
6. `bash scripts/agents/link_addon.sh --dota-dir logs/does_not_exist` → exit 2; prints `dota dir not found: <path>`.
7. `bash scripts/agents/link_addon.sh --help` → exit 0, prints the usage comment.
8. `git diff --stat feat/p0-foundation...HEAD` lists only `scripts/agents/link_addon.sh` and this task file.
9. [human] macOS: `bash scripts/agents/link_addon.sh` with no arguments links into the real Dota install; Workshop Tools (or `dota2 -tools`) list `attackcopy` and the map opens.
10. [human] Windows (Git Bash): same as 9; links are junctions (`dir` in cmd shows `<JUNCTION>`).

## Notes from teamlead
- Links to create (link → target, target absolute, resolved from the script's own location like check.sh line 14):
  - `<dota>/game/dota_addons/attackcopy` → `<repo>/game/dota_addons/attackcopy`
  - `<dota>/content/dota_addons/attackcopy` → `<repo>/content/dota_addons/attackcopy`
- `<dota>` = `--dota-dir <path>` if given (relative paths resolved against the current dir), else the default for the OS:
  - macOS (`uname -s` = Darwin): `$HOME/Library/Application Support/Steam/steamapps/common/dota 2 beta`
  - Windows (`uname -s` matches `MINGW*|MSYS*|CYGWIN*`): `/c/Program Files (x86)/Steam/steamapps/common/dota 2 beta`
  - anything else → exit 2 with `unsupported OS: <uname>; pass --dota-dir`.
- `<dota>` missing → exit 2. Parent `dota_addons/` folders missing inside an existing `<dota>` → `mkdir -p` them.
- Link kind: macOS `ln -s`; Windows `cmd //c mklink /J "<cygpath -w link>" "<cygpath -w target>"` (junction: no admin rights needed). Treat a junction/symlink already pointing at the target as "already linked" (compare with `readlink -f` / `pwd -P`).
- Never delete or overwrite anything: an existing file/dir/link pointing elsewhere → `conflict:` line, keep going for the other pair, exit 1 at the end.
- Data-driven: one list of the two (subdir) pairs and one loop — no copy-pasted game/content blocks.
- `set -euo pipefail`. No network, no sudo, no Steam path guessing beyond the two defaults.
- The file will not be executable (agents cannot chmod); always invoke it as `bash scripts/agents/link_addon.sh`. Owner may `chmod +x` later.
- Items 9–10 need the playtest machine (open question in docs/reports/decisions-needed.md); write the exact steps in ## Result.
- `logs/` is git-ignored scratch; the fake dirs never get committed.

## Handoff

## Result

## Review

## QA
