---
description: Run the architect on a backend piece (questions first, then the plan; nothing is built)
---
Run the `architect` agent now on the piece named below and show me its output unchanged. Give it the turn folder's path, my request verbatim, the decision block, the recorded answers, the memory digest and, when the piece has a screen, the approved design brief. Step 1 returns OPEN QUESTIONS only: run the answered-check, put each one to me one at a time and never answer them yourself. Then run it again with my answers for step 2: it writes `plan-<piece>.md` in the turn folder and ends with `GREEN LIGHT NEEDED`. Show me the summary and wait for 1 (build as planned) or 0 (change). Build nothing in this command; after my 1, the executor's brief names the plan's path.

Piece: $ARGUMENTS
