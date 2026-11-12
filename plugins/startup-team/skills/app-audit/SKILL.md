---
name: app-audit
description: Whole-app audit on a test environment - crawl every route as several role personas, build the access-control grid (who reaches what, against who should), mine per-route request cost (repeated, refetched, slowest, largest), probe endpoints with someone else's ids in both directions, and sweep for the interface faults a crawler cannot see. Use when asked to find access gaps, speed up data loading, check that a permission fix did not lock out legitimate users, or hunt dead-control regressions.
---

# App audit

One pass that answers four questions: who can reach what, what each screen costs, which
endpoints trust an id they should not, and which controls are dead. It finds candidates, then
proves them. A candidate is not a finding.

## The project must say (in its CLAUDE.md)
- The test environment to audit (never production) and how personas sign in there.
- The roles that exist, and where the route-to-role rules are written (the expected matrix).
- How the client calls the server, so requests can be recorded per route.
- A browser automation tool already set up, if any, and the per-route request budgets, if any.
- Whether the environment is shared, and its queue or lock.

No test environment named: stop. Auditing against real users' data is not this skill.

## Guard rails
- **Test environment only**, on data that is scrubbed or made up.
- **Stage A is read-only.** Stage B clicks, so take a backup first and keep a deny-list of
  destructive labels (delete, reset, approve, pay, send, invite) on admin routes.
- **Probes never persist.** Run each inside a transaction that is rolled back, with commit
  disabled.
- **Report, do not fix.** Every finding goes to the owner, then through the team chain.
  Anything about access goes to `security` to confirm.
- On a shared environment use the queue. A storm of deadlocks during someone else's run is not
  a hundred findings.

## What a crawl cannot see (read first)
1. **A forced click hides dead controls.** Automation that clicks regardless of click-through
   makes an unclickable control look clicked. A crawler also never types, pastes or presses
   keys, so a wrapper input that declares an event but never forwards it looks fine. These are
   caught by source scans and guard tests, not by the crawl.
2. **Refusals are usually not logged.** Not-signed-in, not-allowed and not-found responses often
   never reach the error log. Access gaps are invisible there: you must act as the persona and
   read the response.
3. **A page is a fan-out of endpoints.** The landing check sees only the calls made on load.
   Tabs and lazy panels call on click. For any page with tabs, list EVERY endpoint it can call
   and probe each per persona. Never certify a page from its first call.
4. **"Callable by anyone signed in" is the default risk.** An endpoint that takes an id from the
   caller and reads or writes with it, without a check that the caller may see that record, is
   suspect. List them, classify, then probe to confirm.

## Stage A: read-only crawl, every persona
1. Define the personas: one per role bundle, including a plain user with no extra role, a user
   of another customer, and a superuser as the control. Give each the role the route actually
   admits, not more.
2. Collect valid ids for routes with parameters.
3. For each persona and each route, record the landing outcome (reached, bounced for role,
   bounced to sign-in or elsewhere), every request with status, time and size, and every console
   and page error.
4. **Access grid**: persona by route, against the expected matrix copied verbatim from the
   route rules.
   - **Over-permit**: reached what its roles forbid.
   - **Under-permit**: bounced from what its roles allow.
   A route guard can fail open, so join a "reached" landing with the status of its load calls:
   a page that renders while its data is refused is a gap too.

## Request cost, per route
Report call count, unique calls, and:
- **the same call repeated on one load**: dedupe or cache it;
- **a call made on most routes**: it is refetched on every navigation; cache it for the session.
  If it is state the user changes, cache it AND invalidate it on that change;
- **the slowest calls** by high percentile, and **the largest payloads**;
- the difference against the project's budgets, when it has them.
The usual latency killer is a query per row inside a loop, not payload size. The fix is one
batched lookup, proven to return byte-identical output.

## Endpoint probes, both directions
For each sensitive endpoint, as a low-privilege persona:
- call it with ANOTHER customer's or user's id: it must refuse, and the refusal must not echo
  the record;
- call it with its OWN id, and as every role that should be admitted: it must still work.
Report the matrix (leak or deny per persona, endpoint and id). Deny-only testing is how a
permission fix ships a lockout.

## Stage B: click phase (after the backup)
Full clicks on ordinary user routes; destructive labels skipped on admin routes. Record what
opened, what errored, what did nothing.

## Sweep for what the crawl misses
- Source scans for the project's documented fault shapes, and its guard tests in one run.
- Layered controls: a list or picker inside a dialog that sits beneath it or does not take
  clicks; a dialog that closes when you pick inside it.
- Wrapper inputs that do not forward paste and key events.
- Option lists that can produce an empty value; content inside a collapsed section that is not
  mounted and so cannot be reached.

## Report
```
APP AUDIT: <environment> · <personas> personas · <routes> routes
ACCESS GRID:   over-permit <n>, under-permit <n>   (table: persona x route, expected vs seen)
REQUEST COST:  top repeated · on-most-routes · slowest · largest · over budget
PROBES:        <endpoint> — <persona> — foreign id: LEAK | deny — own id: ok | LOCKED OUT
SWEEP:         <fault> — <file:line> — confirmed | rejected (<why>) | stale
NOT RUN:       <what and why>
```

## Fix disposition
- **Safe to draft** (still through `executor`, with a test): a scan hit that has a guard-test
  precedent, a missing cache on a read-only call, a batched lookup with proven-equal output.
- **Report only, the owner decides**: anything that changes who may see or do what. Propose the
  guard, and require a regression test of the refusal AND of each allowed role, as that role and
  never as a superuser, shown red on the old code.
- **Tighten symmetrically.** The most common regression is a guard stricter than the read side
  it protects. Guard the public entry, not a shared inner function other callers rely on.
- A fix for a dead control is unverified until a person clicks it on a deployed test
  environment.
