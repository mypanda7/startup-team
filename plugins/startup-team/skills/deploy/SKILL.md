---
name: deploy
description: Deploy already-merged code by hand, scope-aware - when the automatic deploy cannot run, for a schema change that needs a watched migration, or to pause, resume, check or debug an automatic deploy. Use when `ship`, `hotfix` or `release-train` falls back to a manual deploy, or when the owner asks why production did or did not update. It deploys what is merged; it never merges.
disable-model-invocation: true
---

# Deploy (manual, scope-aware; and the automatic deploy's switch)

For `devops`. Checking is ANALYSE and needs no approval. Everything that changes a host (the
deploy itself, a migration, a restart, a cache clear, pausing or resuming the automatic deploy,
editing its markers) is `devops` PROPOSE and the owner's 1, with the full proposal block. What is
being deployed has already passed `qa`, the `auditor` and its merge approval.

## The project must say (in its CLAUDE.md)
- The environments, which host is which, and how to tell from the inside which one you are on.
- The project's deploy script or steps, and its dry-run mode.
- Which paths mean "build the user interface", "migrate", "restart workers".
- How the web process, the workers and the scheduler are each reloaded, and what is forbidden.
- The health checks and the version marker; the backup step; windows to avoid.
- How the automatic deploy works, where its log and state live, and how it is paused.
If the project has a deploy script, use it and do not hand-roll its steps. If it names nothing,
write the proposal from what the repository shows and mark every assumption for the owner.

## Before anything
- Confirm which environment you are on by the project's check, never by a hostname or a guess.
- One environment at a time, the test environment first when one exists.
- Never two deploys at once, and leave a gap after the last one: migrations take a lock.
- If an automatic deploy exists, see whether a run is in flight before starting by hand.

## 1. Scope the deploy from the diff
Compare what is deployed with what is merged and classify:
- user-interface source changed: build it;
- schema, migrations, seeded data or wiring changed: migrate;
- code that workers or scheduled jobs run changed: restart them;
- nothing but server code: reload the web process.
Run the dry run and put its plan in the proposal as it printed. Do only what the scope needs: an
unneeded build on a small host has taken production down by exhausting memory.

## 2. Order (when the scope includes each step)
1. Backup, when a migration changes data. Mandatory, before anything else.
2. Fetch the merged code. This rolls forward to the live branch only.
3. **Migrate first**, so the schema matches the code before any process serves it. If the
   migration fails, STOP: do not reload onto a half-migrated schema.
4. **Build** the user interface. If the build fails, STOP: do not reload onto a partial bundle.
5. **Clear caches**, every cache the project names. A cache of rendered pages is often separate
   from the data cache, and stale pages can be served for hours.
6. **Reload the web process** the way the project names. Know whether your reload really
   re-imports code: a process that preloads the application can ignore a soft signal and keep
   serving the old code while reporting success.
7. **Restart workers and the scheduler** when their code changed. A web reload does not reach
   them.
8. **Health checks**: the process listens, the main page and a ping endpoint answer.

## 3. Verify the change, not just the host
- The deployed commit equals the merged commit; the served assets carry the new version marker.
- Look at one user-visible effect of the change on the live site.
- Workers show a fresh start time when they were restarted.
- Report each check as it came out, failures included. If a step needs a privilege the session
  does not have, hand the exact command to the owner; never work around the refusal.

## 4. The automatic deploy: check, pause, resume
**Check (ANALYSE).** Is it enabled? When did it last run and what did it decide? What does it
believe is deployed, against what is merged? Prefer its own log to guessing.

**"Why did production not update?"** In this order:
1. Is it switched on?
2. Did the live branch actually move past what is deployed?
3. Is it retrying a gate, or parked on a failed one? Find the failing gate and read the log around
   it; the real error often sits far above the summary line.
4. Is a run stuck in flight?

**Parked on a failure: real or flaky?**
- Flaky: the error is in test set-up or tear-down, a lock or deadlock, or it changes between
  runs. Let the retries run, or re-run the gate by hand without deploying.
- Real: the feature's own assertion fails the same way in isolation, more than once. Fix on a
  branch and merge; the deploy follows.
- Clearing the "failed" marker is not a fix. It only re-arms the same commit. Clear it only after
  a fix has landed, or when the branch has moved past the parked commit.

**Pause (PROPOSE).** Pausing stops future runs, not one in flight. Check for a running one first
and prefer to let it finish: stopping mid-build or mid-migration can leave a half-applied deploy.
Pause it before any by-hand deploy of a tag or a rollback, or it will roll you forward again.

**Resume (PROPOSE).** On resume it deploys whatever merged while it was off. If production
already matches the live branch, set its "deployed" marker to the current commit first so it does
not replay the same deploy. Say in the proposal which of the two will happen.

A manual deploy may not advance the automatic deploy's marker. Say so in the report: the next
automatic run repeating the same commit is harmless but not free.

## Guard rails
- Never run tests, fixtures or experiments on the production host.
- Never switch branches or reset by hand in the checkout that serves production outside the
  approved deploy steps.
- Never read, print or commit a secret; configuration stays on the host.
- Rollback is not this skill's forward path: see the tiers in `release-train`.
