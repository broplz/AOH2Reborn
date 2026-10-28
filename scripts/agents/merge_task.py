#!/usr/bin/env python3
"""Merge an approved task branch into its base branch (never main) — squash, one commit per task.

    merge_task.py <task-id|file> [--check]

Gates (all deterministic, zero tokens):
  status approved · ## Review starts with APPROVE · ## QA starts with PASS ·
  reviewed_sha == qa_sha == last code commit on the branch (tasks/ and logs/ commits don't count) ·
  aoh_lint.py passes · if the task needs approval, tasks/approvals.txt has `<id> approved`.
Exit: 0 merged · 2 gate failed (task set to blocked with the reason) · 3 waiting for approval.
"""
import argparse
import os
import subprocess
import sys

import config
import pipeline_lib as pl
from taskfile import TaskFile

HERE = os.path.dirname(os.path.abspath(__file__))


def gates(tf, branch):
    errors = []
    if tf.get("status") != "approved":
        errors.append(f"status is '{tf.get('status')}', expected approved")
    if tf.verdict("Review") != "APPROVE":
        errors.append("## Review does not start with APPROVE")
    if tf.verdict("QA") != "PASS":
        errors.append("## QA does not start with PASS")
    code = pl.code_head(branch)
    for key in ("reviewed_sha", "qa_sha"):
        sha = tf.get(key, "").strip()
        if not sha:
            errors.append(f"{key} is empty")
        elif not code.startswith(sha) and not sha.startswith(code[:7]):
            errors.append(f"{key} {sha[:10]} != code head {code[:10]} (code changed after the verdict)")
    lint = subprocess.run([sys.executable, os.path.join(HERE, "aoh_lint.py"), tf.path, "--base", pl.task_base(tf), "--branch", branch],
                          cwd=config.ROOT, capture_output=True, text=True, check=False)
    if lint.returncode not in (0, 3):
        errors.append("aoh_lint failed:\n" + (lint.stdout or lint.stderr).strip()[:1500])
    needs_approval = tf.getbool("needs_approval") or lint.returncode == 3
    return errors, needs_approval


def merge(path, check_only=False):
    tf = TaskFile(path)
    tid, branch, base = tf.task_id(), pl.task_branch(tf), pl.task_base(tf)
    if not pl.branch_exists(branch):
        pl.die(f"branch {branch} does not exist")
    if base in ("main", "master"):
        pl.die("tasks never merge into main; set `base:` to a feat/* branch (ADR-0001)")
    errors, needs_approval = gates(tf, branch)
    if errors:
        msg = "; ".join(e.splitlines()[0] for e in errors)
        pl.log(f"merge gates failed for {tid}: {msg}")
        for e in errors:
            print(" - " + e)
        if not check_only:
            pl.switch(branch)
            t = TaskFile(path)
            t.set("status", "blocked"); t.set("blocked_reason", "merge_gate")
            pl.git("add", "--", pl.rel(path)); pl.git("commit", "-q", "-m", f"tasks: {tid} blocked (merge_gate) (driver)")
            pl.notify(f"task {tid} failed merge gates: {msg}")
        return 2
    if needs_approval and not pl.approved(tid, base):
        pl.log(f"task {tid} needs human approval (tasks/approvals.txt)")
        return 3
    if check_only:
        print(f"{tid}: all gates pass (needs_approval={needs_approval})")
        return 0

    pl.switch(base)
    title, prefix = tf.get("title", tid), tf.get("prefix", tf.get("epic", "p0"))
    r = pl.git("merge", "--squash", branch, check=False)
    if r.returncode != 0:
        pl.git("merge", "--abort", check=False)
        pl.git("reset", "-q", "--hard", "HEAD", check=False)
        pl.log(f"squash of {branch} into {base} conflicts; trying to rebase the branch first")
        pl.switch(branch)
        rb = pl.git("rebase", base, check=False)
        if rb.returncode != 0:
            pl.git("rebase", "--abort", check=False)
            t = TaskFile(path)
            t.set("status", "blocked"); t.set("blocked_reason", "merge_conflict")
            pl.git("add", "--", pl.rel(path)); pl.git("commit", "-q", "-m", f"tasks: {tid} blocked (merge_conflict) (driver)")
            pl.notify(f"task {tid}: branch {branch} conflicts with {base}; resolve by hand (git rebase {base}) and rerun")
            return 2
        pl.switch(base)
        pl.git("merge", "--squash", branch)
    t = TaskFile(path)                      # the branch's copy is staged now; close it in the same commit
    t.set("status", "done"); t.set("blocked_reason", "")
    pl.git("add", "--", pl.rel(path))
    body = tf.section("Result")
    message = f"{prefix}: {title} ({tid})\n\n{body}\n\nTask: {pl.rel(path)}\nBranch: {branch} @ {pl.code_head(branch)[:10]}"
    pl.git("commit", "-q", "-m", message)
    merged = pl.head()
    with open(os.path.join(config.LOG_DIR, "merges.log"), "a", encoding="utf-8") as f:
        f.write(f"{pl.now()} MERGED {tid} {branch}@{pl.code_head(branch)[:10]} -> {base}@{merged[:10]}\n")
    pl.git("branch", "-D", branch)
    pl.log(f"merged {tid} into {base} ({merged[:10]}); branch {branch} deleted (recoverable from reflog)")
    try:
        pl.git("push", "origin", base, timeout=config.PUSH_TIMEOUT_S)
        pl.log(f"pushed {base}")
    except Exception as e:  # noqa: BLE001 - push is not a gate (push is best effort)
        pl.log(f"push of {base} failed or timed out ({str(e).splitlines()[0][:120]}); push it later by hand")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not pl.is_clean():
        pl.die("working tree is dirty")
    return merge(pl.find_task(a.task), check_only=a.check)


if __name__ == "__main__":
    sys.exit(main())
