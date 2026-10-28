---
name: aoh-check
description: How to verify AOH2 changes without the game — check.sh (luacheck, stylua, KV validator), test.sh (Lua unit tests on a Dota stub), logs and triage, what only the owner can check. Injected into developer, developer-hard and qa; /aoh-check for humans.
disable-model-invocation: true
---
# Checking and testing (nothing here can launch Dota 2)

| command | what | time |
|---|---|---|
| `scripts/agents/check.sh` | luacheck on the Lua tree (+ .luacheckrc from dota-data), `stylua --check`, `tools/kvcheck.py` on every npc_*.txt | ≈ 10-30 s |
| `scripts/agents/check.sh lua` / `kv` | only that part | |
| `scripts/agents/test.sh [<pattern>]` | `lua tests/run.lua` — every `tests/test_*.lua` (or those matching the pattern) against `tests/dota_stub.lua` | seconds |
| `scripts/agents/diff.sh <task>` | your branch's diff vs base, capped | |
| `python3 scripts/agents/aoh_lint.py <task>` | ADR-0002 conventions on the diff; FAIL lines block the merge | seconds |
| `python3 tools/kvcheck.py --show <entry>` | print one KV entry (ability/item/unit) without reading the file | |
| `python3 tools/vanilla_diff.py [--entries a,b]` | names we reference that the current Dota build lacks | |
| `python3 scripts/agents/triage_log.py <log>` | errors + context from any log | |

Every wrapper logs to `logs/<kind>-<stamp>.log` and prints `CHECK RESULT: OK|FAIL …` /
`TEST RESULT: …` plus a triage. **That triage is what you read.** Never Read a `.log`, never
`cat` it; for more, `Grep` the log with a narrow pattern and head_limit, or `tail -n 40`.

Rules of thumb
- Run the checks once per meaningful change, not after every edit; think first.
- Logic that does not need the engine (queues, parsers, math, table transforms) goes in a
  module that `require`s nothing from Dota at load time, so a test can `require` it on the stub.
  The stub (`tests/dota_stub.lua`) provides `class`, `Vector`, `GameRules:GetGameTime`,
  `IsServer`, `Timers`, a fake unit with modifiers — extend it in the same task when you need
  more (allowed: tests/**).
- What the stub cannot prove (cast actually fires, particles, net tables reaching the client)
  is a `[human]` DoD item: describe in ## Result the exact in-game steps and the console line
  (`print`) that proves it, so the owner's playtest is five minutes, not fifty.
- KV: `kvcheck.py` catches syntax, duplicate keys and missing ScriptFile; `vanilla_diff.py`
  catches names Valve removed. Both are part of check.sh.
- No network from the shell; no package installs. Missing tool → one line under "Found by
  agents" in tasks/backlog.md and a Handoff.
- Strikes: 3 failed check/test runs in a row → stop, Handoff.
