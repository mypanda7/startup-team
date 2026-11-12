---
description: Audit the current turn against my original request
argument-hint: "[turn folder] [project]"
---
Run the `auditor` agent on the latest turn folder (or the one named below). Give it my original request verbatim, the decision block (or "fast lane, no triage"), the recorded answers, every result file, every QA record and the commits. Also give it the `dispatcher`'s record if anything was delegated (say "nothing delegated" otherwise), `browser-pass.md` if a screen changed, and for anything published off the repo the local source file with its checksum. Before you start it, make sure each result file names every commit up to HEAD; findings from a browser pass go into `browser-pass.md` first, never into a relayed message. If I wrote "project" below, tell it the scope is the overall project; otherwise the scope is my instruction plus this turn's diff.

If it returns PRE-AUDIT CHECK FAILED, fix the records it names and run it again. If it returns a SPECIALIST REQUESTS block, run each request, save the answers in the turn folder and resume the same auditor. Show me the verdict unchanged. T items go back to the tech lead, then come to me as one numbered list for my green light; start none on your own. W items come to me as one list of 1/0 proposals; record each answer in the turn folder. Quote any PENDING deploy consequence to me word for word; nothing ships until I answer it.

Turn folder and scope (optional): $ARGUMENTS
