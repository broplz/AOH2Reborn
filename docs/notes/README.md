# Notes for the next agent

Short, factual notes about the Dota 2 VScript/KV/Panorama API as it behaves in 2026 — things
learned the hard way that the next session must not rediscover. One file per topic
(`dota-api.md`, `kv-format.md`, `panorama.md`, `workshop-tools.md`), bullet per fact, with the
source (patch, Valve issue, test in tests/) when there is one. Any pipeline role may append.

- `apicheck.md` — engine call arity check, dota-data source and version, API signature changes.
- `spawn-groups.md` — what PrecacheUnitByNameAsync hands its callback, when UnloadSpawnGroupByHandle is safe.
