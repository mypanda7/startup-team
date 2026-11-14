---
description: Start the AI Tech Lead session; run inside it, start its Business Analyst, Designer, Developer, QA Engineer, DevOps and Security sub sessions
---
Set up the team's standing sessions: the AI Tech Lead, a session of its own, and its six sub
sessions (Business Analyst, Designer, Developer, QA Engineer, DevOps, Security), which sit under it
in the sidebar. `$ARGUMENTS` may name a subset of the sub sessions (`business-analyst`,
`designer`, `developer`, `qa`, `devops`, `security`); with no argument, all six.

The desktop app nests a session under the session that started it, and allows `start_session`
only on a turn the owner typed. So setup takes two runs of this command: run in any other
session, it starts only the AI Tech Lead (case A); run in the AI Tech Lead on a turn the owner
typed there, it starts the sub sessions under it (case B). Follow these steps in order.

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
     whose title IS the role's title, ignoring case and spaces ("Designer", "QA Engineer", ...);
     for the Tech Lead, a title that ends with "Tech Lead", so "AI Tech Lead" matches. A title
     that only contains the word does not match. A session whose title starts with `[run]` is a
     role session and never counts. A session with the role's title that runs in a worktree or
     another folder does not count: name it in your report so I can archive it.
4. The case: this session is the Tech Lead when its id is the registry's `tech-lead` entry, or else
   its title ends with "Tech Lead" (ignoring case and spaces). Then go to case B (step 6).
   Otherwise, case A (step 5).
5. **Case A: this session is not the Tech Lead.** Start no sub session here.
   - Create `<project folder>/.handoff/team-setup-started` holding one line, today's date, so the
     sessions started from now on never get the setup notice.
   - The Tech Lead, by step 3. More than one matches: list them and ask me which one leads (I
     archive the others); start and message none meanwhile. Exactly one: reuse it, never start a
     second one, and send it, by session id, the lines `[startup-team:tech-lead]`,
     `PLUGIN FOLDER: <absolute path of this plugin's folder>`, the `FIRST:` line below when it has
     no sub sessions yet, and `REQUEST: <my pending request, verbatim>` when there is one.
   - None: start it with ONE `start_session` call: initiation `user_asked`, title `AI Tech Lead`,
     name `tech-lead`, model from the table (unless the project's CLAUDE.md names another),
     context `fresh`, `use_worktree: false` (never a worktree: it would not be found by step 3,
     nor see the project's `.handoff/`). Prompt: `[startup-team:tech-lead]`, the full text of
     `sessions/tech-lead-session.md` (the `sessions` and `agents` folders sit beside the
     `commands` folder), `PLUGIN FOLDER: <absolute path of this plugin's folder>`, the line
     `FIRST: no sub sessions exist yet; ask the owner to reply here once, then run start-team from
     the plugin folder on that turn`, and `REQUEST: <my pending request, verbatim>` when there is
     one. Background: at least 80 characters on which project folder it serves and that it leads
     the team.
   - If this session has a tool that moves a session it started to the top level of the sidebar
     (in the desktop app: `detach_session`), use it on the AI Tech Lead, so it is a session of its
     own. Without one, leave it where it is.
   - Write the registry's `tech-lead` entry (step 9 shows the format), keeping every other entry.
   - Tell me in one line: open AI Tech Lead (link it) and reply there once to create the six sub
     sessions. Do not write `team-setup-done`. Stop.
6. **Case B: this session is the Tech Lead.** If this turn was started by another session's
   message, not typed by me, say in one line that the app refuses session starts on such a turn and
   ask me to reply here once. Stop. Otherwise create `.handoff/team-setup-started` if it is
   missing, read `sessions/tech-lead-session.md` and keep it, with the `team-workflow` skill, as
   your standing method.
7. For each named sub session, in the table's order: one match by step 3, use it as it is, whoever
   started it. More than one: list them and ask me which one to use; never guess, and start none
   for that role meanwhile.
8. Start each sub session that has none with ONE `start_session` call, so it sits under this
   session:
   - initiation `user_asked`, the title and name from the table
   - context `fresh`, `use_worktree: false`, never a worktree, whatever else I said
   - the model from the table, unless the project's CLAUDE.md names another
   - prompt: the line `[startup-team:<name>]` so the team gate stays quiet, then the full text of
     the brief, then, when the table names an agent file, a last line
     `AGENT FILE: <absolute path of that file>`
   - background: at least 80 characters saying which project folder it serves and which role it
     holds in the team
9. Write the registry `<project folder>/.handoff/team-sessions.json`: every role found or started,
   this session as `tech-lead`, keyed by name, each with its session id and title, for example
   `{"tech-lead": {"id": "<session id>", "title": "AI Tech Lead"}, "developer": {...}}`. Keep the
   entries of roles this run did not name. Every "find a session" rule of the team reads it first.
10. Companions: for each companion plugin this plugin's marketplace lists (`ROSTER.md` beside the
    `team-workflow` skill names them), run `claude plugin list` once. A copy it shows installed for
    this project, from any marketplace, wins and stays the one in use: do not install the team's
    copy beside it, and leave an installed `<name>@startup-team` as it is (no reinstall). A copy
    only named in the project's CLAUDE.md but not installed does not count. Otherwise run
    `claude plugin install <name>@startup-team --scope local`.
    Apply none of a companion's own hooks, settings or setup questions.
11. Tell me in one line which sub sessions were found and which were started, and name any refused
    start with the app's reason; then any worktree or duplicate sessions from step 3; then which
    companions were installed and which kept, and that they load in sessions started from now on.
12. Once the sub sessions are found or started, create `<project folder>/.handoff/team-setup-done`
    holding one line, today's date, so the setup offer (the `setup-offer` hook) stops.

| Session | Title | Name | Model | Brief | Agent file |
|---|---|---|---|---|---|
| Tech Lead | AI Tech Lead | `tech-lead` | opus | `sessions/tech-lead-session.md` | none |
| Business Analyst | Business Analyst | `business-analyst` | sonnet | `sessions/business-analyst-session.md` | none |
| Designer | Designer | `designer` | sonnet | `sessions/designer-session.md` | `agents/designer.md` |
| Developer | Developer | `developer` | opus | `sessions/developer-session.md` | `agents/executor.md` |
| QA Engineer | QA Engineer | `qa` | sonnet | `sessions/qa-session.md` | `agents/qa.md` |
| DevOps | DevOps | `devops` | opus | `sessions/devops-session.md` | `agents/devops.md` |
| Security | Security | `security` | opus | `sessions/security-session.md` | none |

This command starts no session beyond the AI Tech Lead (case A) and its six sub sessions (case B).
