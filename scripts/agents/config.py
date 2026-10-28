"""Pipeline constants. Models and effort live in .claude/agents/<role>.md; here are the
per-run limits the driver passes to `claude -p` and the loop policy. Override any
value with an environment variable of the same name prefixed AOH_ (e.g. AOH_MAX_RETURNS=2).
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOG_DIR = os.environ.get("AOH_LOG_DIR", os.path.join(ROOT, "logs"))
TASK_DIR = os.path.join(ROOT, "tasks")
BACKLOG = os.path.join(TASK_DIR, "backlog.md")
APPROVALS = os.path.join(TASK_DIR, "approvals.txt")
DECISIONS = os.path.join(ROOT, "docs", "reports", "decisions-needed.md")
SKILLS_DIR = os.path.join(ROOT, ".claude", "skills")

DEV_ROLES = ("developer", "developer-hard")

# `claude -p --max-turns` per role; developer roles scale with the task size.
# There is no 40-minute build here, so sessions are shorter than on BB.
# NB: the CLI caps agentic rounds; RESULT num_turns also counts parallel tool calls, so logged
# turns can exceed this with subtype=success (aws/aws-durable-execution-ci#70, claude-code-action#1795).
MAX_TURNS = {
    "developer": {"S": 25, "M": 40, "L": 55},
    "developer-hard": {"S": 30, "M": 50, "L": 70},
    "reviewer": 15,
    "qa": 25,
    "teamlead": 30,
}

# `--max-budget-usd` per session: a runaway stop, not a target. Claude Code may overshoot it
# by a turn. Starting values copied from BB; tune after the first 10 tasks (report.py).
MAX_BUDGET_USD = {
    "developer": {"S": 1.0, "M": 2.0, "L": 4.0},
    "developer-hard": {"S": 2.0, "M": 4.0, "L": 8.0},
    "reviewer": 1.5,
    "qa": 1.5,
    "teamlead": 3.0,
}

# Shared rule-sets injected into the system prompt per role (order matters; frontmatter stripped).
SKILLS = {
    "developer": ["aoh-task", "aoh-rules", "aoh-check"],
    "developer-hard": ["aoh-task", "aoh-rules", "aoh-check"],
    "reviewer": ["aoh-task", "aoh-rules"],
    "qa": ["aoh-task", "aoh-check"],
    "teamlead": ["aoh-task", "aoh-rules"],
}

# Loop policy
MAX_RETURNS = int(os.environ.get("AOH_MAX_RETURNS", "3"))        # review/QA returns before blocked
MAX_SESSIONS = int(os.environ.get("AOH_MAX_SESSIONS", "3"))      # developer sessions before blocked:too_big
MAX_LOOP_STEPS = int(os.environ.get("AOH_MAX_LOOP_STEPS", "14"))  # safety cap on role runs per run_task
AUTO_UNBLOCK = os.environ.get("AOH_AUTO_UNBLOCK", "1") == "1"    # run teamlead once on blocked
SESSION_TIMEOUT_S = int(os.environ.get("AOH_SESSION_TIMEOUT_S", str(2 * 3600)))
PUSH_TIMEOUT_S = int(os.environ.get("AOH_PUSH_TIMEOUT_S", "180"))
PLAN_BATCH = int(os.environ.get("AOH_PLAN_BATCH", "3"))          # tasks per teamlead planning run

# Size caps the teamlead must respect (production lines of diff, files touched)
SIZE_CAPS = {"S": (150, 5), "M": (300, 10), "L": (500, 15)}

# Paths whose change always needs the owner's approval before the merge (ADR-0001 §3):
# the game-mode core and anything that changes what players can buy or how bosses are scheduled.
APPROVAL_RE = (r"vscripts/(aohgamemode|aohgameround|aohspawner|dashmanager)\.lua$|"
               r"vscripts/modifiers/modifier_(boss|main_boss)\.lua$|vscripts/abilities/other/generic\.lua$|"
               r"scripts/(shops|config)/|scripts/npc/(herolist|npc_heroes_custom)\.txt$")

FINAL_STATUSES = ("done", "split")
STOP_STATUSES = ("blocked",)


def turns_for(role: str, size: str) -> int:
    v = MAX_TURNS.get(role, 25)
    return v.get(size.upper(), v.get("M")) if isinstance(v, dict) else v


def budget_for(role: str, size: str) -> float:
    v = MAX_BUDGET_USD.get(role, 1.0)
    return v.get(size.upper(), v.get("M")) if isinstance(v, dict) else v
