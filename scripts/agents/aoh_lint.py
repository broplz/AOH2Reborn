#!/usr/bin/env python3
"""Deterministic check of a task's diff against the ADR-0002 code conventions. Zero tokens.

    aoh_lint.py <task-id|file> [--base <branch>] [--branch <branch>]

Exit: 0 clean · 1 FAIL (rule broken) · 3 clean but needs human approval (game-mode core, shops,
hero list or a `[human]` DoD item — ADR-0001 §3). WARN lines never fail. Run by qa, by
merge_task.py and by hand. Rules are on ADDED lines only, so legacy code is not a failure until
a task touches it.
"""
import argparse
import os
import re
import sys

import config
import pipeline_lib as pl
from taskfile import TaskFile

ADDON = "game/dota_addons/attackcopy"
LUA_DIR = f"{ADDON}/scripts/vscripts"
SCOPE_FREE = [r"^tasks/", r"^logs/", r"^docs/notes/", r"^docs/reports/", r"^\.claude/agent-memory/"]
PROD_EXCLUDE = [r"\.md$", r"^tasks/", r"^docs/", r"^tests/", r"^\.claude/agent-memory/", r"^tools/vanilla/"]
PROTECTED = [rf"^{ADDON}/panorama/.*_c$", r"\.(vtex_c|vpcf_c|vmat_c|vmdl_c|vmesh_c|vmap|tga|png|dmx|zip)$",
             rf"^{ADDON}/(models|materials|particles|sounds|maps)/", r"^content/dota_addons/attackcopy/(maps|materials|models|particles|sounds)/"]

# (regex on an added Lua line, message) — see .claude/skills/aoh-rules/SKILL.md
LUA_RULES = [
    (r"\bGetItemInSlot\(\s*1[6-9]\s*\)", "hard-coded neutral slot: use DOTA_ITEM_NEUTRAL_ACTIVE_SLOT / DOTA_ITEM_NEUTRAL_PASSIVE_SLOT"),
    (r"\bDOTA_ITEM_NEUTRAL_SLOT\b", "DOTA_ITEM_NEUTRAL_SLOT was removed in 7.38 (ACTIVE/PASSIVE slots)"),
    (r"\bDOTA_DAMAGE_FLAG_BYPASSES_BLOCK\b", "removed enum: use DOTA_DAMAGE_FLAG_BYPASSES_ALL_BLOCK / _PHYSICAL_BLOCK"),
    (r"damage_flags\s*[~=]=\s*\d+", "magic damage flag number: bit.band(keys.damage_flags, DOTA_DAMAGE_FLAG_*)"),
    (r"\border_type\s*[~=]=\s*\d+", "magic order number: use DOTA_UNIT_ORDER_*"),
    (r"GetAbilityType\(\)\s*[~=]=\s*\d+", "magic ability type: use ABILITY_TYPE_*"),
    (r"FindAbilityByName\(\s*[\"']special_bonus_", "talent lookup by name: declare the talent inline in AbilityValues and read GetSpecialValueFor"),
    (r"\bGetLevelSpecialValueFor\(", "GetLevelSpecialValueFor: use GetSpecialValueFor (AbilityValues)"),
    (r"\bkeys\.id\b", "client-supplied player id: use keys.PlayerID (set by the engine) and check ownership"),
    (r"LinkLuaModifier\([^)]*\\\\", "LinkLuaModifier path with backslashes: use / and .lua"),
    (r"\bParticlzeManager\b", "typo: ParticleManager"),
    (r"StartIntervalThink\(\s*0(\.0+)?\s*\)", "think every frame: use >= 0.1 or justify in a comment on the same line"),
    (r"\bprint\(.*\.\.", "print with concatenation in Lua (hot path?): use core/log or remove before review"),
    (r"\bGetClassname\(", "GetClassname is removed from Panorama (GetClassNameAsCStr); in Lua prefer GetUnitName/IsHero checks"),
]
# Per-file checks on the ADDED content of a Lua file
LUA_FILE_RULES = [
    (re.compile(r"^(?!\s*local\s)(?!\s*--)\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)(?!\s*(?:[A-Za-z_][A-Za-z0-9_.]*\.)?class\()(?!.*,\s*(--.*)?$)", re.M),
     "global assignment `{m}` (only `<name> = class({{}})` may be global; everything else `local`)"),
    (re.compile(r"^function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M),
     "global function `{m}`: make it `local function` or a method on the class"),
]
KV_RULES = [
    (r"\"ScriptFile\"\s+\"[^\"]*\\\\", "ScriptFile with backslashes: use /"),
    (r"\"AbilitySpecial\"", "AbilitySpecial in new KV: use AbilityValues"),
    (r"\"LinkedSpecialBonus\"", "LinkedSpecialBonus in new KV: declare the talent inline in AbilityValues"),
    (r"\"BaseClass\"\s+\"ability_datadriven\"", "new ability_datadriven entry: write an ability_lua (ADR-0002 §Lua 10)"),
]
PANORAMA_RULES = [
    (r"FindChildTraverse\(\s*[\"'](Hud|GameEndContainer|HUDElements)", "reaching into Valve's HUD tree by id"),
    (r"DotaDefaultUIElement_t\.\w+\s*=\s*\d+", "hard-coded Valve enum value"),
    (r"\bGetClassname\(", "Entities.GetClassname is removed: GetClassNameAsCStr"),
]


def changed_files(base, branch):
    names = pl.git_out("diff", "--name-only", f"{base}...{branch}").splitlines()
    if pl.current_branch() == branch:          # uncommitted work counts too
        names += pl.git_out("diff", "--name-only", "HEAD").splitlines()
        names += pl.git_out("ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({n for n in names if n})


def added_lines(path, base, branch):
    r = pl.git("diff", f"{base}...{branch}", "--", path, check=False)
    out = r.stdout.splitlines() if r.returncode == 0 else []
    if pl.current_branch() == branch:
        out += pl.git("diff", "HEAD", "--", path, check=False).stdout.splitlines()
        if path in pl.git_out("ls-files", "--others", "--exclude-standard").splitlines():
            try:
                with open(os.path.join(config.ROOT, path), encoding="utf-8", errors="replace") as f:
                    out += ["+" + l.rstrip("\n") for l in f]
            except OSError:
                pass
    return [l[1:] for l in out if l.startswith("+") and not l.startswith("+++")]


def match(path, patterns):
    return any(re.search(p, path) for p in patterns)


def glob_to_re(pattern):
    out, i = "^", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"; i += 3
        elif pattern.startswith("**", i):
            out += ".*"; i += 2
        elif pattern[i] == "*":
            out += "[^/]*"; i += 1
        else:
            out += re.escape(pattern[i]); i += 1
    return out + "$"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("--base")
    ap.add_argument("--branch")
    a = ap.parse_args()
    tf = TaskFile(pl.find_task(a.task))
    base = a.base or pl.task_base(tf)
    branch = a.branch or (pl.task_branch(tf) if pl.branch_exists(pl.task_branch(tf)) else "HEAD")
    files = changed_files(base, branch)
    fails, warns, notes = [], [], []
    needs_approval = False
    allowed = [glob_to_re(p) for p in tf.getlist("allowed_paths")] + [glob_to_re(pl.rel(tf.path))]
    if tf.get("kind", "") != "test":
        allowed.append(glob_to_re("tests/test_*.lua"))
    dod = tf.section("Definition of Done")
    if "[human]" in dod:
        needs_approval = True
        notes.append("DoD has [human] items — owner playtest required before the merge")

    prod_lines = 0
    for path in files:
        if match(path, PROTECTED):
            fails.append(f"{path}: compiled or binary asset changed — only the owner / Workshop Tools do that")
            continue
        added = added_lines(path, base, branch)
        if path.endswith(".lua") and path.startswith((LUA_DIR, "tests/")):
            text = "\n".join(added)
            for pat, msg in LUA_RULES:
                for l in added:
                    if re.search(pat, l) and "aoh-lint: ok" not in l:
                        fails.append(f"{path}: {msg}: {l.strip()[:90]}")
                        break
            if path.startswith(LUA_DIR):
                for rx, msg in LUA_FILE_RULES:
                    for m in rx.finditer(text):
                        name = m.group(1)
                        if name in ("Activate", "Precache") or name.startswith(("modifier_", "item_", "ability_")):
                            continue
                        line = text[text.rfind("\n", 0, m.start()) + 1: text.find("\n", m.start())]
                        if "aoh-lint: ok" in line or line.lstrip().startswith(("if ", "elseif ", "while ", "for ", "return ")):
                            continue
                        if re.search(r"^\s*[A-Za-z_][A-Za-z0-9_.:]*\s*=\s*", line) and ("." in name or ":" in line.split("=")[0]):
                            continue
                        fails.append(f"{path}: {msg.format(m=name)}: {line.strip()[:90]}")
                        break
        if re.search(r"scripts/npc/.*\.txt$", path):
            for pat, msg in KV_RULES:
                for l in added:
                    if re.search(pat, l):
                        fails.append(f"{path}: {msg}: {l.strip()[:90]}")
                        break
        if path.startswith("content/dota_addons/attackcopy/panorama/") and path.endswith((".js", ".xml")):
            for pat, msg in PANORAMA_RULES:
                for l in added:
                    if re.search(pat, l):
                        fails.append(f"{path}: {msg}: {l.strip()[:90]}")
                        break
        if re.search(config.APPROVAL_RE, path):
            needs_approval = True
            notes.append(f"{path}: game-mode core / shops / hero list changed — owner approval required")
        if not match(path, SCOPE_FREE) and allowed and not any(re.match(p, path) for p in allowed):
            fails.append(f"{path}: outside the task's allowed_paths")
        for l in added:
            if not path.endswith(".md") and re.search(r"\b(TODO|FIXME|XXX)\b", l) and not re.search(r"\b(TODO|FIXME|XXX)\b\s*[:(]?\s*\d{4}", l):
                fails.append(f"{path}: TODO/FIXME without a task id: {l.strip()[:80]}")
                break
        if not match(path, PROD_EXCLUDE):
            prod_lines += len(added)

    size = tf.get("size", "M").upper()
    cap_lines, cap_files = config.SIZE_CAPS.get(size, config.SIZE_CAPS["M"])
    prod_files = [f for f in files if not match(f, PROD_EXCLUDE)]
    if prod_lines > cap_lines or len(prod_files) > cap_files:
        warns.append(f"size {size}: {prod_lines} added production lines in {len(prod_files)} files "
                     f"(cap {cap_lines}/{cap_files}) — teamlead: consider splitting next time")

    for l in fails:
        print("FAIL " + l)
    for l in warns:
        print("WARN " + l)
    for l in notes:
        print("NOTE " + l)
    print(f"aoh_lint: {len(files)} files, {prod_lines} production lines, {len(fails)} fail, {len(warns)} warn"
          + (", NEEDS APPROVAL" if needs_approval else ""))
    if fails:
        return 1
    return 3 if needs_approval else 0


if __name__ == "__main__":
    sys.exit(main())
