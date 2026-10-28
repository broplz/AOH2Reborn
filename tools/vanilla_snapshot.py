#!/usr/bin/env python3
"""Fetch the current vanilla Dota 2 KV (owner-run; needs network) into tools/vanilla/ (git-ignored).

    tools/vanilla_snapshot.py [--ref <commit>]

Source: github.com/SteamDatabase/GameTracking-Dota2 — a sparse, shallow clone of
game/dota/pak01_dir/scripts/npc (npc_abilities.txt, items.txt, npc_heroes.txt + heroes/*.txt,
neutral_items.txt, npc_ability_ids.txt). Writes tools/vanilla/BUILD with the tracked build line.
Rerun after every Dota patch; then `python3 tools/vanilla_diff.py`.
"""
import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kvlib as kv  # noqa: E402

REPO = "https://github.com/SteamDatabase/GameTracking-Dota2"
SUB = "game/dota/pak01_dir/scripts/npc"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    tmp = kv.VANILLA + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", "--quiet", REPO, tmp], check=True)
    subprocess.run(["git", "-C", tmp, "sparse-checkout", "set", SUB], check=True)
    if a.ref:
        subprocess.run(["git", "-C", tmp, "fetch", "--depth", "1", "origin", a.ref], check=True)
        subprocess.run(["git", "-C", tmp, "checkout", "--quiet", a.ref], check=True)
    build = subprocess.run(["git", "-C", tmp, "log", "-1", "--format=%ad %s"], capture_output=True, text=True, check=True).stdout.strip()
    shutil.rmtree(kv.VANILLA, ignore_errors=True)
    shutil.copytree(os.path.join(tmp, SUB), kv.VANILLA)
    shutil.rmtree(tmp, ignore_errors=True)
    with open(os.path.join(kv.VANILLA, "BUILD"), "w", encoding="utf-8") as f:
        f.write(build.split("|")[0].strip() + "\n" + build + "\n")
    print(f"vanilla snapshot: {build[:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
