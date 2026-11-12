"""Remind the session to triage a task with the tech lead before starting it.

Skipped for: slash commands, pasted terminal output, requests under 8 words, a request that
starts with "quick:", a role-session brief (it starts with "[startup-team:"), and when
STARTUP_TEAM_GATE_OFF=1. Prints nothing in those cases.
"""
import json
import os
import sys

MIN_WORDS = 8

REMINDER = """Team gate (startup-team): before starting this task, triage it.
1. Load the team-workflow skill if it is not loaded and create a turn folder.
2. Run the tech-lead agent with the request verbatim, the turn folder and the shared memory digest.
3. Follow its decision block: start the CLEAR NOW pieces with the agent and model it names, put its
   QUESTIONS to the owner one at a time (answered-check first), and build no BLOCKED piece.
4. Any UI change needs the designer's proposal and the owner's 1 before it is built.
5. Run each role in its own session where this session can start one (team-workflow, Sessions).
6. Finish with qa and then the auditor before telling the owner it is done.
Answer directly, without triage, only when this is a one-line reply or a pure question.
The owner's words and the project's CLAUDE.md win over this reminder."""


def main() -> None:
    if os.environ.get("STARTUP_TEAM_GATE_OFF") == "1":
        return
    try:
        prompt = str(json.load(sys.stdin).get("prompt", ""))
    except (ValueError, AttributeError):
        return
    text = prompt.strip()
    if not text or text[0] in "/<":
        return
    if text.lower().startswith("[startup-team:"):
        return
    if text.lower().replace(" ", "").startswith("quick:"):
        return
    if len(text.split()) < MIN_WORDS:
        return
    print(REMINDER)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
