---
id: 0013
title: modifier_boss owns a core/boss_queue (0.1 s tick, Submit/Lock/Confirm, clear on destroy); ticket API kept
status: done
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
reviewed_sha: c3a7c32974eb8cb1fa29527b43ff2fb2ec9a4b62
qa_sha: c3a7c32974eb8cb1fa29527b43ff2fb2ec9a4b62
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
### Round 1 (session 1)
What changed
- `modifiers/modifier_boss.lua`: inside `if IsServer()`, `local Q = require("core/boss_queue")`.
  OnCreated keeps the ticket fields, adds `self.queue = Q.new()`, `self.next_stack_at = now + 2.25`,
  `StartIntervalThink(0.1)`. OnIntervalThink: +1 stack when `now >= next_stack_at` (then +2.25),
  then `self.queue:tick(self.parent, now)`. New `Submit(job)`/`Lock()`/`Confirm()`/`OnDestroy()`
  (→ `queue:clear()`). `Lockout()` additionally takes one queue lock (only if none held);
  `ReleaseLockout()` calls and clears it; `self.lockout` flag unchanged for QueryTicket.
  OnDestroy also drops the stored lockout release, because `clear()` resets `locks` to 0 and a
  later release would push it negative.
- `-- luacheck: globals modifier_boss` at the top of modifier_boss.lua: the 4 new methods added 4
  new W112 on the engine-required class global (ratchet counts per message). With the directive
  all 16 baselined W111/W112 for this file are gone → `luacheck_ratchet.py --prune` removed
  exactly those 16 lines from tools/luacheck.baseline (no `--update-baseline`).
- `tests/test_modifier_boss.lua`: 8 tests = DoD 1a-g (+ GetOpenTicket and double-Lockout = one lock).
- Deviation from the notes: the guard hook blocks editing tests/dota_stub.lua ("existing test on
  base"), so `GetStackCount`/`IncrementStackCount` are added on the instance by a `boss()` helper
  in the test file instead. If the teamlead wants them in the stub, that is a kind: test task.
- core/boss_queue.lua and abilities/ untouched.

Callers of the ticket API (not touched, keep working — signatures and behaviour unchanged):
aohgamemode.lua, abilities/other/generic.lua, abilities/bosses/{boss_enigma_fundamental_burst,
boss_enigma_shadow_blast, boss_abyssal_underlord_certain_death, _cleave, _firestorm, _undead_cannon,
boss_invoker_trance, boss_invoker_arcane_whirl, boss_void_spirit_dissimilate, boss_void_spirit_counter,
boss_meteor_init, boss_wisp_friendly_counter, boss_lone_druid_spirit_bear, boss_phantom_lancer_counter,
boss_legion_commander_warpath, _bunker, boss_juggernaut_counter}.lua (grep for modifier_boss / ticket names;
some only match the `modifier_boss_*` prefix).

Verified (run this session)
- `scripts/agents/test.sh modifier_boss` → 8 passed, TEST RESULT: OK
- `scripts/agents/test.sh boss_queue` → 6 passed, TEST RESULT: OK; full `test.sh` → 14 passed, OK
- `scripts/agents/check.sh lua` → CHECK RESULT: OK (lua) (ratchet 0 new; 16 fixed, then pruned)
- DoD 3 greps → 1 and 1; DoD 4 grep → 10
- `python3 scripts/agents/aoh_lint.py 0013` → 0 fail, 0 warn, NEEDS APPROVAL
- `git diff --stat feat/p0-foundation...HEAD` → modifier_boss.lua, test_modifier_boss.lua,
  tools/luacheck.baseline, this task file

For the owner to playtest (DoD 8, [human])
1. Local game, play 3 boss rounds including Enigma or Underlord. Bosses cast their abilities as before
   (Enigma shadow blast / fundamental burst, Underlord firestorm / cannon / certain death in turn).
2. Hover the boss's `modifier_boss` buff (rolling-boulder icon): stack count should be ~27 after
   1 minute (60 / 2.25), same as on feat/p0-foundation.
3. Console: no `Script Runtime Error` mentioning `modifier_boss.lua`. The think has no print
   (hot path), so the proof is the stack count + absence of errors.
Open question: the think now runs 10× more often; queue:tick is O(queue) and idle with no jobs, so
cost should be negligible, but watch for frame drops with many bosses.

## Review
APPROVE
1. Spec: matches Notes target shape — Q required inside `if IsServer()`, OnCreated keeps ticket fields + queue + `next_stack_at` + `StartIntervalThink(0.1)`; think keeps +1/2.25 s (fires at 2.25, 4.5… exactly like the old 2.25 s interval) then `queue:tick`; Submit/Lock/Confirm/OnDestroy delegate; Lockout takes one lock (idempotent via `or`), ReleaseLockout calls+clears it; ticket methods unchanged. No Timers, no OnAbilityExecuted, no print.
2. Scope: modifier_boss.lua, tests/test_modifier_boss.lua, tools/luacheck.baseline (only the 16 modifier_boss lines pruned) — all allowed; core/boss_queue.lua and abilities/ untouched. tests/dota_stub.lua not edited (hook-blocked); the stack-count shim lives in the test helper `boss()` — acceptable, documented deviation.
3. Conventions: single engine global, `-- luacheck: globals modifier_boss` is the honest replacement for 16 baselined warnings; STACK_INTERVAL is a modifier timing constant, not an ability value (no KV owner) — fine. aoh_lint: 0 fail, 0 warn, NEEDS APPROVAL.
4. Dota correctness: all new handlers inside the IsServer block; think 0.1 s as specified; `queue:tick` only touches the unit when the queue is non-empty and unlocked (boss_queue.lua:122), parent is valid while the modifier lives. OnDestroy drops `lockout_release` before `clear()` so a late ReleaseLockout cannot drive `locks` negative — good.
5. KV: none touched.
6. Verification: tests 1a–g exist in tests/test_modifier_boss.lua (test_think_interval, test_enrage_rate_unchanged, test_submit_then_telegraph, test_confirm_ends_cast, test_lock_blocks_start, test_destroy_cancels_all, test_legacy_tickets, test_legacy_lockout_blocks_queue); DoD 3/4 greps consistent with the diff (one StartIntervalThink(0.1), one require, 10 listed methods). check/test runs left to qa. DoD 8 listed as [human], not claimed.
7. Hygiene: no debug prints, no TODOs, English.
Non-blocking: if the teamlead wants GetStackCount/IncrementStackCount in tests/dota_stub.lua, that is a separate kind: test task.

## QA
PASS
1. DoD 1: `test.sh modifier_boss` → 8 passed, TEST RESULT: OK (covers 1a-g).
2. DoD 2: `test.sh boss_queue` → 6 passed, OK.
3. DoD 3: greps → 1 and 1. DoD 4: grep → 10.
4. DoD 5: `check.sh lua` → CHECK RESULT: OK (lua).
5. DoD 6: aoh_lint → 0 fail, 0 warn, NEEDS APPROVAL (expected).
6. DoD 7: diff stat → modifier_boss.lua, test_modifier_boss.lua, luacheck.baseline, task file only; boss_queue.lua and abilities/ not touched.

For the human (DoD 8):
- Local game, play 3 boss rounds including Enigma or Underlord. Bosses cast as before.
- Hover the boss's modifier_boss buff: the stack count should be about 27 after 1 minute (60 / 2.25), the same as on feat/p0-foundation.
- Console: no Script Runtime Error mentioning modifier_boss.lua.
