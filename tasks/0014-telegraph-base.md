---
id: 0014
title: bosses/_shared/telegraph.lua — ability_lua telegraph base that submits jobs to modifier_boss
status: done
epic: p2
prefix: p2
kind: code
size: M
role: developer-hard
base: feat/p0-foundation
branch: task/0014-telegraph-base
depends_on: [0013]
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/bosses/_shared/telegraph.lua
  - tests/test_telegraph.lua
  - tests/dota_stub.lua
checks: lua
tests: [telegraph]
needs_approval: false
returns: 1
sessions: 0
blocked_reason: 
reviewed_sha: b399fd3555b24e89beb22d215716fbcba6c891c9
qa_sha: b399fd3555b24e89beb22d215716fbcba6c891c9
---

## Goal
ADR-0002 §Решение 5 (+ §4 Lua 10): the `generic_*` RunScript functions in abilities/other/generic.lua
poll Timers and the ticket API. This task adds the replacement: one module that builds an
`ability_lua` class for a boss "wrapper" ability whose OnSpellStart builds a boss_queue job and
calls `modifier_boss:Submit(job)`. No wrapper is migrated here (Juggernaut = task 0024); generic.lua
and the KV are untouched.

## Definition of Done
V = `game/dota_addons/attackcopy/scripts/vscripts`
1. `scripts/agents/test.sh telegraph` → `TEST RESULT: OK`; tests/test_telegraph.lua covers at least:
   a. `kind = "no_target"`: OnSpellStart calls `Submit` once on the caster's modifier_boss; `job.telegraph(job)` returns `delay - spell cast point`; `job.cast(job)` issues `CastAbilityNoTarget` on the target spell;
   b. `kind = "point"` with `is_line = 1`: cast issues `CastAbilityOnPosition` at the cursor point; difficulty 2 (`_G.AOHGameMode._difficulty = 2`) → job.iterations = iterations + 1 and telegraph returns `delay*0.8 - cast point`;
   c. `kind = "unit_target"`: difficulty 2 → delay ×0.8, iterations unchanged; cast issues `CastAbilityOnTarget` on the target;
   d. the confirm modifier: once the spell's `IsCooldownReady()` is false it calls `modifier_boss:Confirm()` exactly once and is destroyed;
   e. `job.on_cancel(job)` removes `modifier_anim` from the caster and kills a spawned `npc_target` dummy if one exists;
   f. no modifier_boss on the caster → OnSpellStart does nothing and does not error.
2. `grep -c "Timers" V/bosses/_shared/telegraph.lua` → `0`; `grep -c -E "RequestTicket|QueryTicket|ReleaseTicket|OnAbilityExecuted" V/bosses/_shared/telegraph.lua` → `0`.
3. `grep -c "LinkLuaModifier" V/bosses/_shared/telegraph.lua` → `1` (only the confirm modifier).
4. `grep -n -E "StartIntervalThink\(0\.0" V/bosses/_shared/telegraph.lua` → empty.
5. `scripts/agents/check.sh lua` → `CHECK RESULT: OK (lua)`.
6. `python3 scripts/agents/aoh_lint.py 0014` → 0 fail.
7. `git diff --stat feat/p0-foundation...HEAD` → only allowed_paths + this task file.

## Notes from teamlead
- Public API (keep exactly): `local telegraph = require("bosses/_shared/telegraph")`;
  `boss_x_wrapper = telegraph.class({ kind = "no_target"|"point"|"unit_target", spell = "<target ability name>" })`
  returns a `class({})` with `OnSpellStart`. Numbers come from the wrapper's own KV via
  `self:GetSpecialValueFor`: `delay`, `radius`, `iterations` (0/absent → 1), `is_line`, `line_length`,
  `initial_radius`, `maximum_distance` (0/absent → 475). No `ability_index` — the spell name replaces it.
- Behaviour to port 1:1 from generic.lua (read it, don't copy the Timers): `generic_aoe_notarget`
  :351-403, `generic_aoe` :231-349, `generic_target` :405-528.
  - telegraph(job): `caster:Stop()`, FaceTowards, `EmitSoundOn("Hero_Mars.Spear.Cast", caster)`,
    warning particle via lib/warning.lua globals (`aoe_particle`, `aoe_line_particle`, `line_to_point`;
    unit_target: `particles/custom/aoe_warning_target.vpcf` + `modifier_target_delay` on the target),
    `modifier_anim` for `delay - cast_point`, StartAnimation `ACT_DOTA_CAST_ABILITY_1` with
    `rate = 1 / (delay - cast_point)` (generic.lua has the precedence bug `1 / delay - cp`; the new
    code is correct). Returns `delay - cast_point`.
  - point kind, iteration 2+: retarget to a random enemy hero/basic within the spell's cast range
    (range 0 → 1000), FIND_FARTHEST, as generic_aoe :269-288; first iteration uses the cursor point.
  - cast(job): `spell:EndCooldown()`, face the point, issue the order (player id
    `caster:GetPlayerOwnerID()` for point, `-1` otherwise), unit_target: spawn `npc_target` dummy
    + `modifier_dummy` when the target moved more than `maximum_distance` (generic_target :485-499).
    Adds the confirm modifier; returns true. Target dead/null → return false.
  - `cast_timeout` = `spell:GetCastPoint() + 1.0`; `deadline` = 6 (queue default); `prio` = 0.
- Confirm: a hidden modifier `modifier_telegraph_confirm` (owned by telegraph.lua, linked once) on
  the caster, duration = cast_timeout, think 0.1 s: if `not spell:IsCooldownReady()` → find
  modifier_boss, `:Confirm()`, add `modifier_weak` 0.5 s on the last iteration, then Destroy; elif
  `caster:GetCurrentActiveAbility() == nil and not caster:IsSilenced()` → reissue the order (this
  replaces generic.lua's retry loop). Target abilities are mostly vanilla BaseClass, so they cannot
  call Confirm from OnSpellStart — that is why this modifier exists. OnDestroy stops the think.
- `modifier_anim`, `modifier_weak`, `modifier_dummy`, `modifier_target_delay` are owned and linked by
  abilities/other/generic.lua (:631-879): `require("abilities/other/generic")` at the top, never a
  second LinkLuaModifier. In the test, set `package.loaded["abilities/other/generic"] = true` and
  `package.loaded["lib/warning"]` stubs before requiring the module.
- No globals besides the classes `telegraph.class` returns (assigned by the caller) and
  `modifier_telegraph_confirm`. No `print`.
- tests/dota_stub.lua: add only what the tests need (ability stub with GetSpecialValueFor /
  GetCastPoint / IsCooldownReady / EndCooldown, cast-order recorders on Unit, ParticleManager no-ops).
- Out of scope: generic.lua, KV, every wrapper migration (0024 Juggernaut first).

## Handoff

## Result
### Round 2 (returned items 1-3)
1. Dummy leak: `modifier_telegraph_confirm:OnDestroy` now puts this cast's `modifier_dummy` on
   `DUMMY_LINGER` for every exit path (confirm, cast_timeout expiry, `on_cancel` removal). Before,
   only the confirm path did this. `pick_cast_target` clears `job.dummy`/`job.dummy_mod` at the
   start of each cast, so a later iteration cannot re-extend an earlier dummy. Each dummy is ended
   by its own confirm modifier, and `on_cancel` still kills the current one. New test
   `test_unconfirmed_dummy_lingers`: the boss is silenced, nothing is re-issued, the confirm
   modifier is destroyed without a Confirm, and the dummy's modifier duration becomes 1.
2. Re-issue guard: the re-issue branch has moved to `modifier_telegraph_confirm:reissue`. For a
   `needs_target` kind with an invalid `job.cast_target` (null or dead), it calls `Destroy()` and
   issues no order. New test `test_lost_cast_target_stops_reissue`.
3. Added a line to tasks/backlog.md under "Found by agents" asking a `kind: test` task to move the
   rawset engine surface into tests/dota_stub.lua.

Verified: `scripts/agents/test.sh telegraph` → TEST RESULT: OK (10 passed). The full suite gives
24 passed. `scripts/agents/check.sh lua` → CHECK RESULT: OK (lua). `aoh_lint.py 0014` → 0 fail and
1 size WARN (378 > 300). The DoD 2/4 greps return 0. The diff touches only the allowed files, the
task file and tasks/backlog.md (the Found-by-agents line, as item 3 asks).
Extra [human] check, for when 0024 or a later task migrates a unit_target wrapper: silence the boss
for the whole cast window after an `npc_target` dummy has spawned. The dummy should die about 1 s
after `cast_point + 1 s`.

### Round 1 (developer session 1)
**What changed**
- New `bosses/_shared/telegraph.lua`: `telegraph.class({ kind, spell })` returns an ability_lua class
  whose `OnSpellStart` builds one boss_queue job (`prio 0`, `deadline 6`,
  `cast_timeout = spell:GetCastPoint() + 1.0`) and calls `modifier_boss:Submit(job)`. The per-kind
  differences (hard-difficulty scaling, aim, warning, pre-cast dummy step, order) live in one `KINDS`
  table. An unknown kind fails at load with `assert`. Also adds `modifier_telegraph_confirm`, the only
  `LinkLuaModifier` in the file: hidden, thinks every 0.1 s, confirms once and destroys itself, and
  re-issues the order while the caster is idle and not silenced.
- New `tests/test_telegraph.lua` with 8 tests that cover DoD 1a–1f, plus point retargeting on
  iteration 2+ (and the fall-back to the cursor) and the lost-target case (`cast` returns false).
- Callers: none yet. This is a new module, and the wrappers move over in 0024+. `modifier_boss`,
  `core/boss_queue.lua` and `generic.lua` are unchanged. The module only uses `Submit` and `Confirm`.

**Differences from generic.lua (on purpose)**
- `rate = 1 / (delay - cast_point)` fixes the precedence bug. `modifier_anim` and the animation last
  `delay - cast_point` for every kind. In generic_target they used the full `delay`.
- Warning particles use the difficulty-scaled delay. generic_aoe used the unscaled `keys.delay` for
  particles but the scaled delay for timing, so on hard the warning outlived the cast.
- Retarget picks `enemies[RandomInt(1, #enemies)]` instead of the global `random_from_table`.
- The `team_number` argument to the lib/warning helpers (unused there) is no longer passed.
- On the last iteration, "last" means `job.iterations == 1` when the cast is confirmed. The queue
  decrements the counter after Confirm.
- `on_cancel` also removes `modifier_telegraph_confirm`.

**Verified**
- `scripts/agents/test.sh telegraph` → TEST RESULT: OK (8 passed). The full suite gives 22 passed.
- `scripts/agents/check.sh lua` → CHECK RESULT: OK (lua).
- `python3 scripts/agents/aoh_lint.py 0014` → 0 fail, 1 WARN for size (358 added lines, including
  comments and blank lines, against the M cap of 300).
- DoD 2/4 greps → 0. The `LinkLuaModifier` count is 1. `git diff --stat` shows only the two
  allowed files plus this task file.

**Notes / open questions**
- `tests/dota_stub.lua` is in allowed_paths, but the guard hook blocks edits to it ("existing tests
  change only in kind: test tasks"). All extra engine surface (vector arithmetic, cast-order
  recorders, ability stub, ParticleManager, FindUnitsInRadius and CreateUnitByName, enums) is set up
  in the test file with `rawset`. A later `kind: test` task could move it into the stub.
- aoh_lint's global-assignment regex flags any `name = …` line that does not end in `,`, which
  includes local reassignments and multi-line table fields. I worked around it with named-local
  handlers and bracketed `KINDS` keys.
- The module calls `require("abilities/other/generic")` as the notes say. That file also requires
  lib/timers, lib/my and lib/ai. If a wrapper ability's script loads on the client, these are loaded
  there too. Please check this in 0024.

**[human] playtest (after 0024 migrates a wrapper; nothing uses this module yet)**
1. Start a round with the migrated boss (Juggernaut) on normal difficulty. The boss should stop,
   show the warning circle or line, play the Mars spear sound and wind up, then cast the real spell
   once the warning ends. There must be no double cast, and the boss must not freeze after casting.
2. Do the same on hard (`_difficulty == 2`). Point wrappers should cast one extra time, and the 2nd
   and later casts should aim at a hero in range. All telegraphs should be shorter (×0.8).
3. Unit-target wrapper: run more than 475 away during the warning. An `npc_target` dummy should
   appear between you and the original spot, the spell should hit it, and the dummy should die
   about 1 s later.
4. Silence the boss during the cast. It should re-issue the cast after the silence ends, as long as
   it is within `cast_point + 1 s`; after that the queue moves on.
- Console proof: `script_reload` must produce no Lua errors. With `dota_ability_debug`, or a temporary
  `print` in modifier_boss:Confirm (not committed), you should see exactly one Confirm per iteration.

## Review
APPROVE
Round 2. All three items from round 1 are resolved:
1. Dummy leak: `modifier_telegraph_confirm:OnDestroy` (telegraph.lua:359-369) moves `job.dummy_mod`
   to `DUMMY_LINGER` on every exit path (confirm, timeout, `on_cancel` removal).
   `pick_cast_target` (:129) clears the previous iteration's dummy fields first. This is covered by
   `test_unconfirmed_dummy_lingers`.
2. Re-issue guard: `reissue` (:346-356) calls `Destroy()` when `needs_target` and `cast_target` is
   no longer valid. This is covered by `test_lost_cast_target_stops_reissue`.
3. The backlog line was added under "Found by agents" (tasks/backlog.md:38).

Checklist: 1 spec — the API, job fields (prio 0, deadline 6, cast_timeout = cast point + 1),
difficulty table, rate fix, confirm/weak/re-issue logic and on_cancel match the notes and DoD
1a-1f. 2 scope — the diff touches telegraph.lua, test_telegraph.lua, the task file and a
one-line backlog entry. The backlog entry is allowed by protocol and was requested in round 1. No
existing test was changed. 3 conventions — the only new global is `modifier_telegraph_confirm`.
`LinkLuaModifier` is called once, with `/` and `.lua`. Enums are used throughout. No datadriven
ability was added, and the numbers come from KV. 4 Dota — `IsServer` guards are in place on
OnSpellStart, OnCreated and OnDestroy. Both particles are released. The think is 0.1 s and is
stopped in OnDestroy. Handles are checked with `valid()` / `IsNull` before use. There is no
per-tick FindUnitsInRadius. 5 KV — not touched. 6 Result — the diff file list matches.
aoh_lint: 0 fail, 1 size WARN (371 > 300, for the teamlead). `[human]` items are listed, not
claimed. qa re-runs test.sh and check.sh. 7 hygiene — no print, no TODO, English.

---
REQUEST_CHANGES
1. telegraph.lua:136 + :351 — the `npc_target` dummy leaks when the cast is never confirmed.
   `modifier_dummy` is added with `duration = -1`, and the only things that end it are the confirm
   path (`SetDuration(DUMMY_LINGER)`) and `on_cancel`. boss_queue.lua:108-114 moves on after
   `cast_timeout` without calling `on_cancel`, and `modifier_telegraph_confirm` expires silently.
   One case is a boss silenced for the whole `cast_point + 1 s`: the dummy then stays on the map
   forever. A multi-iteration unit_target also overwrites `job.dummy`/`job.dummy_mod` on every
   iteration, so `on_cancel` only kills the last dummy. The old code retried without a limit, so
   it never hit this. Fix: in `modifier_telegraph_confirm:OnDestroy`, put an unconfirmed dummy on
   `DUMMY_LINGER` or kill it (track a `self.confirmed` flag). Add a test: confirm modifier
   destroyed without the spell going on cooldown → dummy is no longer immortal.
2. telegraph.lua:334 (with :168) — the re-issue path in `OnIntervalThink` calls `issue()`, and for
   unit_target that runs `CastAbilityOnTarget(job.cast_target, …)` without checking that the
   target is still valid. If the hero dies or disconnects (or the dummy is removed) during the
   1.3 s window, the next think passes a dead or null handle (ADR-0002 rule 6). Guard it with
   `valid(job.cast_target)`. If the target is invalid, stop re-issuing and let the modifier run out
   or `Destroy()`. Add a test case for it.
3. Non-blocking, tests/test_telegraph.lua:125 — `rawset(_G, …)` replaces the stub's
   `ParticleManager`/`FindUnitsInRadius`/`CreateUnitByName` for every test file that runs after
   this one. That is acceptable while dota_stub.lua is frozen. Add a line to tasks/backlog.md
   (Found by agents) asking a `kind: test` task to move this surface into tests/dota_stub.lua.

Checklist: 1 spec — the API, job fields, difficulty table (no_target has no scaling, matching
generic.lua:351-403), rate fix and Confirm modifier match the notes, except items 1-2.
2 scope — only the two allowed files and the task file. 3 conventions — no new globals beyond
`modifier_telegraph_confirm`, LinkLuaModifier used once with `/` and `.lua`, enums used, no
datadriven; the local constants are ported timings named in the notes. 4 Dota — IsServer guards
are in place; both particles are released; the think is 0.1 s and stopped in OnDestroy; no
per-tick FindUnitsInRadius; items 1-2 are open. 5 KV — not touched. 6 Result — the grep counts
and file list agree with the diff. aoh_lint gives 0 fail and 1 size WARN (358 > 300, accepted
for the teamlead). `[human]` items are listed, not claimed. 7 hygiene — no print, no TODO,
English.

## QA
PASS
1. DoD 1: `test.sh telegraph` → 10 passed, TEST RESULT: OK (covers a–f plus the round-2 dummy and re-issue tests).
2. DoD 2: grep Timers → 0; grep ticket/OnAbilityExecuted → 0.
3. DoD 3: LinkLuaModifier count → 1.
4. DoD 4: `StartIntervalThink(0.0…` → no matches.
5. DoD 5: `check.sh lua` → CHECK RESULT: OK (lua).
6. DoD 6: `aoh_lint.py 0014` → 0 fail, 1 size WARN (371 > 300).
7. DoD 7: the diff touches the telegraph module, the test file and the task file. It also touches one line in tasks/backlog.md. The protocol allows that file, and the reviewer asked for the line. It is not in allowed_paths, so I treated it as a minor deviation and did not fail on it.

For the human (after 0024 migrates a wrapper; nothing uses the module yet):
- Run the Juggernaut round on normal and on hard (`_difficulty == 2`). Expected: the boss stops, shows the warning, plays the Mars spear sound and winds up, then casts once. There must be no double cast and no freeze.
- On hard, point wrappers cast one extra time, and casts 2+ aim at a hero in range. Telegraphs are ×0.8.
- Unit-target wrapper: run more than 475 away. An `npc_target` dummy appears and the spell hits it. The dummy dies about 1 s later, including when the boss is silenced for the whole cast window.
- Silence the boss mid-cast. It re-issues the cast within `cast_point + 1 s`, then the queue moves on.
- Console: `script_reload` gives no Lua errors, and there is exactly one Confirm per iteration.
