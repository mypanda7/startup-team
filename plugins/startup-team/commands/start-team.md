---
description: Start the Tech Lead session and, under it, the Business Analyst, Designer, QA Engineer, DevOps and Security sub sessions
---
Start the team's standing sessions. This session starts only the Tech Lead session; the Tech Lead
session starts the five sub sessions (Business Analyst, Designer, QA Engineer, DevOps, Security),
so they sit under it. `$ARGUMENTS` may name a subset of the sub sessions (`business-analyst`,
`designer`, `qa`, `devops`, `security`); with no argument, all five. Follow these steps in order.

1. If you have no `start_session` tool (the terminal CLI), say in one line that standing sessions
   need the desktop app and that the team keeps using its sub-agents. Stop.
2. Call `list_sessions` once (all sessions, not only linked ones).
3. Look for the Tech Lead session: a non-archived session whose `cwd` is the project's folder (compared ignoring case, slash direction and a trailing slash; a worktree or subfolder does not count) and whose title contains the role's title, ignoring case and spaces, found with `list_sessions` and messaged by its session id ("Tech Lead"). A session whose title starts with `[run]`
   is a role session and never counts. If more than one matches, list them and ask me which one to
   use; never guess, and start nothing meanwhile.
4. If there is none, read `sessions/tech-lead-session.md` from this plugin (the `sessions` folder
   sits beside the `commands` folder) and start ONE session with `start_session`:
   - initiation `user_asked` (I ran this command), title `Tech Lead`, name `tech-lead`
   - context `fresh`, use_worktree false
   - model sonnet, unless the project's CLAUDE.md names another
   - prompt: the line `[startup-team:tech-lead]` so the team gate stays quiet, then the full text
     of the brief, then the two lines `PLUGIN FOLDER: <absolute path of this plugin's folder>` and
     `SUB SESSIONS: all` (or the names I gave)
   - background: at least 80 characters saying which project folder it serves and that it is the
     team's Tech Lead, which starts and leads the sub sessions
5. If there is one already, send it, by session id, a message of three lines:
   `[startup-team:tech-lead]`, `START SUB SESSIONS: all` (or the names I gave) and
   `PLUGIN FOLDER: <absolute path of this plugin's folder>`.
6. When the Tech Lead session reports, tell me in one line which sessions were found and which
   were started. Do not start a sub session yourself, even if the Tech Lead session could not.

This command starts no session but the Tech Lead's.
