---
description: Run the designer (PROPOSE by default; start with "brief" or "review" for those modes)
---
If `.handoff/team-sessions.json` names a standing `designer` session and this is not it (your own id: `get_session` with "self"), do not run the agent here: send the request to that session as the `team-workflow` skill, step 3, says (owner's words verbatim, paths, answers already given with their questions), say only "Designer has the request." and stop. Otherwise:

Run the `designer` agent now and show me its output unchanged. Pick the mode from the first word of the request: `brief` (from a design I already approved), `review` (read-only review of an existing screen), otherwise PROPOSE. Build nothing in this command.

Give it paths, not pasted text: my request verbatim, the screen or section it applies to and whether that is new or a change (file:line of every section involved), and for `brief` the design source (approved proposal, canvas export, Figma link, images, or my chat instructions; say which) plus my decisions on it verbatim.

- PROPOSE: put its OPEN QUESTIONS to me one at a time and never answer them yourself; drop any I have already answered and apply that answer. Then show the proposal and wait for 1 (build) or 0 (change), unless I already gave my 1 for it in any session: then quote that answer and go on. Ask me again only for a real clarification, naming what is unclear.
- BRIEF: it never blocks or re-judges my approval. Put each OPEN POINT to me one at a time, record my answers verbatim under "## OWNER ANSWERS" in the brief, and quote the brief's path in the build brief. QA and the auditor check the build against it.
- REVIEW: a review is not a green light. Each fix I want goes through PROPOSE.
- If it returns a SUBAGENT REQUESTS block, run each request with the `skill-sub` agent and resume it with the answers.

Request: $ARGUMENTS
