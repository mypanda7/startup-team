---
name: e2e-qa
description: QA recent merges with end-to-end specs, from a high-water mark - walk every merged change since the last pass, write or extend specs for the ones that touch what a user sees, run them against the test environment, and give EVERY change a disposition in a ledger. Also covers running the end-to-end suite from a developer machine and reading its reds. Use after merges land, or when asked which changes still lack end-to-end coverage.
---

# End-to-end QA from a high-water mark

Change-driven QA. Nothing merged goes unaccounted for: each change ends the pass with a written
disposition, and the mark only moves forward.

## The project must say (in its CLAUDE.md)
- The end-to-end runner and its command, and where the specs and their conventions live.
- The ledger file that holds the high-water mark. If it names none, use `docs/qa-e2e-state.md`
  when the project has a `docs/` folder, else `.handoff/qa-e2e-state.md`, and say so.
- The branch merges land on, and the test environment the specs run against.
- How signed-in test personas are prepared, and which roles exist.
- Which paths hold user-facing code.

No runner named: stop and say so. Do not install one.

## The ledger
Keep the file's existing format; never start a second log. It holds:
```
last_qa_change: <id>     last_qa_head: <commit>     last_qa_date: <YYYY-MM-DD>

| Change | Title | Disposition | Spec | Note |
```
Dispositions: `SKIP` (nothing a user sees), `COVERED` (an existing spec already locks it),
`SPEC-ADDED`, `AWAITING-DEPLOY` (not live on the test environment yet; re-check next pass),
`FAIL` (a real regression, reported to the owner).

## Walk the merges
1. Scope: the changes or start point the owner named, else everything merged after
   `last_qa_head`.
2. List the merges in order with each one's file list and title.
3. A merge that only carries other changes (a back-merge between branches) is expanded: ledger
   the changes it carries, mark the carrier `SKIP`, and never list a change twice.
4. Presume `SKIP` when the diff touches no user-facing path. For the rest, read the actual diff
   and search the existing specs before choosing `COVERED` or `SPEC-ADDED`.
5. **Draft every row first.** `SKIP` and `COVERED` rows are complete at that point, so a session
   that is cut short still leaves a true record. Then write specs.

## Two checks before running anything
1. **Is the change live on the test environment?** Many serve a built copy, not the branch.
   Confirm the new behaviour is really there. Not live: `AWAITING-DEPLOY`. Never record a `FAIL`
   against a change that is not deployed. A test run can reset the environment to its base when
   it finishes, so a change you deployed earlier can be gone again.
2. **Are the personas healthy?** A valid sign-in proves the login, not the shape. Check each
   persona still has the role, the record and the customer it is meant to have. A drifted
   persona makes its specs skip into an empty green.
   - Drift does not abort the run, but skips and reds in that persona's specs are suspect: do
     not disposition a change on them.
   - Repairing a persona is a deliberate act on the test environment, never automatic mid-run.
   - If a role's sign-in could not be prepared, do not run that role's specs.

## Writing specs
- Read the suite's conventions and the notes for the area first.
- The test environment is shared and keeps state: seed and clean your own data, use the suite's
  helpers, keep dependent steps in order, and assert that the page raised no render error.
- Put the spec with its area. A new area folder only for a truly new surface.
- **Anything layered gets a real-browser spec by default** (dialogs, menus, pickers, portals):
  the unit layer stubs them, so end-to-end is the only honest check of dismissal, click-through,
  stacking and focus. Assert both directions: picking inside the dialog keeps it open; Escape
  closes the inner layer first; the close control and the backdrop still close the dialog.
- **Traceability.** Put the change id in the spec's title and a comment saying what it locks, so
  one search answers "was this QA'd".
- Gate: type-check the specs, run each new spec alone, then all new specs together.

## Reading a red
Before calling a red a bug:
- Known non-bugs stay non-bugs: specs marked as expected-to-fail or to-fix, a seed step with a
  known failure. An expected failure that now PASSES means the feature shipped, not a bug.
- A failure on a brand-new element usually means "not deployed yet".
- Real-bug signals: a render error or the product's error screen; the same spec failing on every
  attempt; a save whose request never fires.
- Read the shape of a layering red; it is the diagnosis, not a flake:
  - a click that times out because another element intercepts it: an overlay is covering it;
  - a dialog that closes when you pick from a control inside it: a missing dismiss guard;
  - an open menu that cannot be clicked: it sits under the dialog, or does not take clicks.
  These are invisible to unit tests. Do not retry them away.

## Recording and finishing
- A real regression stays `FAIL` and is reported to the owner. Never softened to green, never
  quietly fixed inside the same row. The fix is a task for the team chain.
- Advance the mark (change, head, date) only over rows that have a disposition.
- Specs and the ledger are committed TOGETHER on a branch, one local commit. The push and the
  pull request are `devops` PROPOSE and the owner's 1. Never push to a protected branch.

## Running the suite from a developer machine
- Prefer a machine that is not also serving the test environment: a browser next to the server
  starves both.
- Use the project's one script for the whole sequence (prepare personas, health check, seed,
  run, tear down). Do not re-derive the steps by hand, and do not run the bare runner with
  missing or stale sign-ins: specs would skip for misleading reasons.
- Seeding and repairing change the test environment: allowed there, never on production.
