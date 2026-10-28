#!/usr/bin/env python3
"""PreToolUse hook for Edit | Write | MultiEdit | NotebookEdit.

Blocks writes (1) to protected paths (pipeline config, compiled Panorama, binary assets,
secrets), (2) to existing tests in non-test tasks, (3) outside the task's allowed_paths plus the
role's standing paths. Exit 2 blocks; stderr reaches the model.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aoh_hooklib as h  # noqa: E402

ADDON = "game/dota_addons/attackcopy"
CONTENT = "content/dota_addons/attackcopy"
PROTECTED = [
    ".claude/**", "CLAUDE.md", ".github/**", ".git/**", "tasks/approvals.txt",
    "**/.env", "**/*.env", "**/*secret*", "**/*Secret*",
    # compiled Panorama and binary assets: never edited by hand, never by an agent
    f"{ADDON}/panorama/**/*_c", f"{ADDON}/**/*.vtex_c", f"{ADDON}/**/*.vpcf_c", f"{ADDON}/**/*.vmat_c",
    f"{ADDON}/**/*.vmdl_c", f"{ADDON}/**/*.vmesh_c", f"{ADDON}/**/*.vsndevts_c",
    f"{ADDON}/models/**", f"{ADDON}/materials/**", f"{ADDON}/particles/**", f"{ADDON}/sounds/**",
    f"{ADDON}/maps/**", f"{CONTENT}/maps/**", f"{CONTENT}/materials/**", f"{CONTENT}/models/**",
    f"{CONTENT}/particles/**", f"{CONTENT}/sounds/**", "**/*.png", "**/*.tga", "**/*.dmx", "**/*.zip",
    "tools/vanilla/**", "steam_appid.txt",
]
TEST_PATHS = ["tests/**"]
SCRATCH = ["logs/**"]
SHARED = ["tasks/backlog.md", "docs/notes/**"]          # "Found by agents" and API notes, any pipeline role
ROLE_PATHS = {
    "teamlead": ["tasks/**", "docs/plans/**", "docs/reports/**", "docs/notes/**"] + SCRATCH,
    "developer": SHARED + SCRATCH,
    "developer-hard": SHARED + SCRATCH,
    "reviewer": ["tasks/backlog.md"] + SCRATCH,
    "qa": ["tasks/backlog.md", "tasks/bugs/**"] + TEST_PATHS + SCRATCH,
    "architect": ["docs/**", "tasks/backlog.md"] + SCRATCH,
}
ALLOWED_PATHS_APPLY = ("developer", "developer-hard")


def on_base(root, base, rel):
    import subprocess
    for ref in (base, f"origin/{base}"):
        r = subprocess.run(["git", "cat-file", "-e", f"{ref}:{rel}"], cwd=root,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode == 0:
            return True
    return False


def main():
    if h.unlocked():
        sys.exit(0)
    data = h.load()
    ti = data.get("tool_input") or {}
    file_path = ti.get("file_path") or ti.get("notebook_path") or ""
    if not file_path:
        sys.exit(0)
    root = h.root(data)
    rel = h.relpath(data, file_path)
    role = h.role(data)
    task = h.read_task(data)
    own = h.relpath(data, h.task_path()) if h.task_path() else ""

    if os.path.exists(h.stop_file(data)) and rel != own:
        h.block("session is stopped (strikes/loop). Only your own task file may be edited now: "
                f"{own or '(none)'} — write ## Handoff, set status: blocked, commit, end.")
    if rel.startswith(".."):
        h.block(f"{rel} is outside the repository.")
    if rel.startswith(f".claude/agent-memory/{role}/") or (role == "human" and rel.startswith(".claude/agent-memory/")):
        sys.exit(0)
    if h.matches(rel, PROTECTED):
        h.block(f"{rel} is protected (pipeline config, compiled/binary assets, secrets). Only the human changes it. "
                "Panorama sources live under content/dota_addons/attackcopy/panorama/.")
    if role == "human":
        sys.exit(0)

    kind = task.get("kind", "") if task else ""
    base = os.environ.get("AOH_BASE") or (task.get("base", "main") if task else "main")
    if h.matches(rel, TEST_PATHS) and kind != "test" and role != "qa":
        if os.path.exists(os.path.join(root, rel)) and on_base(root, base, rel):
            h.block(f"{rel} is a test that already exists on {base}. Feature tasks may only add new test files "
                    "(and edit those); existing tests change only in kind: test tasks or by qa. Fix the code, not the test.")

    scope = list(ROLE_PATHS.get(role, []))
    if own:
        scope.append(own)
    if task and role in ALLOWED_PATHS_APPLY:
        scope += task.getlist("allowed_paths")
        if kind != "test":
            scope += ["tests/test_*.lua"]       # a developer may ADD a test for the logic it writes
    if not scope:
        h.block(f"role '{role}' has no write scope here.")
    if not h.matches(rel, scope):
        h.block(f"{rel} is outside this task's allowed_paths. Allowed: {', '.join(scope)}. "
                "If the task really needs this file, stop and say so in ## Handoff (or one line in tasks/backlog.md under Found by agents).")
    sys.exit(0)


if __name__ == "__main__":
    main()
