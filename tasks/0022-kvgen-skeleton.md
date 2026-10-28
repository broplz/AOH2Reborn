---
id: 0022
title: tools/kvgen.py skeleton — YAML source + template, --check against the committed boss wrapper entries
status: ready
epic: p0
prefix: p0
kind: code
size: M
role: developer-hard
base: feat/p0-foundation
branch: task/0022-kvgen-skeleton
depends_on: [0002]
allowed_paths:
  - tools/kvgen.py
  - tools/kvgen_templates/boss_wrapper.kv
  - kv-src/boss_wrappers.yaml
  - tools/fixtures/kvgen/**
checks: kv
tests: []
needs_approval: false
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
---

## Goal
ADR-0002 §Решение 2 (data layer: `kv-src/*.yaml → tools/kvgen.py → scripts/npc/*.txt`) and phase
p0 "каркас kvgen". Build the generator skeleton and prove it on its first family: the boss
telegraph `*_wrapper` entries in npc_abilities_custom.txt (datadriven entries whose OnSpellStart
RunScript calls a `generic_*` function in `abilities\other\generic.lua`). In this task the generator
writes NO game file. `--check` renders every entry from the YAML and compares it with the entry
that is already in npc_abilities_custom.txt. Where the generated KV will live is a separate owner
decision (docs/reports/decisions-needed.md, 2026-10-29), and so is the migration.

## Definition of Done
1. `python3 tools/kvgen.py --check` exits 0 and its last line is `KVGEN RESULT: OK (N entries)`.
   N = the number of `*_wrapper` entries in npc_abilities_custom.txt whose `OnSpellStart/RunScript/Function`
   starts with `generic_`. The teamlead's grep found 56 on 2026-10-29.
2. `python3 tools/kvgen.py --self-test` exits 0 and prints `KVGEN SELFTEST: OK`. It must cover, using
   files under tools/fixtures/kvgen/: (a) a matching entry → OK, (b) a changed value → FAIL naming
   `entry/key` with both values, (c) an entry that is in the YAML but missing from the KV → FAIL, (d) a family
   entry that is in the KV but missing from the YAML → FAIL.
3. `python3 tools/kvgen.py --list boss_wrapper` prints the covered entry names, one per line.
   `python3 tools/kvgen.py --list boss_wrapper | wc -l` equals N from DoD 1.
4. `grep -n -E "^import yaml|^from yaml|import yaml" tools/kvgen.py` → no output (stdlib only).
5. `grep -c "_wrapper" kv-src/boss_wrappers.yaml` → ≥ N.
6. `scripts/agents/check.sh kv` → `CHECK RESULT: OK (kv)`.
7. `git diff --stat feat/p0-foundation...HEAD` → only allowed_paths + this task file. No file
   under game/ is changed.

## Notes from teamlead
- Reuse `tools/kvlib.py` (`parse_file`, `entries`, `Node`, `NPC_DIR`) to read the KV. Do not
  write a second KV parser. Equality in `--check` = the same ordered list of (key, value/child)
  pairs, with keys compared case-sensitively and values compared exactly after trimming whitespace.
  Comments and whitespace are ignored. A mismatch line has the shape
  `KVGEN FAIL <entry>/<path>: kv=<a> gen=<b>`.
- YAML: PyYAML is not installed, and agents must not install packages. kvgen reads a documented
  subset: top-level `family:` and `template:` scalars, then `entries:` as a list of flat mappings of
  scalars (`- name: x` / `  radius: "375"`). Strings may be quoted. Put the subset in the module
  docstring. Anything else is a parse error with file:line.
- Template: tools/kvgen_templates/boss_wrapper.kv in KV text with `{field}` placeholders. Optional
  blocks are allowed only when real entries differ (e.g. a 4th AbilitySpecial or a missing
  `IsCastableWhileHidden`). Prefer per-entry fields over a second template. Wrappers that do not fit
  one template without special-casing stay out of the family. List them in the YAML header as
  `# excluded: <name> — <reason>`, and they are not counted in N.
- Bootstrap the YAML with a one-off mode `python3 tools/kvgen.py --extract boss_wrapper`, which writes
  kv-src/boss_wrappers.yaml from the current KV. Keep the mode: the migration task will reuse it.
  Do not type 56 entries by hand.
- Values are reproduced exactly as they are now, including `ScriptFile "abilities\other\generic.lua"`
  with a backslash. Fixing that is the migration task's job, together with the queue (0014).
- Known entries outside the generic_* family: `boss_spirit_breaker_charge_wrapper` and any wrapper
  without a RunScript. Check them with `python3 tools/kvcheck.py --show <name>`.
- The KV file has 21k lines. Use Grep with head_limit, or Read with offset/limit ≤ 400. Never read it whole.
- Out of scope: writing into scripts/npc, `#base` includes, marker regions, check.sh integration
  (a later task after the owner decides where the output goes), and the 0014 telegraph base.
- Re-spec 2026-10-29 (teamlead): allowed_paths entry fixed to `tools/fixtures/kvgen/**` (guard_paths
  matches globs; a trailing `/` is a literal path). Nothing else changes. N = 55 is accepted: 56 generic_*
  wrappers minus the excluded `boss_legion_commander_gods_rebuke_wrapper` (listed as `# excluded:` in the
  YAML). Session 2 = the fixture list in ## Handoff, then --self-test and the DoD run.

## Handoff
Session 1 (developer-hard), commit 5f6b015. Blocked by a hook: `guard_paths.py` reads the
allowed_paths entry `tools/fixtures/kvgen/` as a literal path, so it rejected the Write of
`tools/fixtures/kvgen/abilities.kv`. Unblock: the teamlead changes the entry to `tools/fixtures/kvgen/**`
(or the hook treats a trailing `/` as a directory). There is also a line under "Found by agents" in tasks/backlog.md.

Done and verified this session:
- `tools/kvgen.py`: the YAML subset parser (documented in the module docstring, errors as file:line),
  the template loader (`"{field}"` placeholders, `[?field]` … `[/field]` optional blocks), the renderer,
  the KV comparer (`KVGEN FAIL <entry>/<path>: kv=<a> gen=<b>`), and the `--check [family]`,
  `--list <family>`, `--extract <family>` and `--self-test` modes. It uses only kvlib and the stdlib.
  `--extract` matches the template against each KV entry by backtracking and binds the fields, so no
  values were typed by hand. It keeps any existing `# excluded:` reasons when it rewrites the file.
- `tools/kvgen_templates/boss_wrapper.kv`: one template. Specials are slots `sN`/`sN_type`/`sN_value`
  with the fixed ids "0N"; RunScript args are slots `aN` rendered as `"aN" "%aN"`. Six entries
  (fissure group, spectral_dagger) put AbilityCastRange after AbilityCooldown, so the template has an
  optional `cast_range_after_cooldown` field for them.
- `kv-src/boss_wrappers.yaml`: 55 entries. One is excluded: `boss_legion_commander_gods_rebuke_wrapper`,
  the only wrapper with AbilityUnitTargetType before AbilityUnitTargetTeam. So N = 56 − 1 = 55.
  `custom_ice_path_wrapper` (Function `generate_warning_aoe_noanim`) and the charge and dissimilate wrappers
  are outside the family by its predicate.
- Results: `--check` → `KVGEN RESULT: OK (55 entries)`. `--list boss_wrapper | wc -l` → 55.
  The YAML grep gives 59 matches for `_wrapper`. The yaml-import grep prints nothing.
  `check.sh kv` → `CHECK RESULT: OK (kv)`.

Next session: write these fixtures. `SELF_TESTS`/`SELF_TEST_ERRORS` in kvgen.py already expect them:
1. `tools/fixtures/kvgen/abilities.kv`: `"DOTAAbilities"` containing three entries.
   - `fixture_target_wrapper`: generic_target, Team ENEMY, CastRange 700, Cooldown "12", ManaCost 0,
     ICWH 1, special 01 FIELD_FLOAT delay 1.2, RunScript Target TARGET plus `delay`.
   - `fixture_aoe_wrapper`: generic_aoe, Texture, Cooldown then CastRange, ManaCost 10, 01 radius,
     no Target.
   - `fixture_charge_wrapper`: Function `charge_wrapper`, which is not a family member and must be ignored.
2. `ok.yaml`: both members, matching the KV.
3. `changed_value.yaml`: the same as ok.yaml, but `cooldown: "99"` on the target wrapper.
4. `missing_in_kv.yaml`: ok.yaml plus a `fixture_ghost_wrapper` entry.
5. `missing_in_yaml.yaml`: only the target wrapper.
6. `bad_syntax.yaml`: a parse error on line 8 (e.g. a nested mapping or an unquoted `a: b: c`).
   The self-test expects the error message to contain `bad_syntax.yaml:8:`.
The easiest way to write the yaml files is to run `--extract`-style output by hand: 2 entries.
Then run `--self-test`, `--check`, `check.sh kv`, fill ## Result, set status review.

## Result

## Review

## QA
