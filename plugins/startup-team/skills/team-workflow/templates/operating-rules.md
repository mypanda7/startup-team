# Operating rules

<!--
Copy this file to .claude/operating-rules.md in your project and fill it in. The startup-team
hooks read it; until you replace the <placeholders>, they print nothing.

How it is used:
- The lines under the first heading (this section) are the FULL block. It is shown to the
  session once, on its first prompt. Keep it under about 1500 characters: only the rules that
  must never be broken, and the facts a session gets wrong when it guesses.
- Each "DIGEST:" line is the short form, repeated on every later prompt. Two lines at most.
- "NOTES:" names the folder that holds the project's notes, relative to the project root. With
  it, the session is pointed at the notes index when it starts (an INDEX.md or README.md in that
  folder; a section whose heading contains "router" is shown in full), at the note whose file
  name matches the prompt, and is reminded to update the notes when it changed files.
- "ROUTE:" is optional, one per line: words that should lead to one note when its file name
  alone would not match.
- Comments like this one, and any line still written as a <placeholder>, are ignored.
- Never put a secret, password or token in this file: it is injected into every session.

Good rules are short, imperative and checkable. Typical subjects:
- which environment this checkout is, and how to check instead of assuming;
- what must never be run here (tests against live data, migrations, deploys);
- the commands to use for tests, lint and build, and the ones that fail on this machine;
- where to look before asking the owner a question.
-->

- <rule 1: the environment this checkout runs in, and the command that confirms it>
- <rule 2: what must never be run or changed without the owner's 1>
- <rule 3: the test, lint and build commands to use, and any that must not be used>
- <rule 4: where answers already live (CLAUDE.md, the notes folder) to check before asking>

DIGEST: <line 1: the one or two rules that matter most, in under 200 characters>
DIGEST: <line 2: optional; the next most important rule or the place to look things up>

NOTES: <folder with the project's notes, for example docs/notes>

ROUTE: <word, word, word -> note-file.md>
