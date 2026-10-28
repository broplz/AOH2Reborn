#!/usr/bin/env bash
# Static checks, logged and triaged. Prints `CHECK RESULT: OK|FAIL` last.
#
#   scripts/agents/check.sh [all|lua|kv] [--all-files]
#
# lua: luacheck (.luacheckrc generated from dota-data) + stylua --check.
#      Default scope = Lua files changed on this branch vs its base (AOH_BASE, else the active
#      feature branch from tasks/backlog.md, else main) plus tests/ — the legacy tree is linted
#      file by file as tasks touch it. --all-files lints everything (phase-0 "format the repo" task, CI nightly).
# kv:  tools/kvcheck.py (syntax, duplicate keys/entries, ScriptFile) with its baseline ratchet,
#      + tools/vanilla_diff.py when tools/vanilla/ has a snapshot.
# Exit 0 OK · 1 FAIL · 5 a required tool is missing (brew install luacheck stylua).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT" || exit 1
WHAT="all"; ALLF=0
for a in "$@"; do case "$a" in all|lua|kv) WHAT="$a" ;; --all-files) ALLF=1 ;; *) echo "unknown argument: $a" >&2; exit 2 ;; esac; done
LOG_DIR="${AOH_LOG_DIR:-$ROOT/logs}"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/check-$(date +%Y%m%d-%H%M%S).log"
LUA_DIR="game/dota_addons/attackcopy/scripts/vscripts"
rc=0
step() { echo "===== $1" | tee -a "$LOG"; }
run() { local name="$1"; shift; "$@" >>"$LOG" 2>&1; local r=$?; echo "===== $name: exit $r" | tee -a "$LOG"; [ $r -ne 0 ] && rc=1; return $r; }

if [ "$WHAT" = all ] || [ "$WHAT" = lua ]; then
  for t in luacheck stylua; do
    command -v "$t" >/dev/null || { echo "missing tool: $t (brew install $t)"; echo "CHECK RESULT: FAIL (missing $t)"; exit 5; }
  done
  if [ "$ALLF" = 1 ]; then
    FILES=("$LUA_DIR" tests)
  else
    BASE="${AOH_BASE:-}"
    [ -z "$BASE" ] && BASE="$(grep -E '^\s*Active feature branch:' tasks/backlog.md 2>/dev/null | head -1 | awk '{print $NF}' | tr -d '`')"
    [ -z "$BASE" ] && BASE="main"
    git rev-parse -q --verify "$BASE" >/dev/null 2>&1 || BASE="HEAD"
    mapfile -t FILES < <( { git diff --name-only "$BASE...HEAD" -- "$LUA_DIR" tests; git diff --name-only HEAD -- "$LUA_DIR" tests; git ls-files --others --exclude-standard -- "$LUA_DIR" tests; } | grep '\.lua$' | sort -u )
    while IFS= read -r f; do [ -f "$f" ] && FILES+=("$f"); done < <(ls tests/*.lua 2>/dev/null)
    mapfile -t FILES < <(printf '%s\n' "${FILES[@]}" | sort -u | while read -r f; do [ -f "$f" ] && echo "$f"; done)
    echo "lua scope: ${#FILES[@]} file(s) changed vs $BASE (+ tests/)" | tee -a "$LOG"
  fi
  if [ "${#FILES[@]}" -gt 0 ]; then
    step "luacheck"
    run luacheck luacheck --no-color -q "${FILES[@]}"
    step "stylua --check"
    run stylua stylua --check "${FILES[@]}"
  fi
fi
if [ "$WHAT" = all ] || [ "$WHAT" = kv ]; then
  step "kvcheck"
  run kvcheck python3 tools/kvcheck.py --quiet-warn
  if [ -d tools/vanilla ]; then
    step "vanilla_diff"
    run vanilla_diff python3 tools/vanilla_diff.py
  else
    echo "(no tools/vanilla snapshot — run python3 tools/vanilla_snapshot.py once to enable vanilla_diff)" | tee -a "$LOG"
  fi
fi
echo "----- triage ($LOG)"
python3 scripts/agents/triage_log.py "$LOG" --max-lines 80
if [ $rc -eq 0 ]; then echo "CHECK RESULT: OK ($WHAT)"; else echo "CHECK RESULT: FAIL ($WHAT) — details: python3 scripts/agents/triage_log.py $LOG"; fi
exit $rc
