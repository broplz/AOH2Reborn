#!/usr/bin/env bash
# Lua unit tests against the Dota API stub. Prints `TEST RESULT: OK|FAIL` last.
#
#   scripts/agents/test.sh [<pattern>]      runs tests/test_*.lua (or those whose name matches <pattern>)
#
# Needs a Lua 5.1-compatible interpreter (`lua5.1`, `luajit` or `lua`): brew install lua@5.1 / luajit.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT" || exit 1
LOG_DIR="${AOH_LOG_DIR:-$ROOT/logs}"; mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/test-$(date +%Y%m%d-%H%M%S).log"
LUA=""
for c in lua5.1 luajit lua; do command -v "$c" >/dev/null && { LUA="$c"; break; }; done
[ -z "$LUA" ] && python3 -c "import lupa" 2>/dev/null && LUA="python3 tools/lua.py"
[ -z "$LUA" ] && { echo "missing tool: lua 5.1 (brew install lua@5.1)"; echo "TEST RESULT: FAIL (no lua)"; exit 5; }
$LUA tests/run.lua "${1:-}" 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}
if [ "$rc" -eq 0 ]; then echo "TEST RESULT: OK"; else echo "TEST RESULT: FAIL — details: python3 scripts/agents/triage_log.py $LOG"; fi
exit "$rc"
