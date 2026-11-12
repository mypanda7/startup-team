---
name: hotfix
description: Get ONE production fix live ahead of the regular release - reproduce, branch off the live branch, minimal diff, test gate, merge, deploy, verify live, sync back, tag. Use when the owner says a fix cannot wait for the next release. Not for features, clean-ups or anything that can ride the scheduled release.
disable-model-invocation: true
---

# Hotfix (a production fix ahead of the regular release)

For the main session and `devops`. A hotfix is the fast lane, not a lane without gates: the fix
still passes `qa` and the `auditor`'s PASS, and every push, merge, deploy, restart and tag goes
through `devops` PROPOSE and the owner's 1. Asking for a hotfix is not the 1 for its steps.

## The project must say (in its CLAUDE.md)
- The live branch, the integration branch, and the branch prefix that marks a hotfix.
- What the hotfix gate runs before merge, and what runs after the deploy.
- Deploy windows to avoid (peak hours), and whether a backup comes first.
- How the deploy happens, the manual fallback, and how workers or scheduled jobs are restarted.
- The rollback command and how releases are tagged.
If it names no hotfix lane, treat the fix as a `ship` of a branch cut from the live branch, and
ask the owner what gate they accept.

## Rules of the lane
- **The fix only.** No refactor, no clean-up, no "while I am here". Anything else is a follow-up
  to the integration branch. An extra commit on the hotfix branch means stop and split it out.
- **Reproduce first.** Rebuild the failure locally with data shaped like production's, see it
  fail, fix it, see it pass. A regression test is proven only by being red on the pre-fix code.
- **Never work in the checkout that serves production.** Use a separate worktree or clone.

## 0. Classify the diff (it decides the deploy)
List the changed files and sort them: user interface build needed, schema or data migration
needed, code that background workers or scheduled jobs run (they must be restarted; reloading the
web process is not enough). Put the classification in the proposal.

## 1. Branch and pick the fix
- Branch from the live branch with the project's hotfix prefix.
- If the fix already merged to the integration branch, cherry-pick that change's OWN commits in
  order. Never the merge commit, and skip any "merge the integration branch in" commit inside the
  list: both drag in unrelated work.
- Conflicts in append-only logs or notes: keep every entry. Conflicts in code are read, not
  guessed.
- Run the pinned lint gate on the changed files. Never reformat with a newer local tool.

## 2. Pull request into the live branch (`devops` PROPOSE, the owner's 1)
The body names what it carries, the evidence (which tests ran where, red before and green after,
what was checked on production) and that the sync back follows. No tracker reference the change
does not implement. No checks appearing usually means the pull request conflicts: check
mergeability; re-opening it does not fix a conflict.

## 3. Test gate
Run `test-gate` in hotfix mode: the tests the diff names, the guard sweeps, a smoke set for any
wide file the fix touches. Schema, migration and CI or toolchain changes still take the full suite
BEFORE merge. The verdict block goes in the pull request body.
- GO: carry on. GO-CONDITIONAL (the full scope was not run): the owner decides, in chat.
  NO-GO: stop and show the failures.
- "Merge on the evidence you have" means do not run extra suites to confirm. It never means merge
  past the pull request's own checks.
- If the test host is stuck and the fix cannot wait, stop and ask the owner. Never kill another
  run to make room: a killed run reads like a red one.
- The branch runs the CI of its OWN base. A CI fix that lives only on the integration branch is
  not there: carry that one commit along and say so in the body.

## 4. Merge and deploy (`devops` PROPOSE, the owner's 1 for each)
- Merge only on finished, green checks for the current head. Closing or bypass-merging while
  checks run cancels them and hides the result.
- Deploy outside the windows the project names. Two hotfixes in one wave: leave a gap between
  them so their migrations do not collide.
- Automatic deploy first. If it has not started after a bounded wait (about ten minutes, or what
  the project says), switch to the manual path in the `deploy` skill: read its dry-run plan, then
  run it. Never hand-roll the steps, never run two deploys at once.

## 5. Verify LIVE, not just healthy
- Restart workers and scheduled jobs when step 0 flagged them (in the proposal).
- Prove the new code serves: the deployed commit equals the merge commit, the built assets carry
  the new version marker, and one user-visible effect of the fix is seen on production.
- Watch the error log for the next hour.
- If the project runs the full suite after a capped hotfix, watch it and report its result. Red
  there means fix forward or roll back: the owner's call.

## 6. Sync back, tag, record (`devops` PROPOSE, the owner's 1)
- Sync the live branch back into the integration branch the SAME session, through a pull request
  from a named branch. Skipping this is how a hotfix regresses at the next release.
- Tag the merge as a named rollback target.
- Record: the issue log entry if an issue drove it, the notes, the carry-over.

## Report
What shipped, the merge commit, the deploy path (automatic or manual), workers restarted or not,
what was verified live, the post-deploy suite result, the sync pull request, the tag.

## Guard rails
- Never reset or switch branches by hand in the production checkout: the deploy steps own it.
- Never run tests, migrations of test data or fixtures on the production host.
- Never bypass a queue, a hold or a budget limit on shared test hosts without the owner's say.
- Rollback follows the tiers in `release-train`, as a new proposal.
