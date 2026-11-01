#!/usr/bin/env python3
"""Validate the addon's KeyValues. Zero tokens, seconds.

    tools/kvcheck.py                      all scripts/npc/*.txt → FAIL/WARN lines, exit 1 on FAIL
    tools/kvcheck.py --entries a,b        only these entries (by name) across all files
    tools/kvcheck.py --show <entry>       print one entry's block with line numbers (agents use this
                                          instead of reading a 20k-line file)
    tools/kvcheck.py --strict             LinkedSpecialBonus / backslash paths are FAIL, not WARN
    tools/kvcheck.py --update-baseline    record today's FAIL lines in tools/kvcheck.baseline (owner only)

Ratchet: FAIL lines listed in tools/kvcheck.baseline (legacy defects the phase-1 tasks remove one
by one) are reported as KNOWN and do not fail the run; anything new does. A task that fixes a
known defect also removes its line from the baseline.

Checks: syntax (balanced braces, key without value), duplicated top-level entries, duplicated
keys inside a block, ScriptFile that does not exist or uses backslashes, LinkedSpecialBonus
(legacy format), AbilitySpecial blocks above the per-file ratchet ABILITY_SPECIAL_BASELINE (FAIL;
the engine reads them as 0), ability_datadriven (WARN; ADR-0002 phases them out),
ability_lua without ScriptFile. Wrappers that RunScript a generic.lua function: ability_index
must resolve (literal or %var in AbilityValues; AbilitySpecial reads as 0) to a spell in that
function's table, and every unit with the wrapper must have that spell.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kvlib as kv  # noqa: E402

LEGACY_KEYS = {"linkedspecialbonus": "LinkedSpecialBonus (legacy; inline the talent in AbilityValues)"}
# AbilitySpecial reads as 0 in the current engine (0054). Ratchet: blocks allowed per file, every
# other file 0; a batch that migrates a file lowers its number here.
ABILITY_SPECIAL_BASELINE = {"npc_abilities_override.txt": 509}


def has_key_deep(node, key):
    k = key.lower()
    for c in node.children:
        if c.key.lower() == k:
            return c
        if c.value is None:
            r = has_key_deep(c, key)
            if r:
                return r
    return None


def check_file(path, only=None, strict=False):
    rel = os.path.relpath(path, kv.ROOT)
    fails, warns = [], []
    root, problems = kv.parse_file(path)
    for p in problems:
        fails.append(f"{rel}:{p}")
    seen, specials = {}, []
    for e in kv.entries(root):
        if only and e.key not in only:
            continue
        special = has_key_deep(e, "AbilitySpecial")
        if special:
            specials.append(f"{e.key}:{special.line}")
        if e.key in seen:
            fails.append(f"{rel}:{e.line}: duplicated entry {e.key} (first at line {seen[e.key]}; one copy is ignored by the engine)")
        seen.setdefault(e.key, e.line)
        for (where, key, first, dup) in kv.duplicate_keys(e, e.key):
            fails.append(f"{rel}:{dup}: duplicate key {key!r} in {where} (first at line {first})")
        base = e.get("BaseClass")
        sf = e.get("ScriptFile")
        if sf and sf.value:
            if "\\" in sf.value:
                (fails if strict else warns).append(f"{rel}:{sf.line}: ScriptFile with backslashes: {sf.value}")
            p = sf.value.replace("\\", "/")
            if not p.endswith(".lua"):
                p += ".lua"
            if not os.path.exists(os.path.join(kv.VSCRIPTS, p)):
                fails.append(f"{rel}:{sf.line}: ScriptFile not found: {sf.value}")
        if base and base.value in ("ability_lua", "item_lua") and not sf:
            fails.append(f"{rel}:{e.line}: {e.key} is {base.value} without ScriptFile")
        if base and base.value == "ability_datadriven":
            warns.append(f"{rel}:{e.line}: {e.key} is ability_datadriven (ADR-0002 phases these out)")
        for k, msg in LEGACY_KEYS.items():
            node = has_key_deep(e, k)
            if node:
                (fails if strict else warns).append(f"{rel}:{node.line}: {e.key}: {msg}")
    allowed = ABILITY_SPECIAL_BASELINE.get(os.path.basename(path), 0)
    if len(specials) > allowed:
        fails.append(f"{rel}: {len(specials)} AbilitySpecial blocks, ratchet allows {allowed} (reads as 0; "
                     f"use AbilityValues, tools/kv_values_migrate.py): {', '.join(specials[allowed:][:5])}")
    return fails, warns, seen


GENERIC_LUA = "abilities/other/generic.lua"


def generic_tables():
    """generic.lua → ({table: {index: spell}}, {function: table}) from its spells_* lists."""
    tables, funcs, current, idx, func = {}, {}, None, 0, None
    with open(os.path.join(kv.VSCRIPTS, GENERIC_LUA), encoding="utf-8") as f:
        for line in f:
            m = re.match(r"local (spells_\w+) = \{", line)
            if m:
                current, idx = m.group(1), 0
                tables[current] = {}
                continue
            if current:
                if line.startswith("}"):
                    current = None
                    continue
                s = re.search(r'(?:\[(\d+)\]\s*=\s*)?"([^"]+)"', line)
                if s:
                    idx = int(s.group(1)) if s.group(1) else idx
                    tables[current][idx] = s.group(2)
                    idx += 1
                continue
            m = re.match(r"function (\w+)\(keys\)", line)
            if m:
                func = m.group(1)
            m = re.search(r"FindAbilityByName\((spells_\w+)\[keys\.ability_index\]\)", line)
            if m and func:
                funcs[func] = m.group(1)
    return tables, funcs


def runscripts(node):
    for c in node.children:
        if c.value is None:
            if c.key.lower() == "runscript":
                yield c
            yield from runscripts(c)


def resolve_index(entry, raw):
    """(index, problem) for a RunScript ability_index value."""
    if raw.isdigit():
        return int(raw), None
    name = raw.lstrip("%")
    values = entry.get("AbilityValues")
    node = values.get(name) if values else None
    if node and node.value is not None:
        return int(float(node.value)), None
    if has_key_deep(entry.get("AbilitySpecial") or kv.Node("", 0), name):
        return None, f"ability_index {raw} is in AbilitySpecial, which reads as 0"
    return None, f"ability_index {raw} not found in AbilityValues"


def unit_abilities(path):
    root, _ = kv.parse_file(path)
    return {u.key: {c.value for c in u.children if re.fullmatch(r"Ability\d+", c.key) and c.value}
            for u in kv.entries(root)}


def check_generic_wrappers(only=None):
    tables, funcs = generic_tables()
    units = {}
    for name in ("npc_units_custom.txt", "npc_heroes_custom.txt"):
        units.update(unit_abilities(os.path.join(kv.NPC_DIR, name)))
    path = os.path.join(kv.NPC_DIR, "npc_abilities_custom.txt")
    rel = os.path.relpath(path, kv.ROOT)
    root, _ = kv.parse_file(path)
    fails = []
    for e in kv.entries(root):
        if only and e.key not in only:
            continue
        for rs in runscripts(e):
            sf, fn, ai = rs.get("ScriptFile"), rs.get("Function"), rs.get("ability_index")
            if not (sf and fn and ai and sf.value.replace("\\", "/") == GENERIC_LUA and fn.value in funcs):
                continue
            table = funcs[fn.value]
            index, problem = resolve_index(e, ai.value)
            spell = tables[table].get(index) if problem is None else None
            if problem is None and spell is None:
                problem = f"ability_index {index} is not in {table}"
            if problem:
                fails.append(f"{rel}:{ai.line}: {e.key}: {problem} ({fn.value} gets nil from FindAbilityByName)")
                continue
            for unit, abilities in sorted(units.items()):
                if e.key in abilities and spell not in abilities:
                    fails.append(f"{rel}:{ai.line}: {e.key} on {unit} casts {spell} ({table}[{index}]), which {unit} lacks")
    return fails


def show(entry):
    for name in kv.KV_FILES:
        path = os.path.join(kv.NPC_DIR, name)
        if not os.path.exists(path):
            continue
        root, _ = kv.parse_file(path)
        for e in kv.entries(root):
            if e.key == entry:
                lines = kv.read_text(path).splitlines()
                end = e.line
                depth = 0
                for i in range(e.line - 1, len(lines)):
                    depth += lines[i].count("{") - lines[i].count("}")
                    if depth == 0 and i > e.line - 1:
                        end = i + 1
                        break
                print(f"# {os.path.relpath(path, kv.ROOT)}:{e.line}-{end}")
                for i in range(e.line - 1, end):
                    print(f"{i + 1}\t{lines[i]}")
                return 0
    print(f"entry {entry!r} not found in {', '.join(kv.KV_FILES)}")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries", help="comma-separated entry names to check")
    ap.add_argument("--show", help="print one entry and exit")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--quiet-warn", action="store_true", help="do not print WARN lines (counts only)")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--no-baseline", action="store_true", help="ignore tools/kvcheck.baseline")
    a = ap.parse_args()
    if a.show:
        return show(a.show)
    only = set(a.entries.split(",")) if a.entries else None
    total_f, total_w, n_entries = [], [], 0
    for name in kv.KV_FILES:
        path = os.path.join(kv.NPC_DIR, name)
        if not os.path.exists(path):
            continue
        f, w, seen = check_file(path, only, a.strict)
        total_f += f; total_w += w; n_entries += len(seen)
    total_f += check_generic_wrappers(only)
    baseline_path = os.path.join(kv.ROOT, "tools", "kvcheck.baseline")
    norm = lambda l: __import__("re").sub(r":\d+:", ":", __import__("re").sub(r"\(first at line \d+\)|line \d+", "", l)).strip()  # noqa: E731
    if a.update_baseline:
        with open(baseline_path, "w", encoding="utf-8") as f:
            f.write("# kvcheck baseline: known legacy FAILs (normalized, no line numbers). Remove a line when a task fixes it.\n")
            for l in sorted({norm(x) for x in total_f}):
                f.write(l + "\n")
        print(f"baseline written: {len(set(norm(x) for x in total_f))} known defects")
        return 0
    known = set()
    if not a.no_baseline and os.path.exists(baseline_path):
        with open(baseline_path, encoding="utf-8") as f:
            known = {l.strip() for l in f if l.strip() and not l.startswith("#")}
    new_f = [l for l in total_f if norm(l) not in known]
    old_f = [l for l in total_f if norm(l) in known]
    for l in new_f:
        print("FAIL " + l)
    for l in old_f:
        print("KNOWN " + l)
    total_f = new_f
    if not a.quiet_warn:
        for l in total_w[:200]:
            print("WARN " + l)
        if len(total_w) > 200:
            print(f"WARN ... {len(total_w) - 200} more warnings")
    print(f"kvcheck: {n_entries} entries, {len(total_f)} fail, {len(old_f)} known (baseline), {len(total_w)} warn")
    return 1 if total_f else 0


if __name__ == "__main__":
    sys.exit(main())
