---
description: Start the AI Tech Lead session and its Business Analyst, Designer, Developer, QA Engineer, DevOps and Security sub sessions
---
Set up the team's standing sessions: the AI Tech Lead and its six sub sessions (Business Analyst,
Designer, Developer, QA Engineer, DevOps, Security). `$ARGUMENTS` may name a subset of the sub
sessions (`business-analyst`, `designer`, `developer`, `qa`, `devops`, `security`); with no
argument, all six.

This session keeps its own title. It starts the six sub sessions and then ONE more session, "AI
Tech Lead", where the owner carries on: the AI Tech Lead triages, plans, audits and leads the sub
sessions. This session must start them on this turn: the desktop app refuses `start_session` on a
turn that another session's message started. Follow these steps in order.

1. If you have no `start_session` tool (the terminal CLI), say in one line that standing sessions
   need the desktop app and that the team keeps using its sub-agents. Stop.
2. Call `get_session` with `self` for this session's id and title, then `list_sessions` once (all
   sessions, not only linked ones). Read `<project folder>/.handoff/team-sessions.json` if it
   exists (the registry, below).
3. A role has a session when:
   - Registry first: the registry names a session id for the role, and `list_sessions` shows a
     non-archived session with that id whose `cwd` is the project's folder (compared ignoring case,
     slash direction and a trailing slash; a worktree or subfolder does not count). That is the
     role's session whatever its title is now, so a renamed session is still found.
   - Otherwise, by title: a non-archived session whose `cwd` is the project's folder (as above) and
     whose title contains the role's title, ignoring case and spaces ("Tech Lead" for the Tech
     Lead, so "AI Tech Lead" matches). A session whose title starts with `[run]` is a role session
     and never counts. A session with the role's title that runs in a worktree or another folder
     does not count: name it in your report so I can archive it.
4. For each named sub session, in the table's order: one match by step 3, use it as it is, whoever
   started it. More than one: list them and ask me which one to use; never guess, and start none
   for that role meanwhile.
5. Start each sub session that has none with ONE `start_session` call:
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
6. The Tech Lead, by step 3:
   - This session is the Tech Lead (its id is the registry's `tech-lead` entry, or its title
     contains "Tech Lead"): start nothing for it. Read `sessions/tech-lead-session.md` (the
     `sessions` and `agents` folders sit beside the `commands` folder) and keep it, with the
     `team-workflow` skill, as your standing method.
   - Exactly one other session is the Tech Lead: reuse it, never start a second one. Send it, by
     session id, the three lines `[startup-team:tech-lead]`, `SUB SESSIONS: <name> = <session id>,
     ...` (every sub session found or started) and `PLUGIN FOLDER: <absolute path of this
     plugin's folder>`.
   - More than one matches: list them and ask me which one leads (I archive the others). Start and
     message none meanwhile.
   - None: start it with ONE `start_session` call as in step 5, with the table's Tech Lead row,
     and the prompt: `[startup-team:tech-lead]`, the full text of `sessions/tech-lead-session.md`,
     then `SUB SESSIONS: <name> = <session id>, ...` (every sub session found or started) and
     `PLUGIN FOLDER: <absolute path of this plugin's folder>`.
7. Write the registry `<project folder>/.handoff/team-sessions.json`: every role found or started,
   keyed by its name, each with its session id and title, for example
   `{"tech-lead": {"id": "<session id>", "title": "AI Tech Lead"}, "developer": {...}}`. Keep the
   entries of roles this run did not name. Every "find a session" rule of the team reads it first.
8. Tell me in one line which sessions were found and which were started, and name any refused
   start with the app's reason. Then name any worktree or duplicate sessions from step 3. When the
   AI Tech Lead is another session, say that I carry on there, and link it.
9. Companions: for each companion plugin this plugin's marketplace lists (`ROSTER.md` beside the
   `team-workflow` skill names them), run `claude plugin list` once and check whether the project
   already has its own copy: the same plugin installed from another marketplace, or a copy the
   project's CLAUDE.md names. If it has, that copy stays the one in use: do not install the
   team's copy beside it. Otherwise run `claude plugin install <name>@startup-team --scope local`.
   Apply none of a companion's own hooks, settings or setup questions. Report in one line which
   were installed and which were kept, and that they load in sessions started from now on.
10. Once the Tech Lead is set and the sub sessions are found or started, create
   `<project folder>/.handoff/team-setup-done` holding one line, today's date, so the setup offer
   (the `setup-offer` hook) stops.

| Session | Title | Name | Model | Brief | Agent file |
|---|---|---|---|---|---|
| Tech Lead | AI Tech Lead | `tech-lead` | opus | `sessions/tech-lead-session.md` | none |
| Business Analyst | Business Analyst | `business-analyst` | sonnet | `sessions/business-analyst-session.md` | none |
| Designer | Designer | `designer` | sonnet | `sessions/designer-session.md` | `agents/designer.md` |
| Developer | Developer | `developer` | opus | `sessions/developer-session.md` | `agents/executor.md` |
| QA Engineer | QA Engineer | `qa` | sonnet | `sessions/qa-session.md` | `agents/qa.md` |
| DevOps | DevOps | `devops` | opus | `sessions/devops-session.md` | `agents/devops.md` |
| Security | Security | `security` | opus | `sessions/security-session.md` | none |

This command starts no session beyond the six sub sessions and the AI Tech Lead.
