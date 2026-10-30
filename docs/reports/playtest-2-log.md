# Playtest 2 — console log triage (tag `aoh/playtest-2`, 2026-10-31)

First full cycle of the map in game. Two runs' console logs were reviewed. Fixed in
`feat/p0-foundation` (§1–§2), everything else is report-only and queued in tasks/backlog.md (§5).
Nothing here was verified in game; every "fixed" line is a `[human]` check for the next playtest.

## 1. "Script Runtime Error: error in error handling" — fixed

- The only `xpcall`/`pcall` in `scripts/vscripts` is `lib/timers.lua` (BMD Timers 1.05). No other
  library installs an error handler.
- Its handler was `msg .. "\n" .. debug.traceback() .. "\n"`. It throws when `msg` is not a string
  (engine errors, `error(table)`) or when `debug` is not exposed to the VScript VM. A throwing handler
  makes Lua report only "error in error handling" and drop the real error. That is why every timer
  callback error at GAME_IN_PROGRESS and in combat showed up this way.
- Fix: one `TimerErrorHandler` that never throws: `tostring(msg)`, `debug.traceback(text, 2)` only
  if available. `Timers:HandleEventError` prints `Warning("Timer <name> error: <msg+traceback>")`.
  Timer behaviour (a failed timer is dropped) is unchanged.
- Next playtest: the real errors behind those dozens of lines will now be visible. One suspect
  (not a timer): `aohgamemode.lua:755` `SpawnEntityFromTableSynchronous("quest", …)`. That is the
  holdout quest entity. If the current build no longer has the `quest` class, it returns nil and
  `:SetTextReplaceValue` on line 756 errors every `OnThink` (0.75 s) during prep time.

## 2. "Attempted to create unknown modifier type modifier_animation_translate_permanent" — fixed

- `LinkLuaModifier` for all three `modifier_animation*` already exists in `lib/animations.lua:55-65`.
  The modifier file is fine (diffed against `modifier_animation_translate.lua`: only the class name,
  3 extra translate codes and `MODIFIER_ATTRIBUTE_MULTIPLE`).
- `lib/animations.lua` is required only by `addon_game_mode.lua` (server VM) and
  `bosses/_shared/telegraph.lua`. The callers of `AddAnimationTranslate` are:
  - `abilities/other/watch_tower_increase_stats.lua:43` — a Lua ability. Its intrinsic modifier is
    created when the watch towers spawn, long before any boss ability (and so `telegraph.lua`) is
    loaded. This ability never required `lib/animations`.
  - `abilities/bosses/boss_{void_spirit,abyssal_underlord,legion_commander}_init.lua` — datadriven
    RunScript, server-only, where `addon_game_mode` already linked the modifier.
- Fix: `watch_tower_increase_stats.lua` requires `lib/animations` (same pattern as telegraph.lua),
  so the modifier is linked in every VM that loads the ability. The registration stays in the
  owner file per ADR-0002 §Code conventions 2. Also dropped three unused `local
  emp_explosion_distortion` shadows in the same file. The `CreateParticle` calls are unchanged;
  the luacheck ratchet keys warnings by line number, so the added require line made them look "new".

## 3. "Cannot create an entity because entity class is NULL -1" (PRE_GAME) — no fix, findings

- Lua does nothing that spawns at PRE_GAME: `OnGameRulesStateChange` only calls `_RevealShop`
  (`AddFOWViewer`). The courier, `npc_playerhelp` and the `quest` entity are created at
  GAME_IN_PROGRESS (`InitVariables`, `_ThinkPrepTime`).
- Every string-literal `CreateUnitByName[Async]` name in vscripts was checked against
  npc_units_custom.txt + npc_heroes_custom.txt. All exist except:
  - `npc_degen_ward` (`abilities/bosses/boss_invoker_degen_ward.lua:10`) — defined nowhere. It
    is a combat spawn, not PRE_GAME. The intended unit is unclear, so it is not fixed.
  - `npc_dota_wisp_spirit` — vanilla Io spirit, expected.
- All 49 `NPCName` values in `scripts/config/aoh2_config.txt` exist in KV.
- The remaining PRE_GAME spawners are not Lua: map entities (`content/.../maps`, binary, not for
  agents) and the engine's own PRE_GAME spawns (couriers, neutral stash, shops). Next step is
  `[human]`: run with `developer 2` / `ent_messages_draw 1` around the PRE_GAME transition, or
  open the map in Hammer and look for entities whose class no longer exists.

## 4a. Particles reported as missing

### Ours: `particles/custom/*` — P1

All eight have both a source in `content/dota_addons/attackcopy/particles/custom/*.vpcf` and a
compiled `game/dota_addons/attackcopy/particles/custom/*.vpcf_c`. The compiled files were last
built in 2023-06 (`ef33a86`). The likely cause is that the current client rejects these stale
`_c` files (old resourcecompiler format, or children/materials they reference no longer exist), so
they need recompiling from source on Windows. The CRC warning in §4d (game folder reached through
a junction/symlink) is the second suspect.

| particle | source | `_c` | used in |
|---|---|---|---|
| watch_tower_aura | yes | yes | `abilities/other/watch_tower_increase_stats.lua:49` |
| watch_tower_ambient | yes | yes | `watch_tower_increase_stats.lua:56` |
| watch_tower_detonation_distortion | yes | yes | `watch_tower_increase_stats.lua:177,183,190,197`; `abilities/bosses/boss_wisp_friendly_counter.lua:151,157,164,171` |
| dash | yes | yes | `abilities/other/hero_attribute_fix.lua:389` |
| blink_cooldown_screen | yes | yes (+ stray `blink_cooldown_screen - copy.vpcf_c`; source `- Copy.vpcf`) | `hero_attribute_fix.lua:195` |
| aoe_warning | yes | yes | 19 sites, e.g. `aohgamemode.lua:398`, `watch_tower_increase_stats.lua:148`, `boss_invoker_solar_strike.lua:8`, `boss_storm_spirit_thundercall.lua:32` |
| custom_emp_explode | yes | yes | `watch_tower_increase_stats.lua:175`; `boss_wisp_friendly_counter.lua:149` |
| abbysal_underlord_custom_darkrift_end | yes | yes | `abilities/heroes/abyssal_underlord_custom_dark_rift.lua:111`; `watch_tower_increase_stats.lua:167`; `boss_wisp_friendly_counter.lua:141`; `boss_abyssal_underlord_undead_cannon.lua:246,255` |

### Vanilla — P2

`tools/vanilla/` holds only the KV snapshot (no particle/pak listing), so particle existence in
the current build cannot be confirmed offline. "Vanilla KV" below means that the current vanilla
KV still references the path.

| particle | vanilla KV still references it | used in |
|---|---|---|
| hero_witchdoctor/witchdoctor_ward_attack | yes (npc_units.txt) | `npc/npc_units_custom.txt:7235` (`npc_courier_replacement` ProjectileModel) |
| hero_invoker/invoker_emp | ability name only, not this path | `watch_tower_increase_stats.lua:134`; `boss_wisp_friendly_counter.lua:107` |
| hero_chen/chen_holy_persuasion_a | no | `npc/npc_abilities_custom.txt:6126` |
| hero_lina/lina_spell_light_strike_array | no | `aohgamemode.lua:407`; `boss_legion_commander_warpath.lua:96` |
| econ/events/ti10/fountain_regen_ti10_lvl3 | no | `lib/my.lua:330` |

Fix per row: find the current name in the Workshop Tools asset browser, or replace it with a
custom particle.

## 4b. dragon_knight / wurmblood models "not in the system" — P2

- `models/heroes/dragon_knight/dragon_knight.vmdl` is used by two creatures in
  npc_units_custom.txt:
  - `npc_dragon_knight` (line 2342): spawned ×3 by `abilities/bosses/boss_legion_commander_bunker.lua:93,104,115`.
  - `npc_playerhelp` (line 8330): the solo-player helper, spawned in `aohgamemode.lua:527` at GAME_IN_PROGRESS.
- Both blocks attach wearables `ItemDef` 7416–7421 under `Creature/AttachWearables` (`Wearable1..6`).
  These are presumably the Wurmblood set. These ids were not checked: `tools/vanilla/items.txt` is the
  shop item file, not items_game, so a vanilla_snapshot of items_game would be needed.
- Neither unit is in `Precache()` (`addon_game_mode.lua:10`, `models`/`units` lists are empty) nor in
  `aoh2_config.txt`. The engine loads them at first spawn. The model path itself is still
  referenced by the vanilla KV snapshot (tools/vanilla), so the likelier culprit is the wearable
  item defs that no longer resolve; to confirm, spawn `npc_dragon_knight` with AttachWearables
  removed.
- Fix: update ItemDefs to the current DK default set (or drop AttachWearables), and add both units
  to `Precache()` `units` once they resolve.

## 4c. Localization — P3

Checked all three `resource/addon_{english,russian,schinese}.txt`. None of them has:
- `buy`, `sell`, `tier1`..`tier5` — used as `#buy`/`#sell`/`#tier1..5` in
  `content/.../panorama/layout/custom_game/skill_bar.xml:44,45,51,60,69,78,87`. (`cost1..5` exist.)
- any `*_npedesc2` key: `#npc_dota_hero_*_npedesc2` is requested by the engine's hero picker for
  every hero in herolist.txt and is not referenced by our code.
- any `*_SummaryDescription` key, including `DOTA_Tooltip_Ability_item_tombstone_SummaryDescription`
  (only `DOTA_Tooltip_Ability_item_tombstone` exists). This is the new tooltip field the engine asks
  for on every custom ability/item, also not referenced by our code.

Fix: add `buy`/`sell`/`tier1..5` in three languages. `npedesc2`/`SummaryDescription` are
engine-requested, so either add them (generated by tools/kvgen.py) or accept the console noise.

## 4d. Other load errors

- **DOTANeutralItems**: the engine looks for `scripts/npc/npc_neutral_items_custom.txt`. We ship
  `scripts/npc/neutral_items.txt` (old name). Rename/port it to the current schema. P2.
- **response_rules_custom.txt**: no `scripts/talker/` directory. This is harmless (we have no custom
  voice-response rules). Silence it with an empty `scripts/talker/response_rules_custom.txt`. P3.
- **Lone Druid bear Missing Attachment attach_attack1 on donkey_wings.vmdl**: `npc_courier_replacement`
  (npc_units_custom.txt:7218) has `BaseClass npc_dota_lone_druid_bear`, model
  `models/props_gameplay/donkey_wings.vmdl`, a ranged attack and the witchdoctor projectile. The
  donkey model has no `attach_attack1`. Fix: make the courier melee/no-attack, or pick a model
  with that attachment. P2.
- **"Cannot open dota_addons/attackcopy to calculate addon CRC"**: the addon folders are reached
  via `scripts/agents/link_addon.sh` (junction on Windows, symlink on macOS), and the CRC code does
  not follow them. This is cosmetic for local tools runs. For Workshop upload, upload from a real
  folder. It may also explain the §4a custom particles; to test, copy instead of link once. P1
  (together with the particle recompile).
- **Missing Panorama images**:
  - `bg_mainshop_psd`: `content/.../panorama/styles/custom_game_info.css:130` points to vanilla
    `s2r://panorama/images/hud/reborn/bg_mainshop_psd.vtex`, which is gone from the current build.
    Our own `images/custom_game/bg_mainshop_psd.png` (+ compiled `_png.vtex_c`) exists and is used
    by `skill_bar.css:117` / `hud.css:158`. Point line 130 at it.
  - `npc_boss_death_prophet_png`, `npc_dota_goodguys_fort_png`: not referenced in our sources. They
    look like the engine/HUD resolving `file://{images}/heroes/<unitname>.png` for a selected or
    killed custom unit (portrait / kill-feed / `end_screen.js` hero icon). Add images or ignore. P3.

## 4e. Debug output in production — P3

| output | source |
|---|---|
| `why aren't you dead` | `vscripts/abilities/other/generic.lua:658` (`modifier_dummy:OnDestroy`) |
| `[VScript] N table: 0x…` ×35 | `vscripts/aohgamemode.lua:287-289` — `print(k, v)` over every round in `_ReadGameConfiguration` |
| `Debug` | `content/.../panorama/scripts/custom_game/damage.js:88` (`$.Msg("Debug")`); `difficulty.js` (obfuscated) has a `'Debug'` string too |
| `hello initDifficulty` | `content/.../panorama/scripts/custom_game/difficulty.js` (obfuscated, `$.Msg('hello initDifficulty')` in `InitDifficulty`) — falls under 0021 (restore clean JS) |

Side note: `generic.lua:650-651` sets `[MODIFIER_STATE_NO_UNIT_COLLISION]` twice in one table.

## 6. Фидбек брата

Gameplay feedback from the same playtest (Windows). New issues are queued as 0046–0052 in
tasks/backlog.md, and their code findings are in those lines. The items below were already covered
by 0040–0045, or turned out not to be:

| feedback | covered by | note |
|---|---|---|
| red crosses after dash | 0040 | `particles/custom/dash`, `blink_cooldown_screen` reported missing (§4a; `hero_attribute_fix.lua:389,195`) |
| `modifier_skill_dashcooldown` shown raw in perks | **not 0044** | the key exists (addon_english.txt:104-113, addon_russian.txt:103-112). skill_bar.js calls `$.Localize(TIER_4_SKILLS[i])` without `#`, and current Panorama returns that verbatim. Queued under "Found by agents" |
| `npc_dota_hero_ursa` in the stats table | **not 0044** | damage.js:23 `$.Localize(Players.GetPlayerSelectedHero(index))` has no `#`. Same fix as above |
| `npc_boss_death_prophet` above the hp bar | **not 0044** | the key exists (addon_english.txt:757, addon_russian.txt:677). This is the engine HUD, not our JS, so check whether the addon localization loads on the Windows client at all |
| courier shown as Spirit Bear | 0043 | `npc_courier_replacement` BaseClass `npc_dota_lone_druid_bear` (npc_units_custom.txt:7218) |
| neutral pick icon blinking, no madstones | 0043 → 0048 | old-schema `neutral_items.txt` |
| "error" unit at spawn | 0042 → 0050 | most likely `npc_playerhelp` (Hired Goon) whose DK model/wearables fail and render as the ERROR model |
| turquoise cone / light square at the fountain | 0040, 0041 → 0051 | missing `blueglow1.vmat_c`, `particle_ring_blurry_generic_projected.vmat_c` |
