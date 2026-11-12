---
name: dev-feature-test
description: Run the current feature branch's tests on the local test environment in a fix loop - scope the tests to the feature, run them plus the same lint and format gate CI runs, fix what the failure literally points to, and repeat until green, with a cap. Use when the owner or the executor wants "is my branch green" before a pull request, or names a test module, an area or a single case to run.
---

# Feature test loop

A scoped **run, read, fix, repeat** cycle on the local test environment, so that green here
predicts green in CI. Read `testing-rules` first: this skill is one use of it. It proves a branch
while it is being built; the verdict before a merge is `test-gate`.

## The project must say (in its CLAUDE.md)
- The local test environment and how to tell this machine has it.
- The commands for one test module, one area, one case, and the whole suite.
- The lint and format gate CI runs, as a command.
- The base branch a feature is compared with.
- Whether the working tree must be synced or deployed into the environment, when a migration is
  needed, and whether a queue or lock guards the environment.

No test command named: stop and say so.

## Hard limits
- **Local test environment only.** The command checks that it is on the test environment and
  refuses otherwise. That same check keeps it off production.
- **Only on a feature branch.** On the base or release branch, or on a detached head, refuse.
- **The loop pushes nothing.**
- **At most 5 fix rounds.** After five, stop and report: something structural is wrong.
- **A refusal from a budget or throttle guard is BLOCKED, not red.** Stop. Do not loop into it.
- If something else is running on the environment, queue behind it rather than wait on a lock.

## Stage 1: scope
1. Check the branch. A dirty working tree is fine: the tree is what gets tested.
2. Decide what to run:
   - **Named** modules, an area or a case: run exactly those.
   - **"all"**: do not hand-run the whole suite here. Hand it to the project's queue or release
     gate, which enforces the caps.
   - **Nothing named**: the test files added or changed on this branch against the base, minus
     any aggregate file that would pull in the whole suite.
   - **Still nothing**: say so. A feature branch that changes source and no tests is a smell.
     Ask whether to supply modules; do not silently run everything.
3. List what will run before running it. Keep the SAME list for every round: the diff changes
   as fixes land, and the scope must not drift with it.

## Stage 2: one pass
Sync the working tree into the environment if the project needs that, migrate only if the branch
changed the data model, clear caches, run each module, then run the lint and format gate.
Classify the outcome:
- **All passed**: go to Stage 4.
- **Sync, migrate or environment failed**: STOP and show the output. Never auto-fix
  infrastructure. It is usually a syntax error that broke an import, or a real migration error;
  the owner decides.
- **A test or the gate failed**: Stage 3. A pure formatting failure is fixed mechanically with
  the project's formatter; no logic changes.
- **Nothing to test**, or **the pre-flight failed**: say which.

## Stage 3: fix, then loop
For each failure:
1. Read the failing output. Decide the root cause: is the TEST wrong (bad assertion or setup) or
   is the SOURCE wrong (a real bug)? Say which.
2. Make the smallest fix in the working tree. Only what the failure literally points to. No
   refactor of surrounding code, no "improving" tests that were not failing.
3. Quick local check of the edited file (it compiles, it lints).
4. One local commit per fix, naming the failing module, so the log ties cause to test.
5. Run Stage 2 again with the same full list, not only the failures: a fix in one place can
   break another.
6. Count the round. Past five: stop and ask.

Never weaken a test to make it pass. If the expected behaviour is not written anywhere, return
`UNCLEAR: <one question>` instead of choosing.

When this loop runs inside a team turn, the fixes are the `executor`'s; `qa` runs the loop
read-only and reports failures as bugs.

## Stage 4: report
```
FEATURE TESTS: GREEN | RED | BLOCKED
BRANCH: <name>   HEAD: <short commit>
RAN: <modules>   ROUNDS: <n>
FIXES: <commit subjects added during the loop>
LINT/FORMAT GATE: clean | SKIPPED (<why>)
```
- `clean`: say "ready for a pull request".
- `SKIPPED`: the gate did not run. Do NOT say ready; name the command the owner must run first,
  because CI will run it.
- Passed first try: still print the report.

## Stage 5: make it clickable (only on final green, only if wanted)
A green test run does not put the change in front of a person: the served copy of the test
environment may still run the old code and the old build. If the project has a local deploy step
for the test environment and the owner did not say "no deploy":
- rebuild the client only if client code changed; otherwise just restart the server;
- verify the served copy answers with the new build before saying it is live;
- tell the owner to hard-refresh.
If the deploy step fails, show its output and do not claim the change is live. The tests are
still green; only the deploy needs another look. This touches the LOCAL test environment only.
A shared or remote one is `devops` PROPOSE and the owner's 1.
