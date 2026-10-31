#!/usr/bin/env python3
"""Arity of engine method calls in vscripts against dota-data's api.json. Zero tokens.

    tools/apicheck.py

Every `:Name(` call whose Name is a class member in tools/vanilla/dota-data/files/vscripts/api.json
gets its top-level arguments counted and compared with the union of that name's signatures over
all classes (trailing args typed `nil` are optional). Undetermined calls are skipped: an argument
`...`, or a call as the last argument (multiple returns) unless even without it there are too many.
tools/apicheck.allow lists names (or name + file) not to check. A finding on a name our Lua also
defines (`function X:Name(`, `X.Name = function`) is tagged "ours?" — the call may be ours.
Exit 0 clean · 1 findings · 0 with a note when api.json is absent (tools/vanilla is git-ignored).
"""
import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kvlib as kv  # noqa: E402

API_JSON = os.path.join(kv.VANILLA, "dota-data", "files", "vscripts", "api.json")
ALLOW = os.path.join(kv.ROOT, "tools", "apicheck.allow")
TOKEN = re.compile(
    r"--\[(=*)\[.*?\]\1\]|--[^\n]*|\[(=*)\[.*?\]\2\]|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'"
    r"|(?P<word>[A-Za-z_]\w*)|(?P<sym>\.\.\.|::|[:(){}\[\],])",
    re.S,
)
CALL_ARG = re.compile(r"^[^(].*\)$", re.S)
OUR_DEF = re.compile(r"function\s+[\w.]+[:.](\w+)\s*\(|\.(\w+)\s*=\s*function\b")
OPENERS = {"function", "if", "do", "repeat"}
CLOSERS = {"end", "until"}
BRACKETS = {"(": ")", "[": "]", "{": "}"}


def api_arities():
    arities = collections.defaultdict(set)
    for cls in json.load(open(API_JSON, encoding="utf-8")):
        for m in cls.get("members", []) if cls["kind"] == "class" else []:
            if m["kind"] != "function":
                continue
            args = m.get("args") or []
            required = len(args)
            while required and "nil" in args[required - 1]["types"]:
                required -= 1
            arities[m["name"]].update(range(required, len(args) + 1))
    return arities


def allowlist():
    """{(name, path or None)} from tools/apicheck.allow."""
    rows = (line.split("#")[0].split() for line in open(ALLOW, encoding="utf-8"))
    return {(r[0], r[1] if len(r) > 1 else None) for r in rows if r}


def tokens(text):
    """(kind, value, offset) for words and symbols; comments and strings are dropped."""
    for m in TOKEN.finditer(text):
        if m.group("word"):
            yield "word", m.group("word"), m.start()
        elif m.group("sym"):
            yield "sym", m.group("sym"), m.start()


def calls(text, names):
    """(offset, name, args) for each `:name(` call; args = list of top-level argument source texts."""
    toks = list(tokens(text))
    for i in range(len(toks) - 2):
        (_, colon, _), (kind, name, at), (_, paren, open_at) = toks[i : i + 3]
        if colon != ":" or kind != "word" or name not in names or paren != "(":
            continue
        args, start, stack, depth = [], open_at + 1, [")"], 0
        for kind, v, pos in toks[i + 3 :]:
            if kind == "word":
                depth += (v in OPENERS) - (v in CLOSERS)
                continue
            if v in BRACKETS:
                stack.append(BRACKETS[v])
            elif stack and v == stack[-1]:
                stack.pop()
                if not stack:
                    args.append(text[start:pos])
                    break
            elif v == "," and len(stack) == 1 and depth == 0:
                args.append(text[start:pos])
                start = pos + 1
        args = [a.strip() for a in args]
        yield at, name, [] if args == [""] else args


def arity_error(args, expected):
    """got-count when it surely mismatches, else None."""
    if "..." in args:
        return None
    got = len(args)
    if args and CALL_ARG.match(args[-1]):
        return got if got - 1 > max(expected) else None
    return None if got in expected else got


def main():
    if not os.path.exists(API_JSON):
        print(f"apicheck skipped: no {os.path.relpath(API_JSON, kv.ROOT)} (see docs/notes/apicheck.md)")
        return 0
    arities = api_arities()
    allow = allowlist()
    files = sorted(glob.glob(os.path.join(kv.VSCRIPTS, "**", "*.lua"), recursive=True))
    texts = {f: kv.read_text(f) for f in files}
    ours = {n for t in texts.values() for m in OUR_DEF.finditer(t) for n in m.groups() if n}
    findings, checked = [], 0
    for f, text in texts.items():
        path = os.path.relpath(f, kv.VSCRIPTS).replace(os.sep, "/")
        for at, name, args in calls(text, arities):
            if (name, None) in allow or (name, path) in allow:
                continue
            checked += 1
            got = arity_error(args, arities[name])
            if got is None:
                continue
            line = text.count("\n", 0, at) + 1
            expected = ",".join(map(str, sorted(arities[name])))
            tag = " ours?" if name in ours else ""
            findings.append(f"FAIL {os.path.relpath(f, kv.ROOT)}:{line} {name} got={got} expected={{{expected}}}{tag}")
    for row in findings:
        print(row)
    print(f"apicheck: {len(findings)} finding(s) in {checked} checked call(s) of {len(arities)} api.json names")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
