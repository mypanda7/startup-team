---
description: Show the board of pieces delegated to cheaper outside models, or dispatch a decision block's DELEGATE pieces
---
Run the `dispatcher` agent. With no argument, run it in WATCH mode: every piece delegated through the gateway the project's CLAUDE.md names, with its status, attempt count and model. With the path of a decision block (or a turn folder holding `decision.md`) as the argument, run it in DISPATCH mode on that block. Save its report unchanged in the turn folder as `board.md` (`board-<phase>.md` for a later dispatch in the same turn) before acting on it, then show me the board unchanged. For every FOR TECH-LEAD entry, send the brief and the evidence to the tech lead (the Tech Lead session if there is one, otherwise the `tech-lead` agent) and tell me what it decided; a second or third retry needs my 1, asked one at a time. If the dispatcher answers `NO GATEWAY`, tell me in one line and do nothing else. Never delegate a piece that carries personal data or secrets.

Decision block or turn folder (optional): $ARGUMENTS
