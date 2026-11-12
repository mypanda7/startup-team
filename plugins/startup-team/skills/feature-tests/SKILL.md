---
name: feature-tests
description: Decide which tests a finished feature actually needs, by risk - flag the risks, pick a tier out loud, write tests only at the flagged layers, look at the real artifact, and report what was deliberately not tested. Use when a piece is functionally complete and before `test-gate` and `ship`, or when the tech lead or architect plans the tests for a piece.
---

# Feature tests (the right tests, not the most tests)

For the `tech-lead` and `architect` when they plan a piece, the `executor` when it writes the
tests, and `qa` when it judges them. The output is a visible tier call the owner can override, not
silent test generation. Green tests never replace `qa` or the `auditor`.

## The project must say (in its CLAUDE.md)
- The test layers it has (unit, component, integration, real-browser, source guards) and the
  command for each, including how to run a subset by name.
- Where tests may run and where never; the personas or roles to test as.
- Any budget on new tests, and its fixture rules.

## Lessons to hold before writing a single test
1. **A test covers only the layer it asserts.** A correct, green server test protects nothing
   when the bug lives in the render, the interaction or the data. Test where THIS feature breaks.
2. **Tests inherit the author's blind spots.** A test of your own mental model passes by
   construction. Only observable behaviour or an adversarial angle catches what you did not think.
3. **Green is not "works".** Environment, data and deploy faults are not unit-testable: they need
   a smoke check and a note.
4. **Never write a confirmation test.** Spend the budget on the negative, the edge and the seam.
5. **Look at the artifact.** A document, an email, an export, a rendered element: open it.
6. **Extract to make it testable.** Logic buried in a huge file gets pulled into a small unit.
7. **A component or library swap is a behaviour-equivalence audit.** List every input the old one
   accepted and ask whether the new one treats it the same, and trace where each value comes from.
   Watch the tolerant-to-strict trap: the old one ignored bad input, the new one enforces it.
8. **A "proven pattern" is proven only for the config it shipped with.** Diff the full config
   against a working instance and understand WHY it works. If the doc and the working code
   disagree, the code wins: fix the doc.
9. **A deny test never runs the write.** Wrongly denying a permitted user is a common shipped bug.
   Run the FULL allow path as each role the route admits, never only as a superuser (it skips the
   very re-checks that refuse real users), and compare the route's roles with the endpoint's.
10. **A regression test is proven only by being red on the pre-fix code.** See it fail once.
    For error paths, assert the failure is logged and surfaced, not just "does not crash".
11. **A static source guard is a real test layer.** A test that scans source for a forbidden form
    protects every future file. When the bug class is "someone writes the broken form again",
    reach for a guard before an end-to-end test, and prove it red once with an offending sample.
12. **A simulated DOM is blind to some real-browser behaviour** (native events through wrapper
    components, portals, focus traps, layering, dismiss). A green test there can pass on broken
    code. Prove those in a real browser, in BOTH directions (it stays open when it should, it
    closes when it should), and open the layer in the test: content that mounts only when open
    renders nothing otherwise.

## 1. Scope the change
List what changed and across which layers (server, client view or component, template or output,
config, schema). The layers hint at the seams.

## 2. Flag the risk
| Flag | When the feature touches | Pulls in |
|---|---|---|
| Money | amounts, tax, billing, balances | unit tests of the maths and its edges |
| Access | permissions, who sees what, roles | the negative gate AND the full allow path per role; for a page, every endpoint it calls, each tab and lazy panel included |
| Seam | a field or rule shared by server and client | integration or an artifact check; one shared fixture both sides assert against |
| Upstream | framework or third-party machinery | integration on the real stack as a real role; a mock skips the re-check |
| Batch | any loop that writes | seed one poisoned row; the rest survive, the bad one is skipped and logged |
| Schema | new options, fields, migrations | a schema test and an idempotent migration; never ship code that reads a field before it exists |
| Retry | a user-triggered write a client may repeat | call it twice; the second is a no-op |
| Interaction | layered dialogs, multi-step flows, realtime, drag, focus, native events | real-browser test, or a source guard when the class is mechanical |
| Artifact | document, email, export, rendered output | render it and look |
| Irreversible | sends, deploys, writes live data | raise the tier |
| Environment | data-shape, staleness, sockets | not unit-testable: smoke check and a note |
| Blast radius | shared by many screens, a core flow, bitten before | raise the tier |
| Swap | replacing a component or library | the equivalence audit (lesson 7) |
| Visual | layering, overlay, responsive | a real look at the project's breakpoints plus guards |

## 3. Pick the tier, and say it
- **Tier 0, nothing.** Cosmetic, copy, pure refactor, docs. No confirmation test.
- **Tier 1, one test, one layer.** Self-contained logic, about one flag. The behaviour plus the
  negative or edge. The default.
- **Tier 2, several layers.** Only with two or more flags, or any of money, access, seam or
  interaction. Cover each flagged layer and verify the artifact.
Declare it in one line: the tier, the flags, what you add, what you skip and why. The owner may
move it up or down before anything is written. If you cannot name two flags, it is not Tier 2.

## 4. Write at the flagged layers only
- Assert the value and the refusal, not just "it ran". Who sees it AND who does not.
- Tests seed their own data and clean up after themselves; never depend on ids or states that
  drift on a shared environment.
- Assert that a new endpoint is actually exposed and guarded the way the framework requires: a
  test that calls the function directly never crosses that gate.
- Migration logic: extract the mapping into a pure function and prove it deterministic.

## 5. Run, by name
Run subsets by module, group or project name as the project's CLAUDE.md shows. A path or pattern
filter that matches nothing is often silent: check the tests you meant actually ran. A refused or
throttled run is blocked, not red.

## 6. The manual check is a deliverable
Every interaction, visual, swap and artifact flag is cleared only by a real, rendered, clicked
product. Write an itemised checklist, one line per flagged risk, as action and expected result.
A flagged risk you did not exercise is OPEN: mark it UNVERIFIED and hand it to `qa`. Never relabel
it "safe" or "same pattern as before". For a swap, exercise what DIFFERS between old and new.

## 7. Report
The tier and flags, the layers covered, what you deliberately did NOT test and why, the artifact
or behaviour you saw. Calibrate the claim: "server green; render checked in a browser; behaviour
X not covered", never "all green, done". New invariants go into the project's notes.

## Budget and the floor
- Every test is paid for on every run by everyone. Extend an existing test or table before adding
  a new file; one table of roles per endpoint, not one test per role; no test that repeats what a
  sweep already covers; set expensive fixtures up once per group, not per test.
- One good negative test beats five happy-path tests. A test that passes by construction: delete.
- A cheaper smoke check may replace a flaky end-to-end test, but only if it is actually run.
