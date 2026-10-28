---
id: NNNN
title: 
status: ready            # ready | dev | review | qa | approved | done | blocked | split
epic: p0                 # phase from the audit / backlog
prefix: p0
kind: code               # code | bug (tasks/bugs/BUG-<id>-<slug>.md, written by qa)
size: S                  # S | M | L — SIZE_CAPS in scripts/agents/config.py
role: developer          # developer | developer-hard
base: feat/p0-foundation # never main (ADR-0001)
branch: task/NNNN-slug
depends_on: []
allowed_paths:
  - 
checks: lua              # lua | kv | all | none — what check.sh runs
tests: []
needs_approval: false    # true if any path matches APPROVAL_RE or DoD has a [human] item
returns: 0
sessions: 0
blocked_reason: 
reviewed_sha: 
qa_sha: 
---

## Goal
One paragraph: what changes and why (link the audit section or ADR).

## Definition of Done
1. Verifiable items only: a command and its expected output, or a grep that must be empty.
2. Anything visible only in the game is `[human]` and makes needs_approval: true.

## Notes from teamlead
Pointers to files, pitfalls, what is out of scope.

## Handoff

## Result

## Review

## QA
