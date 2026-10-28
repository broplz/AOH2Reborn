#!/usr/bin/env python3
"""The daily report, for free: task states, spend per task/role, what needs the human.

    report.py [--days N] [--write]     --write also saves docs/reports/daily-<date>.md (≤ 40 lines)
"""
import argparse
import datetime
import json
import os
import sys
from collections import defaultdict

import config
import pipeline_lib as pl
import run_queue


def sessions(days):
    path = os.path.join(config.LOG_DIR, "agent-sessions.jsonl")
    since = datetime.datetime.now() - datetime.timedelta(days=days)
    rows = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if datetime.datetime.strptime(r["ts"], "%Y-%m-%d %H:%M:%S") >= since:
                    rows.append(r)
    except OSError:
        pass
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    out = [f"# AOH2 pipeline report — {datetime.date.today()} (last {a.days} day(s))", ""]
    rows = run_queue.scan()
    by_status = defaultdict(list)
    for r in rows:
        by_status[r["status"]].append(f"{r['id']}" + (f"(ret {r['returns']})" if r["returns"] not in ("0", "") else ""))
    out.append("## Tasks")
    for st in ("done", "approved", "qa", "review", "in_progress", "returned", "ready", "blocked", "split", "draft"):
        if by_status.get(st):
            out.append(f"- {st}: {', '.join(by_status[st])}")
    left = run_queue.unplanned_backlog(rows)
    if left:
        out.append(f"- backlog without task files: {', '.join(left)}")

    ses = sessions(a.days)
    cost_role, cost_task, n_role = defaultdict(float), defaultdict(float), defaultdict(int)
    for s in ses:
        cost_role[s["role"]] += s.get("cost_usd", 0) or 0
        cost_task[s["task"]] += s.get("cost_usd", 0) or 0
        n_role[s["role"]] += 1
    total = sum(cost_role.values())
    out += ["", f"## Spend: ${total:.2f} in {len(ses)} sessions"]
    for role, c in sorted(cost_role.items(), key=lambda kv: -kv[1]):
        out.append(f"- {role}: ${c:.2f} ({n_role[role]} sessions, ${c / max(n_role[role], 1):.2f} avg)")
    top = sorted(cost_task.items(), key=lambda kv: -kv[1])[:5]
    if top:
        out.append("- top tasks: " + ", ".join(f"{t} ${c:.2f}" for t, c in top))
    errs = [s for s in ses if s.get("subtype") not in ("success", None)]
    if errs:
        out.append("- sessions that did not end normally: " + ", ".join(f"{s['task']}/{s['role']}:{s['subtype']}" for s in errs[:8]))

    out += ["", "## Needs you"]
    att = os.path.join(config.LOG_DIR, "ATTENTION.md")
    try:
        with open(att, encoding="utf-8") as f:
            lines = [l.rstrip() for l in f if l.strip()][-6:]
        out += lines or ["- nothing"]
    except OSError:
        out.append("- nothing")
    try:
        with open(config.DECISIONS, encoding="utf-8") as f:
            pending = [l.rstrip() for l in f if l.startswith("- ")]
        if pending:
            out.append(f"- decisions-needed.md: {len(pending)} open line(s); first: {pending[0][:100]}")
    except OSError:
        pass

    text = "\n".join(out[:40])
    print(text)
    if a.write:
        d = os.path.join(config.ROOT, "docs", "reports")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"daily-{datetime.date.today()}.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"\nwritten: {pl.rel(p)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
