---
name: test-gate
description: The test gate before a merge - plan only the tests a diff needs plus the guard sweeps past incidents taught, skip what is already proven green on the same tree, run them the cheapest honest way, and end with GO, GO-CONDITIONAL or NO-GO backed by evidence. Use before merging a hotfix, a feature branch or the release, or to print the plan only. It never merges or deploys.
---

# Test gate (what must run before this merge, and did it)

For `qa`, `devops` and the main session. The gate decides WHAT to test, runs it, and says whether
the change may go on. It feeds the chain; it replaces neither `qa`'s walk of the product nor the
`auditor`. `ship`, `wrap`, `hotfix` and `release-train` call it as their test step. Runs on local
or test environments need no approval; anything that writes to a shared host beyond submitting a
test run goes through `devops` PROPOSE and the owner's 1.

## Modes
- `hotfix <branch>`: a fix into the live branch. Targeted tests, guard sweeps, a smoke set.
- `feature <branch>`: a branch into the integration branch. Targeted tests and guard sweeps.
- `release`: the integration branch's tip, before the release. The full suite.
- `plan <mode>`: print the plan, run nothing.

## The project must say (in its CLAUDE.md)
- The test commands per layer, and how to run a subset by module or group.
- Where each kind of run may execute (local, a test host, CI), and where it must never run.
- Its guard sweeps: the checks kept because an incident taught them, and what each protects.
- Which files are "wide" (wiring, shared entry points, schema, CI and toolchain files).
- How a green run on a tree is recorded, if it is, so the same tree is not run twice.
If it names no guard sweeps, say "no guard sweeps defined" in the risks. Do not invent a pass.

## Hard rules
- Never run tests against the production host or a database people are using.
- Never kill someone else's run to make room. A killed run reads like a red one.
- A refused, deferred, timed-out or skipped run is NOT a result. Never report GO on a run that
  did not happen.
- The verdict is per commit. A new push invalidates it: run the gate again.
- Verify by identity, not exit code. Some runners exit 0 on failure or on a filter that matched
  nothing: every target the plan listed must appear in the run's output, and the count of tests
  run must be above zero and match what you sent.
- Report failures as they are, with the failing test names and where the log is.

## 1. Put the exact commit under test
Test a named, pushed branch at a known commit, in a clean worktree. A dirty tree never earns GO
for the live branch.

## 2. Plan
From the diff against the base, write the plan and show it as is:
- **Already green?** A recorded green for this exact tree means skip, and name the record.
- **Targeted tests:** the tests that own the changed code, plus the tests of the layer on the
  other side of any contract the diff changes (an API change pulls in the client tests that read
  it).
- **Guard sweeps:** every sweep whose protected area the diff touches, each with its reason.
- **Build:** a production build whenever user-interface source changed, written to a scratch
  folder, never over live assets.
- **RISK lines:** a wide file whose full scope will not run; a schema or data change; a change
  no test resolves to; a change every request passes through. Diff-based scoping cannot see blast
  radius, so name it instead of hiding it.
In hotfix and release modes, any user-interface change runs that layer's FULL suite: a subset has
missed a failure that then blocked the deploy.

## 3. Lint
Always, with the version CI pins. A skipped tool is not a pass.

## 4. Run
- The cheapest honest place first, as the project's CLAUDE.md names it. Where test hosts are
  shared, submit and wait; do not hand-run a second copy of a run CI already owns.
- A hotfix has two legs: your fast run for the early signal, and the pull request's own CI, which
  is the gate the merge waits for. Wait for both.
- **Red?** Isolate before judging. Run the failing test alone, with its group, and on the base
  without the change. Fails on the base: pre-existing (but a branch cut from that base inherits
  it). Passes alone, fails together: ordering or shared state. Cannot tell: treat it as yours.
  Any red not proven pre-existing is NO-GO.
- Flaky and real are different findings. Flaky: the error sits in set-up or tear-down, is a
  lock or deadlock, or moves between runs. Real: the feature's own assertion fails the same way
  alone, more than once. One green re-run proves neither.
- For each real failure decide which side is wrong: the code drifted from the documented rule,
  the rule changed on purpose (fix the test and the note), or the test is wrong.

## 5. Verdict (print exactly this; `n/a` is allowed, silence is not)
```
TEST GATE - <mode> - <branch> @ <commit>   (plan: <scope>, <N> changed files)
  lint:      PASS | FAIL (<what>)
  targeted:  PASS <where it ran> ran=<N> | SKIPPED already green (<record>) | NONE | FAIL <tests>
  guards:    PASS <sweeps> | NONE DEFINED | FAIL <sweeps>
  CI:        PASS <check> | PENDING | FAIL | REFUSED | n/a
  ui:        PASS <scope> [+ full] [+ build] | FAIL <files> | n/a
  risks:     <each RISK line, or "none">
  VERDICT:   GO | GO-CONDITIONAL (<why>) | NO-GO (<why>)
```
- **GO:** every leg PASS, SKIPPED or NONE, and no risks.
- **GO-CONDITIONAL:** every leg green but a risk stands. Name it; the owner decides.
- **NO-GO:** any FAIL, any leg PENDING or REFUSED at verdict time, or a dirty tree bound for the
  live branch.

## 6. Hand back
Save the block in the turn folder and return it to the caller. On NO-GO, the failures go to the
tech lead as fix tasks. On GO or an accepted GO-CONDITIONAL, the merge is still `devops` PROPOSE
and the owner's 1. Remove the gate's worktree.
