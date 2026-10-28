#!/usr/bin/env python3
"""PostToolUse hook for Bash | Edit | Write | MultiEdit.

Three jobs, all per session (state in logs/.loop-<session>.json, removed by session_end.py):
  1. strikes: 3 failed check.sh/test.sh runs in a row -> hard stop (guard_bash/guard_paths then
     allow only the task file, so the agent can write ## Handoff);
  2. loops: the same Edit/Write 4x or the same Bash 6x -> hard stop;
  3. turn budget: at 60% and 85% of AOH_MAX_TURNS tool calls, a reminder to wrap up cleanly
     (commit + ## Handoff) instead of being cut off mid-change by --max-turns.
Exit 2 = message to the model (the tool already ran). JSON additionalContext = soft reminder.
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aoh_hooklib as h  # noqa: E402

LIMIT_IDENTICAL = 4
LIMIT_FAILED = 3
CHECK_RE = re.compile(r"scripts/agents/(check|test)\.sh")
FAIL_RE = re.compile(r"(CHECK RESULT: FAIL|TEST RESULT: FAIL|Traceback \(most recent call last\)|exit code [1-9]|exit=[1-9])")
OK_RE = re.compile(r"(CHECK RESULT: OK|TEST RESULT: OK)")


def main():
    data = h.load()
    if h.role(data) == "human":
        sys.exit(0)
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    resp = data.get("tool_response")
    st = h.load_state(data)
    st["tool_calls"] = st.get("tool_calls", 0) + 1
    messages, soft = [], []

    key = hashlib.sha1((tool + json.dumps(ti, sort_keys=True)).encode()).hexdigest()[:16]
    st["calls"][key] = st["calls"].get(key, 0) + 1

    cmd = ti.get("command", "") if tool == "Bash" else ""
    is_check = bool(cmd and CHECK_RE.search(cmd))
    if is_check:
        text = resp if isinstance(resp, str) else json.dumps(resp, ensure_ascii=False) if resp is not None else ""
        if isinstance(resp, dict) and resp.get("exit_code") is not None:
            failed = resp["exit_code"] != 0
        elif OK_RE.search(text):
            failed = False
        else:
            failed = bool(FAIL_RE.search(text))
        st["failed"] = st.get("failed", 0) + 1 if failed else 0
        if st["failed"] >= LIMIT_FAILED:
            messages.append(f"STRIKES: {st['failed']} failed check/test runs in a row. "
                            "Stop now: commit what you have, write ## Handoff (what failed, what you tried, next idea), "
                            "set status: blocked, commit the task file, end. Do not run the checks again.")

    limit = LIMIT_IDENTICAL + (2 if tool == "Bash" else 0)
    if not is_check and st["calls"][key] >= limit:
        messages.append(f"LOOP: identical {tool} call repeated {st['calls'][key]} times. Change approach, or write ## Handoff and end.")

    try:
        max_turns = int(os.environ.get("AOH_MAX_TURNS", "0"))
    except ValueError:
        max_turns = 0
    if max_turns and not messages:
        n = st["tool_calls"]
        for pct in (60, 85):
            if n >= max_turns * pct // 100 and pct not in st.get("warned", []):
                st.setdefault("warned", []).append(pct)
                soft.append(f"Turn budget: {n} tool calls of ~{max_turns} turns used ({pct}%). If the task will not reach "
                            "`review` soon, wrap up now: commit, fill ## Handoff, keep status in_progress — the next session continues.")
                break

    h.save_state(data, st)
    if messages:
        with open(h.stop_file(data), "w", encoding="utf-8") as f:
            f.write(messages[0])
        sys.stderr.write("\n".join(messages) + "\n")
        sys.exit(2)
    if soft:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": soft[0]}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
