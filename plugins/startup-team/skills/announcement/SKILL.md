---
name: announcement
description: Write an announcement of what shipped, for one of three readers - customers (benefit-first, only what is live and visible, no internals), the whole team (the same plus internal-only tools), or internal stakeholders (the full status, live or not, with open decisions). Use when the owner asks to announce changes, write a customer update, a team update or a stakeholder update. For a terse changelog use `release-notes`.
---

# Announcement (what shipped, for a named reader)

For the main session. This skill writes a text file and shows it in chat. It sends nothing:
posting or mailing an announcement is the owner's act, or a separate step with the owner's 1.

## The project must say (in its CLAUDE.md)
- Where announcements are saved and how the files are named.
- The product's name for each feature and role, in the words users see.
- How to check that something is live (a version marker, a served page), and the live branch.
- The closing line and sign-off the product uses, and where readers report a problem.
If it names no folder, show the text in chat and ask where to save it.

## 0. Settle three things first, and print them
**Reader (the mode).**
- `customer` (default): paying users. They read it as a promise. Only what is LIVE and only what
  a user can SEE.
- `team`: everyone on the owner's team, many not engineers. The customer text plus the tools only
  staff can see or use. Still only what is live and visible to someone.
- `stakeholder`: owner, operations, client-facing people, a new engineer. Everything that moved,
  live or not, with the why. May name subsystems.
No mode given: use `customer` and say so in one line, so a wrong default is cheap to correct.
The modes are not one text at three reading levels. A held release is invisible in `customer` and
`team`, and is the headline in `stakeholder`. If the reader is "the team chat", write `team`: an
internal-only feature left out of the customer text is exactly what the team needs to hear.

**Source.** An existing write-up the owner points to (then do not re-derive, but still verify
live against merged), or the history over a range.

**Range.** A date, a range, a month, or a phrase. Resolve relative phrases against the real
clock, never an assumed date. Default: from the last saved announcement to now. If the range holds
only a handful of user-facing changes, say so and offer a wider one rather than padding.

## 1. Read the real changes
List what merged in the range and read each change's title, and its description when the title
does not tell you what a user sees. Branch names lie. Never describe a change you have not read.
For `stakeholder`, also read what sits unreleased on the integration branch.

## 2. Filter per mode
- `customer`: drop CI, docs, chores, tests, refactors, logging, deploy tooling, and internal fixes
  with no visible symptom. Keep whatever changes what a user sees, can do, or must stop doing.
- `team`: the customer filter, then put back whatever staff can see or use (internal sections,
  back-office screens, role-gated tools). Say who each is for.
- `stakeholder`: keep test, CI and infrastructure work only where it produced a result worth
  telling (a measured speed-up, a test that was passing falsely, a rule now written down).

## 3. Honesty rules (the point of this skill, in every mode)
1. Anything REMOVED or DEGRADED gets its own line in the same voice as a feature: what happened,
   why, what is unaffected, what comes next. If a third party ended a service, say that.
2. Never claim or imply data was lost when it was not, and never imply nothing changed when
   something did.
3. Merged is not deployed. `customer` and `team`: verify each item is live before it goes in.
   `stakeholder`: label every item live, on the integration branch, or held; a held release gets
   its own section with what blocks it and what that means meanwhile.
4. A finding is not an incident. Something found by reading code, not reproduced, says so in the
   same sentence.
5. Lead with the benefit, then the mechanism.
6. Calm words. Lead with reassurance; no alarm vocabulary; never imply the reader or a colleague
   did something wrong.
7. What you could not verify is left out, not hedged.

## 4. Write
**`customer`.** A title with the human date or range. Two to four opening sentences: the headline
change, the shape of the rest, and anything removed, so nobody is ambushed further down. Then
sections with benefit-first headings, grouped by what the reader DOES, not by how it was built.
Prose; bullets only for real lists. Close with the project's report-a-problem line and sign-off.
Zero internal vocabulary: no change or ticket ids, table, endpoint or flag names, no identifiers
in code style; roles in the words a person would use. Length follows the range; never pad.

**`team`.** Same structure and voice. Mark the title as the team edition. Each internal-only item
is its own section that says who it is for in its first sentence. Close with where the team
reports issues. The sections shared with `customer` match it word for word: `team` is a strict
superset.

**`stakeholder`.** Header (from, window, audience) and a one-line summary a busy reader can stop
at, release status included. Then: what customers already have; what is built but not yet with
customers; fixes worth naming; testing and infrastructure; what shipped and when (or why the
release is held); open items and decisions needed.
- Every claim carries its consequence for a user or the business.
- Name a subsystem in words, never a symbol, a path or a code block.
- Numbers earn their place: keep the measured ones, drop the vague ones.
- The last section is the deliverable: each open question on one line, with who decides.
- A hold is a hold, not a failure and not a rollback. Not-yet-live never reads as shipped.

## 5. Check, save, and show the exclusions
Before saving: mode stated; live items verified or labelled; every removal named; findings marked
as findings; the vocabulary ban holds for the mode; no false alarm and no false reassurance.
Save where the project says and show the full text in chat. Then list what you EXCLUDED and why,
one line each: that list is how the owner catches a user-facing change filtered out by mistake.
