---
name: scan-errors
description: "Scan an environment's error log over a time window, cluster the rows into a ranked triage report, skip what was already triaged, and stop for the owner's verdict per cluster. Use for \"what broke in the last 24 hours\", a periodic health sweep, or before deciding which errors deserve a fix. Read-only: fixes go through the team chain after the owner's 1."
---

# Scan errors

Read the error log, group the rows by cause, check each group against what the project already
knows, and hand the owner a report they can answer with numbers. You report; you do not fix.

## The project must say (in its CLAUDE.md)
- Where errors are recorded and the read-only command that reads them, per environment.
- Which environments exist, which one is production, and how each is reached from this machine.
- How a row is marked as already looked at, if the log has such a mark.
- Where its notes, decision records and the triage ledger live (see the `triage-log` skill).
- Optional: other failure sources (failed scheduled jobs, undelivered mail, process logs on disk)
  and any data-integrity checks worth running.

If it names no error log or no read command, stop and say what is missing. Never guess a command
against a live system.

## Guard rails
- **Read-only.** The scan edits no file, marks no row as seen and deletes nothing. Changing the
  log is a separate request.
- **Production must be named.** If the target is production only because it is the default, stop
  and ask before the first read. A tool that happens to allow the call is not the owner's consent.
  Run the read as `devops` ANALYSE when the project routes server access through it.
- **A refused command is not retried blind.** Stop, say the read is read-only and what it may pull
  into the conversation, and wait for the owner's go.
- **Personal data.** Error bodies carry user data. The report stays in the conversation and the
  turn folder. Never in a commit message, a pull request or an outside tool.
- **A clean scan proves little.** The log only holds what threw. Wrong results that raise nothing,
  dead buttons, and most refused requests (not signed in, not allowed, not found) leave no row.
  Say so when the owner reads a clean scan as "it works".

## Procedure
1. **State the run in one line**: environment, window (default the last 24 hours), how many
   clusters to show (default 10), whether already-seen rows are included, which extra sources.
2. **Compute the window in the log's own time zone.** A database clock and the stored timestamps
   can differ by hours; take the cutoff from the application's clock and pass it in as a value.
3. **Read once.** Put every read for this scan into one authorised call where you can.
4. **Cluster by signature**, not by raw text:
   - structured client errors: kind + component or endpoint + message + route, query string cut;
   - stack traces: the last meaningful line, with ids and long numbers replaced by placeholders;
   - skip fields that are unique per row (timestamps, session ids) or every row becomes its own
     cluster;
   - an empty body falls back to the row's title or method, never one "no signature" bucket.
5. **Per cluster record**: count, seen and unseen, first and last time, distinct sessions or users,
   the build or version that produced it, one sample id and the last dozen lines.
6. **Hide clusters whose rows are all marked seen**; print one line saying how many were hidden.
7. **Extra sources, when asked.** Report failed scheduled jobs grouped by job, and undelivered
   mail grouped by error. Pair a failed job with its error cluster and report them as ONE finding.
   A job that fails every day at the same minute on the same record is poisoned by that record:
   the fix is the record plus a skip-and-log guard, not the job's main path.
8. **Health checks, when asked**: read-only queries for states that should never exist (a live
   record pointing at a disabled one, overlapping ranges, a declared field with no column).
   A check that mostly returns false alarms is worse than none: exclude the known harmless shapes.

## Before any verdict: the notes check (mandatory)
For every cluster, search two layers and write the result on its `Notes check` line:
1. **The ledger**: was this signature decided before?
   - `Fixed`, and the new rows all come from builds older than the fix: already fixed, clients not
     yet updated. Verdict Skip or Watch.
   - `Fixed`, but recurring on the current build: the fix regressed or was incomplete. Rank it up,
     then read the note first: it may be the fix's documented, accepted leftover.
   - `Skipped` or parked: do not re-derive it. Report the new count and re-surface the decision.
2. **The project's notes and decision records** for the subsystem: a documented rule the failing
   call breaks (the fix is the missing call site), a deliberate design that accepts this cost
   (inherit Skip or Watch), or an owner decision on record (re-surface, never re-open).
A verdict that contradicts a note says so and names the note.

## Classes worth knowing
| Shape | Usual cause | Default verdict |
|---|---|---|
| "Not allowed" for a signed-in user on a screen their role can reach | The screen admits a role the server refuses | Fix: the most common real bug |
| "Not allowed" from an idle tab, session expired | A poll after sign-out | Skip, or harden the call site |
| Validation message logged as an error | Expected input errors sent to the error log | Fix the logging or Skip |
| Missing column or table, unknown attribute, right after a release | Code ahead of the schema | Deploy-window Skip, or Fix the migration |
| Empty 5xx, connection failed, one session, a hidden tab | Restart, network, a suspended tab | Skip unless several sessions outside a deploy window |
| Module failed to load, on an old build | A client still on the previous build | Watch |
| Stack inside a browser extension | Third-party script | Skip |
| Mail that never left | Bad recipient, bad attachment, one bad row aborting the batch | Fix |
| The same job failing daily | Expired outside credentials, or an exception nobody sees | Fix or escalate |

Also check: a cluster wholly inside a few minutes of a deploy or restart is tagged
`[deploy-window transient]`; one session with many rows is a burst, not a recurring bug.

## Report
```
# Error scan: <environment> · <window> · <rows> rows · <n> unresolved clusters
> <k> already-triaged clusters hidden.

## 1. <count>x (seen <s>/<count>, <sessions> sessions): <signature>
- First -> last:
- Build(s):            <and "older than the current build" when true>
- Sample:              <record id>, then the tail
- Class:
- Notes check:         <ledger and notes result, or "no prior">
- Suspected location:  <file:line when the trace names project code, else "unknown">
- Likely cause:        <one sentence>
- Proposed action:     <one sentence, or "needs investigation", or "skip: <why>">
```
End with: `Reply with the numbers to fix, "all", or "skip".`

## After the verdict
- **Wait.** No file is edited before the owner answers. Approval is per cluster: 1 does not cover 2.
  A remedy that changes data needs its own separate 1, through `devops` PROPOSE.
- **An approved fix is a task for the team chain**: triage, then `executor` on a branch, the
  smallest change that removes the root cause, a regression test for logic, then `qa` and the
  audit. Read the file the trace names in full first: the trace shows the symptom line.
- **Record each decided cluster** in the ledger (`triage-log` skill): `Fixed`, `Skipped` or
  `Watching`. Undecided clusters and hidden blips are not logged.
