---
name: ship-log
description: After a release, turn what shipped into the records the project keeps (completed tasks, changelog drafts, board cards for untracked work) by walking merged changes from a high-water mark, proposing one record per shipped unit, and writing only on the owner's 1. Use when the owner says "log this deploy", "draft the changelog", "create tasks for what shipped", or "the board does not show what is live".
---

# Ship log

Everything that reached production gets a record, exactly once. The mark in a state file says
where the last pass stopped, so nobody has to remember a starting point. This skill writes
records into the project's own systems; notes for readers are `release-notes`.

## The project must say (in its CLAUDE.md)
- Which records it keeps for shipped work (tasks, changelog entries, board cards), where they
  live, and the supported interface that creates them.
- The branch whose merges mean "shipped".
- The audience and tone of each record type.
- How a change links to an existing card or task (a token in the branch, title or body).
- Its classification scheme (for example feature, fix, improvement, internal), and how a record
  is dated when it has sprints or weeks.

If it names no record type, write the proposal to `<turn folder>/ship-log.md` and stop there.

## The state file
One small tracked file per record type (default `docs/<type>-state.md`, else under
`.handoff/`), holding `last_processed_head`, the last change id and the date. No state file
yet: start from the previous release merge, and say that you did.

## Procedure
1. **Scope.** The range the owner named (a change id, a commit range, a date), else everything
   after `last_processed_head` on the shipping branch. A backfill never moves the mark
   backwards.
2. **Collect** the merged changes with their titles, bodies and merge commits. Expand a merge
   that only carries other changes; never count a change twice.
3. **Shipped means shipped.** Only changes that reached the shipping branch. Merged to a
   development branch is not released.
4. **Match before you create.** For each change, look for a record it already has (by its link
   token, then by its change address). An existing record is updated or left alone, never
   duplicated. The change address is the idempotency key: a second run must create nothing new.
5. **Group** commits into one record per shipped unit (one per change, or one per feature when
   several changes ship one thing).
6. **Classify** each from its type and content. When unsure, say so in the proposal instead of
   guessing.
7. **Write for the record's reader:**
   - for people outside engineering: plain words, what they can now do or what was fixed, who it
     helps. No commit ids, file names, internal terms. One small reference line at the very
     bottom may carry the ids for traceability;
   - for internal readers: a little technical, the real change link, still one clear sentence
     first.
   Never copy customer or ticket text into a record.
8. **Print the proposal** as one table (type, date or sprint, change, title, and "new" or
   "exists"), and wait.
9. **On the owner's 1**, create the records through the supported interface in one batch. These
   are writes to a live system: route them through `devops` PROPOSE where the project requires
   it. Records that have a draft state are created as DRAFT; publishing is a human's step.
10. **Read back** what was created, report the counts (created, skipped as existing, failed),
    then move the mark and commit the state file with the owner's next commit.

## Tracked work that shipped without its link
A card can sit in the backlog while its code is live, because the change never carried the
card's token. Sweep for these separately:
1. **Candidates are not findings.** For each backlog card that looks shipped, verify: a merged
   change does what the card says, it is on the shipping branch, the behaviour is present in
   the current code, and no open change still works on it.
2. **Check for a twin**: an auto-created record for the same change beside the tracked card.
   Keep the tracked card and link the change to it.
3. **Its own approval.** Show card, title and evidence per row. Moving a card's status is a
   separate 1 from creating records, and it is given per card.
4. **Every candidate ends with a disposition**: moved, left (why), or needs a human. No
   unexplained remainder.

## Rules
- Idempotent: safe to run twice.
- Never change the status of an existing tracked record in the create steps. Only the sweep
  moves one, on verified evidence and its own 1.
- Never set priority, points or assignee, and never publish.
- A refused write is not retried blind: stop and report.
