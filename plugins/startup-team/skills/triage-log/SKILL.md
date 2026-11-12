---
name: triage-log
description: The append-only ledger of triage outcomes (support tickets and error clusters) and its format. Use when another skill (scan-errors, scan-tickets, reply-tickets) needs to check whether something was already triaged or to record a verdict, when the owner asks what was handled recently, or to add a manual entry.
---

# Triage log

One durable record of what was triaged, how it ended and why, so the same ticket or error cluster
is never worked out from scratch twice. `scan-errors`, `scan-tickets` and `reply-tickets` read it
before any verdict and append to it after one.

## The project must say (in its CLAUDE.md)
- Where the ledger file lives (a tracked notes file). If it names nothing, use
  `.handoff/triage-log.md`, say so, and tell the owner once that a tracked location would let the
  whole team share it.
- Which time zone its dates use. If it names nothing, use the machine's local date.

## Format
One Markdown table, newest row at the top:

```
# Triage log

Append-only record of handled support tickets and error clusters. Newest first.

| Date | Type | Ref | Status | Summary | Grounding / handled by |
|------|------|-----|--------|---------|------------------------|
```

- **Date**: ISO `YYYY-MM-DD`, so the table sorts by string. This is a log format, not the
  product's display format.
- **Type**: `Ticket` or `Error`.
- **Ref**: the ticket id for a ticket; for an error, the cluster signature plus one sample record
  id. For a finding that came from another source, a short descriptive ref
  (`Job log: nightly backup`, `Health: accounts with a disabled approver`).
- **Status** must match the Type:

| Type | Status | Meaning |
|------|--------|---------|
| Ticket | `Resolved` | Reply sent and the ticket closed |
| Ticket | `Replied` | Answer sent, ticket left open |
| Ticket | `Skipped` | No grounded answer was found; needs a person |
| Error | `Fixed` | A root-cause fix exists on a branch or pull request |
| Error | `Skipped` | Not actionable (transient, outside cause, deliberate behaviour) |
| Error | `Watching` | Real, but may already be fixed or too thin to act on; recheck next window |

- **Summary**: one line, plain words, no file paths.
- **Grounding / handled by**: the note, decision record, branch or commit, "verified by a data
  read", or the scan window that the verdict rests on, and who handled it when known.

## Rules
- **Append-only.** Handling a ref again adds a NEW row at the top. Never rewrite an older row. The
  topmost row for a ref is its current state; the rows below are its history.
- **One line per cell.** Strip newlines. Escape a literal `|` as `\|`.
- **Log decisions, not noise.** Only items that got a verdict from the owner, or that a skill
  actually acted on. Never the auto-hidden transient blips, never an item nobody decided.
- **No personal data.** Refer to the ref and the symptom. No names, emails, account or record
  contents: the file is committed.
- **Reject a mismatch.** `Fixed` on a Ticket or `Resolved` on an Error is refused.
- **Look refs up as fixed strings**, never as patterns: refs carry characters that a pattern
  search reads as operators. If a ref you expect is not found, suspect the search first and retry
  with a shorter fixed piece (the bare ticket id, the sample record id) before saying "never
  triaged".

## Appending (used by the other skills)
1. If the file does not exist, create it with the header above, and add a pointer to it wherever
   the project indexes its notes.
2. Build the row or rows, then insert them directly under the separator line, in one edit.
3. Do not commit the ledger on its own. It rides with the fix it records, or with the owner's next
   commit. When a fix is on a branch, its row belongs in that same branch.
4. Before appending, check the topmost row for the ref. If it already says the same thing (the row
   shipped with the fix), do not add a duplicate.

## Review (the owner asks what was handled)
1. **Read the whole table before summarising.** A count from a partial read is wrong. "The last
   ten rows" limits what you print, never what you read.
2. **Judge by current state only.** Group rows by ref and take the topmost row of each. An older
   `Replied` or `Watching` with a newer row above it is history, not an open item.
3. Print: the count by status, the most recent ten rows, then the items to act on: every ref whose
   current state is `Replied` (open, waiting to be closed) or `Watching` (due a recheck).
4. An item you did not check against the live system is labelled "log state as of <date>, not
   checked live". Never present it as confirmed open.
5. Review edits nothing.

## Manual entry
Given a type, a ref, a status, a one-line summary and an optional grounding (default
`manual entry`): validate the status against the type, then append as above with today's date.
This is for outcomes handled outside the scanning skills.
