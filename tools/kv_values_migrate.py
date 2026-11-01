#!/usr/bin/env python3
"""Rewrite legacy AbilitySpecial blocks as AbilityValues (the engine reads AbilitySpecial as 0).

    tools/kv_values_migrate.py --entries a,b        dry run: print the new blocks
    tools/kv_values_migrate.py --generic-wrappers   every entry that RunScripts a generic.lua function
    tools/kv_values_migrate.py --all                every entry with AbilitySpecial
    ... --file npc_items_custom.txt                 another file in scripts/npc (default npc_abilities_custom.txt)
    ... --stats                                     counts per conflict kind instead of the blocks
    ... --write                                     rewrite the file in place

"01" { "var_type" "FIELD_FLOAT" "radius" "190" } becomes "radius" "190"; a sub-block with more
keys (RequiresScepter, CalculateSpellDamageTooltip, ...) becomes "radius" { "value" "190" ... }.
LinkedSpecialBonus becomes the current vanilla form, the talent inlined in the base value:
"radius" { "value" "190" "special_bonus_x" "+N" }, N from the talent's own value (our files, then
vanilla) or, for a vanilla talent with no block, from the vanilla ability that inlines it. A ""
value means "the top-level key": with a talent it becomes "AbilityCastRange" { "value" "<top-level
or vanilla BaseClass value>" "special_bonus_x" "+N" }, without one it is dropped. An AbilitySpecial
with no values is removed, not written as an empty AbilityValues. An entry that already has
AbilityValues, repeats a name or nests deeper is skipped and reported. Migrated entries can still
carry notes for review: non-numeric values, %var with no definition in the entry, nested form,
unresolved talents, dropped "" values, empty or duplicated sub-block keys.
"""
import argparse
import glob
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
LINK, LINK_FIELD = "linkedspecialbonus", "linkedspecialbonusfield"
OUR_ABILITY_FILES = ("npc_abilities_custom.txt", "npc_abilities_override.txt")
VANILLA_ABILITY_FILES = ("npc_abilities.txt", "heroes/*.txt")
VALUE_BLOCKS = ("AbilityValues", "AbilitySpecial")


def blocks_by_name(paths):
    """Every named block (abilities sit at different depths in vanilla files); first one wins."""
    index = {}

    def walk(node):
        for c in node.children:
            if c.value is None:
                index.setdefault(c.key, c)
                walk(c)
    for path in paths:
        walk(kv.parse_file(path)[0])
    return index


def plain(node):
    """A key's value: "x" "1" → "1"; vanilla "x" { "value" "1" ... } → "1"."""
    if node is None:
        return None
    return node.value if node.value is not None else plain(node.get("value"))


def lookup(ability, key):
    """A key's value in an ability: top level, then its value blocks (key spelling, value)."""
    for holder in [ability] + [ability.get(b) for b in VALUE_BLOCKS if ability.get(b)]:
        node = holder.get(key) if holder is ability else kvcheck.has_key_deep(holder, key)
        if plain(node) is not None:
            return node.key, plain(node)
    return None, None


class Talents:
    """Talent values for LinkedSpecialBonus: our talent blocks, vanilla talent blocks, vanilla inlines."""

    def __init__(self):
        self.ours = blocks_by_name(os.path.join(kv.NPC_DIR, f) for f in OUR_ABILITY_FILES)
        vanilla = [p for g in VANILLA_ABILITY_FILES for p in sorted(glob.glob(os.path.join(kv.VANILLA, g)))]
        self.vanilla = blocks_by_name(vanilla)
        self.inlined = defaultdict(list)  # talent -> [(vanilla ability, key, "+N")]
        for name, ability in self.vanilla.items():
            values = ability.get("AbilityValues")
            for key in (values.children if values else []):
                for c in key.children:
                    if c.value is not None and c.key.startswith("special_bonus_"):
                        self.inlined[c.key].append((name, key.key, c.value))

    def bonus(self, entry, key, talent, field):
        """("+N", where) or (None, why)."""
        for source, index in (("ours", self.ours), ("vanilla talent", self.vanilla)):
            if talent in index:
                _, value = lookup(index[talent], field)
                if value is not None:
                    return signed(value), source
        base = entry.get("BaseClass").value if entry.get("BaseClass") else ""
        same_key = [r for r in self.inlined.get(talent, []) if r[1].lower() == key.lower()]
        for pick in ([r for r in same_key if r[0] == base], same_key):
            if len({r[2] for r in pick}) == 1:
                return signed(pick[0][2]), f"vanilla {pick[0][0]}.{pick[0][1]}"
        return None, f"no {talent}.{field} block and no vanilla '{key}' inlining it with one value"

    def top_level(self, entry, key):
        """("Key", value) for a "" sub-block: the entry's top-level key, else its vanilla BaseClass's."""
        node = entry.get(key)
        if node is not None and node.value:
            return node.key, node.value
        base = entry.get("BaseClass")
        ability = self.vanilla.get(base.value) if base else None
        return lookup(ability, key) if ability else (None, None)


def signed(value):
    return value if value[:1] in "+-" else "+" + value


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


def values_block(entry, special, indent, talents):
    """(new AbilityValues lines, [] to drop the block, or None; skip kind or None; [(note kind, detail)])."""
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
        link = {c.key.lower(): c.value for c in rest if c.key.lower() in (LINK, LINK_FIELD)}
        rest = [c for c in rest if c.key.lower() not in link]
        key, value, bonus = name.key, name.value, None
        if link:
            bonus, where = talents.bonus(entry, key, link[LINK], link.get(LINK_FIELD, "value"))
            notes.append(("talent inlined" if bonus else "talent not resolved, link dropped",
                          f"{key}: {link[LINK]} {bonus or ''} ({where})"))
            if bonus:
                rest.append(kv.Node(link[LINK], 0))
                rest[-1].value = bonus
        if value == "":
            key, value = talents.top_level(entry, key) if bonus else (None, None)
            if value is None:
                notes.append(("empty value dropped", f"{name.key} line {name.line}"))
                continue
        if key in names:
            return None, "name repeats", [("", f"{key!r} line {name.line}")]
        names.add(key)
        if not numeric(value):
            notes.append(("non-numeric value", f"{key}={value!r} line {name.line}"))
        if not rest:
            out.append(f'{indent}\t"{key}"\t\t"{value}"')
            continue
        notes.append(("nested form (extra keys)", f"{key}: {', '.join(c.key for c in rest)}"))
        out += [f'{indent}\t"{key}"', f"{indent}\t{{", f'{indent}\t\t"value"\t\t"{value}"']
        out += [f'{indent}\t\t"{c.key}"\t\t"{c.value}"' for c in rest]
        out.append(f"{indent}\t}}")
    if not names:
        return [], None, notes
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
    talents = Talents()
    for e in kv.entries(root):
        special = e.get("AbilitySpecial")
        if special is None or not (a.all or e.key in wanted):
            continue
        blocks.append(e.key)
        start = special.line - 1
        indent = lines[start][: len(lines[start]) - len(lines[start].lstrip())]
        new, skip, entry_notes = values_block(e, special, indent, talents)
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
