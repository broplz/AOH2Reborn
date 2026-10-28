#!/usr/bin/env python3
"""Stop / SubagentStop hook.

1. Anti-early-quit (agents only, at most 2 nudges per session): a developer may not end with the
   task still `in_progress` and no ## Handoff; a reviewer/qa may not end without a verdict.
   Blocking a stop returns {"decision":"block","reason":...} — Claude continues with the reason.
2. Writes one line per session to logs/agent-sessions.log and removes the loop-detector state.
   Token counts come from the transcript; a streamed assistant message appears there several
   times with the same message id (partial, then final), so usage is taken once per message id —
   the last record wins. Never fails the session.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aoh_hooklib as h  # noqa: E402

MAX_NUDGES = 2


def nudge(data, st, reason):
    st["nudges"] = st.get("nudges", 0) + 1
    h.save_state(data, st)
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def transcript_tokens(path):
    per_msg = {}
    try:
        with open(path, encoding="utf-8") as f:
            for n, line in enumerate(f):
                try:
                    rec = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                msg = rec.get("message") or {}
                usage = msg.get("usage") or {}
                if not usage:
                    continue
                key = msg.get("id") or rec.get("uuid") or f"line{n}"
                per_msg[key] = usage          # last record for a message id wins
    except OSError:
        pass
    tok = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}
    for usage in per_msg.values():
        tok["in"] += usage.get("input_tokens", 0) or 0
        tok["out"] += usage.get("output_tokens", 0) or 0
        tok["cache_read"] += usage.get("cache_read_input_tokens", 0) or 0
        tok["cache_write"] += usage.get("cache_creation_input_tokens", 0) or 0
    return tok


def main():
    data = h.load()
    role = h.role(data)
    st = h.load_state(data)
    stopped = os.path.exists(h.stop_file(data))
    task = h.read_task(data)

    if role != "human" and task and not stopped and st.get("nudges", 0) < MAX_NUDGES and data.get("hook_event_name") == "Stop":
        status = task.get("status", "")
        if role in ("developer", "developer-hard") and status in ("in_progress", "ready", "returned") and not task.section("Handoff"):
            nudge(data, st, "The task is not finished: status is still `" + status + "` and ## Handoff is empty. Either continue "
                  "the work, or commit what you have, fill ## Handoff (done / failed / tried / next idea), "
                  "set status (`blocked` if stuck, `in_progress` if just out of budget), commit the task file, then end.")
        if role == "reviewer" and task.verdict("Review") == "NONE":
            nudge(data, st, "## Review has no verdict yet. Write APPROVE or REQUEST_CHANGES with numbered items, "
                  "set status, commit the task file, then end.")
        if role == "qa" and task.verdict("QA") == "NONE":
            nudge(data, st, "## QA has no verdict yet. Write PASS or FAIL with numbered items (repro + log path), "
                  "set status, commit the task file, then end.")

    tok = transcript_tokens(data.get("transcript_path", ""))
    logs = h.logs_dir(data)
    sid = data.get("session_id", "")
    line = (f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} event={data.get('hook_event_name', '')} role={role} "
            f"task={os.environ.get('AOH_TASK', '-')} session={sid} tool_calls={st.get('tool_calls', 0)} "
            f"nudges={st.get('nudges', 0)} stopped={int(stopped)} tokens in={tok['in']} out={tok['out']} "
            f"cache_read={tok['cache_read']} cache_write={tok['cache_write']}\n")
    with open(os.path.join(logs, "agent-sessions.log"), "a", encoding="utf-8") as f:
        f.write(line)
    for leftover in (f".loop-{sid}.json", f".stop-{sid}"):
        try:
            os.remove(os.path.join(logs, leftover))
        except OSError:
            pass
    sys.exit(0)


if __name__ == "__main__":
    main()
