#!/usr/bin/env python3
"""luacheck baseline ratchet: known legacy warnings live in tools/luacheck.baseline, only NEW ones fail.

  python3 tools/luacheck_ratchet.py [paths...]   check (default tree when no paths)
  python3 tools/luacheck_ratchet.py --prune      drop baseline entries that no longer occur
  python3 tools/luacheck_ratchet.py --update-baseline   regenerate (owner only)
"""
import argparse
import os
import re
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(ROOT, "tools", "luacheck.baseline")
DEFAULT_PATHS = ["game/dota_addons/attackcopy/scripts/vscripts", "tests"]
HEADER = "# luacheck baseline: known legacy warnings (normalized, no line numbers). Shrink with --prune; never add by hand.\n"
POS = re.compile(r":\d+:\d+:")


def lint(paths):
    """Return raw warning lines, or None after printing a fatal luacheck failure."""
    cmd = ["luacheck", "--no-color", "--codes", "--formatter", "plain", *paths]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if p.returncode >= 3:
        print(p.stderr.strip())
        print(f"RATCHET: FAIL (luacheck exit {p.returncode})")
        return None
    return [l for l in p.stdout.splitlines() if POS.search(l)]


def normalize(line):
    # "path:1:2: (W111) msg" -> "path: (W111) msg"
    return POS.sub(":", line, count=1)


def read_baseline():
    if not os.path.exists(BASELINE):
        return Counter()
    with open(BASELINE, encoding="utf-8") as f:
        return Counter(l.rstrip("\n") for l in f if l.strip() and not l.startswith("#"))


def write_baseline(counter):
    with open(BASELINE, "w", encoding="utf-8") as f:
        f.write(HEADER)
        f.writelines(l + "\n" for l in sorted(counter.elements()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--prune", action="store_true")
    a = ap.parse_args()

    whole_tree = a.update_baseline or a.prune
    lines = lint(DEFAULT_PATHS if whole_tree or not a.paths else a.paths)
    if lines is None:
        return 1
    current = Counter(normalize(l) for l in lines)

    if a.update_baseline:
        write_baseline(current)
        print(f"baseline written: {sum(current.values())} warnings")
        return 0
    baseline = read_baseline()
    if a.prune:
        kept = baseline & current
        write_baseline(kept)
        print(f"baseline pruned: {sum(baseline.values()) - sum(kept.values())} removed")
        return 0

    new = current - baseline
    budget = Counter(new)
    for raw in lines:
        key = normalize(raw)
        if budget[key] > 0:
            budget[key] -= 1
            print("NEW " + raw)
    scope = tuple(p.rstrip("/") for p in (a.paths or DEFAULT_PATHS))
    in_scope = Counter({k: v for k, v in baseline.items() if k.split(":", 1)[0].startswith(scope)})
    fixed = sum((in_scope - current).values())
    known = sum((current & baseline).values())
    n_new = sum(new.values())
    print(f"luacheck ratchet: {n_new} new, {known} known, {fixed} fixed")
    print("RATCHET: FAIL" if n_new else "RATCHET: OK")
    return 1 if n_new else 0


if __name__ == "__main__":
    sys.exit(main())
