#!/usr/bin/env python3
"""Rewrite legacy AbilitySpecial blocks as AbilityValues (the engine reads AbilitySpecial as 0).

    tools/kv_values_migrate.py --entries a,b        dry run: print the new blocks
    tools/kv_values_migrate.py --generic-wrappers   every entry that RunScripts a generic.lua function
    tools/kv_values_migrate.py --all                every entry with AbilitySpecial
    ... --file npc_items_custom.txt                 another file in scripts/npc (default npc_abilities_custom.txt)
    ... --stats                                     counts per conflict kind instead of the blocks
    ... --write                                     rewrite the file in place

"01" { "var_type" "FIELD_FLOAT" "radius" "190" } becomes "radius" "190"; a sub-block with more
keys (LinkedSpecialBonus, RequiresScepter, ...) becomes "radius" { "value" "190" ... }. An entry
that already has AbilityValues, repeats a name or nests deeper is skipped and reported. Migrated
entries can still carry notes for review: non-numeric values, %var with no definition in the
entry, nested form, empty or duplicated sub-block keys.
"""
import argparse
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kvlib as kv  # noqa: E402
import kvcheck  # noqa: E402

NUMBER = re.compile(r"[-+]?(\d+\.?\d*|\.\d+)f?")
VAR_REF = re.compile(r"%(\w+)")
SKIP_KINDS = ("already has AbilityValues", "name repeats", "unexpected nesting")


def block_end(lines, start):
    """Index of the line closing the block whose key is at lines[start]."""
    depth, opened = 0, False
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        opened = opened or "{" in lines[i]
        if opened and depth == 0:
            return i
    raise ValueError(f"unclosed block at line {start + 1}")


def numeric(value):
    """A number or a per-level list of numbers ("1 2 3")."""
    return bool(value.split()) and all(NUMBER.fullmatch(t) for t in value.split())


def var_refs(node):
    for c in node.children:
        if c.value is None:
            yield from var_refs(c)
        else:
            yield from ((m, c.line) for m in VAR_REF.findall(c.value))


def values_block(entry, special, indent):
    """(new AbilityValues lines or None, skip kind or None, [(note kind, detail)])."""
    out, names, notes = [f'{indent}"AbilityValues"', f"{indent}{{"], set(), []
    if entry.get("AbilityValues"):
        return None, "already has AbilityValues", notes
    seen_subkeys = set()
    for sub in special.children:
        if sub.value is not None or any(c.value is None for c in sub.children):
            return None, "unexpected nesting", [("", f"line {sub.line}")]
        if sub.key in seen_subkeys:
            notes.append(("duplicate sub-block key", f"{sub.key!r} line {sub.line}"))
        seen_subkeys.add(sub.key)
        fields = [c for c in sub.children if c.key.lower() != "var_type"]
        if not fields:
            notes.append(("empty sub-block", f"line {sub.line}"))
            continue
        name, rest = fields[0], fields[1:]
        if name.key in names:
            return None, "name repeats", [("", f"{name.key!r} line {name.line}")]
        names.add(name.key)
        if not numeric(name.value):
            notes.append(("non-numeric value", f"{name.key}={name.value!r} line {name.line}"))
        if not rest:
            out.append(f'{indent}\t"{name.key}"\t\t"{name.value}"')
            continue
        notes.append(("nested form (extra keys)", f"{name.key}: {', '.join(c.key for c in rest)}"))
        out += [f'{indent}\t"{name.key}"', f"{indent}\t{{", f'{indent}\t\t"value"\t\t"{name.value}"']
        out += [f'{indent}\t\t"{c.key}"\t\t"{c.value}"' for c in rest]
        out.append(f"{indent}\t}}")
    out.append(f"{indent}}}")
    for ref, line in var_refs(entry):
        if ref not in names:
            notes.append(("%var not defined in entry", f"%{ref} line {line}"))
    return out, None, notes


def generic_wrappers(root):
    _, funcs = kvcheck.generic_tables()
    return {e.key for e in kv.entries(root) for rs in kvcheck.runscripts(e)
            if (rs.get("ScriptFile") and rs.get("Function")
                and rs.get("ScriptFile").value.replace("\\", "/") == kvcheck.GENERIC_LUA
                and rs.get("Function").value in funcs)}


def print_stats(name, edits, skipped, notes, blocks):
    print(f"== {name}: {len(blocks)} entries with AbilitySpecial, {len(edits)} migratable, {len(skipped)} skipped")
    by_kind = defaultdict(list)
    for entry, kind, detail in skipped:
        by_kind["SKIP " + kind].append(f"{entry} ({detail})" if detail else entry)
    for entry, kind, detail in notes:
        by_kind["NOTE " + kind].append(f"{entry}: {detail}")
    for kind in sorted(by_kind):
        items = by_kind[kind]
        entries = {i.split(" ", 1)[0].rstrip(":") for i in items}
        print(f"  {kind}: {len(items)} in {len(entries)} entries")
        for i in items[:8]:
            print(f"    {i}")
        if len(items) > 8:
            print(f"    ... {len(items) - 8} more")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries", help="comma-separated entry names")
    ap.add_argument("--generic-wrappers", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--file", default="npc_abilities_custom.txt")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    path = os.path.join(kv.NPC_DIR, a.file)
    root, _ = kv.parse_file(path)
    wanted = set(a.entries.split(",")) if a.entries else set()
    if a.generic_wrappers:
        wanted |= generic_wrappers(root)
    lines = kv.read_text(path).split("\n")
    edits, skipped, notes, blocks = [], [], [], []
    for e in kv.entries(root):
        special = e.get("AbilitySpecial")
        if special is None or not (a.all or e.key in wanted):
            continue
        blocks.append(e.key)
        start = special.line - 1
        indent = lines[start][: len(lines[start]) - len(lines[start].lstrip())]
        new, skip, entry_notes = values_block(e, special, indent)
        if skip:
            skipped.append((e.key, skip, entry_notes[0][1] if entry_notes else ""))
            continue
        notes += [(e.key, kind, detail) for kind, detail in entry_notes]
        edits.append((start, block_end(lines, start), new, e.key))
    if a.stats:
        print_stats(a.file, edits, skipped, notes, blocks)
        return 0
    for start, end, new, name in sorted(edits, reverse=True):
        lines[start:end + 1] = new
        if not a.write:
            print(f"# {name} (line {start + 1})\n" + "\n".join(new))
    for entry, kind, detail in skipped:
        print(f"SKIP {entry}: {kind} {detail}".rstrip())
    if a.write:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(lines))
    print(f"kv_values_migrate: {len(edits)} migrated{'' if a.write else ' (dry run)'}, {len(skipped)} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
