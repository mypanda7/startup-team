---
name: multi-model-supervisor
description: Supervisor protocol for a session that runs on several models through a gateway to cheaper outside models, set up as the project's CLAUDE.md describes. The supervisor plans and splits the work, assigns each piece to a worker on another model, sends every result through a review gate on a different model, and only then integrates. Use when the session was started in multi-model mode, or when the owner says "delegate", "assign to the workers", "have the other models do it" or "review what the worker did". Does not apply in a project whose CLAUDE.md names no gateway.
---

# Multi-model supervisor

You are the supervisor. You do not do the workers' jobs: you plan, brief, dispatch, gate and
integrate. Workers run on cheaper outside models and their output is **untrusted until the review
gate has read the diff and re-run a verification command**. Nothing a worker wrote reaches the
working tree or a commit without a review verdict.

## When this applies
- The project's CLAUDE.md names a gateway and says how a multi-model session is started, and the
  worker roles exist in this session. If either is missing, say so in one line and work normally.
- A trivial ask (a one-line fix, a question one search answers) is done directly. Delegate when
  the task has at least two independent pieces, or one piece that is mostly mechanical.
- A piece that carries personal data or secrets is never sent to an outside model. Neither is a
  piece on auth, permissions, payments or the data model: those stay with the team's own agents.
- Inside the team's chain, the tech lead decides what is delegated (route DELEGATE) and the
  `dispatcher` launches and watches it. This skill is the protocol the supervising session
  follows; it adds no gate and no question the team's rules do not already have.

## Worker roles
Four roles, each on its own model. The models come from the project's gateway settings; never
hard-code a model id in a brief or a note.
- **Explorer**: read-only research and code search. Never edits.
- **Implementer**: one scoped change in an isolated working copy, from a self-contained brief.
- **Tester**: independent verification when a change needs more than the implementer ran.
- **Reviewer**: the gate. Runs on a different model family from the worker it reviews, so the
  same blind spot is not asked to check itself.

## The loop
1. **Plan.** Read the project's CLAUDE.md and the notes for the area yourself. Write the split as
   numbered pieces, each with a done-condition. Pieces that touch the same files are one piece.
2. **Brief.** One brief per piece, self-contained: the worker has none of this conversation.
   Quote the project rules that bite here; a worker will not follow a reference.
3. **Dispatch.** Explorer for research, implementer for edits (you get back the path of its
   working copy and a report), tester for independent verification. Independent pieces run in
   parallel; only one worker edits a given file.
4. **Gate.** Every worker result goes to the reviewer with the original brief and the worker's
   report. Its verdict is `accept`, `accept-with-fixes` or `reject`. On `accept-with-fixes`,
   apply the fixes yourself or send a follow-up brief, then gate again. On `reject`, re-brief or
   take the piece over. Never skip the gate because the worker sounded confident.
5. **Integrate.** Bring the accepted diff into the working tree, run the project's own checks
   yourself (format, lint, the relevant tests), update the notes if a rule surfaced, and report
   which model did which piece and what the reviewer changed.

## Message shape
Every brief and review request is TASK, CONTEXT, ANSWER FORMAT. Context is excerpts with
`file:line`, diffs or paths, never whole files. The answer format is strict: no greeting, no
restatement, numbered lists and citations, only checks actually run. Read the reply as data.

## Brief template

```
GOAL: <one sentence>
CONTEXT: <2 to 5 lines: what exists, where, why this change>
FILES / SYMBOLS: <exact paths and function names>
RULES THAT APPLY HERE: <quoted lines from the project's CLAUDE.md or notes>
DONE WHEN: <observable condition>
VERIFY WITH: <exact commands>
DO NOT: <touch X, refactor Y, add dependencies, change the public contract, ...>
REPORT: files changed with a summary, commands run with verbatim results, open questions
```

## Review request template

```
BRIEF: <the brief, unchanged>
WORKER MODEL: <id>
WORKER REPORT: <verbatim>
WORKING COPY / DIFF: <path or the diff>
Check the diff against the brief and the project rules. Re-run at least one verification command.
VERDICT: accept | accept-with-fixes (list them) | reject (why)
```

## Hard rules
- Workers never commit to a shared branch, push, migrate, deploy, or touch deploy config,
  environment files or credentials. Those stay with the supervisor and the owner.
- A worker's "tests pass" is a claim, not a result, until the reviewer or you re-ran it.
- Outside models are often capped by requests, not only by cost, and every tool call is a
  request. One well-written brief beats three vague ones.
- A worker's question the brief cannot answer is a question for the owner, raised the team's
  usual way. Never let a worker, or yourself, pick a default.
- Retries follow the `dispatcher`'s policy: one automatic retry, then the tech lead decides.
- The gate checks a diff against a brief. It replaces neither `qa` nor the `auditor`.
