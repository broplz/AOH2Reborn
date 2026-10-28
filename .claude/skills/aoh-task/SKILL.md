---
name: aoh-task
description: The AOH2 task-file protocol — statuses, sections, who writes what, how a session ends. Injected into every pipeline role by the driver; humans can load it with /aoh-task.
disable-model-invocation: true
---
# Task protocol (ADR-0001)

One task = one file `tasks/<id>-<slug>.md` = one branch `task/<id>-<slug>` off `base` (a `feat/*`
branch, never main). One role per session; a session starts with no memory of the previous one,
so **the task file and the branch are the only state** — everything you learned goes there.

## Status, and who sets it
| status | set by | meaning |
|---|---|---|
| draft → ready | teamlead | task written; ready means the driver may start it |
| in_progress | developer | work on the branch has begun |
| review | developer | every non-[human] DoD item holds, ## Result filled, everything committed |
| qa | reviewer | APPROVE written |
| approved | qa | PASS written → the driver merges (squash) into base, or waits for the owner's approval |
| returned | reviewer / qa | numbered items to fix; the developer gets it back |
| blocked | developer / driver | stuck: ## Handoff explains; `blocked_reason` says why |
| done / split | driver / teamlead | merged, or replaced by smaller tasks |

The driver (scripts/agents/run_task.py) owns `returns`, `sessions`, `reviewed_sha`, `qa_sha`,
branch switching, merging, and auto-commits anything left uncommitted after a session. Never
touch those fields and never run git switch/merge/rebase/push yourself.

## Sections, and who writes them
- `## Goal`, `## Definition of Done`, `## Notes from teamlead` — teamlead. DoD items are commands
  + expected results; `[human]` items (anything only the running game shows) are checked by the
  owner at approval — agents list them, never claim them.
- `## Handoff` — developer, whenever a session ends before `review`: what is done, what failed,
  what was tried, the next idea. The next session starts from it.
- `## Result` — developer at `review`: what changed, how verified, open questions, what the owner
  should playtest and what console output proves it. Newest round on top; never claim a check
  you did not run.
- `## Review` — reviewer: first line APPROVE | REQUEST_CHANGES, then numbered items file:line.
- `## QA` — qa: first line PASS | FAIL, then numbered items with repro + log path; "For the
  human:" list for `[human]` items.

## Ending a session (every role)
1. Everything committed on the current branch (`git status` clean), task file included.
2. Status set to what the table says for your role; verdict/handoff written.
3. Then end. No tidying, no "one more thing", no switching branches.
Out of turns, strikes (3 failed check/test runs in a row), a hook blocking what the task needs,
a spec contradiction → that is a Handoff, not a reason to improvise.

## Sizes and limits
S ≤ 150 production lines / 5 files, M ≤ 300 / 10, L ≤ 500 / 15 (tests, docs and generated KV
don't count). A developer gets at most 3 sessions per task and 3 returns; after that the
teamlead splits it. Found something outside the task? One line in `tasks/backlog.md` under
"Found by agents" and move on.

## Commits
`<prefix>: <what>` with the task's `prefix` (`p0`, `p1`, … = the phase); task-file-only commits
are `<id>: <what>` (e.g. `0003: review verdict`). English. No TODO without a task id.
