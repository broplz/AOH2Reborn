# Decisions needed (append-only; the teamlead and agents write here, the owner answers in an ADR or the backlog)

- 2026-10-28 (architect): where does the game run for playtests — Workshop Tools are Windows-only; Mac + Parallels on ARM is unverified. Decides how the `[human]` gate is executed and how often.
- 2026-10-28 (architect): which Steam account owns the Workshop item and can push updates (contributors reportedly cannot). Decides the release step in finish_feature.sh.
- 2026-10-28 (teamlead): 0003 (stylua over the whole tree) has no agent-runnable write path — `.claude/hooks/guard_bash.py:56` blocks direct `stylua`, `scripts/agents/check.sh` only runs `stylua --check`. Options: add a format mode to check.sh (e.g. `check.sh lua --fix --all-files`), or the owner runs `stylua game/dota_addons/attackcopy/scripts/vscripts tests` and commits. 0003 stays in the backlog until decided.
- 2026-10-28 (teamlead): tasks/TEMPLATE.md (cited by CLAUDE.md and the teamlead prompt) does not exist; 0001/0002 were written from scripts/agents/taskfile.py + the task protocol. Add the template or confirm that shape.
