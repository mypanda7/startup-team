# startup-team

A small expert team for Claude Code, packaged as a plugin. It gives any project the same way of
working: a tech lead triages every task, a designer gets the owner's approval before any UI is
built, an architect plans backend pieces, an executor builds one piece at a time, QA tests it the way a user would, an auditor checks
the result against the owner's own words, and devops proposes anything that leaves the machine.
Where the host can start sessions (the Claude desktop app), each role runs in its own session.

The team is project-agnostic. Everything specific to a project (brand, stack, hosting, standing
decisions) stays in that project's `CLAUDE.md`, and the project's rules always win.

## Install

```bash
claude plugin marketplace add mypanda7/startup-team
```

```bash
claude plugin install startup-team@startup-team --scope local
```

Update later with:

```bash
claude plugin update startup-team@startup-team
```

## What is in it

| Part | What it does |
|---|---|
| `agents/tech-lead` | First stop. Splits a task into pieces, lists the open questions, names the route and model per piece. |
| `agents/designer` | PROPOSE, BRIEF and REVIEW modes. No UI is built before the owner's 1. |
| `agents/architect` | Plans API, data model, auth and job pieces before the build. |
| `agents/executor` | Builds one piece from a brief. One local commit. Never pushes. |
| `agents/qa` | Runs the product and walks every case. PASS or FAIL with steps to reproduce. Never fixes. |
| `agents/auditor` | PASS or FAIL against the owner's request, with evidence it re-ran itself. |
| `agents/devops` | Read-only analysis, and proposals for every push, deploy or server change. |
| `agents/security` | Security analysis of the owner's own project. Findings only, no fixes. |
| `agents/skill-sub` | A read-only helper that answers one narrow question for another agent. |
| `skills/team-workflow` | The chain for the main session, plus `scripts/team.py`. |
| `commands/` | `/startup-team:triage`, `:design`, `:qa`, `:audit`, `:learn`. |
| `hooks/` | The team gate: on every request of 8 words or more it reminds the session to triage with the tech lead first. |

### The team gate

The gate only adds a reminder; it never blocks a prompt. It stays quiet for slash commands, pasted
terminal output, short replies, and any request that starts with `quick:`, and the briefs of role sessions. Set
`STARTUP_TEAM_GATE_OFF=1` to turn it off for a session. It needs Python on the PATH; without one it
does nothing.

## How a task runs

1. A turn folder is created for the task in the project's git-ignored `.handoff/`.
2. The tech lead returns a decision block: pieces that are clear now, questions, blocked pieces.
3. Questions go to the owner one at a time, with options and a recommendation. An answer is final.
4. UI pieces get a design proposal and the owner's 1. Backend pieces get a plan.
5. The executor builds each piece and commits it locally.
6. QA runs the product and reports bugs with steps. Fixes go back to the tech lead.
7. The auditor checks the whole turn. Fixes go back to the tech lead.
8. Devops proposes the push or deploy. The owner approves it.

## One session per role

In a host that can start sessions, every run of the tech lead, designer, architect, executor, QA,
auditor, devops and security opens as its own session that the owner can open, steer and stop. The
main session briefs each one, waits for it, and reads the file it leaves in the turn folder.
Questions and approvals still come to the owner in the main session, one at a time.

Role sessions share the project's checkout, so only one session that writes source runs at a time;
the read-only ones may run side by side. Without a session tool (the plain CLI), or when the owner
says "here" or "no sessions", the same chain runs with sub-agents. `skill-sub` is always a sub-agent.

## Shared memory

`team.py memory` keeps one append-only file per project (`.handoff/memory/agent-memory.jsonl`) with
owner answers, facts, open items, pointers and learned notes. Its digest goes into every brief.
Text that looks like a secret is refused.

## How the team learns

Day-to-day notes stay in each project. A rule worth sharing travels like this:

1. An agent or the main session proposes it in generic words (`team.py learn propose`).
2. The tool refuses it if it holds a secret, an email, an IP or web address, a local path, the
   project's own name, or any word in the project's `.handoff/private-words.txt`. No rule leaves a
   project before that list exists.
3. The owner answers 1 or 0.
4. `team.py learn apply` checks the text again, adds one line to
   [LEARNED.md](plugins/startup-team/skills/team-workflow/LEARNED.md) and raises the plugin version.
5. The change is committed on a branch that the owner merges. Every project picks it up on its
   next plugin update, and the main session passes the rules into each agent's brief.

Only that one line leaves the project. Evidence, turn folders, memory and the proposal log stay in
the project's git-ignored `.handoff/`.

## Keeping projects out of this repository

This repository is public and shared across projects. Nothing about a single project, its owner,
its users, its hosts or its secrets belongs here, in a file or in a commit message.

Maintainers: install the push guard in your clone, and list your projects' private words in a file
that never leaves your machine.

```bash
cp tools/pre-push .git/hooks/pre-push
```

Then write one word or phrase per line into `.git/private-words.txt`. The guard refuses any push
whose commits (files or messages) contain one of them.

## Requirements

Claude Code, git, and Python 3.9 or newer for `team.py`.
