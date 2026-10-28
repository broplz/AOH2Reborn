"""Shared helpers for the pipeline scripts: logging, git, task lookup, notifications."""
import datetime
import glob
import os
import re
import subprocess
import sys

import config
from taskfile import TaskFile


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def stamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def log(msg: str) -> None:
    os.makedirs(config.LOG_DIR, exist_ok=True)
    line = f"[{now()}] {msg}"
    print(line, file=sys.stderr, flush=True)
    with open(os.path.join(config.LOG_DIR, "pipeline.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def die(msg: str, code: int = 1) -> None:
    log("ERROR: " + msg)
    sys.exit(code)


def notify(msg: str) -> None:
    """Something needs the human: ATTENTION file + optional AOH_NOTIFY_CMD (gets the text on stdin)."""
    os.makedirs(config.LOG_DIR, exist_ok=True)
    with open(os.path.join(config.LOG_DIR, "ATTENTION.md"), "a", encoding="utf-8") as f:
        f.write(f"- {now()} {msg}\n")
    log("ATTENTION: " + msg)
    cmd = os.environ.get("AOH_NOTIFY_CMD")
    if cmd:
        try:
            subprocess.run(cmd, shell=True, input=msg.encode(), timeout=60, check=False)
        except Exception as e:  # noqa: BLE001 - notification must never break the pipeline
            log(f"notify failed: {e}")


# ---- git ----------------------------------------------------------------
def run(cmd, check=True, capture=True, timeout=None, env=None, cwd=None):
    r = subprocess.run(cmd, cwd=cwd or config.ROOT, check=False, timeout=timeout, env=env,
                       stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.PIPE if capture else None, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed ({r.returncode}): {(r.stderr or '').strip()[:500]}")
    return r


def git(*args, check=True, timeout=None):
    return run(["git", *args], check=check, timeout=timeout)


def git_out(*args) -> str:
    return git(*args).stdout.strip()


def current_branch() -> str:
    return git_out("branch", "--show-current")


def branch_exists(name: str) -> bool:
    return git("rev-parse", "--verify", "--quiet", f"refs/heads/{name}", check=False).returncode == 0


def is_clean() -> bool:
    return git_out("status", "--porcelain") == ""


def switch(branch: str, create_from: str = "") -> None:
    if not is_clean():
        raise RuntimeError("working tree is dirty; commit or stash before switching")
    if create_from:
        git("switch", "-c", branch, create_from)
    else:
        git("switch", branch)


def head() -> str:
    return git_out("rev-parse", "HEAD")


def code_head(branch: str) -> str:
    """Last commit on <branch> that touched something outside tasks/ and logs/ (the SHA verdicts refer to)."""
    out = git_out("log", "-1", "--format=%H", branch, "--", ".", ":(exclude)tasks", ":(exclude)logs", ":(exclude).claude/agent-memory")
    return out or git_out("rev-parse", branch)


def autocommit(message: str) -> bool:
    """Commit whatever an agent left uncommitted so the next session (or the merge) sees it."""
    git("add", "-A")
    if git_out("diff", "--cached", "--name-only") == "":
        return False
    git("commit", "-q", "-m", message)
    log(f"auto-committed: {message}")
    return True


# ---- tasks ----------------------------------------------------------------
def task_files():
    files = sorted(glob.glob(os.path.join(config.TASK_DIR, "[0-9]*.md")))
    return [f for f in files if os.path.basename(f) not in ("TEMPLATE.md", "README.md")]


def find_task(ref: str) -> str:
    """Accept a path, a bare file name or a task id."""
    if os.path.isfile(ref):
        return os.path.abspath(ref)
    cand = os.path.join(config.TASK_DIR, ref)
    if os.path.isfile(cand):
        return cand
    for f in task_files():
        if os.path.basename(f).startswith(ref + "-") or os.path.basename(f) == ref + ".md":
            return f
    raise FileNotFoundError(f"no task file for '{ref}'")


def rel(path: str) -> str:
    return os.path.relpath(path, config.ROOT)


def task_branch(tf: TaskFile) -> str:
    b = tf.get("branch", "").strip()
    if b:
        return b
    slug = re.sub(r"^\d+[a-z]?-", "", os.path.basename(tf.path)[:-3])
    return f"task/{tf.task_id()}-{slug}"


def task_base(tf: TaskFile) -> str:
    base = tf.get("base", "").strip()
    if base:
        return base
    return backlog_active_base()


def backlog_active_base() -> str:
    try:
        with open(config.BACKLOG, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^\s*Active feature branch:\s*`?([^\s`]+)`?", line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return "main"


def backlog_order():
    """Ids in the order they appear in the backlog's `## Next` section."""
    ids, inside = [], False
    try:
        with open(config.BACKLOG, encoding="utf-8") as f:
            for line in f:
                if line.startswith("## "):
                    inside = line.strip().lower().startswith("## next")
                    continue
                if inside:
                    m = re.match(r"^\s*[-*]\s*`?(\d+[a-z]?)\b", line)
                    if m:
                        ids.append(m.group(1))
    except OSError:
        pass
    return ids


def approved(task_id: str, base: str = "") -> bool:
    """`<id> approved` in tasks/approvals.txt — on the base branch (where the owner edits it),
    on main, or in the working tree; any of them counts."""
    texts = []
    try:
        with open(config.APPROVALS, encoding="utf-8") as f:
            texts.append(f.read())
    except OSError:
        pass
    for ref in (base, "main", "master"):
        if ref:
            r = git("show", f"{ref}:{rel(config.APPROVALS)}", check=False)
            if r.returncode == 0:
                texts.append(r.stdout)
    pat = re.compile(rf"^\s*{re.escape(task_id)}\s+(approved|ok|yes)\b", re.I | re.M)
    return any(pat.search(t) for t in texts)
