#!/usr/bin/env python3
"""Names our KV and Lua reference that the current vanilla build no longer defines. Zero tokens.

    tools/vanilla_diff.py [--entries a,b] [--lua] [--update-baseline]

Needs tools/vanilla/ (python3 tools/vanilla_snapshot.py). Reports:
  FAIL  BaseClass of one of our entries that vanilla lacks (the entry is broken)
  FAIL  a vanilla ability/item we override that no longer exists (dead override)
  WARN  a special_bonus_* we override as a stand-alone block while vanilla inlines it in the
        owning ability (the override is probably a no-op — verify in tools)
  INFO  vanilla heroes missing from herolist.txt
With --lua also greps vscripts for string literals naming vanilla abilities/modifiers/items
that are gone. Baseline ratchet like kvcheck (tools/vanilla_diff.baseline).
"""
import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kvlib as kv  # noqa: E402

OUR_BASES = {"ability_datadriven", "ability_lua", "item_datadriven", "item_lua"}


def vanilla():
    if not os.path.isdir(kv.VANILLA):
        print("no tools/vanilla snapshot — run: python3 tools/vanilla_snapshot.py")
        sys.exit(5)
    ab, items, heroes, talents_inline = set(), set(), set(), set()
    root, _ = kv.parse_file(os.path.join(kv.VANILLA, "npc_abilities.txt"))
    ab.update(e.key for e in kv.entries(root))
    root, _ = kv.parse_file(os.path.join(kv.VANILLA, "items.txt"))
    items.update(e.key for e in kv.entries(root))
    for f in glob.glob(os.path.join(kv.VANILLA, "heroes", "*.txt")):
        root, _ = kv.parse_file(f)
        for h in kv.entries(root):
            heroes.add(h.key)
            defs = h.get("AbilityDefinitions")
            if defs:
                for a in defs.children:
                    ab.add(a.key)
                    text = kv.read_text(f)
                    for m in re.finditer(r'"(special_bonus_[a-z0-9_]+)"\s+"[+\-x]', text):
                        talents_inline.add(m.group(1))
    ids = set()
    p = os.path.join(kv.VANILLA, "npc_ability_ids.txt")
    if os.path.exists(p):
        ids.update(re.findall(r'"([a-z0-9_]+)"\s+"\d+"', kv.read_text(p)))
    build = ""
    try:
        with open(os.path.join(kv.VANILLA, "BUILD"), encoding="utf-8") as f:
            build = f.readline().strip()
    except OSError:
        pass
    return ab, items, heroes, talents_inline, ids, build


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries")
    ap.add_argument("--lua", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    a = ap.parse_args()
    only = set(a.entries.split(",")) if a.entries else None
    ab, items, heroes, inline, ids, build = vanilla()
    known_names = ab | items | ids
    fails, warns, infos = [], [], []

    def ours(name):
        root, _ = kv.parse_file(os.path.join(kv.NPC_DIR, name))
        return [e for e in kv.entries(root) if not only or e.key in only]

    for e in ours("npc_abilities_custom.txt") + ours("npc_items_custom.txt"):
        b = e.get("BaseClass")
        if b and b.value not in OUR_BASES and b.value not in known_names:
            fails.append(f"{e.key}: BaseClass {b.value} no longer exists in vanilla")
    for e in ours("npc_abilities_override.txt"):
        if e.key in known_names:
            if e.key.startswith("special_bonus_") and e.key in inline and e.key not in ab:
                warns.append(f"{e.key}: talent is inlined in the owning ability's AbilityValues in vanilla; a stand-alone override is likely a no-op")
            continue
        if e.key.startswith("special_bonus_") and e.key in inline:
            warns.append(f"{e.key}: talent exists only inline in vanilla; stand-alone override is likely a no-op")
        else:
            fails.append(f"{e.key}: overridden vanilla ability does not exist any more")
    for e in ours("npc_items_custom.txt"):
        if not e.get("BaseClass") and e.key not in items and not e.key.startswith("item_recipe_"):
            warns.append(f"{e.key}: overrides a vanilla item that items.txt no longer has (engine-defined? verify)")
    hl_root, _ = kv.parse_file(os.path.join(kv.NPC_DIR, "herolist.txt"))
    listed = {e.key for top in hl_root.children for e in top.children}
    for h in sorted(heroes):
        if h.startswith("npc_dota_hero_") and h not in listed and h not in ("npc_dota_hero_base", "npc_dota_hero_target_dummy"):
            infos.append(f"herolist.txt lacks {h}")
    if a.lua:
        rx = re.compile(r'"((?:item_|modifier_|special_bonus_)?[a-z_]+_[a-z0-9_]+)"')
        vanilla_like = re.compile(r"^(item_[a-z0-9_]+|[a-z_]+_(?:custom_)?[a-z0-9_]+)$")
        for f in glob.glob(os.path.join(kv.VSCRIPTS, "**", "*.lua"), recursive=True):
            text = kv.read_text(f)
            for m in rx.finditer(text):
                n = m.group(1)
                if n.startswith("modifier_") or "custom" in n or "boss" in n or "aoh" in n or not vanilla_like.match(n):
                    continue
                if n.startswith(("item_",)) and n not in items and n in ids:
                    continue
                if n in ids and n not in known_names - ids:
                    pass
                if (n.startswith("item_") and n not in items) or (not n.startswith("item_") and n.split("_")[0] in {x.split("_")[0] for x in ab} and n not in ab and n not in ids):
                    warns.append(f"{os.path.relpath(f, kv.ROOT)}: literal {n!r} is not a vanilla name in this build")
    baseline = os.path.join(kv.ROOT, "tools", "vanilla_diff.baseline")
    if a.update_baseline:
        with open(baseline, "w", encoding="utf-8") as f:
            f.write(f"# vanilla_diff baseline ({build}). Remove a line when a task fixes it.\n")
            for l in sorted(set(fails)):
                f.write(l + "\n")
        print(f"baseline written: {len(set(fails))}")
        return 0
    known = set()
    if os.path.exists(baseline):
        with open(baseline, encoding="utf-8") as f:
            known = {l.strip() for l in f if l.strip() and not l.startswith("#")}
    new = [l for l in fails if l not in known]
    for l in new:
        print("FAIL " + l)
    for l in fails:
        if l in known:
            print("KNOWN " + l)
    for l in warns[:60]:
        print("WARN " + l)
    if len(warns) > 60:
        print(f"WARN ... {len(warns) - 60} more")
    for l in infos:
        print("INFO " + l)
    print(f"vanilla_diff ({build}): {len(new)} fail, {len(fails) - len(new)} known, {len(warns)} warn")
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
