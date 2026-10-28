#!/usr/bin/env python3
"""PreToolUse hook for Read | Grep | Glob — context protection.

The KV files are 10-20k lines each and the Lua tree has 300+ files; binary assets are useless
as text. Agents read big files only in slices (offset/limit), grep the tree only with a
narrowing glob/type and a head_limit, and never read binaries, logs or secrets.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aoh_hooklib as h  # noqa: E402

NEVER = ["**/.env", "**/*.env", "**/*secret*", "**/*Secret*", ".git/**"]
BINARY_EXT = (".vtex_c", ".vpcf_c", ".vmat_c", ".vmdl_c", ".vmesh_c", ".vxml_c", ".vjs_c", ".vcss_c", ".vsndevts_c",
              ".vmap", ".vtex", ".vpcf", ".vmat", ".vmdl", ".tga", ".png", ".dmx", ".zip", ".bin", ".wav", ".mp3")
BIG_TREES = ("tools/vanilla/", "logs/", "node_modules/")
READ_LIMIT = 400          # max lines per Read of a big file
SIZE_LIMIT = 200 * 1024   # bytes: bigger files anywhere need offset/limit (every npc_*.txt is bigger)
GREP_LIMIT = 150          # max head_limit over the whole repo / a big tree


def main():
    if h.unlocked():
        sys.exit(0)
    data = h.load()
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    role = h.role(data)
    root = h.root(data)

    if tool == "Read":
        fp = ti.get("file_path") or ""
        if not fp:
            sys.exit(0)
        rel = h.relpath(data, fp)
        if h.matches(rel, NEVER):
            h.block(f"{rel}: secrets/git internals are never read.")
        if role == "human":
            sys.exit(0)
        limit = ti.get("limit")
        if rel.lower().endswith(BINARY_EXT):
            h.block(f"{rel} is a compiled or binary asset — nothing to read. Panorama sources are under "
                    "content/dota_addons/attackcopy/panorama/; KV and Lua under game/dota_addons/attackcopy/scripts/.")
        if rel.endswith(".log"):
            h.block(f"{rel}: raw logs flood the context. Use `python3 scripts/agents/triage_log.py {rel}` "
                    "(check.sh/test.sh already print it), or `tail -n 40` via Bash.")
        try:
            size = os.path.getsize(os.path.join(root, rel))
        except OSError:
            size = 0
        if (rel.startswith(BIG_TREES) or size > SIZE_LIMIT) and (not limit or int(limit) > READ_LIMIT):
            h.block(f"{rel} is {size // 1024} KB. Locate the spot with Grep (glob/type + head_limit), then Read "
                    f"with offset + limit ≤ {READ_LIMIT}. For a KV entry: `python3 tools/kvcheck.py --show <entry>` prints just that block.")
        sys.exit(0)

    if role == "human":
        sys.exit(0)

    if tool == "Grep":
        path = ti.get("path") or "."
        rel = h.relpath(data, path)
        narrow = bool(ti.get("glob") or ti.get("type"))
        hl = ti.get("head_limit")
        big = rel in (".", "") or rel.startswith(BIG_TREES) or rel.rstrip("/") in ("game", "content", "game/dota_addons/attackcopy")
        if big and not narrow:
            h.block(f"Grep over `{rel}` needs a narrowing `glob` or `type` (e.g. glob \"*.lua\" or \"npc_abilities_custom.txt\").")
        if big and (hl is None or int(hl) > GREP_LIMIT):
            h.block(f"Grep over `{rel}` needs head_limit ≤ {GREP_LIMIT} (files_with_matches first, then content on one file).")
        sys.exit(0)

    if tool == "Glob":
        pattern = ti.get("pattern") or ""
        path = ti.get("path") or "."
        rel = h.relpath(data, path)
        target = (rel.rstrip("/") + "/" + pattern) if rel not in (".", "") else pattern
        if target.split("/")[0] in ("tools/vanilla", "node_modules") or target.startswith("tools/vanilla"):
            h.block(f"Glob `{target}` walks the vanilla snapshot; use tools/vanilla_diff.py or Grep one file there.")
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
