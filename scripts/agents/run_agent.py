#!/usr/bin/env python3
"""Run ONE role session with `claude -p --agent <role>` and record what it cost.

    run_agent.py <role> [<task>] [--prompt "<extra>"] [--max-turns N] [--budget USD] [--session N]
                 [--mode plan|unblock]

The driver (run_task.py / run_queue.py) calls this; a human can too. The session is fresh:
the only state an agent gets is the task file, the branch and the rule-sets in its system prompt.
Output: the result JSON goes to logs/agent-<task>-<role>-<stamp>.json, one line to
logs/agent-sessions.jsonl, and a RESULT line on stderr. Exit 0 even when the agent failed —
the task file's status is what the driver reads next.
"""
import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

import config
import pipeline_lib as pl
from taskfile import TaskFile


def skills_text(role: str) -> str:
    parts = []
    for name in config.SKILLS.get(role, []):
        path = os.path.join(config.SKILLS_DIR, name, "SKILL.md")
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            pl.log(f"skill {name} missing at {path}")
            continue
        if text.startswith("---"):          # strip frontmatter
            end = text.find("\n---", 3)
            if end > 0:
                text = text[end + 4:]
        parts.append(f"<!-- {name} -->\n{text.strip()}\n")
    return "\n".join(parts)


def build_prompt(role: str, tf, mode: str, extra: str, session: int) -> str:
    if tf is None:
        task_line = ""
    else:
        task_line = (f"Task file: {pl.rel(tf.path)} (id {tf.task_id()}, status `{tf.get('status')}`). "
                     f"Branch `{pl.task_branch(tf)}` is checked out on top of `{pl.task_base(tf)}`.")
    if role in config.DEV_ROLES:
        status = tf.get("status")
        hint = ""
        if status == "returned":
            hint = " Status is `returned`: fix exactly the numbered items in ## Review / ## QA, nothing else."
        elif tf.section("Handoff"):
            hint = " ## Handoff is filled: continue from it; the work is already on this branch."
        return (f"{task_line} Developer session {session} of {config.MAX_SESSIONS}.{hint} "
                "Follow your workflow: read the whole task file first, then the spec sections it cites. "
                "End the session only when the task status is `review` or `blocked` and everything is committed. "
                "Never touch the `returns` and `sessions` fields — the driver maintains them." + (" " + extra if extra else ""))
    if role == "reviewer":
        return (f"{task_line} Review it: `scripts/agents/diff.sh {pl.rel(tf.path)}` gives the diff, "
                f"`python3 scripts/agents/aoh_lint.py {pl.rel(tf.path)}` the convention check. "
                "Write APPROVE or REQUEST_CHANGES into ## Review, set status (`qa` or `returned`), "
                "commit the task file, end." + (" " + extra if extra else ""))
    if role == "qa":
        return (f"{task_line} QA it: `scripts/agents/check.sh {tf.get('checks', 'all')}`" +
                (f", then `scripts/agents/test.sh` for {tf.get('tests')}" if tf.getlist("tests") else "") +
                ", then verify every Definition of Done item literally ([human] items go under 'For the human'). "
                "Write PASS or FAIL into ## QA, "
                "set status (`approved` or `returned`), commit the task file, end." + (" " + extra if extra else ""))
    if role == "teamlead":
        if mode == "unblock":
            reason = tf.get("blocked_reason", "unknown")
            return (f"{task_line} It is blocked ({reason}). Read it whole (Handoff, Review, QA, Notes) and decide ONE of: "
                    "(a) split — write 2-3 smaller task files from tasks/TEMPLATE.md, set this task's status to `split` "
                    "and note the new ids in ## Notes from teamlead; (b) re-spec — fix the Definition of Done, "
                    "allowed_paths or size here, set returns to 0, blocked_reason empty and status `ready`; "
                    "(c) escalate — append one line to docs/reports/decisions-needed.md and leave status `blocked`. "
                    "Commit as `tasks: <id> <split|re-spec|escalate>`. Never write product code." + (" " + extra if extra else ""))
        return (f"Planning run on branch `{pl.current_branch()}`. Read tasks/backlog.md: for the first {config.PLAN_BATCH} "
                "items under `## Next` that have no task file yet, write task files from tasks/TEMPLATE.md "
                "(read the ADR section each item cites; check real file names in the repo). Commit them as "
                "`tasks: plan <ids>`. Never write product code." + (" " + extra if extra else ""))
    return (task_line + " " + extra).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("role")
    ap.add_argument("task", nargs="?")
    ap.add_argument("--prompt", default="")
    ap.add_argument("--max-turns", type=int)
    ap.add_argument("--budget", type=float)
    ap.add_argument("--session", type=int, default=1)
    ap.add_argument("--mode", default="")
    ap.add_argument("--dry-run", action="store_true", help="print the command and prompt, do not run")
    a = ap.parse_args()

    role = a.role
    tf = TaskFile(pl.find_task(a.task)) if a.task else None
    size = tf.get("size", "M") if tf else "M"
    turns = a.max_turns or config.turns_for(role, size)
    budget = a.budget or config.budget_for(role, size)
    prompt = build_prompt(role, tf, a.mode, a.prompt, a.session)

    # A clean environment: when the driver itself runs inside a Claude Code session (Remote
    # Control, an interactive shell), the parent's CLAUDE_* variables would make the child
    # believe it is that session (same session id, child-session flags, auto-mode policy).
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith(("CLAUDE_CODE_", "CCR_", "CLAUDE_AUTO", "CLAUDE_AFTER", "CLAUDE_INTERNAL", "CLAUDE_ADDITIONAL",
                                 "CLAUDE_EFFORT", "CLAUDE_PID", "CLAUDE_PROJECT_", "CLAUDE_SESSION", "CLAUDE_CHROME", "CLAUDE_CLIENT",
                                 "CLAUDE_ENABLE")) or k in ("CLAUDECODE", "AI_AGENT"))}
    env.update({
        "AOH_ROLE": role,
        "AOH_TASK": pl.rel(tf.path) if tf else "",
        "AOH_BASE": pl.task_base(tf) if tf else pl.backlog_active_base(),
        "AOH_BRANCH": pl.task_branch(tf) if tf else pl.current_branch(),
        "AOH_MAX_TURNS": str(turns),
        "AOH_SESSION": str(a.session),
        "AOH_LOG_DIR": config.LOG_DIR,
    })

    sysdir = tempfile.mkdtemp(prefix="aoh-sys-")
    sysfile = os.path.join(sysdir, "system.md")
    with open(sysfile, "w", encoding="utf-8") as f:
        f.write(f"# Session facts\nRole: {role}. " + (f"Task: {pl.rel(tf.path)}. " if tf else "") +
                f"Turn limit: {turns}. Budget: ${budget:.2f}. Work only through the tools; the driver handles branches.\n\n")
        f.write(skills_text(role))

    cmd = ["claude", "-p", prompt, "--agent", role,
           "--permission-mode", "dontAsk", "--permission-prompts", "none",
           "--output-format", "json", "--max-turns", str(turns), "--max-budget-usd", f"{budget:.2f}",
           "--append-system-prompt-file", sysfile]
    cmd += shlex.split(os.environ.get("AOH_CLAUDE_ARGS", ""))   # e.g. --model sonnet for an experiment
    if a.dry_run:
        print(" ".join(repr(c) if " " in c else c for c in cmd))
        print("--- system prompt file ---")
        print(open(sysfile, encoding="utf-8").read())
        shutil.rmtree(sysdir, ignore_errors=True)
        return 0

    os.makedirs(config.LOG_DIR, exist_ok=True)
    tid = tf.task_id() if tf else (a.mode or "none")
    out_path = os.path.join(config.LOG_DIR, f"agent-{tid}-{role}-{pl.stamp()}.json")
    pl.log(f"RUN role={role} task={tid} session={a.session} turns={turns} budget=${budget:.2f}")
    t0 = os.times().elapsed
    try:
        r = subprocess.run(cmd, cwd=config.ROOT, env=env, text=True, capture_output=True, stdin=subprocess.DEVNULL,
                           timeout=config.SESSION_TIMEOUT_S, check=False)
        stdout, stderr, rc, timed_out = r.stdout, r.stderr, r.returncode, False
    except subprocess.TimeoutExpired as e:
        stdout, stderr, rc, timed_out = (e.stdout or ""), (e.stderr or ""), 124, True
    finally:
        shutil.rmtree(sysdir, ignore_errors=True)
    dur = int(os.times().elapsed - t0)

    data = {}
    try:
        data = json.loads(stdout) if stdout.strip().startswith("{") else {}
    except json.JSONDecodeError:
        data = {}
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(stdout if stdout else json.dumps({"stderr": stderr, "rc": rc}))
    if stderr.strip():
        with open(out_path + ".stderr", "w", encoding="utf-8") as f:
            f.write(stderr)

    summary = {
        "ts": pl.now(), "role": role, "task": tid, "session": a.session,
        "subtype": "timeout" if timed_out else data.get("subtype", f"rc{rc}"),
        "is_error": data.get("is_error", rc != 0), "turns": data.get("num_turns"),
        "cost_usd": round(float(data.get("total_cost_usd") or 0), 4), "duration_s": dur,
        "session_id": data.get("session_id"), "denials": len(data.get("permission_denials") or []),
        "terminal_reason": data.get("terminal_reason"), "log": pl.rel(out_path),
    }
    with open(os.path.join(config.LOG_DIR, "agent-sessions.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(summary) + "\n")
    pl.log(f"RESULT role={role} task={tid} subtype={summary['subtype']} turns={summary['turns']} "
           f"cost=${summary['cost_usd']} duration={dur}s denials={summary['denials']} log={summary['log']}")
    if summary["denials"]:
        pl.log("permission denials: " + "; ".join(
            str(d.get("tool_input", {}).get("command") or d.get("tool_name")) for d in data.get("permission_denials", [])[:5]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
