"""Minimal Valve KeyValues (KV1) reader shared by the tools. No dependencies.

Handles `"key" "value"`, `"key" { ... }`, `//` comments, `[$CONDITION]` tags (ignored),
`#base` lines (recorded, not followed) and unquoted tokens. Keeps line numbers so every
finding can be reported as file:line. Byte-for-byte faithful enough for validation; it is not
a writer.
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ADDON = os.path.join(ROOT, "game", "dota_addons", "attackcopy")
NPC_DIR = os.path.join(ADDON, "scripts", "npc")
VSCRIPTS = os.path.join(ADDON, "scripts", "vscripts")
VANILLA = os.path.join(ROOT, "tools", "vanilla")

KV_FILES = ["npc_abilities_custom.txt", "npc_abilities_override.txt", "npc_items_custom.txt",
            "npc_items_override.txt", "npc_units_custom.txt", "npc_heroes_custom.txt", "herolist.txt", "neutral_items.txt"]


class Node:
    __slots__ = ("key", "line", "children", "value")

    def __init__(self, key, line):
        self.key, self.line, self.children, self.value = key, line, [], None

    def get(self, key):
        k = key.lower()
        for c in self.children:
            if c.key.lower() == k:
                return c
        return None

    def __iter__(self):
        return iter(self.children)


def read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def tokenize(text):
    i, n, line = 0, len(text), 1
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1; i += 1; continue
        if c in " \t\r":
            i += 1; continue
        if text.startswith("//", i):
            j = text.find("\n", i); i = n if j < 0 else j; continue
        if c in "{}":
            yield (c, line); i += 1; continue
        if c == '"':
            j, s = i + 1, []
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n:
                    s.append(text[j:j + 2]); j += 2; continue
                if text[j] == "\n":
                    line += 1
                s.append(text[j]); j += 1
            yield ("S:" + "".join(s), line); i = j + 1; continue
        if c == "[":
            j = text.find("]", i); yield ("C", line); i = (n if j < 0 else j + 1); continue
        j = i
        while j < n and text[j] not in " \t\r\n{}\"":
            j += 1
        yield ("S:" + text[i:j], line); i = j


def parse_text(text):
    """Returns (root, problems). root.children[0] is the file's top block (e.g. DOTAAbilities)."""
    problems, root, stack, pending = [], Node("<root>", 0), [], None
    stack.append(root)
    for t, l in tokenize(text):
        if t == "C":
            continue
        if t == "{":
            nd = Node(pending[0] if pending else "?", pending[1] if pending else l)
            if not pending:
                problems.append(f"{l}: {{ without a key")
            stack[-1].children.append(nd); stack.append(nd); pending = None
        elif t == "}":
            if pending:
                problems.append(f"{pending[1]}: key without a value {pending[0]!r}"); pending = None
            if len(stack) == 1:
                problems.append(f"{l}: extra }}")
            else:
                stack.pop()
        else:
            s = t[2:]
            if pending is None:
                pending = (s, l)
            else:
                nd = Node(pending[0], pending[1]); nd.value = s
                stack[-1].children.append(nd); pending = None
    if len(stack) > 1:
        problems.append("unclosed block(s): " + ", ".join(f"{x.key}@{x.line}" for x in stack[1:]))
    return root, problems


def parse_file(path):
    return parse_text(read_text(path))


def entries(root):
    """Top-level entries of a KV file (the children of DOTAAbilities / DOTAUnits / ...)."""
    out = []
    for top in root.children:
        if top.key.startswith("#"):
            continue
        out.extend(c for c in top.children if c.value is None)
    return out


def duplicate_keys(node, path=""):
    """Yield (path, key, first_line, dup_line) for keys repeated inside one block (recursively).
    Keys that Valve's own files repeat on purpose are skipped."""
    seen = {}
    for c in node.children:
        k = c.key.lower()
        if k in SKIP_DUP:
            continue
        if k in seen:
            yield (path or node.key, c.key, seen[k], c.line)
        else:
            seen[k] = c.line
    for c in node.children:
        if c.value is None:
            yield from duplicate_keys(c, f"{path}/{c.key}" if path else c.key)


SKIP_DUP = {"precache", "particle", "firesound", "item", "model", "soundfile"}
