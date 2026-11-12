# Builder preflight: frontend (TEMPLATE)
What this is: the one short sheet a builder reads BEFORE a frontend piece, instead of the long docs.
Where to keep it: copy it into your own repo at the path your CLAUDE.md names for it (for example
`.claude/preflight-frontend.md`), fill in every `<...>`, and delete this paragraph and any heading
you have nothing for.

Rules for filling it in: keep it to one screen. One line per rule, in the imperative. Only rules a
build has actually broken or would plausibly break. Each line may end with a pointer to the longer
file that carries the why ("-> <file>, only when you touch <thing>"), so the builder opens that
file only on that line.

## Non-negotiables
- UI building blocks: <the one component library or set of primitives every control uses; what is
  banned (native dialogs, a second library); which existing shell a new dialog or menu reuses>
- Data fetching and state: <the one way screens load and change data; where shared keys or stores
  live; what is never done by hand>
- Framework traps: <the two or three mistakes this framework punishes that a newcomer makes>
- Formats: <how dates, times, money and numbers are shown and typed; the shared helpers to call;
  the native inputs that are not allowed>
- Colours and themes: <where the tokens live; never a raw value where a token exists; which themes
  every change must cover>
- Widths and touch: <the widths every screen is checked at; the minimum touch target; no
  hover-only action>
- Access: <where "who may see this screen" is declared, and every place that must agree with it>
- Styling rules: <anything about scoped styles, layered content or naming that breaks silently>
- Names and wording: <product or brand spellings, constants to use instead of literals>

## Shared components that already exist
<List the components that already take a variant or kind, where their options are defined, and the
rule: add a variant, never a copy. Say which screens must not change behaviour when one gains a
variant.>

## Tests
- Per piece: <the command that runs only what this change reaches>
- Last piece of a feature: <the full-suite command, and when it is allowed>
- Never: <the invocation that can silently match nothing or rewrite unrelated files>
- Environment: <runtime version, the folder to run from, where a new test file must be registered>
- What a green run does NOT prove: <what the test setup stubs out, and who does the real-browser
  pass>
- Lint: <the command for the changed files only>

## Commit
<One commit per piece; stage by path, only this piece's files. Name the files that are always
dirty and must never be swept in. Say what the result file must contain: files changed, the tail of
each check, the commit id, who does the browser pass, deviations from the brief.>

## When unsure
<Stop and return the question with the evidence. Never widen the brief. Never pick a default for
a point the design or the owner has not settled.>
