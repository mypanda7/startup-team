---
description: Run QA on the current turn's built pieces
---
If `.handoff/team-sessions.json` names a standing `qa` session and this is not it (your own id: `get_session` with "self"), do not run the agent here: send the request to that session as the `team-workflow` skill, step 3, says (owner's words verbatim, paths, answers already given with their questions), say only "QA Engineer has the request." and stop. Otherwise:

Run the `qa` agent on the latest turn folder (or the one named below), in its own session where the host can start one. Give it my original request verbatim, the decision block, the recorded answers, the design brief or plan, every result file and the commits. Show me its QA record unchanged. BUGS go back to the tech lead as fix tasks; an UNCLEAR question comes to me.

Turn folder (optional): $ARGUMENTS
