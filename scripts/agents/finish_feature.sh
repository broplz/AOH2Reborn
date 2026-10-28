#!/usr/bin/env bash
# Human-run. Land a finished feature branch on main (ADR-0001 §3): rebase onto main from the
# recorded fork point, run the checks, PLAYTEST BY HAND, ff-merge, clean up. The pipeline never does this.
#
#   scripts/agents/finish_feature.sh feat/<pN>-<slug> [--no-check]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
MAIN="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed "s#origin/##")"
[ -z "$MAIN" ] && { git rev-parse -q --verify master >/dev/null && MAIN=master || MAIN=main; }
NAME="${1:?usage: finish_feature.sh feat/<pN>-<slug>}"; shift || true
CHECK=1; [ "${1:-}" = "--no-check" ] && CHECK=0
FORK="aoh/fork/${NAME#feat/}"
[ -z "$(git status --porcelain)" ] || { echo "working tree is dirty" >&2; exit 1; }
git rev-parse -q --verify "refs/tags/$FORK" >/dev/null || { echo "no tag $FORK; create it on the commit the feature forked from: git tag $FORK <sha>" >&2; exit 1; }
echo "1/4 rebase $NAME onto main from $FORK"
git switch "$NAME"
git rebase --onto "$MAIN" "$FORK" "$NAME"
echo "    optional: squash to meaningful commits now (git rebase -i $MAIN), then press Enter"; read -r _
if [ "$CHECK" = 1 ]; then
  echo "2/4 checks + tests, then your playtest"
  scripts/agents/check.sh all
  scripts/agents/test.sh
  echo "    launch the map in Workshop Tools, run the phase gate from the ADR (one full game, console clean), then press Enter"; read -r _
fi
echo "3/4 ff-merge into $MAIN"
git switch "$MAIN"
git merge --ff-only "$NAME"
echo "4/4 cleanup + push"
git branch -d "$NAME"
git tag -d "$FORK"
git push origin "$MAIN" || echo "push failed — push main later by hand"
echo "done: $MAIN is at $(git log -1 --oneline)"
