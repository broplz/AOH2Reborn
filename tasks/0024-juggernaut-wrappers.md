---
id: 0024
title: Juggernaut's 3 boss wrappers → ability_lua on bosses/_shared/telegraph.lua (split from backlog 0014)
status: blocked
epic: p2
prefix: p2
kind: code
size: S
role: developer-hard
base: feat/p0-foundation
branch: task/0024-juggernaut-wrappers
depends_on: [0014]
allowed_paths:
  - game/dota_addons/attackcopy/scripts/npc/npc_abilities_custom.txt
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_juggernaut_blade_fury_wrapper.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_juggernaut_omni_slash_wrapper.lua
  - game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses/boss_juggernaut_instant_strike_wrapper.lua
checks: all
tests: [telegraph]
needs_approval: true
returns: 0
sessions: 1
blocked_reason: aoh_lint.py:46 rejects the mandated `boss_x = telegraph.class(...)` global (DoD 2 vs DoD 6); lint fix is outside allowed_paths
reviewed_sha: 
qa_sha: 
---

## Goal
Backlog 0014 second half: migrate the first boss off generic.lua tickets (ADR-0002 §5). The three
Juggernaut `*_wrapper` entries in npc_abilities_custom.txt become `ability_lua` entries built with
`telegraph.class` (task 0014). Names stay, so the unit AI (npc_units_custom.txt:451-470) and
boss_juggernaut_init.lua keep working unchanged.

## Definition of Done
K = `game/dota_addons/attackcopy/scripts/npc/npc_abilities_custom.txt`, B = `game/dota_addons/attackcopy/scripts/vscripts/abilities/bosses`
1. In K, each of `boss_juggernaut_blade_fury_wrapper`, `boss_juggernaut_omni_slash_wrapper`, `boss_juggernaut_instant_strike_wrapper` has `"BaseClass" "ability_lua"`, `"ScriptFile" "abilities/bosses/<name>.lua"`, an `AbilityValues` block, and no `AbilitySpecial`, `OnSpellStart`, `RunScript` or `ability_index` (check with Grep on the entry's line range).
2. `grep -c "telegraph.class" B/boss_juggernaut_*_wrapper.lua` → 1 per file.
3. `python3 tools/kvcheck.py` → no new error vs feat/p0-foundation (baseline unchanged).
4. `scripts/agents/check.sh all` → `CHECK RESULT: OK (all)`.
5. `scripts/agents/test.sh telegraph` → `TEST RESULT: OK`.
6. `python3 scripts/agents/aoh_lint.py 0024` → 0 fail (NEEDS APPROVAL expected).
7. `git diff --stat feat/p0-foundation...HEAD` → only allowed_paths + this task file; generic.lua not in it.
8. [human] Local game, Juggernaut boss on easy and on difficulty 2: Blade Fury, Leading Blade (below 75 % HP) and Omnislash (below 50 % HP) each show their warning and then fire; no freeze over 10 rounds (ADR-0002 §3 p2 gate); no Lua error from telegraph.lua or the wrappers in the console.

## Notes from teamlead
- Values (copy exactly into AbilityValues; current entries K:18818-18857, :18895-18933, :19013-19065):
  | wrapper | kind | spell | values |
  |---|---|---|---|
  | blade_fury_wrapper | no_target | boss_juggernaut_blade_fury | radius 375, delay 0.8 |
  | omni_slash_wrapper | unit_target | boss_juggernaut_omni_slash | delay 1.5 |
  | instant_strike_wrapper | point | boss_juggernaut_instant_strike | radius 140, delay 1.20, is_line 1, line_length 1000 |
  Drop `ability_index` (28 / 3 / 27). Keep every other key (AbilityBehavior, target team/type/flags,
  cast range, cast point, cooldown, mana cost, IsCastableWhileHidden, AbilityTextureName, immunity/dispel).
- Each Lua file: `local telegraph = require("bosses/_shared/telegraph")` and one line
  `boss_juggernaut_<x>_wrapper = telegraph.class({ kind = …, spell = … })`. Nothing else.
- The wrappers are HIDDEN → no tooltip needed. Do not touch the target abilities, boss_juggernaut_init
  (phase controller = 0015) or boss_juggernaut_counter.
- Edit K with Edit on the exact entry; never Read K whole (Grep + Read offset/limit ≤ 400).
- 2026-10-30 escalated: lint regex vs `telegraph.class` → docs/reports/decisions-needed.md. Stays blocked
  until the owner widens aoh_lint.py:46 (then only DoD 6 + ## Result remain) or orders the mixin re-spec.

## Handoff
Session 1 (developer-hard) — blocked on a spec contradiction (DoD 2 vs DoD 6), no strikes.

Done (committed):
- K: the three `*_wrapper` entries are `ability_lua` + `ScriptFile "abilities/bosses/<name>.lua"` +
  `AbilityValues` with exactly the values from the notes; `AbilitySpecial`, `OnSpellStart`/`RunScript`
  and `ability_index` dropped; every other key kept (blade_fury still has its POINT|AOE behavior as
  before — telegraph's no_target kind ignores the cursor).
- B: three files, each `local telegraph = require(...)`, one `-- luacheck: globals <name>` line
  (same pattern as modifier_boss.lua:5 / telegraph.lua:17; without it luacheck W111 fails), and
  `<name> = telegraph.class({ kind = …, spell = … })`.
- Verified: `check.sh all` → CHECK RESULT: OK (all); `test.sh telegraph` → TEST RESULT: OK (10 passed);
  Grep for AbilitySpecial/OnSpellStart/RunScript/ability_index finds nothing in the three entries.

Blocker: `python3 scripts/agents/aoh_lint.py 0024` → 3 FAIL "global assignment … (only
`<name> = class({})` may be global)". The rule (aoh_lint.py:46) exempts only `= class(`, while the
notes, DoD 2 and telegraph.lua:5 require `= telegraph.class(`. Both fixes are outside allowed_paths:
- preferred: aoh_lint.py regex also exempts `= <module>.class(` (e.g. `(?!(\w+\.)?class\()`), or
- telegraph.lua gains a mixin (`boss_x = class({})` + `telegraph.mixin(boss_x, spec)`), which would
  change DoD 2 and the notes.
Not done on purpose: copying methods with a `pairs` loop in each wrapper (duplication, violates
"Nothing else") or dodging the regex. Backlog line added under "Found by agents".
Next: once the lint (or spec) is fixed, re-run aoh_lint 0024 — nothing else is pending; then fill
## Result (callers: npc_units_custom.txt:451-470 AI and boss_juggernaut_init.lua use the names only,
unchanged) and set review.

## Result

## Review

## QA
