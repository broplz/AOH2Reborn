#!/usr/bin/env bash
# Human-run. Start a feature branch the pipeline will merge tasks into (ADR-0001).
#
#   scripts/agents/new_feature.sh feat/<pN>-<slug>
#
# Creates the branch from main, tags its fork point aoh/fork/<name> (explicit base for the finish
# rebase — R4 in ADR-0002), and points tasks/backlog.md at it.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
MAIN="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed "s#origin/##")"
[ -z "$MAIN" ] && { git rev-parse -q --verify master >/dev/null && MAIN=master || MAIN=main; }
NAME="${1:?usage: new_feature.sh feat/<pN>-<slug>}"
case "$NAME" in feat/*) ;; *) echo "name must start with feat/" >&2; exit 2 ;; esac
[ -z "$(git status --porcelain)" ] || { echo "working tree is dirty" >&2; exit 1; }
git switch "$MAIN"
git switch -c "$NAME"
git tag "aoh/fork/${NAME#feat/}" "$MAIN"
if grep -qE '^\s*Active feature branch:' tasks/backlog.md; then
  python3 - "$NAME" <<'PY'
import re, sys
name = sys.argv[1]
p = "tasks/backlog.md"
t = open(p, encoding="utf-8").read()
t = re.sub(r"(?m)^(\s*Active feature branch:\s*).*$", r"\g<1>" + name, t)
open(p, "w", encoding="utf-8").write(t)
PY
  git add tasks/backlog.md
  git diff --cached --quiet || git commit -q -m "tasks: active feature $NAME"
fi
echo "on $NAME (fork point tagged aoh/fork/${NAME#feat/}). Next: scripts/agents/run_queue.py --plan"
