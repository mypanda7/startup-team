---
name: testing-rules
description: The team's testing discipline for any project - where tests may run, what is cheap and what is expensive, what never runs on production, how to share a test environment, and how to read a red run. Load before running, writing or gating any test, and before any heavy operation on a shared test machine.
---

# Testing rules

The commands belong to the project. The discipline is the same everywhere. Which tests a piece
needs is `feature-tests`; the gate before a merge is `test-gate`; the local fix loop is
`dev-feature-test`; QA of merged changes is `e2e-qa`.

## The project must say (in its CLAUDE.md)
- The test commands: one targeted test, one area, the whole suite, lint and format, end-to-end.
- Where each may run: this machine, a local test environment, a shared test environment, CI.
- Which environment is production and how to tell which machine a session is on.
- What a shared test environment costs (metered CPU, a queue, a lock) and its limits.
- The breakpoints for screen checks.

If it names no test command, read the project's manifest and CI config, propose the commands,
and get the owner's 1 before treating them as the rule. Never invent a command against a live
system.

## Never on production
- No tests, no fixtures, no seed data and no test accounts on production. Ever.
- Check which machine and which environment you are on before any environment-scoped command.
  Two machines can look alike; a default target is not proof.
- A command that names a target refuses when the target is not the test environment. Put the
  guard in the command, not in your memory.
- A migration on production is a deploy step: `devops` PROPOSE and the owner's 1.

## Cheapest proof first
1. **Local, targeted.** Run the changed code's own tests and the guards that cover it. This is
   where a feature is built and broken.
2. **Local, one area.** The area's tests, when the change crosses files.
3. **A real browser**, for anything a person clicks: every role it concerns, the happy path, the
   refusals, the empty and error states, at the project's breakpoints. Write down each step as
   you take it; the record becomes an end-to-end spec in the same change. The pass proves it
   once; the spec replays it.
4. **The whole suite** runs where the project says a release is gated, not per change.
5. Do not push to learn whether something works. CI confirms; it is not the first reader.

A fix for a production problem: reproduce it locally with data shaped like the report, fix until
green, run the targeted check, ship through `devops`, then run the whole suite.

## What is expensive
- The whole suite, a whole area on a shared machine, a rebuild of the test environment, a
  restore from a copy of real data. Each is asked for, never incidental.
- **Batch.** Wait until the branch is ready and run once. While a long run is in flight, do not
  start another for something that can wait; say what is waiting.
- **Do not repeat a green.** The same code that passed needs no second run.
- **A budget is a limit, not a hint.** If the environment meters CPU or caps runs per day, a
  refusal is BLOCKED, not red. Stop. Overrides are the owner's call, not yours.
- Check the machine before a heavy run (memory, load). A starved machine produces false reds.

## Sharing a test environment
- **Queue, do not race.** Use the project's queue or lock. Two runs against one database
  produce deadlocks that look like a hundred failures, none of them yours.
- Tests run against a test database, not the copy a person is clicking through. A test run must
  neither change that copy's data nor make a tester wait.
- Know what the environment serves. Many serve a built copy, not your working tree: a brand-new
  element that "is missing" may simply not be deployed there yet.
- A run can reset the environment to its base branch when it finishes. Re-deploy your change
  before testing by hand again.

## Reading a red run
- **A red suite is not automatically yours, and not automatically someone else's.** Check each
  failure alone before claiming or disclaiming it:
  - fails without your change too: it was already broken; report it, do not absorb it;
  - passes alone, fails in the suite: shared state or ordering, not a regression;
  - fails only with your change: yours.
- Tell a real assertion failure from infrastructure noise (deadlock, timeout, refused).
- An infrastructure failure (sync, migrate, environment) is surfaced and stopped on. Never
  "fixed" on your own.
- Never soften a real failure to green, skip it, or weaken the test to pass.

## Writing tests
- A fix for logic, maths or workflow gets a regression test that is RED on the old code. A test
  never seen red proves nothing.
- **Every refusal test has its allow twin.** Test that the wrong person is refused AND that each
  permitted role still gets through, as that role, never as a superuser: a superuser skips the
  very checks that fail real users.
- Test at the smallest layer that proves the point. A unit test cannot stand in for a browser
  check of layout, layering, focus or dismissal, because the unit layer stubs them.
- Seed and clean your own data. Never depend on rows another test or a person left behind.
- Register a new test wherever the project's runners discover tests, or it never runs.
- Keep the count honest: fold duplicates, and do not add ten tests that restate one.

## Before saying "ready"
- The tests passed AND the same lint and format gate CI runs passed. A gate that was skipped is
  reported as SKIPPED, never as clean.
- Say where each check ran and on which commit.
- A check you could not run is NOT RUN with the reason, as `qa` reports it.
