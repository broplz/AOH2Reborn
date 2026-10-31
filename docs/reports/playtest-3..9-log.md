# Playtests 3–9 — console log triage (2026-10-31)

Seven short runs on `feat/p0-foundation` (tags `aoh/playtest-3`, `aoh/playtest-4`, then untagged
diagnostic builds up to 1dec912). The goal was the "game ends after round 1 / the Radiant ancient
dies with no kill" bug. Diagnostics were removed in 661e3a7. Tasks are queued in tasks/backlog.md
(0052 closed, 0054–0058).

## 1. Ancient at 0 HP — found: `AbilitySpecial` is not read
- `ancient_increase_stats` rescales the ancient's max HP each round from `health_base` +
  `health_per_round`. Both came back as 0 from `GetSpecialValueFor`, so the first rescale set max
  HP to 0 and the ancient was gone without an `entity_killed`.
- The current engine does not read legacy `AbilitySpecial` blocks for our custom abilities (the
  same root as the empty item tooltips, 0052). With the entry moved to `AbilityValues` (1dec912)
  the values arrive and the ancient survives. The spike 0052 is confirmed.
- All our KV is still `AbilitySpecial` (~1138 blocks), so every `GetSpecialValueFor` in a custom
  ability or item may return 0. Migration: 0054 (P1).
- Second case already found: weavers in round 12 (Swarm, with Nyx) flicker every frame:
  `custom_weaver_behavior` reads `interval` (5) as 0 and calls `StartIntervalThink(0)`, and
  `item_flicker_boss` has `AbilityCooldown 0`. Brother's report; fix 0057.
- The ancient now refuses a max HP <= 0 with a warning instead of applying it.

## 2. Spawn groups — not involved
`AOHSpawner:End()` passed the `PrecacheUnitByNameAsync` callback id to `UnloadSpawnGroupByHandle`.
With the unload disabled the ancient still died, so the hypothesis is refuted. The call stays
removed: by api.json the id is a `precacheId`, not a `SpawnGroupHandle`. See
docs/notes/spawn-groups.md.

## 3. API signature changes — fixed (0c689f8)
`GetIntellect(skipNoConsume)`, `GetAttacksPerSecond(ignoreTempAttackSpeed)`,
`SpendCharge(delayRemove)` now need an argument; `UseResources` gained `useHealth` as the 2nd
argument. `tools/apicheck.py` gates call arity in `check.sh lua` (docs/notes/apicheck.md). Our own
callbacks with odd arity: 0053.

## 4. Lua errors still in the log
`lib/safe_call` (handler that cannot throw, wrapped game-mode thinks, event listeners, every
`class()` and every RunScript function under `AOH_SAFE_CALL_ALL`, now off) made these visible:
- `boss_death_prophet_init.lua:8-21` — the two threshold timers keep running after DP dies;
  nothing stops them, so `caster:GetHealthPercent()` runs on a dead/removed unit. 0055.
- `abilities/other/generic.lua:471` (`generic_target`) — `spell:GetCastPoint()` in the timer.
  0056.

## 5. "error in error handling" every ~9 s — open
Still periodic after the timers handler fix (a197533). `safe_call` on every Lua class and RunScript
function did not catch it, so the source is not one of our Lua classes: a datadriven KV action, a
Panorama/engine callback or a library outside the wrapped set. 0058.

## Next playtest `[human]`
- the ancient survives several rounds and its HP grows per round;
- weavers flicker at most every 3 s (after 0057);
- count the "error in error handling" lines and note the time between them.
