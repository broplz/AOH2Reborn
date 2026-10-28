#!/usr/bin/env python3
"""Print only what matters from a build/test/import log: counts, each distinct error with a
little context, warnings from our own files. Hard cap on output so it never floods a context.

    triage_log.py <log> [--max-lines 120] [--context 4] [--all-warnings]
"""
import argparse
import re
import sys
from collections import OrderedDict

ERROR_RE = re.compile(
    r"(^|\s)(error(\[E\d+\])?:|fatal error:|ERROR[: ]|\bFAILED\b|TEST-UNEXPECTED-(FAIL|ERROR)|"
    r"Traceback \(most recent call last\)|npm ERR!|error TS\d+|patch does not apply|does not match index|"
    r"Hunk #\d+ FAILED|CONFLICT \(|ninja: build stopped|\*\*\* \[|Assertion failure|Error: |"
    r"Command failed|exited with code [1-9]|No such file or directory|Permission denied|"
    r"Unhandled rejection|\[ERROR\]|\berror\b\s+\w+:\s)", re.I)
IGNORE_RE = re.compile(r"(-Werror|error-prone|errors?=|0 errors|no errors|error_code|\.error\b|ErrorResult|"
                       r"warning: .*error|RESULT: OK|BUILD RESULT|tests? passed)", re.I)
WARN_RE = re.compile(r"\bwarning(\[\w+\])?:", re.I)
OURS_RE = re.compile(r"vscripts/|scripts/npc/|tests/|tools/")
LOC_RE = re.compile(r"((?:[\w./-]+)\.(?:lua|txt|js|xml|css|py|sh|yaml|yml|toml)(?::\d+)+)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--max-lines", type=int, default=120)
    ap.add_argument("--context", type=int, default=4)
    ap.add_argument("--all-warnings", action="store_true")
    a = ap.parse_args()
    try:
        with open(a.log, encoding="utf-8", errors="replace") as f:
            lines = [l.rstrip("\n") for l in f]
    except OSError as e:
        print(f"cannot read {a.log}: {e}")
        return 1

    errors = OrderedDict()   # normalized line -> (first index, count)
    warnings = OrderedDict()
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or IGNORE_RE.search(s):
            continue
        key = re.sub(r"\d+", "N", re.sub(r"\x1b\[[0-9;]*m", "", s))[:160]
        if ERROR_RE.search(s):
            if key in errors:
                errors[key] = (errors[key][0], errors[key][1] + 1)
            else:
                errors[key] = (i, 1)
        elif WARN_RE.search(s) and (a.all_warnings or OURS_RE.search(s)):
            if key in warnings:
                warnings[key] = (warnings[key][0], warnings[key][1] + 1)
            else:
                warnings[key] = (i, 1)

    out = [f"log: {a.log} ({len(lines)} lines) — {sum(c for _, c in errors.values())} error lines, "
           f"{len(errors)} distinct; {len(warnings)} distinct warnings from our files"]
    tail_hint = lines[-1].strip()[:120] if lines else ""
    for key, (idx, count) in list(errors.items())[:12]:
        out.append("")
        loc = LOC_RE.search(lines[idx])
        out.append(f"--- error x{count}" + (f" @ {loc.group(1)}" if loc else "") + f" (line {idx + 1})")
        lo, hi = max(0, idx - a.context), min(len(lines), idx + a.context + 1)
        for j in range(lo, hi):
            out.append(("> " if j == idx else "  ") + lines[j][:200])
    if len(errors) > 12:
        out.append(f"... {len(errors) - 12} more distinct errors; grep the log with a narrower pattern")
    for key, (idx, count) in list(warnings.items())[:8]:
        out.append(f"warn x{count}: {lines[idx].strip()[:180]}")
    if not errors:
        out.append("no error lines matched" + (f"; last line: {tail_hint}" if tail_hint else ""))
    for l in out[:a.max_lines]:
        print(l)
    if len(out) > a.max_lines:
        print(f"... truncated to {a.max_lines} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
