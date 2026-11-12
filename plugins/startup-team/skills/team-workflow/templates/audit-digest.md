This is a TEMPLATE for a project's audit digest: the short list of standing rules the `auditor` checks, so it need not read the whole CLAUDE.md on every audit.
Copy it into your own repo as `.claude/audit-digest.md` (or a path your CLAUDE.md names), fill it in, and delete these two lines.

# Audit digest

<Two lines: what this file is for, and that each heading names where the full text of its rules
lives. The auditor opens that source only when a checklist item turns on wording missing here.
Keep the whole file under about 60 lines; one line per rule.>

## Machines, toolchain and tests (source: <CLAUDE.md section or note>)
- <How to tell which machine you are on (local, shared test box, production) and never guess.>
- <The exact test, lint and build commands per machine, and which site or database tests may hit.>
- <Traps in the test runner: filters that silently match nothing, where new tests must be registered.>
- <What must be declared in a result file when a test is loosened or skipped.>
- <Limits on shared machines: what may not run side by side, and which refusals are not failures.>

## Frontend rules (source: <CLAUDE.md section, design note or skill>)
- <What proves a screen change: the record, the widths to check, where screenshots are saved.>
- <Platforms the product ships on and what must be handled differently on each.>
- <The one approved way to fetch data, and the one approved component library.>
- <Formats the owner has fixed: dates, money, numbers, copy tone.>
- <Brand rules that are settled and must not be re-proposed: colours, type, spacing.>
- <Patterns banned outright, each with the search that must return nothing.>

## Backend rules (source: <CLAUDE.md section or note>)
- <Where new endpoints, models and jobs go, and where they must never go.>
- <What to check before using a field or changing a schema, and what a schema change needs after.>
- <Access rules: what must be authorised on every call, and what a refusal may reveal.>
- <Code style: formatter, linter, line length.>

## Security and data (source: <CLAUDE.md section or note>)
- <Secrets: where they live and what must never appear in a diff, a log or a report.>
- <Data that needs extra care (personal, financial, children's) and the rule for each.>

## Notes and process (source: <CLAUDE.md section or note>)
- <When a fix or a constraint must be written into the project's notes, and where the index is.>
- <Branch flow: where work branches from, what merges where, which branch deploys.>
- <Retry limit for delegated work and when the owner must be asked before another try.>
- <How the owner signals approval, and what always needs it.>
- <Checks the auditor must re-run word for word every time, with the commands.>

## Settled owner decisions (source: <where recorded answers live>)
- <A decision the owner has already made that agents keep reopening. One line each, no history.>
