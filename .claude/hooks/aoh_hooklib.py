"""Shared bits for the AOH2 hooks. Hooks get JSON on stdin; exit 2 blocks (stderr goes to the model).

Role detection: AOH_ROLE (set by the driver) or the `agent_type` field Claude Code adds when the
session runs with --agent or inside a subagent; otherwise "human". AOH_UNLOCK=1 disables every
check — for the owner's own shell only.
"""
import json
import os
import re
import sys

ROLES = ("teamlead", "developer", "developer-hard", "reviewer", "qa", "architect")


def load():
    try:
        return json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return {}


def root(data):
    return os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()


def role(data):
    r = os.environ.get("AOH_ROLE") or data.get("agent_type") or "human"
    return r if r in ROLES else ("human" if r in ("human", "") else r)


def task_path():
    return os.environ.get("AOH_TASK", "")


def unlocked():
    return os.environ.get("AOH_UNLOCK") == "1"


def relpath(data, path):
    r = root(data)
    return os.path.relpath(os.path.abspath(os.path.join(r, path)), r).replace(os.sep, "/")


def logs_dir(data):
    d = os.environ.get("AOH_LOG_DIR") or os.path.join(root(data), "logs")
    os.makedirs(d, exist_ok=True)
    return d


def stop_file(data):
    return os.path.join(logs_dir(data), f".stop-{data.get('session_id', '')}")


def state_path(data):
    return os.path.join(logs_dir(data), f".loop-{data.get('session_id', 'nosession')}.json")


def load_state(data):
    try:
        with open(state_path(data), encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {"calls": {}, "failed_ui": 0, "failed_full": 0, "tool_calls": 0, "warned": [], "nudges": 0}


def save_state(data, st):
    with open(state_path(data), "w", encoding="utf-8") as f:
        json.dump(st, f)


def block(msg):
    sys.stderr.write("BLOCKED by hook: " + msg + "\n")
    sys.exit(2)


def glob_to_re(pattern):
    out, i = "^", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"; i += 3
        elif pattern.startswith("**", i):
            out += ".*"; i += 2
        elif pattern[i] == "*":
            out += "[^/]*"; i += 1
        elif pattern[i] == "?":
            out += "[^/]"; i += 1
        else:
            out += re.escape(pattern[i]); i += 1
    return out + "$"


def matches(path, patterns):
    return any(re.match(glob_to_re(p), path) for p in patterns)


def read_task(data):
    """Frontmatter of the current task via scripts/agents/taskfile.py (same parser as the driver)."""
    p = task_path()
    if not p:
        return None
    sys.path.insert(0, os.path.join(root(data), "scripts", "agents"))
    try:
        from taskfile import TaskFile  # type: ignore
        full = p if os.path.isabs(p) else os.path.join(root(data), p)
        return TaskFile(full)
    except Exception:  # noqa: BLE001
        return None
