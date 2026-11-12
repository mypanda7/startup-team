---
description: Run the designer (PROPOSE by default; start with "brief" or "review" for those modes)
---
Run the `designer` agent now and show me its output unchanged. Pick the mode from the first word of the request: `brief` (from a design I already approved), `review` (read-only review of an existing screen), otherwise PROPOSE. Build nothing in this command.

Give it paths, not pasted text: my request verbatim, the screen or section it applies to and whether that is new or a change (file:line of every section involved), and for `brief` the design source (approved proposal, canvas export, Figma link, images, or my chat instructions; say which) plus my decisions on it verbatim.

- PROPOSE: put its OPEN QUESTIONS to me one at a time and never answer them yourself; drop any I have already answered and apply that answer. Then show the proposal and wait for 1 (build) or 0 (change).
- BRIEF: it never blocks or re-judges my approval. Put each OPEN POINT to me one at a time, record my answers verbatim under "## OWNER ANSWERS" in the brief, and quote the brief's path in the build brief. QA and the auditor check the build against it.
- REVIEW: a review is not a green light. Each fix I want goes through PROPOSE.
- If it returns a SUBAGENT REQUESTS block, run each request with the `skill-sub` agent and resume it with the answers.

Request: $ARGUMENTS
