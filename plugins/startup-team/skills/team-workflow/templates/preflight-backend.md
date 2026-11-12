# Builder preflight: backend
This is the short sheet the executor reads BEFORE a backend piece, instead of the project's long notes: one line per rule a build has actually broken, with a pointer to the note that explains why.
Copy it to `.claude/preflight-backend.md` in your project (or the path your CLAUDE.md names), replace every `<...>` line, and keep it under about 60 lines.

## Endpoints and guards
- <Where a new endpoint goes and the form it takes; which files are closed to new code.>
- <The guard every endpoint calls, and the order: scope first, then the record against that scope.>
- <Which read helpers apply no permission checks, and how such a read must be scoped.>
- <How a refusal is worded, and what it must never reveal.>
- <When bypassing a permission check is allowed, and what must come before it.>
- <Fields only the server may set, and how they are protected from the caller.>

## Data and transactions
- <How transactions, savepoints and rollbacks are done here; what is forbidden.>
- <Caches that can serve stale values, and how to measure or bypass them safely.>
- <What a schema change needs: who runs the migration, on which local databases, and when the
  tests that need the new column can run.>
- <How to check a field or column name before using it.>
- <What must be restarted after a backend change, and who does it.>

## Tests
- <The exact command for the narrow run, and the environment or database to run it on.>
- <What never to run per piece (the full suite), and where tests must never run.>
- <Fixture rules: how test data is created and cleaned up, what is forbidden in setup.>
- <Where a new test file is registered so the runner and CI pick it up.>
- <Known red tests, or where the brief lists them; any other red is the builder's.>
- <Performance checks: how a query ceiling is tested.>
- <The lint and format commands, with the pinned versions CI uses.>

## Notes
- <When a piece owes a line in the project's notes, the style, and where the index pointer goes.>
- <The check to run when a note is touched.>

## Commit
- <One commit per piece, `git add` by path; the files that are never part of a piece's commit.>
- <Where the subject comes from and what trailer is used.>
- <What the result file must carry for a backend piece (verify output, measured counts).>

## When unsure
- Return `BLOCKED: <one question>` with the evidence. Never assume, and never re-implement a
  helper that does not fit the brief.
