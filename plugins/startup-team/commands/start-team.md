---
description: Make this session the Tech Lead and start the Business Analyst, Designer, Developer, QA Engineer, DevOps and Security sub sessions
---
Set up the team's standing sessions: the Tech Lead (this session) and its six sub sessions (Business
Analyst, Designer, Developer, QA Engineer, DevOps, Security). `$ARGUMENTS` may name a subset of the
sub sessions (`business-analyst`, `designer`, `developer`, `qa`, `devops`, `security`); with no
argument, all six.

This session becomes the Tech Lead: it is renamed "Tech Lead" and does the Tech Lead's work
itself, and it starts the sub sessions, so they sit under it in the sidebar. It must start them on
this turn: the desktop app refuses `start_session` on a turn that another session's message
started. Follow these steps in order.

1. If you have no `start_session` tool (the terminal CLI), say in one line that standing sessions
   need the desktop app and that the team keeps using its sub-agents. Stop.
2. Call `get_session` with `self` for this session's title, then `list_sessions` once (all
   sessions, not only linked ones).
3. A role has a session when there is a non-archived session whose `cwd` is the project's folder
   (compared ignoring case, slash direction and a trailing slash; a worktree or subfolder does not
   count) and whose title contains the role's title, ignoring case and spaces. A session whose
   title starts with `[run]` is a role session and never counts. A session with the role's title
   that runs in a worktree or another folder does not count: name it in your report so I can
   archive it.
4. The Tech Lead:
   - If this session's title already contains "Tech Lead", it is the Tech Lead. Go on.
   - If another session is the Tech Lead by step 3, stop for the Tech Lead and ask me which one
     leads: this session (I archive the other one) or the existing one (this session keeps its
     name and sends that session the message in step 7). Do nothing for the Tech Lead meanwhile.
   - Otherwise rename this session with `set_session_title` (`self`, title `Tech Lead`).
   Then read `sessions/tech-lead-session.md` (the `sessions` and `agents` folders sit beside the
   `commands` folder) and keep it, with the `team-workflow` skill, as your standing method: its
   section "When you are the main session" says how the two fit.
5. For each named sub session, in the table's order: one match by step 3, use it as it is, whoever
   started it. More than one: list them and ask me which one to use; never guess, and start none
   for that role meanwhile.
6. Start each sub session that has none with ONE `start_session` call:
   - initiation `user_asked` (I ran this command), the title and name from the table
   - context `fresh`, `use_worktree: false`. Never a worktree, whatever else I said: a session in a
     worktree is not found by the rule in step 3, and it does not see the project's `.handoff/`
     or its current branch.
   - the model from the table, unless the project's CLAUDE.md names another
   - prompt: the line `[startup-team:<name>]` so the team gate stays quiet, then the full text of
     the brief, then, when the table names an agent file, a last line
     `AGENT FILE: <absolute path of that file>`
   - background: at least 80 characters saying which project folder it serves and which role it
     holds in the team
7. Only when I chose an existing, separate Tech Lead session in step 4: send it, by session id, a
   message of three lines: `[startup-team:tech-lead]`, `SUB SESSIONS: <name> = <session id>, ...`
   (every sub session found or started) and `PLUGIN FOLDER: <absolute path of this plugin's
   folder>`.
8. Tell me in one line which sessions were found and which were started, and name any refused
   start with the app's reason. Then name any worktree or duplicate sessions from step 3. If this
   session became the Tech Lead and does not run on the table's Tech Lead model, say so: only I can
   change this session's model, in the model menu.
9. Once the Tech Lead is set and the sub sessions are found or started, create
   `<project folder>/.handoff/team-setup-done` holding one line, today's date, so the setup offer
   (the `setup-offer` hook) stops.

| Session | Title | Name | Model | Brief | Agent file |
|---|---|---|---|---|---|
| Tech Lead | Tech Lead | `tech-lead` | opus | `sessions/tech-lead-session.md` | none |
| Business Analyst | Business Analyst | `business-analyst` | sonnet | `sessions/business-analyst-session.md` | none |
| Designer | Designer | `designer` | sonnet | `sessions/designer-session.md` | `agents/designer.md` |
| Developer | Developer | `developer` | opus | `sessions/developer-session.md` | `agents/executor.md` |
| QA Engineer | QA Engineer | `qa` | sonnet | `sessions/qa-session.md` | `agents/qa.md` |
| DevOps | DevOps | `devops` | opus | `sessions/devops-session.md` | `agents/devops.md` |
| Security | Security | `security` | opus | `sessions/security-session.md` | none |

This command starts no session beyond the six sub sessions.
