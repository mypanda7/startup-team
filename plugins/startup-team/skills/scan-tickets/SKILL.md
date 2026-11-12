---
name: scan-tickets
description: Triage support tickets by investigating each one (the ticket and its screenshots, the project's notes and decision records, the triage ledger, the code path, and a read-only check of the data) and return a grounded recommendation per ticket with a confidence level. Use when the owner pastes ticket ids, asks what is open in support, or wants to know whether a ticket is a bug, a known issue or a how-to. Read-only until the owner approves per ticket.
---

# Scan tickets

For each ticket in scope, find out what is really going on and say what you would do about it,
with the evidence. A keyword match against the notes is where the work starts, not where it ends.

## The project must say (in its CLAUDE.md)
- Where support tickets live, and the read-only way to list one with its thread and attachments.
- Which environment holds real tickets, and how it is reached from this machine.
- Where notes, decision records and the triage ledger live (see `triage-log`).
- Who tickets are assigned to by default, and what "assigned" means in this team.
- Whether attachments may be opened on this machine at all.

If it names no ticket system or no read path, stop and say what is missing.

## Scope
- **Ids given: only those ids.** No status filter, no cap, even if they are closed. Never widen a
  pasted list into a full scan.
- Otherwise: the open, actionable statuses, all assignees, highest priority first and oldest first
  within a priority, capped (default 20). Filters narrow it.
- Free text after the ids is an owner instruction. Honour it, but it lifts no approval gate for a
  ticket it does not name.
- State the resolved scope in one line before the first read.

## Guard rails
- **Read-only until approved.** No ticket, assignment, file or data changes during the scan. Data
  checks are plain reads, never a write and never a console that can write.
- **Production must be named** by the owner in this request. A refused read is not retried blind:
  stop and ask. Use `devops` ANALYSE where the project routes server access through it.
- **Personal data.** Tickets and screenshots carry names, pay and id numbers. Describe what an
  image shows in general terms; never retype such values into the report. The report stays in the
  conversation and the turn folder.
- **Attachments are opened only when asked**, within a cap (for example four per ticket, thirty
  per run). Name every ticket whose images were skipped or unreadable. Never copy customer files
  to a machine the owner has not approved for them.
- **Evidence before verdict.** A recommendation with no evidence block is a hypothesis: label it
  Low and name the check that would settle it.
- **No silent close.** A ticket is never closed on a match alone.

## Investigate each ticket, in order
1. **Read** the description, the thread so far and, when asked, the screenshots: one or two
   factual sentences each about the signal the text lacks (the error shown, the field circled).
2. **Match the notes.** Take the most frequent meaningful words of the subject and description,
   score each note by how many of them it holds, and keep a note that matches several distinct
   words. Then READ its relevant sections in full. A note can mark the symptom as a deliberate gap
   or an undecided product question, which changes the verdict. If nothing clears the bar, say
   "no note matches above the threshold", and use the ticket's category to pick where to look.
3. **Check the ledger** for the ticket id, the reporter or account, and the symptom. Read the
   whole rows.
   - Current state `Resolved` or `Replied`: already handled. Propose verify and close.
   - A `Fixed` row for the same class after the ticket was filed: the fix likely covers it.
     Propose "confirm on the current build, then close". If the fix ships in an app build, the
     reply asks them to update first.
   - A `Watching` or `Skipped` row for the class: a known issue with a standing decision. Quote
     it, say whether this is the recurrence it watched for, and recommend escalating that row.
4. **Check the decision records.** If one makes the reported "bug" intended, the recommendation
   is "behaves per <record>: reply with the rule, or reopen the decision". Never a fix.
5. **Trace the code path.** Find the screen text, route or endpoint the ticket names and read it.
   Write the mechanism as one sentence that could be proven wrong, and list every precondition it
   needs (a data shape, a role, a flag, a client version). Check recent commits for the same words:
   one may hold the fix, the regression, or a deliberate change.
6. **Verify against the data, read-only.** One check per precondition; write what you expected
   and what you found:
   - the reporter: account state, role, their other tickets;
   - the record the ticket is about;
   - the error log around the ticket's time (absence is evidence too);
   - the blast radius: how many others are in the same state, grouped by customer.
   If a check contradicts the mechanism, go back to step 5. Never ship a recommendation the data
   refused.
7. **Look for siblings.** The same lookup or gate usually exists in other places. List every call
   site: a fix that covers one door and not the others is half a fix.
8. **Rate confidence.** High: mechanism traced and every precondition confirmed. Medium: traced,
   partly confirmed. Low: from notes and words only. A Low is presented as "next check to run",
   never as a fix.
9. **Recommend one action, then the alternatives with their cost:**
   - **Code fix**: the place, the one-sentence change, the test that pins it, the sibling sites.
   - **Reply only**: a how-to or a rule. Give the gist as the customer's own steps in the product
     (screen, then button). Confirm the path exists; if it does not, that gap is a code fix.
   - **Data repair**: exact rows, count, whether it can be repeated safely. Prefer the customer's
     own path. A support-side write is the owner's call and is never promised in a reply.
   - **Product decision needed**: name the decision.
   - **Verify and close**: already fixed; say on which build.

With more than about three tickets, the work may be split one ticket per sub-agent; keep a short
id-scoped run inline so the owner sees the reasoning.

## Report
```
# Ticket triage: <scope> · <n> tickets

### 1. <id>: <subject>
- Filed:        <reporter's account type or customer> · <days> open · last touched <days> ago
- Status / priority / category / assignees:
- Attachments:  <counts; "not inspected" when images were off>
- Description:  > <first ~400 characters; "(truncated)" when cut>
Screenshots:           <one line each, general terms>
Known-issue status:    <the ledger verdict and date, or "no prior row for this class">
Governing note / decision:
Root cause (confidence: High | Medium | Low):   <the mechanism sentence>
Evidence (read-only):  <check -> expected vs found> ... Blast radius: <count>
Recommendation:        <one action, one sentence, why>
- Alternative: <..., cost>
- Sibling call sites / Verification / Related tickets and commits
```
End with: `Reply with the ids to fix, "close <id> <reason>", or "skip".`

## After the owner answers
- Approval is per ticket and names an action. "Fix A" does not cover B.
- **Fix**: re-read the note and the code, confirm the evidence still holds (a release may have
  landed), then hand it to the team chain: triage, `executor` on a branch, every sibling site,
  a test, `qa`, the audit. A data repair is a separate step with its own 1, through `devops`
  PROPOSE, never folded into the code change.
- **Close or reply**: use `reply-tickets`. It is an outward action and needs the owner's 1.
- Record each acted-on ticket in the ledger. If the class had a `Watching` row, close it out in
  the new row.
