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
| `agents/skill-sub` | A read-only helper that answers one narrow question for another agent, using one named skill. |
| `agents/dispatcher` | Launches and watches pieces delegated to cheaper outside models through a gateway. Does nothing without one. |
| `agents/messenger` | Carries one question to, or reads replies from, a channel outside the app that the project names. |
| `agents/video` | Builds and renders video in code from an approved brief. |
| `skills/team-workflow` | The chain for the main session, plus `scripts/team.py`, the skill roster (`ROSTER.md`) and the project templates. |
| `skills/` (the rest) | Shipping, testing and operations skills: see "Skills" below. |
| `commands/` | `/startup-team:triage`, `:design`, `:plan`, `:qa`, `:audit`, `:dispatch`, `:learn`, `:companions`, `:start-team` (starts the standing sessions). |
| `sessions/` | The standing briefs for the Tech Lead, Business Analyst, Designer, Developer, QA Engineer, DevOps and Security sessions. |
| `hooks/` | The team gate, plus the project's operating rules and notes reminders: see "Hooks" below. |

### Hooks

| Hook | Runs on | What it does |
|---|---|---|
| `setup-offer` | first prompt of a session | Until the project has `.handoff/team-setup-done`, asks once per session whether to run `/startup-team:start-team` (1 = yes, 0 = ask again next session). |
| `tech-lead-gate` | every prompt | Reminds the session to triage first: the full text once per session, two lines after. |
| `operating-rules` | every prompt | Prints the project's own non-negotiable rules and points at the most relevant project note. |
| `notes` | session start, first prompt, stop | Points at the project's notes index, and reminds the session to update notes when code changed and no note did. |

No hook ever blocks a prompt. They need Python on the PATH; without one they do nothing.

The gate stays quiet for slash commands, pasted terminal output, agent reports, short replies, a
single short question with no build verb, and the briefs the team sends to its role sessions and
standing sessions (they start with `[startup-team:`). A request that starts with `quick:` skips
triage; QA and the auditor still run.

The rules and notes hooks print nothing until the project has a `.claude/operating-rules.md`
(copy `skills/team-workflow/templates/operating-rules.md` and fill it in).

Switches, set to `1` for a session: `STARTUP_TEAM_GATE_OFF`, `STARTUP_TEAM_GATE_FULL` (always the
full gate text), `STARTUP_TEAM_RULES_OFF`, `STARTUP_TEAM_NOTES_OFF`. `STARTUP_TEAM_RULES_FILE`
names another rules file.

## How a task runs

1. A turn folder is created for the task in the project's git-ignored `.handoff/`.
2. The tech lead returns a decision block: pieces that are clear now, questions, blocked pieces.
3. Questions go to the owner one at a time, with options and a recommendation. An answer is final.
4. UI pieces get a design proposal and the owner's 1. Backend pieces get a plan.
5. The executor builds each piece and commits it locally.
6. QA runs the product and reports bugs with steps. Fixes go back to the tech lead.
7. The auditor checks the whole turn. Fixes go back to the tech lead.
8. Devops proposes the push or deploy. The owner approves it.

## Sessions

In a host that can start sessions (the Claude desktop app), the team works in two kinds of session.

- **Standing sessions** are long-lived: one Tech Lead session per project and, under it, up to six
  sub sessions (Business Analyst, Designer, Developer, QA Engineer, DevOps, Security), started once and used
  for every task.
- **Role sessions** are opened for one run of a role and end with it, so the owner can open, steer
  and stop each run on its own.

They fit together like this. When the project has a Tech Lead session, the tech lead, designer, executor
(as the Developer), QA, devops and security work in the standing team, and no role session is
opened for them; otherwise they open a role session like the others. The architect's and auditor's
work goes to the Tech Lead session, and opens a role session only when there is none. `skill-sub` is always a sub-agent, and the Business Analyst is only ever a sub session.

### Standing sessions

`/startup-team:start-team` renames the session you run it in "Tech Lead", so your main session is
the Tech Lead, and starts its sub sessions under it in the Claude desktop app's sidebar, each from
its brief in `sessions/`, in the project's own folder (never a worktree). The app only lets a turn the owner started call `start_session`, so
a separate Tech Lead session, whose turns are always started by a message, could never start them. Pass any of
`business-analyst`, `designer`, `developer`, `qa`, `devops` or `security` to start only those sub
sessions.

```
Tech Lead (your main session)  triages, plans, audits
    ├── Business Analyst asks the owner one question at a time
    ├── Designer         proposes, briefs and reviews UI
    ├── Developer        builds one piece at a time, one local commit each
    ├── QA Engineer      runs the product, PASS or FAIL
    ├── DevOps           proposes every push or deploy
    └── Security         analysis only
```

The Tech Lead is your main session: it triages, plans and audits there, and messages each sub
session directly. A project may instead keep a separate Tech Lead session (`start-team` asks when
it finds one); then the main session sends it each request, and it relays to a sub session only as
a backup, when the main session cannot find or reach one. The owner can type to any of them
directly.

| Session | What it does | Main session uses it for |
|---|---|---|
| Tech Lead (main session) | Triages, plans backend pieces by the `architect` method and audits each turn by the `auditor` method; starts and leads the sub sessions. Never builds, edits source, commits or pushes. | Each request (a decision block), each plan and each audit. |
| Business Analyst | Relays questions to the owner one at a time and sends each answer back verbatim. Never answers or decides. | Question batches. |
| Designer | Proposes, briefs and reviews UI by the `designer` agent's method. Never builds. | Every design step. |
| Developer | Builds one piece at a time from a brief by the `executor` agent's method, with one local commit each. Never pushes or deploys. | Every build piece. |
| QA Engineer | Runs the product and reports PASS or FAIL with steps to reproduce. Never fixes. | Testing, once the pieces are built. |
| DevOps | Read-only analysis, and proposals for every push or deploy. Runs nothing before the owner's 1. | Shipping and server checks. |
| Security | Analysis only: findings by severity, fixes as proposals for the owner. | Security checks. |

A session exists for a role when there is a non-archived session whose `cwd` is the project's folder (compared ignoring case, slash direction and a trailing slash; a worktree or subfolder does not count) and whose title contains the role's title, ignoring case and spaces, found with `list_sessions` and messaged by its session id. A session whose title starts with `[run]` is a role session and never counts as a standing session.
An existing session is used, whoever started it, and a second one is never started. If more than
one session matches a role, they are listed and the owner says which one to use. The command renames
the session it runs in "Tech Lead" and starts only its six sub sessions, and no other session
starts them. Only the
Developer session writes source.

### Role sessions

The main session briefs each role session, waits for it, and reads the file it leaves in the turn
folder. Follow-ups for the same piece go back to the session that already has the context. Role
sessions never ask the owner anything themselves: their questions go to the Business Analyst
sub session when there is one, and otherwise the main session asks them, one at a time. Approvals come
to the owner in the main session.

Role sessions share the project's checkout, so only one session that writes source runs at a time;
the read-only ones may run side by side.

### Without sessions

Without a session tool (the plain CLI), when a session cannot be started, or when the owner says
"here" or "no sessions", the same chain runs with sub-agents, and the main session asks the owner
its questions itself, one at a time. In the terminal CLI `/startup-team:start-team` says so and
does nothing.

## Skills

Every skill says near its top what the project's CLAUDE.md must name for it to work (branches,
environments, commands, where records live). Nothing in a skill weakens the chain: each push,
merge, tag, deploy, send or delete is proposed and waits for the owner's 1.

| Skill | Use it to |
|---|---|
| `ship` | Take one finished, audited branch live. Runs only when asked. |
| `wrap` | Checkpoint a session: notes, commit, pull request to the integration branch. |
| `hotfix` | Get one production fix live ahead of the regular release. Runs only when asked. |
| `release-train` | Run the scheduled release, with rollback tiers. Runs only when asked. |
| `deploy` | Deploy merged code by hand, or check, pause and resume an automatic deploy. Runs only when asked. |
| `release-notes` | Write version notes and a plain-language "what's new". |
| `announcement` | Announce what shipped, for customers, the team or stakeholders. |
| `ship-log` | Record what shipped in the project's own trackers, from a high-water mark. |
| `test-gate` | Plan and run only the tests a diff needs, and give a GO or NO-GO. |
| `feature-tests` | Add the right tests for a finished feature, by risk tier. |
| `testing-rules` | Where tests run, what is expensive, what never runs on production. |
| `dev-feature-test` | Run a feature's tests on the local test environment in a fix loop. |
| `e2e-qa` | QA merged changes with end-to-end specs, from a high-water mark. |
| `test-accounts` | Create and delete throwaway accounts on a test environment. |
| `app-audit` | Crawl every route as several roles; build the access grid and the cost per route. |
| `scan-errors` | Cluster an error log over a time window into a triaged report. |
| `scan-tickets` | Investigate support tickets against notes, code and data. |
| `reply-tickets` | Draft a grounded reply to a ticket; sending needs the owner's 1. |
| `triage-log` | Keep the append-only ledger of triage outcomes. |
| `scrum-master` | Turn notes and ideas into cards and epics; run standup, review, retro. |
| `start-epic` | Build an epic's cards through the team chain, one piece at a time. |
| `optimize-image` | Shrink images: dry run, check by eye, apply on the owner's OK. |
| `repeated-judgment` | Make one judgement over many items cheaply and verify every hit. |
| `multi-model-supervisor` | Supervise a session that runs on several models through a gateway. |

### Skills the agents borrow

Each agent may also borrow a named skill from a companion plugin for one narrow question, through
`skill-sub`. Which agent may borrow which skill, the companion plugins and where to get them, and
the rule that the team's rules always win, are in
[ROSTER.md](plugins/startup-team/skills/team-workflow/ROSTER.md). Companion plugins are optional
and are their authors' own work; none ships with this plugin and none of their content is copied
here.

This repository's marketplace lists each companion with a link to its original repository, so an
install or update fetches the author's latest version from there:

```bash
claude plugin install agent-skills@startup-team --scope local
```

```bash
claude plugin update agent-skills@startup-team --scope local
```

`/startup-team:companions` does this for the ones you choose. The companions are `agent-skills`,
`antislop`, `taste-skill`, `ui-ux-pro-max`, `frontend-design`, `design`, `humanizer` and `ponytail`.
The links are not pinned to a version, so an update brings whatever the author has published.

## Project setup files

The plugin works with none of these. Each is a fill-in template under
`skills/team-workflow/templates/` that a project copies into its own repository.

| Template | Copy to | Read by |
|---|---|---|
| `routing-digest.md` | `.claude/routing-digest.md` | The tech lead, in place of the whole CLAUDE.md |
| `audit-digest.md` | `.claude/audit-digest.md` | The auditor, for the project's standing rules |
| `preflight-frontend.md` | `.claude/preflight-frontend.md` | The executor, before a frontend piece |
| `preflight-backend.md` | `.claude/preflight-backend.md` | The executor, before a backend piece |
| `operating-rules.md` | `.claude/operating-rules.md` | The rules and notes hooks |

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
