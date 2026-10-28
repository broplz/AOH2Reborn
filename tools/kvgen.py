"""kvgen: KV entries rendered from kv-src/*.yaml tables through tools/kvgen_templates/*.kv.

ADR-0002, decision 2 (data layer). This skeleton writes no game file: `--check` renders every
YAML entry and compares it with the entry that is already in scripts/npc.

Usage
  python3 tools/kvgen.py --check [family ...]   compare YAML+template with the committed KV
  python3 tools/kvgen.py --list <family>        print the entry names a family covers
  python3 tools/kvgen.py --extract <family>     (re)write the family's YAML from the current KV
  python3 tools/kvgen.py --self-test            run the checker against tools/fixtures/kvgen/

YAML subset (stdlib only, no PyYAML). Anything else is a parse error with file:line.
  - Blank lines and whole-line comments (`# ...`) are ignored, except header lines
    `# excluded: <name> — <reason>`, which list family members left out of the table on purpose.
  - Top level, column 0: `family: <scalar>`, `template: <scalar>` (path from the repo root),
    then `entries:` with no value.
  - Under `entries:`: a list of flat mappings of scalars. An item starts with `- key: value`;
    its other keys follow on their own lines, indented to the column of the first key.
  - Scalars: plain (no leading quote or YAML indicator, no `: ` and no ` #` inside),
    'single-quoted' (`''` is a quote), or "double-quoted" (no `"` and no backslash inside).
    Empty values, nested collections, anchors, flow style and multi-line scalars are not allowed.

Template = KV text with `"{field}"` placeholders (always inside quotes). A line holding only
`[?field]` opens an optional block, `[/field]` closes it; the block is rendered only when the
entry has `field`. Every field of an entry must be used by the template, and every placeholder
outside a skipped block must have a value.

Equality in --check: the same ordered (key, value | child block) pairs; keys compared
case-sensitively, values exactly after trimming whitespace; comments and layout are ignored.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kvlib  # noqa: E402

FIXTURES = os.path.join(kvlib.ROOT, "tools", "fixtures", "kvgen")


def is_generic_wrapper(entry):
    """Boss telegraph wrappers: `*_wrapper` whose OnSpellStart/RunScript/Function is generic_*."""
    node = entry
    for key in ("OnSpellStart", "RunScript", "Function"):
        node = node.get(key) if node else None
    return entry.key.endswith("_wrapper") and bool(node and node.value and node.value.startswith("generic_"))


FAMILIES = {
    "boss_wrapper": {
        "yaml": "kv-src/boss_wrappers.yaml",
        "template": "tools/kvgen_templates/boss_wrapper.kv",
        "kv": os.path.join(kvlib.NPC_DIR, "npc_abilities_custom.txt"),
        "member": is_generic_wrapper,
    },
}


class KvgenError(Exception):
    pass


# ---------------------------------------------------------------- YAML subset

TOP_KEYS = ("family", "template")
EXCLUDED_RE = re.compile(r"#\s*excluded:\s*(\S+)\s+—\s+(.+)")
PAIR_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*):(?: (.*))?")
INDICATORS = "'\"[]{}&*!|>%@`#,?-"


def parse_scalar(text, where):
    if text.startswith('"'):
        body = text[1:-1]
        if len(text) < 2 or not text.endswith('"') or '"' in body or "\\" in body:
            raise KvgenError(f"{where}: bad double-quoted scalar {text!r}")
        return body
    if text.startswith("'"):
        body = text[1:-1]
        if len(text) < 2 or not text.endswith("'") or "'" in body.replace("''", ""):
            raise KvgenError(f"{where}: bad single-quoted scalar {text!r}")
        return body.replace("''", "'")
    if not text or text[0] in INDICATORS or ": " in text or " #" in text or text != text.strip():
        raise KvgenError(f"{where}: unsupported plain scalar {text!r} (quote it)")
    return text


def parse_yaml(path):
    """Returns {"family", "template", "entries": [dict], "excluded": {name: reason}}."""
    doc = {"entries": [], "excluded": {}}
    in_entries, item, item_col = False, None, None
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for no, raw in enumerate(lines, 1):
        where = f"{os.path.relpath(path, kvlib.ROOT)}:{no}"
        line = raw.rstrip()
        stripped = line.lstrip(" ")
        if not stripped:
            continue
        if stripped.startswith("#"):
            m = EXCLUDED_RE.fullmatch(stripped)
            if m:
                doc["excluded"][m[1]] = m[2]
            continue
        if "\t" in line:
            raise KvgenError(f"{where}: tabs are not allowed")
        col = len(line) - len(stripped)
        if col == 0 and not in_entries:
            m = PAIR_RE.fullmatch(stripped)
            if not m or m[1] not in TOP_KEYS + ("entries",) or m[1] in doc and m[1] != "entries":
                raise KvgenError(f"{where}: expected one of family:, template:, entries:")
            if m[1] == "entries":
                if m[2] is not None:
                    raise KvgenError(f"{where}: entries: takes no inline value")
                in_entries = True
                continue
            doc[m[1]] = parse_scalar(m[2] or "", where)
            continue
        if stripped.startswith("- ") and in_entries:
            item, item_col = {}, col + 2
            doc["entries"].append(item)
            stripped, col = stripped[2:].lstrip(" "), item_col
        m = PAIR_RE.fullmatch(stripped)
        if item is None or col != item_col or not m:
            raise KvgenError(f"{where}: expected `- key: value` or `key: value` at column {item_col}")
        if m[1] in item:
            raise KvgenError(f"{where}: duplicate key {m[1]!r}")
        item[m[1]] = parse_scalar(m[2] or "", where)
    for key in TOP_KEYS:
        if key not in doc:
            raise KvgenError(f"{os.path.relpath(path, kvlib.ROOT)}: missing top-level `{key}:`")
    for i, entry in enumerate(doc["entries"]):
        if "name" not in entry:
            raise KvgenError(f"{os.path.relpath(path, kvlib.ROOT)}: entry #{i + 1} has no name")
    return doc


def yaml_scalar(value):
    if '"' in value or "\\" in value:
        return "'" + value.replace("'", "''") + "'"
    return '"' + value + '"'


# ---------------------------------------------------------------- template

OPT_RE = re.compile(r"\[([?/])([A-Za-z_][A-Za-z0-9_]*)\]")
FIELD_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class Tok:
    """One template token: `{` / `}` or a string that may hold `{field}` placeholders."""

    def __init__(self, kind, text=""):
        self.kind, self.text = kind, text.strip()
        parts = FIELD_RE.split(self.text)
        self.fields = parts[1::2]
        self.regex = re.compile("".join(re.escape(p) if i % 2 == 0 else "(.*)" for i, p in enumerate(parts)))

    def bind(self, kv_tok, bound):
        if kv_tok[0] != self.kind:
            return None
        if self.kind != "S":
            return bound
        m = self.regex.fullmatch(kv_tok[1].strip())
        if not m:
            return None
        new = dict(bound)
        for field, value in zip(self.fields, m.groups()):
            if new.setdefault(field, value) != value:
                return None
        return new

    def render(self, values):
        return '"' + FIELD_RE.sub(lambda m: values[m[1]], self.text) + '"' if self.kind == "S" else self.kind


class Opt:
    def __init__(self, field, items):
        self.field, self.items = field, items


def load_template(rel):
    path = os.path.join(kvlib.ROOT, rel)
    stack = [(None, [])]
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for no, line in enumerate(lines, 1):
        m = OPT_RE.fullmatch(line.strip())
        if m and m[1] == "?":
            stack.append((m[2], []))
            continue
        if m:
            if stack[-1][0] != m[2]:
                raise KvgenError(f"{rel}:{no}: [/{m[2]}] does not close an open block")
            field, items = stack.pop()
            stack[-1][1].append(Opt(field, items))
            continue
        for tok, _ in kvlib.tokenize(line):
            if tok == "C":
                raise KvgenError(f"{rel}:{no}: [conditions] are not supported in templates")
            stack[-1][1].append(Tok("S", tok[2:]) if tok.startswith("S:") else Tok(tok))
    if len(stack) > 1:
        raise KvgenError(f"{rel}: unclosed [?{stack[-1][0]}]")
    return stack[0][1]


def template_fields(items):
    out = []
    for item in items:
        for field in template_fields(item.items) if isinstance(item, Opt) else item.fields:
            if field not in out:
                out.append(field)
    return out


def render_tokens(items, values, used):
    out = []
    for item in items:
        if isinstance(item, Opt):
            if item.field in values:
                out += render_tokens(item.items, values, used)
            continue
        missing = [f for f in item.fields if f not in values]
        if missing:
            raise KvgenError(f"{values.get('name', '?')}: no value for {', '.join(missing)}")
        used.update(item.fields)
        out.append(item.render(values))
    return out


def render(items, values):
    """Entry fields → kvlib.Node of the generated entry."""
    used = set()
    text = "\n".join(render_tokens(items, values, used))
    unused = sorted(set(values) - used)
    if unused:
        raise KvgenError(f"{values['name']}: fields not used by the template: {', '.join(unused)}")
    root, problems = kvlib.parse_text(text)
    if problems or len(root.children) != 1:
        raise KvgenError(f"{values['name']}: rendered KV does not parse: {problems}")
    return root.children[0]


def flatten(node):
    out = [("S", node.key)]
    if node.value is not None:
        return out + [("S", node.value)]
    for child in node:
        out += flatten(child)
    return out[:1] + [("{",)] + out[1:] + [("}",)]


def match(seq, toks, j, bound):
    """Backtracking match of template items against KV tokens; returns the field values or None."""
    if not seq:
        return bound if j == len(toks) else None
    head, rest = seq[0], seq[1:]
    if isinstance(head, Opt):
        found = match(head.items + rest, toks, j, bound)
        return found if found is not None else match(rest, toks, j, bound)
    new = head.bind(toks[j], bound) if j < len(toks) else None
    return None if new is None else match(rest, toks, j + 1, new)


# ---------------------------------------------------------------- check

def show(node):
    if node is None:
        return "<missing>"
    return node.value.strip() if node.value is not None else f"{node.key} {{...}}"


def compare(kv, gen, path, out):
    for i in range(max(len(kv.children), len(gen.children))):
        a = kv.children[i] if i < len(kv.children) else None
        b = gen.children[i] if i < len(gen.children) else None
        if a is None or b is None or a.key != b.key or (a.value is None) != (b.value is None):
            where = f"{path}/{(a or b).key}"
            out.append(f"KVGEN FAIL {where}: kv={a.key if a else '<missing>'} gen={b.key if b else '<missing>'}")
            return
        if a.value is None:
            compare(a, b, f"{path}/{a.key}", out)
        elif a.value.strip() != b.value.strip():
            out.append(f"KVGEN FAIL {path}/{a.key}: kv={show(a)} gen={show(b)}")


def kv_entries(kv_path):
    root, problems = kvlib.parse_file(kv_path)
    if problems:
        raise KvgenError(f"{kv_path}: {problems[0]}")
    return {e.key: e for e in kvlib.entries(root)}


def check_family(yaml_path, kv_path):
    """Returns (fail lines, number of entries checked)."""
    doc = parse_yaml(yaml_path)
    fam = FAMILIES.get(doc["family"])
    if not fam:
        raise KvgenError(f"{yaml_path}: unknown family {doc['family']!r}")
    items = load_template(doc["template"])
    kv = kv_entries(kv_path)
    fails, names = [], set()
    for values in doc["entries"]:
        name = values["name"]
        names.add(name)
        if name not in kv:
            fails.append(f"KVGEN FAIL {name}: in YAML but missing from KV")
            continue
        gen = render(items, values)
        compare(kv[name], gen, name, fails)
    for name, entry in kv.items():
        if fam["member"](entry) and name not in names and name not in doc["excluded"]:
            fails.append(f"KVGEN FAIL {name}: family member in KV but missing from YAML")
    return fails, len(doc["entries"])


def cmd_check(families):
    fails, total = [], 0
    for name in families or sorted(FAMILIES):
        fam = FAMILIES[name]
        f, n = check_family(os.path.join(kvlib.ROOT, fam["yaml"]), fam["kv"])
        fails += f
        total += n
    for line in fails:
        print(line)
    print(f"KVGEN RESULT: FAIL ({len(fails)} mismatches)" if fails else f"KVGEN RESULT: OK ({total} entries)")
    return 1 if fails else 0


def cmd_list(family):
    for values in parse_yaml(os.path.join(kvlib.ROOT, FAMILIES[family]["yaml"]))["entries"]:
        print(values["name"])
    return 0


def cmd_extract(family):
    fam = FAMILIES[family]
    yaml_path = os.path.join(kvlib.ROOT, fam["yaml"])
    reasons = parse_yaml(yaml_path)["excluded"] if os.path.exists(yaml_path) else {}
    items = load_template(fam["template"])
    fields = template_fields(items)
    excluded, rows = {}, []
    for name, entry in kv_entries(fam["kv"]).items():
        if not fam["member"](entry):
            continue
        found = match(items, flatten(entry), 0, {})
        if found is None:
            excluded[name] = reasons.get(name, "does not fit the template")
            continue
        rows.append([f"{k}: {yaml_scalar(found[k])}" for k in fields if k in found])
    out = [f"# Generated once by `python3 tools/kvgen.py --extract {family}`; edit values here, not in scripts/npc.",
           "# Subset of YAML read by tools/kvgen.py (see its docstring)."]
    out += [f"# excluded: {name} — {reason}" for name, reason in excluded.items()]
    out += ["", f"family: {family}", f"template: {fam['template']}", "entries:"]
    for row in rows:
        out += ["  - " + row[0]] + ["    " + line for line in row[1:]]
    os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
    with open(yaml_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print(f"KVGEN EXTRACT: {len(rows)} entries, {len(excluded)} excluded → {fam['yaml']}")
    return 0


SELF_TESTS = [
    # (yaml fixture, expected substrings of the fail lines; empty = must pass)
    ("ok.yaml", []),
    ("changed_value.yaml", ["KVGEN FAIL fixture_target_wrapper/AbilityCooldown: kv=12 gen=99"]),
    ("missing_in_kv.yaml", ["KVGEN FAIL fixture_ghost_wrapper: in YAML but missing from KV"]),
    ("missing_in_yaml.yaml", ["KVGEN FAIL fixture_aoe_wrapper: family member in KV but missing from YAML"]),
]
SELF_TEST_ERRORS = [("bad_syntax.yaml", "bad_syntax.yaml:8:")]


def cmd_self_test():
    kv_path = os.path.join(FIXTURES, "abilities.kv")
    problems = []
    for name, expected in SELF_TESTS:
        fails, _ = check_family(os.path.join(FIXTURES, name), kv_path)
        if not expected and fails:
            problems.append(f"{name}: expected OK, got {fails}")
        problems += [f"{name}: expected {e!r}, got {fails}" for e in expected if not any(e in f for f in fails)]
    for name, expected in SELF_TEST_ERRORS:
        try:
            parse_yaml(os.path.join(FIXTURES, name))
            problems.append(f"{name}: expected a parse error")
        except KvgenError as e:
            if expected not in str(e):
                problems.append(f"{name}: expected {expected!r} in {e}")
    for line in problems:
        print("KVGEN SELFTEST FAIL " + line)
    print("KVGEN SELFTEST: FAIL" if problems else "KVGEN SELFTEST: OK")
    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", nargs="*", choices=sorted(FAMILIES), metavar="FAMILY")
    mode.add_argument("--list", choices=sorted(FAMILIES))
    mode.add_argument("--extract", choices=sorted(FAMILIES))
    mode.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    try:
        if args.self_test:
            return cmd_self_test()
        if args.list:
            return cmd_list(args.list)
        if args.extract:
            return cmd_extract(args.extract)
        return cmd_check(args.check)
    except KvgenError as e:
        print(f"KVGEN ERROR: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
