# Backlog

Active feature branch: feat/p0-foundation
(The pipeline merges tasks into this branch; `main` changes only by the owner's hand —
scripts/agents/finish_feature.sh after a playtest. Order under `## Next` is the owner's priority;
the teamlead writes task files for the first items that have none: `scripts/agents/run_queue.py --plan`.
Audit and phase plan: docs/adr/0002-target-architecture.md → "AOH2Reborn — аудит и план модернизации".)

## Next
- 0001 p0: `scripts/agents/link_addon.sh` — symlink/junction game/ and content/ into the Dota 2 Workshop Tools folder (macOS + Windows paths, idempotent, prints what it did) — ADR-0001 §Как запускать · S · checks none · needs_approval ([human]: the map opens in tools)
- 0002 p0: convert `resource/addon_russian.txt` from UTF-16 LE to UTF-8 (BOM-less) and normalize line endings in resource/*.txt; `python3 tools/kvcheck.py` still clean — audit §KV · S · checks kv
- ~~0003~~ done by owner 2026-10-29 (de8efbf): p0: `stylua` over the whole Lua tree in ONE commit, no logic changes; `scripts/agents/check.sh lua --all-files` stylua part green — ADR-0001 §Решение 4 · L (generated) · checks lua · role developer
- 0004 p0: fix 5 `not x == y` sites (luacheck W582; (not x)==y in Lua): boss_aghanim_spell_swap.lua:266-267, boss_void_spirit_counter.lua:108, windrunner_force_fire_toggle.lua:89, aohgameround.lua:132, modifier_boss.lua:56 → `x ~= true`; then drop '582' from tools/gen_luacheckrc.py ignore and regen · S · checks lua · role developer
- 0005 p0: luacheck on `check.sh lua --all-files` = 4341 legacy warnings (mostly W112/W111 on modifier/ability class globals). Add a baseline ratchet like tools/kvcheck.baseline, or `allow_defined_top` in the generator for Dota class pattern; goal: --all-files green so stylua+luacheck gate the whole tree · M · checks lua · role developer
- 0004 p0: `tools/kvgen.py` skeleton: reads `kv-src/*.yaml`, renders KV via templates, `--check` compares with the committed output; first template = the 59 `*_wrapper` boss telegraph entries — audit §KV "Генерация" · M · checks kv · role developer-hard · depends 0002
- 0005 p1: fix the 19 "critical bugs" rows that are one-line fixes (ParticlzeManager, `point`, `caster`, `enemy`, windrunner `not`, `1/delay` precedence, `is_talon`, `v[GetModifierPercentageCooldown]`, DOTA_UNIT_TARGET_FLAGS_NONE); each with a test where logic allows — audit §Критичные баги · M · checks all · role developer-hard · needs_approval
- 0006 p1: CustomGameEvent handlers use `keys.PlayerID` + ownership check (aohgamemode vote/credits, aohgameskills, dashmanager) — audit bug 7 · S · checks lua · role developer-hard · needs_approval
- 0007 p1: remove the 4 duplicated KV entries and the 55 duplicate keys in tools/kvcheck.baseline (decide per entry which copy the engine kept — the LAST one wins — and keep that); baseline shrinks to 0 — audit §A6 · M · checks kv
- 0008 p1: replace removed vanilla names: `aghanim_spear` (boss_aghanim_spear → ability_lua), `skeleton_king_vampiric_aura`, `beastmaster_call_of_the_wild_boar`, marci talent; tools/vanilla_diff.baseline → 0 — audit §vanilla · M · checks kv · needs_approval ([human]: Aghanim boss spear fires)
- 0009 p1: neutral slots: `lib/end_screen.lua` reads DOTA_ITEM_NEUTRAL_ACTIVE_SLOT and _PASSIVE_SLOT; items[9] not overwritten — audit bug 13 · S · checks lua
- 0010 p1: Universal attribute: `modifier_bonus`, `modifier_tier_4`, `diff_doom` handle DOTA_ATTRIBUTE_ALL explicitly — audit §Legacy 5 · S · checks lua
- 0011 p1: magic numbers → enums with bit.band (`damage_flags ~= 16` ×13, `order_type == 1/10`, `GetAbilityType() ~= 1`) — audit §Legacy 8 · M · checks lua
- 0012 p1: dedicated-server shop check: `[human]` lobby test per Valve #34007; if broken, a Lua purchase filter (`SetItemAddedToInventoryFilter`) that enforces ItemPurchasable 0 — ADR-0002 §KV · M · role developer-hard · needs_approval
- 0013 p2: `modifier_boss` uses `core/boss_queue.lua` (tick 0.1 s, Submit/Lock/Confirm/clear on OnDestroy); old RequestTicket/QueryTicket kept as thin adapters until 0014-0016 land — ADR-0002 §5 · M · tests [boss_queue] · role developer-hard · needs_approval
- 0014 p2: `generic_aoe` family → `ability_lua` base class `bosses/_shared/telegraph.lua` submitting jobs; migrate Juggernaut's wrappers first — ADR-0002 §5 · L · role developer-hard · needs_approval ([human]: Juggernaut casts every ability, no freeze over 10 rounds)
- 0015 p2: boss phase controller replaces the 16 `boss_*_init.lua` (thresholds from KV) — ADR-0002 §5 · M · role developer-hard
- 0016 p2: `boss_revenge` base (9 files) + `boss_counter` base (3 files) — audit §Дубли 1,4 · M · role developer
- 0017 p3: override talents → inline `AbilityValues` in the owning ability (generated from a table by tools/kvgen.py); 126 WARN lines in vanilla_diff → 0 — ADR-0002 §KV · L · checks kv · role developer-hard · needs_approval
- 0018 p4: `core/fx.lua` (once/attach with auto-release) and the 40 unreleased CreateParticle sites — audit §Производительность · L · checks lua
- 0019 p4: `global_damage_effects` → damage filter path; parent-first filters in octarine, mars, zuus, echo_wand handlers — audit §Производительность · M · role developer-hard
- 0020 p4: delete dead code: statcollection/, dpsmanager.lua, 15 unreferenced files, options/containers/selection/modmaker/attachments Panorama libs — audit §Мёртвый код · M · needs_approval
- 0021 p5: restore clean JS from `scriptsUnobfuscated_2021-04-05.zip` for hud/end_screen/difficulty/skill_bar; drop the zip — audit §Panorama · M · needs_approval ([human]: HUD, vote, skill bar, end screen work)

## Found by agents
(one line each: what, where, why it matters — the teamlead promotes these into tasks)
- 0004: 6th W582 site `abilities/heroes/windrunner_force_fire_toggle.lua:89` `not target:GetTeam() ~= self.parent:GetTeam()` is always true (auto focus-fire also fires on allied/deny targets); blocks `check.sh lua --all-files` once 582 is un-ignored — add the file to 0004's allowed_paths with fix `target:GetTeam() ~= self.parent:GetTeam()` (behaviour change) or drop the clause (behaviour-identical).

## For the owner
- accept docs/adr/0001-ai-team.md and docs/adr/0002-target-architecture.md (status Proposed → Accepted) before the first `run_queue.py --plan`
- answer docs/reports/decisions-needed.md (playtest machine, Workshop account)
- brew install luacheck stylua lua@5.1; python3 tools/vanilla_snapshot.py; `claude` once in the repo to trust it (hooks)
