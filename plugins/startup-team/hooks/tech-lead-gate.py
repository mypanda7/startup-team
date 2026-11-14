"""Remind the session to triage a task with the tech lead before starting it.

Lanes, in order:
- OFF      STARTUP_TEAM_GATE_OFF=1: nothing.
- SKIP     slash commands, pasted terminal output, agent reports and task notifications, and a
           role-session brief (it starts with "[startup-team:"): nothing.
- FAST     the request starts with "quick:": no triage, but the closing qa and audit still apply.
           The marker is explicit intent, so it counts even on a short request.
- SHORT    an unmarked request under 8 words: nothing.
- DIRECT   one short question (ends in "?", under 40 words, one sentence, no build verb): nothing.
- GATED    everything else: the full steps on the session's first gated prompt, a two-line
           reminder after that. STARTUP_TEAM_GATE_FULL=1 forces the full text every time.

Python 3.9+, standard library only. Never blocks: always exits 0 and swallows every error.
"""
import hashlib
import json
import os
import re
import sys
import tempfile

MIN_WORDS = 8
DIRECT_MAX_WORDS = 40

# A report or notification from another agent or session is not the owner's request.
NOT_THE_OWNER = ("<task-notification>", "[SYSTEM NOTIFICATION", "Another Claude session sent a message")

BUILD_VERBS = (
    "add|build|change|commit|create|delete|deploy|edit|fix|implement|make|migrate|move|push|"
    "refactor|remove|rename|run|update|write"
)
# A second sentence, or a build verb, means it is a task and not one question. A "." only breaks a
# sentence before a space, so a question that names "config.py" stays one sentence.
NOT_DIRECT = re.compile(r"[.!?;]\s+[a-z]|(^|[^a-z])(" + BUILD_VERBS + r")([^a-z]|$)")

REMINDER = """Team gate (startup-team): before starting this task, triage it.
1. Load the team-workflow skill if it is not loaded and create a turn folder.
2. If this session is the Tech Lead (its title contains "Tech Lead"), triage here by the Tech Lead
   brief. Otherwise send the request to the project's Tech Lead session (see the team-workflow
   skill for how to find it) if there is one, by its session id; otherwise run the tech-lead agent.
   Give it the request verbatim, the turn folder and the shared memory digest.
   Save its decision block in the turn folder before any piece starts.
3. Follow its decision block: start the CLEAR NOW pieces with the agent and model it names, put its
   QUESTIONS to the owner one at a time (answered-check first), and build no BLOCKED piece.
   A PROPOSAL is a suggestion: build it only after the owner's 1.
4. Any UI change needs the designer's proposal and the owner's 1 before it is built.
5. Run each role in its own session where this session can start one (team-workflow, Sessions).
6. Finish with qa and then the auditor before telling the owner it is done. The result file
   lists every deviation from what the owner approved, or "none".
Answer directly, without triage, only when this is a one-line reply or a pure question, or when
every item was already green-lit by the owner (say so in the result file).
A request that starts with "quick:" skips triage, never the closing qa and audit.
The owner's words and the project's CLAUDE.md win over this reminder."""

SHORT_REMINDER = """Team gate (startup-team; full steps were shown earlier this session): tech-lead decision block
first, designer proposal + owner's 1 for UI, role sessions, questions one at a time, qa then the auditor before "done"."""

FAST_REMINDER = """Team gate (startup-team), fast lane ("quick:"): no tech-lead triage for this request.
If anything is built or changed, still finish with qa and then the auditor before telling the
owner it is done; give them the request and "no triage, fast lane" in place of a decision block."""


def first_time(session_id: str) -> bool:
    """True the first time this session reaches the gate. Fails open (True) on any error."""
    if not session_id:
        return True
    try:
        folder = os.path.join(tempfile.gettempdir(), "startup-team-hooks")
        os.makedirs(folder, exist_ok=True)
        name = "gate-" + hashlib.sha1(session_id.encode("utf-8", "replace")).hexdigest()[:16]
        marker = os.path.join(folder, name)
        if os.path.exists(marker):
            return False
        with open(marker, "w"):
            pass
    except OSError:
        pass
    return True


def main() -> None:
    if os.environ.get("STARTUP_TEAM_GATE_OFF") == "1":
        return
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
        prompt = str(payload.get("prompt", ""))
        session_id = str(payload.get("session_id", "") or "")
    except (ValueError, AttributeError):
        return
    text = prompt.strip()
    # "/" is a slash command; "<" covers pasted terminal output (<bash-input>, <bash-stdout>, ...).
    if not text or text[0] in "/<":
        return
    if text.lower().startswith("[startup-team:"):
        return
    if text.startswith(NOT_THE_OWNER) or "<agent-message from=" in text[:400]:
        return
    lower = text.lower()
    if lower.replace(" ", "").startswith("quick:"):
        print(FAST_REMINDER)
        return
    words = len(text.split())
    if words < MIN_WORDS:
        return
    if words < DIRECT_MAX_WORDS:
        flat = " ".join(lower.split())
        if flat.endswith("?") and not NOT_DIRECT.search(flat):
            return
    full = first_time(session_id)
    if os.environ.get("STARTUP_TEAM_GATE_FULL") == "1":
        full = True
    print(REMINDER if full else SHORT_REMINDER)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
