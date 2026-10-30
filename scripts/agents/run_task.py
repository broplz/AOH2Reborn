#!/usr/bin/env python3
"""Drive ONE task until it is done, blocked or waiting for the human.

    run_task.py <task-id|file> [--once]

The loop (each step is a fresh `claude -p` session; state lives in the task file + branch):

    ready/returned/in_progress -> developer(-hard)   (sessions capped, then blocked:too_big)
    review                     -> reviewer           (APPROVE -> qa, REQUEST_CHANGES -> returned)
    qa                         -> qa                 (PASS -> approved, FAIL -> returned)
    approved                   -> merge_task         (squash into base, or wait for approval)
    blocked                    -> teamlead unblock once (split / re-spec / escalate), then stop
    returned x MAX_RETURNS     -> blocked:returns

Exit codes: 0 done · 2 blocked (needs the human) · 3 waiting for approval · 1 error.
The driver owns git: it creates and switches branches, auto-commits what agents leave behind,
and maintains `sessions`, `returns`, `reviewed_sha`/`qa_sha` when an agent forgot them.
"""
import argparse
import os
import subprocess
import sys

import config
import merge_task
import pipeline_lib as pl
from taskfile import TaskFile

HERE = os.path.dirname(os.path.abspath(__file__))


def run_agent(role, path, **kw):
    cmd = [sys.executable, os.path.join(HERE, "run_agent.py"), role, path]
    for k, v in kw.items():
        if v not in (None, "", False):
            cmd += [f"--{k.replace('_', '-')}", str(v)]
    subprocess.run(cmd, cwd=config.ROOT, check=False)


def commit_task(path, message):
    pl.git("add", "--", pl.rel(path))
    if pl.git_out("diff", "--cached", "--name-only"):
        pl.git("commit", "-q", "-m", message)


def set_blocked(tf, reason, message=""):
    tf.set("status", "blocked")
    tf.set("blocked_reason", reason)
    commit_task(tf.path, f"tasks: {tf.task_id()} blocked ({reason}) (driver)")
    pl.notify(f"task {tf.task_id()} blocked: {reason}. {message}".strip())


def dev_role(tf):
    r = tf.get("role", "developer").strip()
    return r if r in config.DEV_ROLES else "developer"


def ensure_branch(tf):
    branch, base = pl.task_branch(tf), pl.task_base(tf)
    if not pl.branch_exists(base):
        pl.die(f"base branch {base} does not exist (create it with scripts/agents/new_feature.sh)")
    if pl.current_branch() != branch:
        if pl.branch_exists(branch):
            pl.switch(branch)
        else:
            pl.switch(branch, create_from=base)
            pl.log(f"created {branch} from {base}")
    tf = TaskFile(tf.path)
    if not tf.get("branch"):
        tf.set("branch", branch)
        commit_task(tf.path, f"tasks: {tf.task_id()} branch (driver)")
    return TaskFile(tf.path)


def backfill_verdict(role, tf):
    """Repair protocol slips so one forgotten field never stalls the pipeline, and record which
    code the verdict applies to: the branch's code head right after the session (reviewer and qa
    cannot change code, so this is exactly what they looked at)."""
    changed = False
    code = pl.code_head(pl.current_branch())
    if role == "reviewer":
        v = tf.verdict("Review")
        if v == "APPROVE" and tf.get("status") not in ("qa", "approved"):
            tf.set("status", "qa"); changed = True
        if v == "REQUEST_CHANGES" and tf.get("status") != "returned":
            tf.set("status", "returned"); changed = True
        if v != "NONE" and tf.get("reviewed_sha") != code:
            tf.set("reviewed_sha", code); changed = True
    if role == "qa":
        v = tf.verdict("QA")
        if v == "PASS" and tf.get("status") != "approved":
            tf.set("status", "approved"); changed = True
        if v == "FAIL" and tf.get("status") != "returned":
            tf.set("status", "returned"); changed = True
        if v != "NONE" and tf.get("qa_sha") != code:
            tf.set("qa_sha", code); changed = True
    if changed:
        commit_task(tf.path, f"tasks: {tf.task_id()} {role} backfill (driver)")
    return TaskFile(tf.path)


def run_unblock(tf):
    branch, base = pl.task_branch(tf), pl.task_base(tf)
    pl.switch(base)
    if pl.branch_exists(branch):
        pl.git("checkout", branch, "--", pl.rel(tf.path))
        commit_task(tf.path, f"tasks: {tf.task_id()} sync from branch (driver)")
    run_agent("teamlead", tf.path, mode="unblock")
    pl.autocommit(f"tasks: {tf.task_id()} unblock (driver auto-commit)")
    tf = TaskFile(tf.path)
    if tf.get("status") == "ready":
        tf.set("returns", 0); tf.set("sessions", 0); tf.set("blocked_reason", "")   # a re-spec starts the counters over
        commit_task(tf.path, f"tasks: {tf.task_id()} re-spec counters (driver)")
        if pl.branch_exists(branch):
            pl.switch(branch)
            pl.git("checkout", base, "--", pl.rel(tf.path))
            commit_task(tf.path, f"tasks: {tf.task_id()} re-spec (driver)")
    return TaskFile(tf.path)


def run_task(path, once=False):
    tid = TaskFile(path).task_id()
    steps, unblock_tried = 0, False
    while steps < config.MAX_LOOP_STEPS:
        steps += 1
        # read the task file from its branch: the base copy may be stale (ready vs approved on the branch)
        if pl.branch_exists(pl.task_branch(TaskFile(path))):
            ensure_branch(TaskFile(path))
        tf = TaskFile(path)
        status = tf.get("status", "draft")
        pl.log(f"task {tid}: status={status} returns={tf.get('returns', 0)} sessions={tf.get('sessions', 0)}")

        if status in config.FINAL_STATUSES:
            pl.log(f"task {tid}: {status}")
            return 0
        if status == "draft":
            pl.log(f"task {tid} is a draft; set status: ready to run it")
            return 1
        if status == "blocked":
            reason = tf.get("blocked_reason", "")
            if reason in ("merge_gate", "merge_conflict", "escalated"):
                pl.notify(f"task {tid} blocked ({reason}) — this one is for you, not the teamlead; see {pl.rel(path)}")
                return 2
            if config.AUTO_UNBLOCK and not unblock_tried:
                unblock_tried = True
                tf = run_unblock(tf)
                if once:
                    return 2 if tf.get("status") == "blocked" else 0
                continue
            pl.notify(f"task {tid} stays blocked ({tf.get('blocked_reason', '?')}); see {pl.rel(path)} and docs/reports/decisions-needed.md")
            return 2
        if status == "approved":
            ensure_branch(tf)
            rc = merge_task.merge(path)
            if rc == 3:
                pl.notify(f"task {tid} waits for your approval: add a line `{tid} approved` to tasks/approvals.txt and rerun")
                return 3
            if rc != 0:
                continue  # merge() set blocked with the reason
            return 0
        if status in ("ready", "in_progress", "returned"):
            tf = ensure_branch(tf)
            sessions = tf.getint("sessions", 0)
            if sessions >= config.MAX_SESSIONS:
                set_blocked(tf, "too_big", f"{sessions} developer sessions without reaching review; teamlead should split it")
                continue
            tf.set("sessions", sessions + 1)
            commit_task(path, f"tasks: {tid} session {sessions + 1} (driver)")
            role = dev_role(tf)
            run_agent(role, path, session=sessions + 1)
            pl.autocommit(f"{tid}: wip after {role} (driver auto-commit)")
            tf = TaskFile(path)
            if tf.get("status") == "review":        # `sessions` counts attempts since the last review, not rounds
                tf.set("sessions", 0)
                commit_task(path, f"tasks: {tid} reached review (driver)")
        elif status == "review":
            ensure_branch(tf)
            run_agent("reviewer", path)
            pl.autocommit(f"{tid}: wip after reviewer (driver auto-commit)")
            tf = backfill_verdict("reviewer", TaskFile(path))
            if tf.get("status") == "returned":
                bump_returns(tf)
        elif status == "qa":
            ensure_branch(tf)
            run_agent("qa", path)
            pl.autocommit(f"{tid}: wip after qa (driver auto-commit)")
            tf = backfill_verdict("qa", TaskFile(path))
            if tf.get("status") == "returned":
                bump_returns(tf)
        else:
            pl.die(f"task {tid}: unknown status '{status}'")
        if once:
            return 0
    pl.notify(f"task {tid}: loop cap ({config.MAX_LOOP_STEPS} steps) reached; check logs/pipeline.log")
    return 2


def bump_returns(tf):
    n = tf.incr("returns")
    commit_task(tf.path, f"tasks: {tf.task_id()} returns={n} (driver)")
    if n >= config.MAX_RETURNS:
        set_blocked(TaskFile(tf.path), "returns", f"{n} review/QA returns; teamlead should re-spec or split")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task")
    ap.add_argument("--once", action="store_true", help="run a single role step and exit")
    a = ap.parse_args()
    if not pl.is_clean():
        pl.die("working tree is dirty; commit or stash first (the driver switches branches)")
    path = pl.find_task(a.task)
    return run_task(path, once=a.once)


if __name__ == "__main__":
    sys.exit(main())
