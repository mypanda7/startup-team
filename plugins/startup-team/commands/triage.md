---
description: Triage a task with the tech lead and show the decision block
---
Load the `team-workflow` skill if it is not loaded. Create a turn folder, then triage this request. If this session is the Tech Lead (its title contains "Tech Lead"), triage it here yourself by `sessions/tech-lead-session.md` and save the block as `decision.md`. Otherwise, if there is a Tech Lead session for this project (a non-archived session whose `cwd` is the project's folder (compared ignoring case, slash direction and a trailing slash; a worktree or subfolder does not count) and whose title contains "Tech Lead", ignoring case and spaces, found with `list_sessions` and messaged by its session id), send it the request verbatim, the turn folder path and the shared memory digest with SendMessage (its session id as `to`), wait for its decision block, and save it as `decision.md` in the turn folder. A session whose title starts with `[run]` is a role session and never counts as a standing session. Otherwise run the `tech-lead` agent with the same three things and save its block the same way. Show me the block unchanged. Start nothing yet.

Request: $ARGUMENTS
