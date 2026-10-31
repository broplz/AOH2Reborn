# apicheck — engine call arity

`tools/apicheck.py` (step `apicheck` in `scripts/agents/check.sh lua|all`) counts the top-level
arguments of every `:Name(` call in `scripts/vscripts/**/*.lua` whose `Name` is a class member in
dota-data's `api.json`, and fails on a count no signature of that name allows.

- Source: npm `@moddota/dota-data` **0.47.2** (same version as `tools/gen_luacheckrc.py`),
  unpacked into `tools/vanilla/dota-data/` (git-ignored; without it the step prints a note and passes):
  `curl -sSL -o /tmp/dota-data-0.47.2.tgz https://registry.npmjs.org/@moddota/dota-data/-/dota-data-0.47.2.tgz`,
  then `mkdir -p tools/vanilla/dota-data` and
  `tar xzf /tmp/dota-data-0.47.2.tgz -C tools/vanilla/dota-data --strip-components=1`.
  Bump the version here and in gen_luacheckrc together after a Dota patch.
- Rules: signatures of one name are merged over all classes; trailing args typed `nil` are optional
  (a `nil` in the middle is only nullable). Skipped as undetermined: an arg `...`, or a call as the
  last arg unless the count is too high even without it. Strings and comments are ignored.
- False positives: our callbacks that share an engine name (`OnCreated()`, `GetModifier*()` called
  by our own code) go into `tools/apicheck.allow` — `Name` for everywhere, `Name path` (relative to
  `scripts/vscripts/`) for one file. Findings on a name our Lua also defines are tagged `ours?`.
- API changes it caught (fixed 2026-10-31): `GetIntellect(skipNoConsume)`,
  `GetAttacksPerSecond(ignoreTempAttackSpeed)`, `SpendCharge(delayRemove)` now take a required
  arg; `UseResources(mana, useHealth, gold, cooldown)` gained `useHealth` as the **2nd** arg — an old
  3-arg call `(mana, gold, cooldown)` becomes `(mana, false, gold, cooldown)`, not a 4th arg at the end.
