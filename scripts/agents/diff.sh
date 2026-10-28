#!/usr/bin/env bash
# The task's diff against its base, capped so a reviewer never floods its context.
#
#   scripts/agents/diff.sh <task-file> [--names] [--max-lines N] [-- <path>...]
#
# Excludes tasks/, logs/ and .claude/agent-memory/ (agents' notes). Over the cap it prints the stat and the first N lines and says how
# to read the rest per file (`scripts/agents/diff.sh <task> -- <path>`).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || exit 1
TASK="${1:?task file}"; shift
NAMES=0; MAX=1500; PATHS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --names) NAMES=1 ;;
    --max-lines) MAX="$2"; shift ;;
    --) shift; PATHS="$*"; break ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
BASE="$(python3 scripts/agents/taskfile.py get "$TASK" base)"
[ -z "$BASE" ] && BASE="$(grep -E '^\s*Active feature branch:' tasks/backlog.md | head -1 | awk '{print $NF}' | tr -d '\`')"
[ -z "$BASE" ] && BASE="main"
RANGE="$BASE...HEAD"
if [ "$NAMES" = 1 ]; then
  git diff --stat "$RANGE" -- . ':(exclude)tasks' ':(exclude)logs' ':(exclude).claude/agent-memory'
  exit 0
fi
echo "# diff $RANGE (code head $(git log -1 --format=%h HEAD -- . ':(exclude)tasks' ':(exclude)logs' ':(exclude).claude/agent-memory'))"
git diff --stat "$RANGE" -- . ':(exclude)tasks' ':(exclude)logs' ':(exclude).claude/agent-memory'
echo
if [ -n "$PATHS" ]; then
  # shellcheck disable=SC2086
  git diff "$RANGE" -- $PATHS | head -n "$MAX"
  exit 0
fi
TOTAL="$(git diff "$RANGE" -- . ':(exclude)tasks' ':(exclude)logs' ':(exclude).claude/agent-memory' | wc -l | tr -d ' ')"
git diff "$RANGE" -- . ':(exclude)tasks' ':(exclude)logs' ':(exclude).claude/agent-memory' | head -n "$MAX"
if [ "$TOTAL" -gt "$MAX" ]; then
  echo
  echo "### TRUNCATED: $TOTAL diff lines, showed $MAX. Read the rest per file: scripts/agents/diff.sh $TASK -- <path>"
fi
