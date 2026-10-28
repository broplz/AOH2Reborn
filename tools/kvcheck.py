#!/usr/bin/env python3
"""Validate the addon's KeyValues. Zero tokens, seconds.

    tools/kvcheck.py                      all scripts/npc/*.txt → FAIL/WARN lines, exit 1 on FAIL
    tools/kvcheck.py --entries a,b        only these entries (by name) across all files
    tools/kvcheck.py --show <entry>       print one entry's block with line numbers (agents use this
                                          instead of reading a 20k-line file)
    tools/kvcheck.py --strict             AbilitySpecial / LinkedSpecialBonus / backslash paths are FAIL, not WARN
    tools/kvcheck.py --update-baseline    record today's FAIL lines in tools/kvcheck.baseline (owner only)

Ratchet: FAIL lines listed in tools/kvcheck.baseline (legacy defects the phase-1 tasks remove one
by one) are reported as KNOWN and do not fail the run; anything new does. A task that fixes a
known defect also removes its line from the baseline.

Checks: syntax (balanced braces, key without value), duplicated top-level entries, duplicated
keys inside a block, ScriptFile that does not exist or uses backslashes, AbilitySpecial and
LinkedSpecialBonus (legacy format), ability_datadriven (WARN; ADR-0002 phases them out),
ability_lua without ScriptFile.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kvlib as kv  # noqa: E402

LEGACY_KEYS = {"abilityspecial": "AbilitySpecial (legacy; use AbilityValues)",
               "linkedspecialbonus": "LinkedSpecialBonus (legacy; inline the talent in AbilityValues)"}


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
    seen = {}
    for e in kv.entries(root):
        if only and e.key not in only:
            continue
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
    return fails, warns, seen


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
