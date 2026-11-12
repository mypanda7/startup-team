---
name: wrap
description: End-of-session checkpoint - update the project notes, commit what is pending, and get the session's work onto the integration branch through a pull request, without touching the live branch or deploying. Use when the owner says to wrap up, park the work or close the session. To take a finished branch live use `ship`.
---

# Wrap (end of session, to the integration branch)

For the main session. A wrap parks progress; it does not release. Every push, pull request and
merge goes through `devops` PROPOSE and the owner's 1. Work that was built this turn still passes
`qa` and the `auditor` before it merges; a wrap of unfinished work says plainly that it is
unfinished and stops at the pull request.

## The project must say (in its CLAUDE.md)
- The integration branch (and that the live branch is a different one), or that there is none.
- Where durable notes live, and where the carry-over for the next session is written.
- The pinned lint gate and how to run it locally.
- What the integration branch's CI does and does NOT run.
- The merge method for the integration branch.
If the project has no integration branch, a wrap ends at local commits plus a proposal to push the
feature branch. It never merges to the live branch: that is `ship`.

## Before the session's first code (three habits that cannot be fixed afterwards)
- **Base the work on the integration branch.** A branch cut from the live branch pays the release
  price (the full gate) for every small change. Keep that base for a real hotfix.
- **Queue, do not race.** Where test hosts are shared, submit runs the way the project's CLAUDE.md
  names. Never start a run that swaps code under a run already in flight.
- **Front-load the decisions.** List the judgment calls the work will raise (scope edges, bad data
  found on the way, the neighbouring case, destructive clean-ups) and put them to the owner before
  building. A late "also do X" is another push and another full check round. Findings that could
  not be foreseen are held and bundled, not pushed one by one.

## 1. Notes
Review the session's diff and the conversation. Record root causes, non-obvious invariants,
decisions and hard-won traps in the project's notes. Read the target section in full first. Do not
record generic patterns, task state, brittle paths or what the diff already says. If nothing
qualifies, say so: a silent omission and a considered one look the same afterwards.

## 2. Commit what is pending (local)
- Stage files by name, never everything at once. Leave out anything that looks like a secret.
- One focused message that says why. Never amend a published commit; a failed hook gets a new
  commit.
- Never open the pull request from the integration branch itself: if the session's commits sit on
  it locally, move them to a named branch first.
- Run the pinned lint gate AFTER the last commit. A pass from before late files were added proves
  nothing about them.

## 3. Push and pull request to the integration branch (`devops` PROPOSE, the owner's 1)
The body covers ALL of the session's progress, because it becomes the merge record: Summary
(grouped: code, notes, tooling, and why) and Verification (what ran, what it proved, what was NOT
covered). Name the notes it updates.

## 4. Watch, then merge: two separate steps
- Poll until every check is completed and read each conclusion. An empty output is not green.
- Merge (`devops` PROPOSE, the owner's 1) only on green for the current head. Verify the merge by
  state: the pull request reads merged and the integration branch contains the commit.
- Leave the feature branch alive unless nothing is stacked on it.
- **Say what green proves here.** If the integration branch is a fast lane (lint and unit checks
  only, the full suite kept for the release), report it in those words. Never "CI is green, ready
  to release" on evidence that was never collected.
- A branch stacked on another feature branch may have had no checks: say so in the report.
- A red check: verify it in isolation before claiming or disclaiming it. Re-run the failing test
  alone, then with its neighbours, and against the base without your change. Fails on the base too:
  pre-existing. Passes alone, fails in the suite: shared state or ordering. Report both kinds.

## 5. Several open pull requests from the session
A wrap that leaves a train of green pull requests open is not wrapped: they rot and conflict.
- Inventory them, then order them: a stacked branch after the one it sits on.
- One merge per proposal step, each verified merged before the next. No loops of merges.
- Mergeability settles AFTER each merge. Wait for the host to recompute; the first answer is often
  stale.
- A real conflict is resolved in a scratch worktree on the feature branch, never on the
  integration branch. Conflicting code is read, not guessed.
- Every sync creates a new head: its checks must be green AGAIN, read by head commit.

## 6. End clean
- End on the integration branch, fast-forwarded. If another worktree holds that branch, do not
  check it out twice: update that worktree if it is clean, or stay where you are and say so.
- If the turn ran a script that changed local data, re-run its read-only check now and report that
  result. What was true at apply time may be stale.
- Write the carry-over where the project keeps it: what is done, what is open, what is next.

## Report
Notes touched, commits, pull request and merge state, what the checks did and did not prove, the
current branch, what is left for the next session.

## Guard rails
- A wrap never touches the live branch and never deploys.
- Never force-push, never skip hooks, never merge past a red, running or cancelled check.
- Stop and report at the first step that blocks.
