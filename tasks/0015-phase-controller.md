---
id: 0015
title: bosses/_shared/phases.lua — HP-threshold phase controller; boss_juggernaut_init migrated to it
status: ready
epic: p2
prefix: p2
kind: code
size: M
role: developer-hard
base: feat/p0-foundation
branch: task/0015-phase-controller
depends_on: [0024]
allowed_paths:
  - game/dota_addons/attackcopy/scripts/vscripts/bosses/_shared/phases.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_juggernaut_init.lua
  - game/dota_addons/attackcopy/scripts/npc/npc_abilities_custom.txt
  - tests/test_phases.lua
  - tests/dota_stub.lua
  - tools/luacheck.baseline
checks: all
tests: [phases]
needs_approval: true
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
---

## Goal
ADR-0002 §Решение 5: the 16 `boss_*_init.lua` files each poll `GetHealthPercent()` with Timers and
`EndCooldown()` a wrapper when HP drops under a KV threshold. This task adds one shared phase
controller (a hidden intrinsic modifier with a 0.5 s think, thresholds from KV) and migrates the
first init, Juggernaut's, from `ability_datadriven` + Timers to `ability_lua` on the controller.
The other 15 inits are later tasks.

## Definition of Done
V = `game/dota_addons/attackcopy/scripts/vscripts`, K = `game/dota_addons/attackcopy/scripts/npc/npc_abilities_custom.txt`
1. `scripts/agents/test.sh phases` → `TEST RESULT: OK`; tests/test_phases.lua covers at least:
   a. on create: each `locked` ability gets `StartCooldown(9999)`, each `initial` ability gets `StartCooldown(<its KV value>)`;
   b. HP 80 % with thresholds 75/50 → nothing unlocked; HP 74 % → the 75-ability gets `EndCooldown()` once, the 50-one does not;
   c. an ability already unlocked is not touched again on later thinks (EndCooldown count stays 1);
   d. HP exactly at the threshold (75 %) does NOT unlock (strict `<`, as today);
   e. all phases unlocked → the think stops (`StartIntervalThink(-1)`);
   f. an ability name the unit does not have is skipped without an error.
2. K entry `boss_juggernaut_init`: `"BaseClass" "ability_lua"`, `"ScriptFile" "abilities/bosses/boss_juggernaut_init.lua"`, `AbilityValues` with `blade_fury_cooldown 4`, `instant_strike_threshold 75`, `omni_slash_threshold 50`; no `AbilitySpecial`, `Modifiers`, `RunScript` (Grep the entry's line range).
3. `grep -c "Timers" V/abilities/bosses/boss_juggernaut_init.lua V/bosses/_shared/phases.lua` → `0` for both; `grep -c "^function init" V/abilities/bosses/boss_juggernaut_init.lua` → `0`.
4. `grep -c "StartIntervalThink(0.5)" V/bosses/_shared/phases.lua` → `1`; `grep -c "LinkLuaModifier" V/bosses/_shared/phases.lua` → `1`.
5. `python3 tools/kvcheck.py` → no new error vs feat/p0-foundation.
6. `scripts/agents/check.sh all` → `CHECK RESULT: OK (all)`.
7. `python3 scripts/agents/aoh_lint.py 0015` → 0 fail (NEEDS APPROVAL expected).
8. `git diff --stat feat/p0-foundation...HEAD` → only allowed_paths + this task file.
9. [human] Local game, Juggernaut boss: Blade Fury first casts ~4 s after spawn; Leading Blade only after HP < 75 %; Omnislash only after HP < 50 %; no Lua error mentioning phases.lua or boss_juggernaut_init in the console.

## Notes from teamlead
- Current behaviour to keep (V/abilities/bosses/boss_juggernaut_init.lua, 25 lines; KV K:19150-~19190):
  on create `boss_juggernaut_instant_strike_wrapper` and `boss_juggernaut_omni_slash_wrapper`
  StartCooldown(9999), `boss_juggernaut_blade_fury_wrapper` StartCooldown(blade_fury_cooldown);
  every 0.5 s, `GetHealthPercent() < instant_strike_threshold` → EndCooldown instant strike;
  `< omni_slash_threshold` → EndCooldown omni slash. The datadriven modifier is misnamed
  `modifier_enigma_init` (copy-paste) — the new code does not reuse that name.
- API (keep exactly): `local phases = require("bosses/_shared/phases")`;
  `boss_juggernaut_init = phases.class({ initial = { boss_juggernaut_blade_fury_wrapper = "blade_fury_cooldown" }, locked = { boss_juggernaut_instant_strike_wrapper = "instant_strike_threshold", boss_juggernaut_omni_slash_wrapper = "omni_slash_threshold" } })`.
  Table values are KV key names; numbers are read with `self:GetSpecialValueFor(key)` (ADR-0002 §4 Lua 3).
  `phases.class` returns an ability class whose `GetIntrinsicModifierName` is
  `modifier_boss_phases` (owned and linked once in phases.lua), hidden, not purgable, `RemoveOnDeath` true.
- Server only (`if not IsServer() then return end` in OnCreated/OnIntervalThink). Parent null/dead →
  StartIntervalThink(-1). OnDestroy stops the think. No `print`.
- KV: keep `AbilityBehavior` (PASSIVE | HIDDEN) and `AbilityType`; hidden → no tooltip.
- depends_on 0024 only to keep the Juggernaut boss changes in one order on one file (K); the code
  does not need the telegraph.
- tests/dota_stub.lua: add only what the tests need (GetHealthPercent, ability StartCooldown/EndCooldown recorders, FindAbilityByName).
- Legacy warnings: if check.sh reports "fixed" baseline entries run `python3 tools/luacheck_ratchet.py --prune`, never `--update-baseline`.

## Handoff

## Result

## Review

## QA
