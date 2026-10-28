---
name: aoh-rules
description: AOH2 code conventions from ADR-0002 (target architecture) — Lua, KV and Panorama rules every change must follow, plus the Dota-2026 compatibility traps. Injected into developer, developer-hard, reviewer and teamlead; /aoh-rules for humans.
disable-model-invocation: true
---
# Code conventions (ADR-0002) — what aoh_lint.py and the reviewer check

## Lua
1. **No globals.** `local` for every variable and function; the only globals are the classes the
   engine needs (`modifier_x = class({})`, `ability_x = class({})`), one owner file each, plus
   `Activate`/`Precache`. Helpers are modules: `local fx = require("core/fx")`.
2. **One file = one ability/item + its modifiers.** File name = the KV name. `LinkLuaModifier`
   exactly once, in the owning file, with a `/`-separated path ending in `.lua`.
3. **Numbers live in KV.** `self:GetSpecialValueFor("x")` reads `AbilityValues`; talents are
   declared inline in KV (`"x" { "value" "10" "special_bonus_unique_foo" "+5" }`), never looked
   up with `FindAbilityByName("special_bonus_…")`. No `GetLevelSpecialValueFor(name, lvl-1)`.
4. **Enums, not magic numbers.** `DOTA_DAMAGE_FLAG_REFLECTION` with `bit.band`, never `== 16`;
   `DOTA_ITEM_NEUTRAL_ACTIVE_SLOT` / `DOTA_ITEM_NEUTRAL_PASSIVE_SLOT` (16/17 since 7.38), never
   `GetItemInSlot(16)`; `DOTA_UNIT_ORDER_*`, `DOTA_ABILITY_TYPE_*`. `DOTA_ATTRIBUTE_ALL`
   (Universal) is a fourth primary attribute — never "else = INT".
5. **Server/client.** `if not IsServer() then return end` at the top of server-only handlers.
   Client events: read `keys.PlayerID` (set by the engine), never a player id from the payload;
   check that the unit belongs to that player before acting on it.
6. **Handles die.** Anything used from a Timer or a later think: `if not unit or unit:IsNull()`
   then `IsAlive()` where it matters. Stop every timer/think in `OnDestroy`. No `AddNewModifier`
   on a dead unit.
7. **Particles and sounds.** Every `ParticleManager:CreateParticle` ends in
   `ReleaseParticleIndex` (one-shot) or `DestroyParticle` + `ReleaseParticleIndex` (attached);
   use `core/fx.lua` helpers. Every looping `EmitSoundOn` has a `StopSoundOn` on the same path.
8. **Events are global.** A modifier event handler (`OnTakeDamage`, `OnAttackLanded`, …) fires
   for every unit on the map: compare `keys.unit`/`keys.attacker`/`keys.target` with
   `self:GetParent()` on the first line, before any other API call.
9. **Thinks ≥ 0.1 s.** `StartIntervalThink` under 0.1 only with a comment saying why; no
   `FindUnitsInRadius` per tick unless the task asks; no `print` in hot paths (use `core/log.lua`).
10. **Boss abilities** go through the cast queue (`modifier_boss:Submit(job)`), not through
    `generic.lua` tickets or `Timers` polling; no new `ability_datadriven` entries.

## KeyValues
- New and migrated entries use `AbilityValues`, never `AbilitySpecial`/`LinkedSpecialBonus`.
- `ScriptFile` paths use `/` and omit nothing (`abilities/heroes/foo.lua`); the file must exist.
- No duplicate keys inside an entry and no duplicated top-level entries (kvcheck fails).
- A vanilla name used as `BaseClass`, overridden, or referenced in Lua must exist in the current
  build (`tools/vanilla_diff.py`); if Valve removed it, the task says what replaces it.
- Every player-visible ability/item gets `DOTA_Tooltip_ability_<name>` / `DOTA_Tooltip_ability_<name>_Description`
  in `resource/addon_english.txt` (ru/zh may lag; English never).
- Generated KV (`tools/kvgen.py` output, once it exists) is edited in its source table, never by hand.

## Panorama
- Sources only under `content/dota_addons/attackcopy/panorama/`; compiled `*_c` under `game/` are
  never edited (the Workshop Tools recompile them).
- No reaching into Valve's HUD tree (`FindChildTraverse` from the `Hud` root, hiding Valve
  element ids, hard-coded enum numbers); use `GameUI.SetDefaultUIEnabled` with named enums.
- Client → server payloads carry no player id; the server uses `keys.PlayerID`.

## Compatibility traps (Dota 7.34 → 7.41f, verified against build 6968)
- Talents are inlined in the owning ability's `AbilityValues`; stand-alone talent overrides are dead.
- Removed names: `aghanim_spear`, `skeleton_king_vampiric_aura`, `beastmaster_call_of_the_wild_boar`.
- Removed API: `DOTA_ITEM_NEUTRAL_SLOT`, `DOTA_DAMAGE_FLAG_BYPASSES_BLOCK` (→ `_ALL_BLOCK`/`_PHYSICAL_BLOCK`),
  `CDOTA_Item:IsNeutralDrop`, `GetModifierIsRatPack` (→ `IsPackRat`), `Entities.GetClassname` (Panorama → `GetClassNameAsCStr`).
- `DOTA_MAX_ABILITIES` is 40; vanilla heroes carry `generic_hidden` and innate slots in Ability4/5 —
  never loop `0..15` by index to find a hero's abilities; look them up by name.
- Shops on dedicated servers are broken since 7.41e (Valve #34007); shop tasks need a `[human]`
  check on a dedicated lobby, not only local.
