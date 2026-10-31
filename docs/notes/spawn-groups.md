# Spawn groups and PrecacheUnitByNameAsync

Context: in a playtest the Radiant ancient vanished between rounds with no `entity_killed`.
`AOHSpawner:End()` unloaded the handle that `PrecacheUnitByNameAsync` gave its callback.
As a playtest step the unload is now disabled, and both points log `sg=` (see `aohspawner.lua`).

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

## Not verified (no network in the agent session — check VDC, moddota.com/api, Valve Holdout)
- Our `Precache`/`End` pair is copied from Valve's Holdout example, which treats the precache id
  as a spawn group handle.
- When the unit is already loaded (by the map, by `Precache(context)` or by an earlier async
  call), the id may be an existing group's, perhaps the map's. It may also be the same id for
  several spawners.
- If the map's group is unloaded, its entities, the ancient included, are torn down without a
  kill and so without `entity_killed`.

## Rule until the playtest answers
Unload only a handle your own call created: not <= 0, not `GetActiveSpawnGroupHandle()`, not the
ancient's `GetSpawnGroupHandle()`, and not one another spawner still holds. Otherwise do not
unload. The precache cost is small next to losing the map.

## Playtest readout
Compare the `AOHSpawner precached ... sg=` values with each other and with the map's group. If
the ancient survives into round 2 with the unload disabled, the hypothesis holds.
