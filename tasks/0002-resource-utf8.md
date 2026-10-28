---
id: 0002
title: addon_russian.txt stays UTF-16LE BOM CRLF on disk, stored as UTF-8 in git via .gitattributes
status: ready
epic: p0
prefix: p0
kind: code
size: S
role: developer
base: feat/p0-foundation
branch: task/0002-resource-utf8
depends_on: []
allowed_paths:
  - .gitattributes
  - tools/normalize_text.py
  - game/dota_addons/attackcopy/resource/addon_russian.txt
  - tasks/backlog.md
checks: none
tests: []
needs_approval: true
returns: 0
sessions: 2
blocked_reason:
reviewed_sha: 707f9ca88cbb8954a742bd9854f0011c0946b280
qa_sha: 707f9ca88cbb8954a742bd9854f0011c0946b280
---

## Goal
The bytes of addon_russian.txt on disk stay exactly as they are on the base branch
(UTF-16LE, BOM, CRLF), because nobody has confirmed that Dota reads a UTF-8 file. Git stores
the file as UTF-8 with LF through `.gitattributes` `working-tree-encoding`, so `git diff`,
`git show` and `grep` on blobs work. The round-1 UTF-8 conversion and tools/normalize_text.py
are reverted.

## Definition of Done
P = `game/dota_addons/attackcopy/resource/addon_russian.txt`
1. `grep -c -x 'game/dota_addons/attackcopy/resource/addon_russian.txt text working-tree-encoding=UTF-16LE-BOM eol=crlf' .gitattributes` → `1`.
2. `git ls-files --eol -- P` → `i/lf    w/-text attr/text eol=crlf` followed by P (blob is LF text; the UTF-16 working file is not text to git; the attribute applies).
3. `wc -c P` → `691310` (the same size as the base blob, see Notes). Byte identity is DoD 9a ([human]).
4. `git status --short` → empty after the final commit (the clean filter round-trips the on-disk file to the committed blob).
5. `git show HEAD:P | head -c 10` → `    "lang"` (4 spaces + `"lang"`, readable UTF-8 in the blob). `git show HEAD:P | grep -c -E '^\s*"[^"]+"\s+"'` → `2626`.
6. (moved to 9b — fresh clone needs commands the agent sandbox denies.)
7. `ls tools/normalize_text.py` → `No such file or directory`.
8. `git diff --stat feat/p0-foundation...HEAD` lists only `.gitattributes`, `P` and this task file. The round-1 "Found by agents" line about wiring `normalize_text.py --check` is gone from tasks/backlog.md. P changes from a binary to a text blob, which is expected once.
9a. [human] Owner: `git check-attr text working-tree-encoding eol -- P` → `P: text: set`, `P: working-tree-encoding: UTF-16LE-BOM`, `P: eol: crlf`; `git hash-object --no-filters P` → `c7571a0b60f7079ea7ee46eb9b1f09238da03bd9` (= `git rev-parse feat/p0-foundation:P`).
9b. [human] Owner: `git clone --quiet --branch task/0002-resource-utf8 . logs/0002-clone`, then `git hash-object --no-filters logs/0002-clone/P` → `c7571a0b60f7079ea7ee46eb9b1f09238da03bd9`.
9. [human] Owner: fresh clone of the merged base → `cmp` the clone's P against `git show <old-base-sha>:P` saved by the owner → no output. Dota with language Russian still shows Russian tooltips; this is a regression check only, because the bytes did not change.

## Notes from teamlead
- Re-spec 2026-10-28 (unblock, round 3): the product work is done (owner commits 707f9ca + a3aa8c6, review APPROVE). The only blocker was that the agent sandbox denies `git check-attr`, `git hash-object` and `git clone`. Old DoD 2, 3 and 6 are now owner checks 9a/9b (the owner must approve anyway: needs_approval). New DoD 2 and 3 use commands qa already ran in round 2 (`git ls-files --eol`, `wc -c`). Developer: change no code; run DoD 1-5, 7, 8, write a round-3 line on top of ## Result, set review. Reviewer/qa: do not FAIL for 9a/9b; list them under "For the human". Do not run `scripts/agents/check.sh none` (checks: none means skip; the script has no `none` mode).
- Base blob facts for 9a/9b: `feat/p0-foundation:P` = c7571a0b60f7079ea7ee46eb9b1f09238da03bd9, 691310 bytes.
- Re-spec 2026-10-28 by owner decision (blocked_reason): keep UTF-16LE BOM CRLF on disk because Dota's UTF-8 support is unverified and has no source. Store UTF-8 in git. Revert the conversion and drop the tool. Round 1 (commit 6eb99bd, review af53388 APPROVE, qa dd303a4 PASS) did the opposite; those verdicts are void and their sections are cleared below.
- The branch still contains 6eb99bd (UTF-8 P + tools/normalize_text.py + backlog line). Do the steps in this order. The order matters because the attribute changes how git reads and writes P:
  1. `git restore --source=feat/p0-foundation -- P`. Do this **before** .gitattributes exists, so the raw UTF-16 bytes land on disk. Confirm with DoD 3.
  2. `git rm tools/normalize_text.py`. Remove the round-1 backlog line with Edit.
  3. Write `.gitattributes` with exactly one line (DoD 1). Do not use other patterns or a global `* text=auto`. english/schinese are already UTF-8 LF and must not be touched.
  4. `git add --renormalize P`, then `git add .gitattributes tasks/backlog.md`, then commit `p0: keep addon_russian.txt UTF-16 on disk, UTF-8 in git`.
  5. Run DoD 3–6.
- If DoD 2 does not report the encoding, or step 4 errors about the encoding, git does not support `UTF-16LE-BOM`. Do not improvise with `UTF-16`, which writes a BE BOM, or with another tool. Write a Handoff and set status: blocked.
- Base file facts: 3142 lines, all CRLF (round 1 counted crlf=3142), BOM `FF FE`, 2626 key lines. That makes the round trip exact.
- Do not edit any string content. checks: none, because kvcheck does not read resource/.
- needs_approval: owner fresh-checkout test (DoD 9) and deletion of tools/normalize_text.py.

## Handoff
Session 2: the repo already holds the round-2 work (owner-made 707f9ca + a3aa8c6: P bytes restored, .gitattributes, tool and backlog line removed). I changed no code. Review is APPROVE; QA is FAIL only because DoD 2, 3 and 6 could not be run.
Ran in session 2: `git rev-parse feat/p0-foundation:P` → c7571a0b60f7079ea7ee46eb9b1f09238da03bd9 (allowed); `git status --short` → empty (allowed).
Denied again in session 2: `git check-attr …` (DoD 2) and `git hash-object --no-filters P` (DoD 3). I did not try the clone (DoD 6), because it depends on DoD 3.
Next: the owner runs DoD 2, 3 and 6 (the hash must be c7571a0b…), or allows `git check-attr`, `git hash-object` and `git clone` for the next session. Nothing suggests a product defect.
Earlier note (session 1): Bash commands were all denied.
Failed: `git restore --source=feat/p0-foundation -- P` (step 1) and `git rm tools/normalize_text.py` (step 2) were both denied. Grep is not available either.
Tried: no other route. The task needs git restore, rm, add --renormalize and commit, and the Write/Edit tools cannot do these. Writing UTF-16LE bytes with Write is not possible.
Next idea: the owner allows `git restore`, `git rm`, `git add` and `git commit` (and `git check-attr`, `git hash-object`, `git clone`) for this task, then the next session runs steps 1-5 in the order given in Notes.

## Result
Round 2: owner restored the UTF-16LE BOM CRLF bytes of P, added the single `.gitattributes` line and removed tools/normalize_text.py and the round-1 backlog line (707f9ca, a3aa8c6). Session 2 changed no code. Verified by me: `git status --short` empty; base blob id is c7571a0b60f7079ea7ee46eb9b1f09238da03bd9. Not verified (Bash denied): DoD 2, 3, 6. Owner playtest: DoD 9 (Russian tooltips still show).

Round 1 (superseded by the re-spec): converted P to UTF-8/LF with tools/normalize_text.py, commit 6eb99bd. The owner rejected it; see Notes.

## Review
APPROVE

Round 2 (code head 707f9ca, owner-made commits 707f9ca + a3aa8c6).
Checklist:
1. Spec: matches the re-spec. `.gitattributes` has exactly the single DoD-1 line (no global patterns). tools/normalize_text.py was deleted in 707f9ca. The round-1 backlog line was removed, so tasks/backlog.md equals base and is absent from the diff. HEAD:P is a UTF-8 blob: `head -c 10` gives `    "lang"` and the key-line count is 2626 (DoD 5, I ran both). HEAD:P is the same blob as 6eb99bd:P (c52a357), which is the renormalized form of the base text, so no string content changed. On-disk P is 691310 bytes, the same size as the base blob (diff stat `Bin 691310 -> …`). `git status --short` is empty (DoD 4). Both together strongly indicate the UTF-16LE-BOM CRLF bytes are restored (DoD 3).
2. Scope: the diff vs base touches only `.gitattributes`, P and the task file (DoD 8). english/schinese are untouched.
3. Conventions: n/a (no Lua/KV). aoh_lint: 0 fail, 0 warn, NEEDS APPROVAL (expected: needs_approval + [human] DoD 9).
4. Dota correctness: n/a. The on-disk bytes Dota reads are unchanged.
5. KV: n/a (checks: none; kvcheck does not read resource/).
6. Verification: ## Result has no round-2 entry, so it makes no claims to verify. I could not run `git check-attr` (DoD 2), `git hash-object --no-filters` (DoD 3) or the clone (DoD 6): Bash denied them in this session. qa should run DoD 2, 3 and 6 directly. DoD 9 stays with the owner.
7. Hygiene: clean.

Non-blocking notes (no return needed):
1. tasks/0002-resource-utf8.md:60-67: ## Handoff still says "nothing in the repo changed", and ## Result has only the round-1 line. Round 2 was done by the owner, so nobody wrote a Result. The owner or qa may want to add one line on top of ## Result, for example "Round 2: owner restored P bytes, added .gitattributes, removed tools/normalize_text.py (707f9ca)".

## QA
Round 2 (superseded by the round-3 re-spec; old DoD numbering): FAIL (not verifiable in this session: DoD 2, 3 and 6 were denied by the Bash permission mode, so I cannot approve)

Verified:
1. DoD 1: grep -c -x → 1. OK.
2. DoD 4: `git status --short` is empty. OK.
3. DoD 5 (first half): `git show HEAD:P | head -c 10` → `    "lang"`. OK. I did not run the 2626 key-line count.
4. DoD 7: tools/normalize_text.py does not exist. OK.
5. DoD 8: `git diff --stat feat/p0-foundation...HEAD` lists only .gitattributes, P (Bin 691310 -> 442721) and the task file. OK.
6. Indirect evidence for DoD 3: on-disk P is 691310 bytes, equal to the base blob size. `git ls-files --eol` shows `i/lf w/-text attr/text eol=crlf`. This is not the literal check.

Not verified (blocked):
7. DoD 2: `git check-attr text working-tree-encoding eol -- P` was denied.
8. DoD 3: `git hash-object --no-filters P` was denied. The base blob id is c7571a0b60f7079ea7ee46eb9b1f09238da03bd9, so compare against it.
9. DoD 6: the fresh clone was not attempted because the DoD 3 commands were denied.
10. Check/test: `scripts/agents/check.sh none` exits with "unknown argument: none". checks is none, so I skipped it.

Repro: run the DoD 2, 3 and 6 commands in a session that allows them. Expected: the id matches c7571a0b…; actual: the commands are denied. Nothing suggests a product defect.

Non-blocking: ## Handoff and ## Result still describe round 1 and a failed session; add a round-2 line.

For the human:
- DoD 9: fresh clone of the merged base, `cmp` the clone's P against `git show <old-base-sha>:P` saved earlier → no output. Dota with language Russian still shows Russian tooltips.
- Run DoD 2, 3 and 6 yourself (or allow them) and approve if the hash is c7571a0b60f7079ea7ee46eb9b1f09238da03bd9.
