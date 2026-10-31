# Spawn groups and PrecacheUnitByNameAsync

Context: in a playtest the Radiant ancient vanished between rounds with no `entity_killed`.
`AOHSpawner:End()` unloaded the handle that `PrecacheUnitByNameAsync` gave its callback, and that
was the suspect.

## Outcome (playtests 3–9, 2026-10-31)
The hypothesis is **refuted** by the console log: with the unload disabled the ancient still hit
0 HP. The cause was `ancient_increase_stats` reading its legacy `AbilitySpecial` values as 0, so the
per-round rescale set max HP to 0 (docs/reports/playtest-3..9-log.md). Spawn groups played no part.

The unload stays removed anyway: the callback argument is a precache id, not a `SpawnGroupHandle`
(below), so `UnloadSpawnGroupByHandle(id)` was never a valid call. `AOHSpawner` no longer keeps the
id and has no `End()`.

## Documented (tools/vanilla/dota-data/files/vscripts/api.json, ModDota dota-data)
- `PrecacheUnitByNameAsync(unitName, callback: fun(precacheId: int), playerId?) -> nil`, server
  only: "Asynchronously precaches a DOTA unit by its dota_npc_units.txt name, provides a callback
  when it's finished." The callback argument is typed `precacheId: int`, not `SpawnGroupHandle`.
  `PrecacheItemByNameAsync` uses the same signature.
- `UnloadSpawnGroupByHandle(handle: SpawnGroupHandle)`: "Unload a spawn group by handle." Nothing
  says what happens to the group's entities or whether death events fire.
- `CBaseEntity:GetSpawnGroupHandle()` and `GetActiveSpawnGroupHandle()` exist, so you can compare
  a handle with the map's own group.
- `DOTA_SpawnMapAtPosition` callbacks receive a real `spawnGroupHandle: SpawnGroupHandle`.

## Rule
Unload only a handle your own call created as a spawn group (`DOTA_SpawnMapAtPosition`). Never pass
a precache id to `UnloadSpawnGroupByHandle`. Our `Precache`/`End` pair was copied from Valve's
Holdout example, which treated the precache id as a handle.
