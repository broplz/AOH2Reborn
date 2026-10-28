# AOH2 Reborn — agent handbook

Attack on Hero 2 Rebalanced: a Dota 2 custom game (Lua VScripts + KeyValues + Panorama), addon
name `attackcopy`. One owner sets direction and makes the key decisions; AI agents do the work one
task at a time. Sources of truth: docs/adr/ (accepted decisions), tasks/<id>-*.md (your task),
tasks/backlog.md (the queue). If this file and an ADR disagree, the ADR wins — say so in ## Result.

## Repo map
- game/dota_addons/attackcopy/scripts/vscripts/   server Lua: aohgamemode.lua, aohgameround.lua, abilities/, bosses/, items/, modifiers/, lib/
- game/dota_addons/attackcopy/scripts/npc/        KeyValues: npc_abilities_custom.txt (21k lines), npc_abilities_override.txt, npc_items_custom.txt, npc_units_custom.txt, npc_heroes_custom.txt, herolist.txt
- game/dota_addons/attackcopy/scripts/{config,shops}/   rounds (aoh2_config.txt), shops
- game/dota_addons/attackcopy/resource/           addon_english/russian/schinese.txt (localization)
- content/dota_addons/attackcopy/panorama/        Panorama SOURCES (xml/js/css). game/.../panorama/**/*_c are COMPILED — never edit them.
- content/.../maps, game/.../{models,particles,materials,sounds,soundevents}   binary assets — not for agents
- tools/            kvcheck.py (KV validator), vanilla_diff.py (our names vs current Dota), gen_luacheckrc.py
- tests/            Lua unit tests with a Dota API stub (tests/run.lua, tests/dota_stub.lua)
- scripts/agents/   the pipeline: check.sh, test.sh, diff.sh, aoh_lint.py, run_*.py, merge_task.py
- tasks/ (TEMPLATE.md, backlog.md, approvals.txt) · docs/adr · docs/notes · docs/reports · logs/ (git-ignored)

## Hard rules (hooks enforce them; a blocked call is not a bug — read the message, adapt)
1. One task per session; its file is named in the prompt (also $AOH_TASK). Read it whole first.
   Edit only its allowed_paths plus the task file. Found something else? One line in
   tasks/backlog.md under "Found by agents", then move on.
2. The driver owns git branches: never switch, checkout, merge, rebase, push, fetch or reset.
   Commit small and often on the current branch: `<prefix>: <what>` (prefix from the task).
3. Verify only via scripts/agents/check.sh (luacheck + stylua + kvcheck) and scripts/agents/test.sh
   (Lua unit tests). They print `CHECK RESULT: OK|FAIL` / `TEST RESULT: OK|FAIL` and a triage —
   that is what you read. Nobody can run the game here: in-game behaviour is a `[human]` DoD item.
4. KV files are huge: never Read npc_*.txt whole — Grep with head_limit, then Read with
   offset/limit ≤ 400. Never read binary assets (*_c, .vmap, .vtex, .vmdl, .vpcf, .tga, .png).
5. Strikes: 3 failed check/test runs in a row on one task → stop, fill ## Handoff, set
   status: blocked, commit, end. Same when a hook blocks what the task needs.
6. English in code, comments, commits and task files. No TODO without a task id.
7. Never touch: .claude/, CLAUDE.md, .github/, tasks/approvals.txt, compiled *_c files, binary
   assets, *.env, *secret*. Never install packages; ask via the backlog.

## Bash discipline (permission mode dontAsk: a denied call just fails — take another route)
- One plain command per Bash call, from the repo root. No `;` `&&` `||` `$(...)` backticks,
  variables, `cd`, heredocs, redirects into files, `tee`, `sed -i`, `cp`/`mv`. Files are made and
  changed only with the Write/Edit tools. Pipes only into head/tail/grep/wc/sort/uniq/cut.

## Commands
- scripts/agents/check.sh [lua|kv|all]      luacheck + stylua --check + tools/kvcheck.py (≈ 10 s)
- scripts/agents/test.sh [<pattern>]         Lua unit tests in tests/ against the Dota stub
- scripts/agents/diff.sh <task>              the task's diff vs its base, capped (what reviewers read)
- python3 scripts/agents/aoh_lint.py <task>  code-convention rules (ADR-0001 §4) on the diff; qa and the merge run it
- python3 tools/vanilla_diff.py              names in our KV that the current Dota build no longer has

## Where to look
docs/adr/0001-ai-team.md (this pipeline) · docs/adr/0002-target-architecture.md (code conventions,
boss cast queue) · the audit report linked from docs/adr/0002 · tasks/TEMPLATE.md (task format) ·
docs/notes/ (Dota API notes — extend them when you learn something the next agent will need)
