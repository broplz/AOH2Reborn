---
id: 0018
title: core/fx.lua — particle helpers with automatic release (module + tests only)
status: ready
epic: p4
prefix: p4
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0018-core-fx
depends_on: []
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/core/fx.lua
  - tests/test_fx.lua
checks: lua
tests: [fx]
needs_approval: false
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
---

## Goal
Add `core/fx.lua`, the particle helper module that ADR-0002 §Решение 2 (`core/`: fx …) and
ADR-0002 §Lua 7 / aoh-rules rule 7 tell every ability to use, so that no call site has to remember
`ReleaseParticleIndex` / `DestroyParticle`. This task ships the module and its unit tests only;
migrating the legacy CreateParticle sites is a later task (backlog 0018 follow-ups).

## Definition of Done
1. `scripts/agents/check.sh lua` prints `CHECK RESULT: OK`.
2. `scripts/agents/test.sh fx` prints `TEST RESULT: OK`, and tests/test_fx.lua has at least the 6
   test functions listed in Notes (`grep -c "^function M.test_" tests/test_fx.lua` ≥ 6).
3. `grep -n "^[A-Za-z_][A-Za-z0-9_]* *=" game/dota_addons/attackcopy/scripts/vscripts/core/fx.lua`
   is empty (no globals; the module is `local M = {}` … `return M`).
4. `grep -c "ParticleManager:CreateParticle" game/dota_addons/attackcopy/scripts/vscripts/core/fx.lua`
   prints `1` (one private `create` helper used by every public function).
5. `python3 scripts/agents/aoh_lint.py 0018` passes.
6. `git diff --stat feat/p0-foundation` lists only the two allowed files plus this task file.

## Notes from teamlead
API (exact names; later tasks and the reviewer rely on them):
- `fx.once(name, attach, owner, controls)` → creates, applies `controls`, calls
  `ReleaseParticleIndex`; returns nothing. For fire-and-forget effects.
- `fx.attach(name, attach, owner, controls)` → creates, applies `controls`, returns the index. The
  caller must later call `fx.stop(index, immediate)`.
- `fx.stop(index, immediate)` → `DestroyParticle(index, immediate == true)` then
  `ReleaseParticleIndex(index)`; `nil` index is a no-op (callers clear fields in OnDestroy).
- `fx.bind(modifier, name, attach, owner, controls)` → creates, applies `controls`, then
  `modifier:AddParticle(index, false, false, -1, false, false)` so the engine destroys it with the
  modifier; returns the index.
- `controls` is an optional table `cp → value`: a Vector → `SetParticleControl(idx, cp, v)`; a table
  `{ ent = unit, attach = PATTACH_*, point = "attach_hitloc" }` →
  `SetParticleControlEnt(idx, cp, v.ent, v.attach, v.point, v.ent:GetAbsOrigin(), true)`. One private
  `apply(idx, controls)` loop; no per-type branches duplicated across the public functions.
- Read `ParticleManager` at call time (do not cache it in a local at require time) — the tests
  swap it.

Tests (tests/test_fx.lua, same `local M = {} … return M` shape as tests/test_boss_queue.lua, uses
`T.eq`/`T.truthy`): the stub has no ParticleManager and tests/dota_stub.lua is frozen for this task.
Each test installs a recorder table in `_G.ParticleManager` (records every call in order) and
restores the previous value before returning — tests/test_telegraph.lua already rawsets one
globally, so never assume it is nil and never leave yours behind. `Vector` comes from the stub; for
`{ ent = … }` use `T.stub.unit("x")` and give it a `GetAbsOrigin` in the test.
Required tests: `test_once_releases`, `test_once_applies_vector_and_ent_controls`,
`test_attach_returns_index_without_release`, `test_stop_destroys_then_releases`,
`test_stop_nil_is_noop`, `test_bind_registers_with_modifier`.

Out of scope: touching any existing CreateParticle site (telegraph.lua included), sounds, core/log.
