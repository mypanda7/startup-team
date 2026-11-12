---
name: release-train
description: Run the scheduled release from the integration branch to the live branch - preflight, reconcile drift, release-candidate validation, the owner's go/no-go, merge, tag, verify, record - plus the tiered rollback path. Use on release day, when the owner asks to cut a release, or when a release must be rolled back. For one urgent fix use `hotfix`; for one finished branch use `ship`.
disable-model-invocation: true
---

# Release train (the scheduled release, and rollback)

For the main session and `devops`. The release is a production deploy. Every push, merge, tag,
deploy, restart and rollback goes through `devops` PROPOSE and the owner's 1, and the go/no-go in
phase 3 is the owner's alone: never infer it from momentum or from an approval in an earlier
session. What rides the train has already passed `qa` and the `auditor` in its own turn.

## The project must say (in its CLAUDE.md)
- The integration branch, the live branch, and the release day or cadence.
- The preflight check, the full-suite command and where it may run.
- What end-to-end validation a release candidate gets, and on which environment.
- Deploy windows to avoid, the backup step, and when a backup is mandatory.
- The merge method for the release, how releases are tagged, and the rollback commands.
- Kill switches or feature flags, if any.
If there is no integration branch, the "train" is a `ship` with phases 2, 3 and 5 of this skill.

## Phase 0. Is it release day?
Check the date against the project's cadence. Off-schedule releases need the owner to say so
explicitly; otherwise the urgent path is `hotfix`.

## Phase 1. Preflight and reconcile
- **Drift canary.** The live branch must hold nothing the integration branch lacks. If it does,
  sync it back first (a pull request from a named branch, conflicts resolved there), then re-check.
- **Suite on the candidate's tip.** A red is triaged before it is believed: known flakes,
  environment limits and refused runs are not red code, and a refused or deferred run graded
  nothing. A real failure is fixed on a branch into the integration branch and the check re-run.
  Never wave a real red through.
- **Reconcile each real failure against the notes.** Decide which side is wrong: the code drifted
  from the documented rule (fix the code), the rule changed on purpose (fix the test and the
  note), or the test is wrong (fix the test). Do not just make it pass.
- **Flag what the deploy will do:** migrations, worker restarts, seeded data, new wiring. Each
  flag is a line in the phase 3 summary.

## Phase 2. Release-candidate validation
- Suite evidence comes from `test-gate` in release mode: the full suite, once, on the exact tree.
  A full green on the same tree is the evidence; do not burn a duplicate run.
- End-to-end checks run against a DEPLOYED build of the candidate on the test environment, not
  against source. Confirm the build under test contains the candidate.
- Do not rerun what CI already ran on the same commit; cite it.

## Phase 3. Go/no-go (the owner; never skipped)
Present one compact summary: commit count, notable changes, the phase 1 flags, suite and
end-to-end verdicts, open risks. Then ask for an explicit GO. Before the merge, remind the owner
of the manual steps: a backup now (mandatory when a migration changes data) and the deploy window.
A real red gate is a NO-GO: fix it, or drop that change from the train (revert it on the
integration branch). Never "ship anyway, it is probably fine".

## Phase 4. Ship (`devops` PROPOSE, the owner's 1)
- Open the release pull request from the integration branch to the live branch, the body listing
  what ships.
- Watch every check to completion and read each conclusion.
- Merge with the method the project names. Where rollback works by reverting merges, the release
  is a MERGE COMMIT, never a squash: a squash breaks the ancestry between the two branches and the
  rollback.
- A bypass of a review rule the author cannot satisfy is not a bypass of the GO, and is never
  used on a red release.
- Watch the deploy to the end. If the automatic deploy cannot run, use the `deploy` skill.

## Phase 5. Tag, verify, record
1. Tag the release as the named rollback target (`devops` PROPOSE).
2. Verify live: health checks, the version marker, worker restarts when workers changed, one
   user-visible change.
3. Record: `release-notes`, then `announcement`, and whatever tracker the project keeps.
4. Watch the error log through the following hours.
5. The drift canary resets: the two branches should hold the same content again.

## Rollback (tiers; pick the lowest that fixes it)
Read the project's rollback table first. Every tier is a `devops` PROPOSE with the owner's 1.
- **Tier 0, switch it off.** The feature sits behind a flag or kill switch: flip it. No deploy.
- **Tier 1, revert the code.** Revert the merge and deploy the revert. Show the dry run of exactly
  what is undone and get an explicit confirmation first.
- **Tier 2, back to a tagged release.** Deploy the previous release tag.
- **Tier 3, data.** A migration that changed data and went wrong is NOT fixed by a code revert:
  it needs a compensating migration or a restore from the backup. Rule this tier in or out
  consciously before any revert that crosses a schema change.
- **Emergency, the code host is down.** Pause any automatic deploy FIRST, then deploy the tag by
  hand on the host with the `deploy` skill.
After any rollback: run the verification, then sync the revert back to the integration branch the
same session, or the next train re-ships the fault.

## Guard rails
- No merge to the live branch without the owner's explicit GO in this conversation.
- No squash of the release where history carries the rollback.
- No second full suite hand-run on a shared test host; submit and let the queue order it.
- If any step fails unexpectedly, stop and report. Do not improvise on release day.
