---
name: test-accounts
description: Create, list or delete throwaway test accounts on a test environment only, run-stamped so a sign-up or onboarding flow can be retested any number of times. Use when QA needs a fresh user in a given state (never onboarded, invited but not yet joined, a limited-role admin), or when old test accounts need purging. Refuses production.
---

# Test accounts

Fresh accounts on demand, in the exact state a test needs, and gone again afterwards.

## The project must say (in its CLAUDE.md)
- The test environment(s) this may run on, how production is recognised, and how each is reached.
- The seed script or supported interface that creates and deletes users. This skill does not
  write raw rows.
- The reserved address pattern for test accounts (a domain that can never receive mail, such as
  one under `.test` or `.invalid`).
- Where the shared test password is kept (a seed or example-config file in the project).
- The roles and account states worth minting.

If it names no test environment, refuse. If it names no seed script, propose one as a build
task for the team chain; do not improvise writes against a database.

## Guards: two, both must pass
1. **Refuse if the target is production**, by its identity, not by its name alone.
2. **Refuse unless the target is marked as a test environment** (the project's own test flag).

Either guard alone is a single point of failure, and this writes real user rows. The guards live
in the script itself, so they hold whoever runs it. A target that is only "the default" is not
enough: say which environment before the first write.

Creating and deleting accounts on a test environment that the project's CLAUDE.md names is
within this skill. Anything on another environment needs the owner's 1 through `devops` PROPOSE.

## Design rules for a mint
- **Run-stamp every address** (`<role>-<MMDD-HHMMSS>@<reserved domain>`). "That account already
  exists" can then never block a retest.
- **Mint the state the test needs, not a finished user.** An account meant to test onboarding is
  created NOT onboarded, so the wizard still fires. An invitee has no user record at all until
  the invitation is opened: that missing half is the thing under test.
- **Give a tooling account the narrowest role the screen admits**, never a superuser. A superuser
  hides exactly the permission bugs the account exists to catch.
- **One set per run**: for example an owner, a joiner, an invitee and a limited admin. Print the
  whole set once.
- **Passwords**: generate one per project and keep it in the project's seed or example-config
  file. Do not print it in chat; say where it is. Never reuse a real person's password.
- One-time links (an invitation, a magic link) change on every mint. Read the new one from the
  output; an older link is dead. Open it in a clean private window: a signed-in session hides
  the flow.

## Actions
- **create**: mint a new stamped set and print the addresses, their states and the stamp.
- **list**: show the test accounts that exist, by the reserved pattern.
- **delete `<stamp>`**: purge one run.
- **delete** (no stamp): purge EVERY account matching the reserved pattern. Print the count
  first and confirm it is only the reserved pattern before running.

## Deleting safely
- Match only the reserved pattern. Never a wider filter, never a real domain.
- Delete dependents before the user (sign-up rows, invitations, memberships). Removing the user
  first strands the link and blocks the delete.
- Read back afterwards: the list for that stamp must be empty.

## Before you run it
- **Not while a test suite or a CI job is using the same environment.** They contend on the same
  data, and the usual result is a deadlock that surfaces as a misleading "not found". Check what
  is running first, or go through the project's test queue.
- Some pipelines snapshot the test environment and restore it afterwards. Accounts minted during
  such a run can vanish with no error. If accounts disappear for no reason, that is why.
- A refresh of the test environment from a copy of real data wipes whatever the accounts were
  attached to. Mint again afterwards.

## Report
```
TEST ACCOUNTS: created | listed | deleted
ENVIRONMENT: <name>   GUARDS: not production - yes · test flag - yes
STAMP: <MMDD-HHMMSS>
- <address> — <state: not onboarded | invited, no user yet | limited admin of <...>> — <purpose>
PASSWORD: in <file>, not shown
LINKS: <one-time links, when minted>
```
