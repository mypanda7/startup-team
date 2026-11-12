TEMPLATE: a project's routing digest, the short file the tech lead reads instead of the whole CLAUDE.md when it routes a task.
Copy it to `.claude/routing-digest.md` in your project (or name another path in your CLAUDE.md), fill each heading, then delete these two lines.

# Routing digest

Read this when routing. It carries only what a routing decision needs. It does NOT replace
CLAUDE.md when a piece is built: a piece that touches any item below reads the full rule first.
Keep it under 60 lines; it is read on every request. One line per fact, each pointing at its source.

## Where work runs and how it is checked
<!-- One line per environment (local, shared, staging, production): how to tell which one you are
     on, and what must never run there. -->
<!-- The test commands: the narrow run for one piece, the full run, and which of them are slow,
     shared or must never run two at a time. -->
<!-- The lint, format, build and notes-check commands a VERIFY line should name. -->

## What keeps a piece HERE
<!-- The areas where a wrong change is costly and judgement is needed (for example auth, money,
     migrations, deploy files). One line per area, with the file or folder pattern that marks it. -->
<!-- Kinds of work whose "done" needs a browser, the owner's eyes, the local stack, a database
     change or credentials. -->
<!-- Rules that span several places (a guard that must exist on every door of a kind, a pattern
     that tests cannot prove), each with the CLAUDE.md rule or note that holds the full text. -->

## Rules a brief must QUOTE
<!-- The project rules a builder will not know unless the brief states them. One line each:
     where new code of each kind goes, the required libraries and patterns, formats for dates,
     money and copy, code style, where a new test must be registered, where notes go. -->

## Where the answers already are
<!-- The index of the project's notes or decision records, and one line per subsystem naming its
     note. A fact documented there is never a question for the owner. -->
<!-- The code index or graph tool, if the project has one, and how to check it is fresh. -->
<!-- Where recorded owner answers live besides the shared memory. -->

## Standing owner decisions
<!-- Decisions that hold for every task until the owner changes them (for example which branch
     work lands on, what never ships without a 1, what is never asked again). One line each. -->

## Design
<!-- Where the design rules and approved designs live, and what counts as an approved design. -->

## Delegation (delete this section if the project has no gateway to cheaper outside models)
<!-- The command that shows whether the gateway is up and what allowance is left. -->
<!-- What may be delegated, what never is, the limits per minute and per day, and where the
     recorded outcomes per model are kept. -->
