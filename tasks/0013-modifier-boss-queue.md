---
id: 0013
title: modifier_boss owns a core/boss_queue (0.1 s tick, Submit/Lock/Confirm, clear on destroy); ticket API kept
status: ready
epic: p2
prefix: p2
kind: code
size: M
role: developer-hard
base: feat/p0-foundation
branch: task/0013-modifier-boss-queue
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/modifiers/modifier_boss.lua
  - tests/test_modifier_boss.lua
  - tests/dota_stub.lua
  - tools/luacheck.baseline
checks: lua
tests: [boss_queue, modifier_boss]
needs_approval: true
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
---

## Goal
ADR-0002 §Решение 5: `modifier_boss` holds one `core/boss_queue.lua` queue per boss and drives it
from its think, so boss abilities can move off the generic.lua ticket system (0014-0016). This
task only adds the queue and its public methods; every existing caller of the ticket API keeps
working unchanged, and the enrage stack keeps its current rate.

## Definition of Done
V = `game/dota_addons/attackcopy/scripts/vscripts`
1. `scripts/agents/test.sh modifier_boss` → `TEST RESULT: OK`; tests/test_modifier_boss.lua has at least these tests (names free):
   a. after OnCreated the think interval is 0.1;
   b. thinking every 0.1 s for 4.5 s of game time → stack count 2 (enrage: +1 per 2.25 s, as today);
   c. `Submit(job)` returns an id and the next think calls `job.telegraph`;
   d. `Confirm()` during the cast phase ends the job on the next think (`done`);
   e. while a `Lock()` release is unreleased no job starts; after release it starts;
   f. `OnDestroy()` calls `on_cancel` of the active and queued jobs;
   g. legacy: `RequestTicket` 0,1 / `QueryTicket(0)` true, `QueryTicket(1)` false / `ReleaseTicket` → `QueryTicket(1)` true; `Lockout()` makes `QueryTicket` false and blocks queue starts until `ReleaseLockout()`.
2. `scripts/agents/test.sh boss_queue` → `TEST RESULT: OK` (core/boss_queue.lua untouched).
3. `grep -c "StartIntervalThink(0.1)" V/modifiers/modifier_boss.lua` → `1`; `grep -c 'require("core/boss_queue")' V/modifiers/modifier_boss.lua` → `1`.
4. `grep -c -E "function modifier_boss:(Submit|Lock|Confirm|OnDestroy|RequestTicket|GetOpenTicket|QueryTicket|ReleaseTicket|Lockout|ReleaseLockout)\(" V/modifiers/modifier_boss.lua` → `10`.
5. `scripts/agents/check.sh lua` → `CHECK RESULT: OK (lua)`.
6. `python3 scripts/agents/aoh_lint.py 0013` → 0 fail (NEEDS APPROVAL expected).
7. `git diff --stat feat/p0-foundation...HEAD` → only allowed_paths + this task file; `V/core/boss_queue.lua` and `V/abilities/` not in it.
8. [human] Local game, 3 boss rounds incl. Enigma or Underlord (ticket users): bosses cast as before, damage-outgoing buff on the boss grows at the same pace as on feat/p0-foundation, no Lua error from modifier_boss.lua in the console.

## Notes from teamlead
- Queue API (core/boss_queue.lua, do not edit): `Q.new()`, `q:submit(job, now)` → id,
  `q:lock()` → idempotent release fn, `q:confirm()`, `q:clear()`, `q:tick(unit, now)`. `now` =
  `GameRules:GetGameTime()`.
- Target shape, all inside the existing `if IsServer() then` block:
  - OnCreated: `self.queue = Q.new()`, `self.next_stack_at = now + 2.25`, `StartIntervalThink(0.1)`;
    keep the ticket fields (`available_ticket`, `open_ticket`, `lockout`).
  - OnIntervalThink: `if now >= self.next_stack_at then IncrementStackCount(); next_stack_at += 2.25 end`,
    then `self.queue:tick(self.parent, now)`. Stack rate must stay +1/2.25 s (it drives
    GetModifierDamageOutgoing_Percentage and move speed).
  - `Submit(job)` → `self.queue:submit(job, now)`; `Lock()` → `self.queue:lock()`; `Confirm()` → `self.queue:confirm()`;
    `OnDestroy()` → `self.queue:clear()`.
  - Legacy adapters: RequestTicket/GetOpenTicket/QueryTicket/ReleaseTicket keep their exact
    behaviour. `Lockout()` additionally takes one queue lock (store the release fn, only if none is
    held); `ReleaseLockout()` calls and clears it. The `self.lockout` flag stays for QueryTicket.
- Callers of the ticket API (generic.lua, boss_enigma_*, boss_abyssal_underlord_*, boss_invoker_*)
  are NOT touched here; their migration is 0014-0016.
- No `OnAbilityExecuted` and no Timers (ADR-0002 §5). No `print`; the think is a hot path.
- Test harness: tests/run.lua puts vscripts on package.path, so `require("modifiers/modifier_boss")`
  defines the global class. `stub.attach(unit, modifier_boss)` gives GetParent/StartIntervalThink
  (`m._think`); use `stub.setTime`/`stub.advance` for game time. The stub has no
  `GetStackCount`/`IncrementStackCount`/`SetStackCount`: add them to `stub.attach` in
  tests/dota_stub.lua (stack stored on the instance), nothing else in the stub.
- Legacy warnings in modifier_boss.lua are baselined; if check.sh reports "fixed" entries run
  `python3 tools/luacheck_ratchet.py --prune`, never `--update-baseline`.
- `base` is feat/p0-foundation although the epic is p2: the owner has not opened feat/p2-boss-engine;
  the driver decides the branch.

## Handoff

## Result

## Review

## QA
