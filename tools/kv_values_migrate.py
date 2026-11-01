#!/usr/bin/env python3
"""Rewrite legacy AbilitySpecial blocks as AbilityValues (the engine reads AbilitySpecial as 0).

    tools/kv_values_migrate.py --entries a,b        dry run: print the new blocks
    tools/kv_values_migrate.py --generic-wrappers   every entry that RunScripts a generic.lua function
    ... --write                                     rewrite npc_abilities_custom.txt in place

"01" { "var_type" "FIELD_FLOAT" "radius" "190" } becomes "radius" "190"; a sub-block with more
keys (LinkedSpecialBonus, RequiresScepter, ...) becomes "radius" { "value" "190" ... }. An entry
that already has AbilityValues, repeats a name or nests deeper is skipped and reported.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kvlib as kv  # noqa: E402
import kvcheck  # noqa: E402

PATH = os.path.join(kv.NPC_DIR, "npc_abilities_custom.txt")


def block_end(lines, start):
    """Index of the line closing the block whose key is at lines[start]."""
    depth, opened = 0, False
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        opened = opened or "{" in lines[i]
        if opened and depth == 0:
            return i
    raise ValueError(f"unclosed block at line {start + 1}")


def values_block(special, indent):
    """New AbilityValues lines, or (None, reason)."""
    out, names = [f'{indent}"AbilityValues"', f"{indent}{{"], set()
    for sub in special.children:
        if sub.value is not None or any(c.value is None for c in sub.children):
            return None, f"unexpected nesting at line {sub.line}"
        fields = [c for c in sub.children if c.key.lower() != "var_type"]
        if not fields:
            continue
        name, rest = fields[0], fields[1:]
        if name.key in names:
            return None, f"name {name.key!r} repeats (line {name.line})"
        names.add(name.key)
        if not rest:
            out.append(f'{indent}\t"{name.key}"\t\t"{name.value}"')
            continue
        out += [f'{indent}\t"{name.key}"', f"{indent}\t{{", f'{indent}\t\t"value"\t\t"{name.value}"']
        out += [f'{indent}\t\t"{c.key}"\t\t"{c.value}"' for c in rest]
        out.append(f"{indent}\t}}")
    out.append(f"{indent}}}")
    return out, None


def generic_wrappers(root):
    _, funcs = kvcheck.generic_tables()
    return {e.key for e in kv.entries(root) for rs in kvcheck.runscripts(e)
            if (rs.get("ScriptFile") and rs.get("Function")
                and rs.get("ScriptFile").value.replace("\\", "/") == kvcheck.GENERIC_LUA
                and rs.get("Function").value in funcs)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries", help="comma-separated entry names")
    ap.add_argument("--generic-wrappers", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    root, _ = kv.parse_file(PATH)
    wanted = set(a.entries.split(",")) if a.entries else set()
    if a.generic_wrappers:
        wanted |= generic_wrappers(root)
    lines = kv.read_text(PATH).split("\n")
    edits, skipped = [], []
    for e in kv.entries(root):
        special = e.get("AbilitySpecial")
        if e.key not in wanted or special is None:
            continue
        if e.get("AbilityValues"):
            skipped.append(f"{e.key}: already has AbilityValues")
            continue
        start = special.line - 1
        indent = lines[start][: len(lines[start]) - len(lines[start].lstrip())]
        new, reason = values_block(special, indent)
        if reason:
            skipped.append(f"{e.key}: {reason}")
            continue
        edits.append((start, block_end(lines, start), new, e.key))
    for start, end, new, name in sorted(edits, reverse=True):
        lines[start:end + 1] = new
        if not a.write:
            print(f"# {name} (line {start + 1})\n" + "\n".join(new))
    for s in skipped:
        print("SKIP " + s)
    if a.write:
        with open(PATH, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(lines))
    print(f"kv_values_migrate: {len(edits)} migrated{'' if a.write else ' (dry run)'}, {len(skipped)} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
