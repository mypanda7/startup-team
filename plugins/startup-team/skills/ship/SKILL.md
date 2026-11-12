---
name: ship
description: Take ONE finished, QA-passed and audited branch live - notes, lint gate, push, pull request, CI watch, merge, deploy watch, live check, sync back. Use when the owner says to ship a branch that is done. For an end-of-session checkpoint to the integration branch use `wrap`; for an urgent production fix use `hotfix`; for the scheduled release use `release-train`.
disable-model-invocation: true
---

# Ship (one finished branch, to live)

The method for the main session and `devops`. It never weakens the chain: nothing ships before
`qa` and the `auditor`'s PASS, and every push, pull request, merge, tag and deploy goes through
`devops` PROPOSE and the owner's 1. Asking for "ship" starts this skill; it is not the 1 for its
steps. Each write boundary (push and pull request, merge, deploy) is its own proposal, unless the
project's CLAUDE.md says one approval covers a named sequence.

## The project must say (in its CLAUDE.md)
- The branch that is live, the integration branch if there is one, and which merge deploys.
- Where durable notes live and what earns a note.
- The lint or format gate CI runs, and the command that runs the SAME pinned version locally.
- The merge method per branch (merge commit or squash) and any protected-branch rule.
- How a deploy is watched and what proves it worked (health checks, a version marker).
- Any tracker convention: which words in a branch, title, body or commit move a card.
If one of these is missing, `devops` ANALYSE finds what the repository shows and the gap goes to
the owner as a question. Never guess a branch or a deploy path.

## 0. Preflight (read-only)
- Branch state: what is on the branch that the target lacks, and nothing uncommitted. Uncommitted
  work is the owner's call. Never commit it silently.
- Confirm the turn has the QA record and the auditor's PASS for exactly this commit. A new commit
  after the PASS reopens QA and the audit for what changed.

## 1. Notes (blocking, before the push)
Review the branch diff and record what is note-worthy where the project keeps notes:
- a root-cause fix for a non-obvious bug: the invariant;
- a constraint, race or trap that took more than one look to understand;
- a design decision or named convention: the why.
Read the target note's section in full before appending, so you do not duplicate or contradict it.
Commit the note on the same branch so the why ships with the what. Skip only after a real review
found nothing, and say so with what you reviewed. "It is already in a plan or in memory" is not a
reason to skip. Do not record generic patterns, task state or what the diff already says.

## 2. The pinned lint gate (blocking, before the push)
Run the gate at the version CI pins, after the LAST commit, not from memory of an earlier pass.
- A newer local linter is not the gate: rules and import ordering drift between versions.
- "Tool not installed, skipped" with exit 0 is not a pass.
- Hooks that auto-fix rewrite files: commit the fix-ups and run again until clean.
- A gate that reports "no changed files" has verified nothing.

## 3. Push and pull request (`devops` PROPOSE, the owner's 1)
- Base the pull request on the branch CI actually watches. A pull request stacked on another
  feature branch often gets NO checks at all: that is unverified, not green. Retarget it to a
  watched base first, confirm the base by reading it back, and re-trigger the checks.
- A pull request with no checks may be a conflicting one: check mergeability before waiting.
- Body: Summary, Verification (what ran, where, what it proved, what was NOT covered).
- Tracker references are commands, not citations. If the project's tracker reacts to ids in a
  branch name, title, body or commit message, a docs-only change must carry none, and a mention
  that only describes a task must be written so it does not match.
- If the branch fixes a logged issue, fold its log entry into this same pull request.

## 4. Watch CI
- First ask whether CI ran at all. A run that fails in seconds with no step logs was refused
  (quota, billing, a missing runner): that is not a result. Tell the owner; do not wait on a green
  that cannot come, and do not treat it as red code.
- Watch by identity: poll until every named check is completed, then read each conclusion. An
  empty or filtered output is not green.
- A green check does not say how much ran. If the project scopes tests by diff, say which scope
  ran; a diff-scoped run cannot see blast radius (wiring files, schema, permissions, anything every
  request passes through). Ask for the full scope when the change is of that kind.
- Real failure (logs present): show the failing job and the first error line and stop. Verify a
  red in isolation before claiming or disclaiming it (see `test-gate`).

## 5. Merge (`devops` PROPOSE, the owner's 1)
- Merge only after reading green conclusions for the CURRENT head commit. An admin or bypass merge
  also walks past red, running and cancelled checks: use it only when the owner approves that
  exact bypass, and say in the report that it was used and why.
- If CI could not run, the proposal says so, lists the local evidence instead, and the owner
  decides.
- Verify by state, not exit code: the pull request reads merged and the target branch contains
  the commit.
- Do not delete a branch other pull requests are stacked on.

## 6. Deploy watch and live check
- A merge to a branch that auto-deploys is a deploy. Watch it to the end.
- If the automatic deploy cannot run, the fallback is the `deploy` skill, as a new proposal.
- Health checks prove the host is up, not that the change is live. Check the served version
  marker and look at one user-visible effect of the change.
- If background workers or scheduled jobs run the changed code, confirm they were restarted.
- Space two merges that both migrate: back-to-back deploys can collide on a migration lock.

## 7. Sync back and close
- If the project has an integration branch, it must never fall behind the live branch: propose
  the sync through `devops` the same session.
- Report: what merged, the deploy path taken, what was verified live, what was not, sync done or
  pending. Then the release records the project keeps (`release-notes`, `announcement`).

## Guard rails
- Never force-push, never skip hooks, never amend a published commit.
- Never merge on a real failure. Never report a refused run as green or as red.
- If a step fails unexpectedly, stop and report. Do not improvise recovery.
