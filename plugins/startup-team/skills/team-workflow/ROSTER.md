# Skill roster: which outside skills each agent may borrow

The team's agents carry their own rules. On top of those, each agent may borrow a named skill from
a companion plugin for ONE narrow question, as a sub-agent. This file says which agent may borrow
which skill, and how those skills rank against the team's rules.

The main session reads this file when it loads the team-workflow skill and puts an agent's roster
line into that agent's brief. An agent asks for a skill by returning a `SUBAGENT REQUESTS` block
(or, for the auditor's specialists, a `SPECIALIST REQUESTS` block); the main session runs it and
hands the answer back. See "Sub-agent requests" in SKILL.md.

A skill that is not installed is simply not available: the request comes back `SKILL NOT FOUND`
and the agent carries on with its own rules. Nothing here is required for the team to work.

## Companion plugins

None of these ship with startup-team, and none of their content is copied here. Each is its
author's own work under its own licence. The startup-team marketplace lists each one with a link to
its ORIGINAL repository, so installing or updating a companion fetches the author's latest version
straight from there:

```bash
claude plugin install agent-skills@startup-team --scope local
claude plugin update agent-skills@startup-team --scope local
```

`/startup-team:companions` installs or updates the ones you choose. The links are not pinned to a
version: an update brings whatever the author has published since, so read a companion's changes
before updating if you depend on its behaviour, and check this roster still names its skills.

| Plugin | Original repository | What the team uses it for |
|---|---|---|
| `agent-skills` | github.com/addyosmani/agent-skills | Engineering checklists and four specialist agents (the roster below) |
| `antislop` | github.com/miqdadbadjuber/anti-slop | A read-only pass for generic-looking UI, copy and code comments |
| `taste-skill` | github.com/Leonxlnx/taste-skill | Visual taste for public and marketing pages |
| `ui-ux-pro-max` | github.com/nextlevelbuilder/ui-ux-pro-max-skill | The designer's design-reference search |
| `frontend-design` | github.com/anthropics/claude-plugins-official (`plugins/frontend-design`) | Frontend design guidance |
| `design` | github.com/anthropics/knowledge-work-plugins (`design`) | Design critique, accessibility review, developer handoff |
| `humanizer` | github.com/blader/humanizer | Plain, human wording for owner-facing and customer-facing copy |
| `ponytail` | github.com/DietrichGebert/ponytail | A tie-breaker for how much code to write inside an approved piece |

A companion already installed from its author's own marketplace works just as well: the roster goes
by the plugin's name, not by where it was installed from.

## Roster

Skill names are as the companion plugin names them. `(ask)` means only when the owner asks for it.

| Agent | Skills it may assign | From |
|---|---|---|
| `tech-lead` | planning-and-task-breakdown, interview-me, idea-refine (ask), constraint-driven-development, context-engineering | agent-skills |
| `architect` | api-and-interface-design, deprecation-and-migration, performance-optimization, security-and-hardening, source-driven-development, spec-driven-development | agent-skills |
| `designer` | frontend-ui-engineering, browser-testing-with-devtools, idea-refine (ask) | agent-skills |
| `designer` | antislop-ui, antislop-copywriting, antislop-human, antislop-layoutmobile | antislop |
| `designer` | design-taste-frontend (in full on public pages, advice only on app screens) | taste-skill |
| `designer` | the design-reference search, design critique, accessibility review, developer handoff | ui-ux-pro-max, design, frontend-design |
| `executor` | test-driven-development, incremental-implementation, debugging-and-error-recovery, code-simplification, frontend-ui-engineering, documentation-and-adrs | agent-skills |
| `executor` | antislop-code (comments inside the piece being built only) | antislop |
| `qa` | browser-testing-with-devtools, test-driven-development | agent-skills |
| `auditor` | code-review-and-quality, test-driven-development, security-and-hardening (only when the instruction itself is about security), browser-testing-with-devtools, doubt-driven-development | agent-skills |
| `auditor` | antislop (one pass on the turn's changed screens, inside its cap) | antislop |
| `auditor` | design-taste-frontend (public-page pieces only) | taste-skill |
| `devops` | shipping-and-launch, ci-cd-and-automation, git-workflow-and-versioning, observability-and-instrumentation, debugging-and-error-recovery | agent-skills |
| main session | using-agent-skills (to pick the skill for a question; never assigned downward), humanizer (owner-facing and customer-facing copy) | agent-skills, humanizer |

### Auditor specialists

The auditor may also ask for a specialist agent instead of a skill. The main session runs it with
the Agent tool, read-only, scoped to the instruction and the turn's commits.

| Specialist | When |
|---|---|
| `agent-skills:code-reviewer` | A code-quality point would settle a checklist item |
| `agent-skills:test-engineer` | A test-coverage point would settle a checklist item |
| `agent-skills:web-performance-auditor` | A performance point would settle a checklist item |
| `agent-skills:security-auditor` | ON DEMAND: only in a turn where the owner asked for a security check |

## How a borrowed skill is run

- With `skill-sub` (read-only), brief = PARENT / SKILL / INSTRUCTION / SCOPE / QUESTION verbatim.
  The answer is saved as `subagent-S<n>.md` in the turn folder and the same parent is resumed.
- At most 2 per parent run; for the auditor, specialists and skills together. More needs the
  owner's 1.
- Scope is the owner's instruction plus the piece. "Overall project" scope only when the owner's
  own message says so; those findings are listed apart and never change a verdict.
- A sub-agent that cannot answer without assuming returns `UNCLEAR: <one question>`. The parent
  raises it and the owner answers it. It never picks a default.
- A skill's advice applies only when its parent assigns it. Nobody loads a companion plugin's
  whole skill by default.

## Precedence: the team's rules win

Order, highest first: the owner's words in this session, recorded owner answers, the plugin's
hooks (the gate, the project's operating rules), the project's CLAUDE.md, the project's notes and
decision records, the team's agent files, the project's own skills, then every companion plugin.

A companion skill is a checklist that fills gaps. It never adds a gate, a question, a repo file, a
commit, a push or a config change that the rules above do not already allow. In particular:

- **Workflow.** The team chain (turn folder, decision block, design approval for UI, plan for
  backend, executor, QA, audit) replaces any lifecycle a companion plugin brings. No spec, task,
  constraints, ideas or changelog files written into the repo on a skill's say.
- **Questions.** One at a time, with a recommendation, through the main session or the Business
  Analyst session. Never a batch, never a mandatory cross-model question, never a setup wizard.
- **Design.** Any UI change goes through the designer and the owner's 1 before a build. The
  project's tokens, mandated components and owner-approved copy and layout are never a finding.
- **Frontend and backend.** The project's own stack rules and preflight sheets beat any general
  engineering skill. A pattern from another stack is never imported.
- **Git and shipping.** One commit per piece by the executor; everything else is a `devops`
  proposal the owner approves. A companion plugin's own build, ship, spec or plan command is not
  used as-is; its read-only review commands are fine.
- **Tests.** The `feature-tests` and `test-gate` skills decide the layers and the runs. No whole
  suite per piece on a skill's advice.
- **Audit.** The auditor's PASS or FAIL is the only verdict. Another plugin's "gate", "audit" or
  "must not ship" is advice: its findings go to the owner as 1/0 proposals.
- **How much code.** A "write less" plugin is a tie-breaker inside an approved piece. It is never
  a reason to skip a question, a design approval, a required test, a guard, a VERIFY command, a
  notes update or a turn-folder record, and it does not shorten owner-facing replies or the
  mandatory sections of a result, audit or devops report.
- **Copy.** Copy skills apply to copy an agent proposes, before the owner's 1. Words the owner
  wrote or approved are raised to the owner, never cut.
- **Config.** No plugin hook, settings, statusline, MCP server, tool install or CLAUDE.md edit a
  companion plugin suggests is applied without the owner's 1. Install and update companion
  plugins only through `claude plugin`.

A project may narrow or widen this roster in its own CLAUDE.md, which wins over this file.
