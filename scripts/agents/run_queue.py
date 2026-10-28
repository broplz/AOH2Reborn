#!/usr/bin/env python3
"""Run the queue: every runnable task in backlog order, one at a time, until the queue is empty
or something needs the human.

    run_queue.py [--plan] [--continue-on-block] [--max-tasks N] [--list]

--plan               when nothing is runnable, let the teamlead write task files for the next
                     backlog items (AOH_PLAN_BATCH, default 3), then continue
--continue-on-block  skip a blocked/waiting task and go on with independent ones (default: stop)
--list               print the queue and exit (status from the task branch when one exists)

A task is runnable when its status is ready/in_progress/returned/review/qa/approved and every id
in depends_on is done. Builds are serialized by a lock, so the queue is sequential by design.
"""
import argparse
import os
import re
import subprocess
import sys

import config
import pipeline_lib as pl
import run_task
from taskfile import TaskFile

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNABLE = ("ready", "in_progress", "returned", "review", "qa", "approved")


def live_task(path):
    """Task file as it is on its branch (if the branch exists), else the working-tree copy.
    A final status on the base copy (done/split) wins — the branch copy is history then."""
    tf = TaskFile(path)
    if tf.get("status") in config.FINAL_STATUSES:
        return tf
    branch = pl.task_branch(tf)
    if pl.branch_exists(branch) and pl.current_branch() != branch:
        r = pl.git("show", f"{branch}:{pl.rel(path)}", check=False)
        if r.returncode == 0:
            return TaskFile.from_text(r.stdout, path)
    return tf


def scan():
    rows = []
    for path in pl.task_files():
        tf = live_task(path)
        rows.append({"path": path, "id": tf.task_id(), "status": tf.get("status", "draft"),
                     "deps": tf.getlist("depends_on"), "role": tf.get("role", "developer"),
                     "size": tf.get("size", "M"), "returns": tf.get("returns", "0"),
                     "sessions": tf.get("sessions", "0"), "title": tf.get("title", "")})
    order = {tid: i for i, tid in enumerate(pl.backlog_order())}
    rows.sort(key=lambda r: (order.get(r["id"], 10_000), r["id"]))
    return rows


def runnable(rows):
    done = {r["id"] for r in rows if r["status"] in config.FINAL_STATUSES}
    for r in rows:
        if r["status"] in RUNNABLE and all(d in done for d in r["deps"]):
            return r
    return None


def unplanned_backlog(rows):
    have = {r["id"] for r in rows}
    return [tid for tid in pl.backlog_order() if tid not in have]


def plan():
    base = pl.backlog_active_base()
    if pl.current_branch() != base:
        pl.switch(base)
    subprocess.run([sys.executable, os.path.join(HERE, "run_agent.py"), "teamlead", "--mode", "plan"], cwd=config.ROOT, check=False)
    pl.autocommit("tasks: plan (driver auto-commit)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--continue-on-block", action="store_true")
    ap.add_argument("--max-tasks", type=int, default=50)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if not pl.is_clean():
        pl.die("working tree is dirty; commit or stash first")

    if a.list:
        for r in scan():
            print(f"{r['id']:>6}  {r['status']:<12} {r['role']:<15} {r['size']}  ret={r['returns']} ses={r['sessions']}  "
                  f"deps={','.join(r['deps']) or '-'}  {r['title']}")
        left = unplanned_backlog(scan())
        if left:
            print(f"backlog items without a task file: {', '.join(left)}")
        return 0

    ran, planned_once, skip = 0, False, set()
    while ran < a.max_tasks:
        base = pl.backlog_active_base()
        if pl.current_branch() != base:
            pl.switch(base)                      # scan from the base branch: newest planning lives there
        rows = [r for r in scan() if r["id"] not in skip]
        nxt = runnable(rows)
        if nxt is None:
            if a.plan and unplanned_backlog(rows) and not planned_once:
                planned_once = True
                pl.log("nothing runnable; planning the next backlog items")
                plan()
                continue
            waiting = [r["id"] for r in rows if r["status"] == "blocked"]
            pl.log("queue empty" + (f"; blocked: {', '.join(waiting)}" if waiting else ""))
            return 0
        planned_once = False
        ran += 1
        pl.log(f"=== task {nxt['id']} ({nxt['title']}) ===")
        rc = run_task.run_task(nxt["path"])
        if rc in (2, 3):
            if not a.continue_on_block:
                return rc
            skip.add(nxt["id"])
        if rc == 1:
            return 1
    pl.log(f"max tasks ({a.max_tasks}) reached")
    return 0


if __name__ == "__main__":
    sys.exit(main())
