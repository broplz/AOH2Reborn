#!/usr/bin/env python3
"""PreToolUse hook for Bash.

Blocks destructive git/shell for everyone (AOH_UNLOCK=1 overrides), and for agents: shell-side
file writes (Write/Edit only, so guard_paths sees them), direct luacheck/stylua/lua runs
(check.sh/test.sh only — they log and triage), raw logs, branch switching/merging/pushing (the
driver's job), network, and role-gated commands. Exit 2 blocks; stderr reaches the model.

Patterns are matched against the command with quoted strings blanked out, and word-level
patterns are anchored to a command position (start or after a pipe) so that a word inside an
argument — a file called `surfer.json`, a grep for "curl" — never trips them.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aoh_hooklib as h  # noqa: E402

CMD = r"(?:^|\|)\s*"       # start of a (sub)command: beginning of line or right after a pipe

ALWAYS_BLOCK = [
    (r"\bgit\s+push\b[^|;&]*(\s--force(?!-with-lease)\b|\s-f\b)", "force push without lease"),
    (r"\bgit\s+reset\s+--hard", "git reset --hard"),
    (r"\bgit\s+clean\b", "git clean"),
    (r"\bgit\s+branch\s+-D\b", "force branch delete"),
    (r"\bgit\s+config\s+--global", "global git config"),
    (CMD + r"rm\s+-[a-zA-Z]*[rR]", "recursive rm"),
    (CMD + r"sudo\b", "sudo"),
    (CMD + r"(brew|pip3?|cargo|gem|luarocks)\s+(install|uninstall|remove)\b|" + CMD + r"npm\s+(i|install|ci|uninstall|update)\b",
     "package install (ask via tasks/backlog.md)"),
    (r"\bchmod\s+-R", "recursive chmod"),
    (r">\s*\S*(\.env|secret)", "writing secrets"),
    (r"(^|[;&|]\s*)claude\b", "nested claude sessions"),
]
# Agents: raw command (before quote stripping) — substitutions hide inside quotes.
AGENT_RAW_BLOCK = [
    (r"\$\(|`", "command substitution — one plain command per Bash call"),
    (r"\$\{?[A-Za-z_?#@*0-9]", "shell variables — write literal values"),
    (r"<<", "heredocs — create files with the Write tool"),
]
AGENT_ONLY_BLOCK = [
    (r"(;|&&|\|\|)", "command chaining — one command per Bash call"),
    (r"\|(?!\s*(tail|head|grep|wc|sort|uniq|cut|cat)\b)", "pipes only into tail/head/grep/wc/sort/uniq/cut"),
    (r"(?<![0-9&<])>>?(?!\s*/dev/null)", "redirect into a file — use the Write/Edit tools"),
    (CMD + r"tee\b", "tee (scripts already log into logs/)"),
    (CMD + r"sed\s+-[a-zA-Z]*i", "in-place sed — use the Edit tool"),
    (CMD + r"(perl|ruby)\s+-[a-zA-Z]*[pie]\b", "in-place one-liners — use the Edit tool"),
    (CMD + r"python3?\s+-c\b", "python -c — use Write/Edit or a script under tools/"),
    (CMD + r"(cp|mv|ln|install|truncate|dd|rsync)\b", "copy/move from shell — use Write/Edit"),
    (CMD + r"(bash|sh|zsh)\s+-c\b|\beval\b|" + CMD + r"source\b|\bxargs\b", "sub-shells/eval — one plain command per call"),
    (r"(^|\s)cd\s", "cd — run everything from the repo root"),
    (r"\bgit\s+-C\b", "git -C — run git from the repo root"),
    (r"\bgit\s+(switch|checkout|merge|rebase|push|pull|fetch|stash|worktree|cherry-pick|revert|reset)\b",
     "git branch/remote operations are the driver's job (scripts/agents/run_task.py)"),
    (CMD + r"(luacheck|stylua|lua5?\.?1?|luajit|busted)\b", "direct luacheck/stylua/lua — use scripts/agents/check.sh and test.sh (log + triage)"),
    (CMD + r"(cat|head|less|more|bat)\s+[^|]*\.log\b", "raw log — python3 scripts/agents/triage_log.py <log> (or tail -n 40)"),
    (CMD + r"tail\s+(-n\s*|-)?(\d{3,})\b[^|]*\.log\b", "tail of a log over 99 lines — use triage_log.py"),
    (CMD + r"(cat|head|tail|less|more|bat)\s+[^|]*npc_[a-z_]+\.txt\b", "KV files are 10-20k lines — Grep with head_limit, then Read with offset/limit"),
    (CMD + r"(curl|wget|nc|ssh|scp|rsync)\b", "network from the shell (tools/vanilla_snapshot.py is the one allowed fetch; the owner runs it)"),
    (CMD + r"(open|osascript|xdg-open)\b", "GUI from the shell"),
    (CMD + r"(dota2|hammer|resourcecompiler|steam)\b", "the game and its tools cannot run here — [human] items are for the owner"),
]
ROLE_GATED = [
    (r"scripts/agents/check\.sh\b", {"developer", "developer-hard", "qa"}, "running checks"),
    (r"scripts/agents/test\.sh\b", {"developer", "developer-hard", "qa"}, "running tests"),
    (r"tools/vanilla_snapshot\.py\b", set(), "refreshing the vanilla snapshot (network; the owner runs it)"),
    (r"scripts/agents/(run_task|run_queue|run_agent|merge_task|finish_feature|new_feature)\b", set(), "driver scripts"),
]
QUOTED = re.compile(r'"(?:\\.|[^"\\])*"|\'[^\']*\'')


def main():
    if h.unlocked():
        sys.exit(0)
    data = h.load()
    raw = (data.get("tool_input") or {}).get("command") or ""
    if not raw:
        sys.exit(0)
    if os.path.exists(h.stop_file(data)):
        h.block("session is stopped (strikes/loop). No more commands: write ## Handoff in the task file, set status: blocked, commit with the Edit tool only, and end.")
    short = raw.strip().replace("\n", " ")[:140]
    cmd = QUOTED.sub('""', raw)
    for pattern, why in ALWAYS_BLOCK:
        if re.search(pattern, cmd):
            h.block(f"{why}: `{short}`")
    role = h.role(data)
    if role == "human":
        sys.exit(0)
    for pattern, why in AGENT_RAW_BLOCK:
        if re.search(pattern, raw):
            h.block(f"{why}: `{short}`")
    for pattern, why in AGENT_ONLY_BLOCK:
        if re.search(pattern, cmd):
            h.block(f"{why}: `{short}`")
    for pattern, roles, why in ROLE_GATED:
        if re.search(pattern, cmd) and role not in roles:
            h.block(f"{why}; role '{role}' may not run `{short}`")
    sys.exit(0)


if __name__ == "__main__":
    main()
