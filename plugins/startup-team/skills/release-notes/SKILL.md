---
name: release-notes
description: Write release notes from the real commit history, in two forms - short store or version notes with a hard length limit, and a plain-language "what's new / what's fixed" digest for non-technical readers. Use when the owner asks for release notes, patch notes, a changelog entry or "what shipped lately". For a narrative announcement to customers or the team use `announcement`.
---

# Release notes (from history, never from memory)

For the main session. This skill edits one notes file and nothing else: it does not commit, tag,
push, build or deploy. Shipping the file goes the normal way (`wrap` or `ship`, through `devops`
PROPOSE and the owner's 1).

## The project must say (in its CLAUDE.md)
- The file each form is written to, and whether newest goes on top.
- Any length limit and wrapper format (for example an app store's character cap and locale tag).
- How versions are tagged, and the product names users know features by.
If it names no file, show the notes in chat and ask the owner where they go. Create nothing
unasked.

## Pick the form
- **Version notes.** Short, user-facing, keyed to a version, inside the project's length limit.
  Only what a user will notice: features, fixes, visible changes. No refactors, tests or tooling.
- **Digest ("what's new").** A plain-language summary for internal non-engineers (operations,
  support, sales, QA) of what was implemented and what was fixed over a range.
Both may be written over the same range.

## 1. Fix the range, and say it
Resolve in this order and echo the range and the commit count before writing:
1. an explicit range the owner gave;
2. "since" a version tag, a named change, or a date;
3. default: everything since the last entry. Each digest entry ends with a hidden high-water
   marker (the last commit it covered); the next run starts there. No marker: fall back to the
   last version tag, then to the last merge into the live branch.
For version notes, confirm the previous tag with the owner. If you are not on the live branch,
say so and ask; do not switch branches on your own.

## 2. Collect, and drop the noise
Take the non-merge commits in the range. Drop lint, format, dependency-bump and notes-only
commits. For anything you cannot describe with confidence, read the change itself: a branch name
or a terse subject tells you nothing about what a user sees. If nothing user-facing is left, say
so and stop. Never write an empty entry.

## 3. Bundle and classify
- One bullet per shipped feature or fix, not per commit. Fold follow-ups into their feature.
- Group by area (the commit scope, or the feature's product name).
- Two sections: **Fixes** (fix-type commits, anything about a regression) and **New and improved**
  (everything else). A mixed group goes with its majority; a tie goes to Fixes.
- Leave out a section that is empty.

## 4. Write for the reader
- Start each line with the outcome for the person using the product: "People can now see how each
  amount was calculated", not the name of the code that does it.
- No commit ids in the body, no file, function, table or endpoint names, no words like refactor,
  payload, migration or regression. Use the product's own feature names.
- One sentence per bullet; a short nested list only for real sub-points.
- Version notes: count the characters against the limit before showing them.

## 5. Shape of a digest entry
```
## <date>
_Summary of changes shipped since <previous entry or range>._

### New and improved
- <outcome>

### Fixes
- <outcome>

<one muted line: N changes, the range, a few short commit ids>
<hidden marker: the last commit covered>
```
The marker is load-bearing: always set it to the end of the range.

## 6. Confirm, then write
Show the rendered text. Write only after the owner's 1 (or their edits). Add the entry in the
project's order (newest on top unless it says otherwise), then show the diff.

## Rules
- Every line traces to a real change in the range. Never invent, never pad.
- Only what is in the range, and for version notes only what will be in that version's build.
- Never rewrite or reorder older entries. Never move the marker backwards for a backfill.
- Do not run the project's release or build script: the owner runs it after approving the notes.
