---
description: Start the Tech Lead session and the Business Analyst, Designer, Developer, QA Engineer, DevOps and Security sub sessions
---
Start the team's standing sessions: the Tech Lead session and its six sub sessions (Business
Analyst, Designer, Developer, QA Engineer, DevOps, Security). `$ARGUMENTS` may name a subset of the
sub sessions (`business-analyst`, `designer`, `developer`, `qa`, `devops`, `security`); with no
argument, all six.

This session starts all of them itself, on this turn. The desktop app refuses `start_session` on a
turn that another session's message started, and the Tech Lead session's turns are always started
by a message, so the Tech Lead session can never start them. Follow these steps in order.

1. If you have no `start_session` tool (the terminal CLI), say in one line that standing sessions
   need the desktop app and that the team keeps using its sub-agents. Stop.
2. Call `list_sessions` once (all sessions, not only linked ones).
3. For the Tech Lead and then each named sub session, in the table's order, look for its session:
   a non-archived session whose `cwd` is the project's folder (compared ignoring case, slash
   direction and a trailing slash; a worktree or subfolder does not count) and whose title contains
   the role's title, ignoring case and spaces. A session whose title starts with `[run]` is a role
   session and never counts. One match: use it as it is, whoever started it. More than one: list
   them and ask me which one to use; never guess, and start none for that role meanwhile. A
   session with the role's title that runs in a worktree or another folder does not count: name it
   in your report so I can archive it.
4. Start each role that has no session with ONE `start_session` call:
   - initiation `user_asked` (I ran this command), the title and name from the table
   - context `fresh`, `use_worktree: false`. Never a worktree, whatever else I said: a session in a
     worktree is not found by the rule in step 3, and it does not see the project's `.handoff/`
     or its current branch.
   - the model from the table, unless the project's CLAUDE.md names another
   - prompt: the line `[startup-team:<name>]` so the team gate stays quiet, then the full text of
     the brief (the `sessions` and `agents` folders sit beside the `commands` folder), then, when
     the table names an agent file, a last line `AGENT FILE: <absolute path of that file>`. The
     Tech Lead's prompt ends instead with `PLUGIN FOLDER: <absolute path of this plugin's folder>`.
   - background: at least 80 characters saying which project folder it serves and which role it
     holds in the team
5. Then send the Tech Lead session, by session id, a message of three lines:
   `[startup-team:tech-lead]`, `SUB SESSIONS: <name> = <session id>, ...` (every sub session found
   or started) and `PLUGIN FOLDER: <absolute path of this plugin's folder>`.
6. Tell me in one line which sessions were found and which were started, and name any refused
   start with the app's reason. Then name any worktree or duplicate sessions from step 3.

| Session | Title | Name | Model | Brief | Agent file |
|---|---|---|---|---|---|
| Tech Lead | Tech Lead | `tech-lead` | opus | `sessions/tech-lead-session.md` | none |
| Business Analyst | Business Analyst | `business-analyst` | sonnet | `sessions/business-analyst-session.md` | none |
| Designer | Designer | `designer` | sonnet | `sessions/designer-session.md` | `agents/designer.md` |
| Developer | Developer | `developer` | opus | `sessions/developer-session.md` | `agents/executor.md` |
| QA Engineer | QA Engineer | `qa` | sonnet | `sessions/qa-session.md` | `agents/qa.md` |
| DevOps | DevOps | `devops` | opus | `sessions/devops-session.md` | `agents/devops.md` |
| Security | Security | `security` | opus | `sessions/security-session.md` | none |

This command starts no session beyond these seven.
