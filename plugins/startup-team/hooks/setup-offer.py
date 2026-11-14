"""Offer to set up the team's standing sessions on the first owner prompt of a session.

Prints the offer once per session until the project has `.handoff/team-setup-done`, which
/startup-team:start-team creates. An owner who answers 0 sees it again in the next session.

Quiet for: STARTUP_TEAM_GATE_OFF=1, slash commands, pasted terminal output, agent reports and
messages, and role-session briefs (they start with "[startup-team:"), so it never fires in a sub
session.

Python 3.9+, standard library only. Never blocks: always exits 0 and swallows every error.
"""
import hashlib
import json
import os
import sys
import tempfile

# A report or notification from another agent or session is not the owner's request.
NOT_THE_OWNER = ("<task-notification>", "[SYSTEM NOTIFICATION", "Another Claude session sent a message")

DONE_MARKER = os.path.join(".handoff", "team-setup-done")

OFFER = """Team setup (startup-team): before anything else this turn, say "startup-team installed
successfully." and ask the owner, as the only question:
"Create the AI Tech Lead session and its six sub sessions (Business Analyst, Designer, Developer,
QA Engineer, DevOps, Security)? 1 = yes, 0 = no."
The agents, sub-agents and skills already came with the package; this only creates the sessions.
Do not start the owner's request until they answer.
- On 1: run /startup-team:start-team on that owner turn. It starts the six sub sessions and a new
  session titled "AI Tech Lead"; tell the owner to carry on in AI Tech Lead, and send it their
  request.
- On 0: carry on with their request; the offer returns in the next session.
Skip the offer silently when this session has no start_session tool (the terminal CLI), or when a
Tech Lead session already exists for this project folder (the `tech-lead` id in
`.handoff/team-sessions.json` is a live session there, or else this session's or a listed
session's title contains "Tech Lead"): then create `.handoff/team-setup-done` in the project
folder (one line: today's date) and continue."""


def first_offer(session_id: str) -> bool:
    """True the first time this session is offered. Fails open (True) on any error."""
    if not session_id:
        return True
    try:
        folder = os.path.join(tempfile.gettempdir(), "startup-team-hooks")
        os.makedirs(folder, exist_ok=True)
        name = "offer-" + hashlib.sha1(session_id.encode("utf-8", "replace")).hexdigest()[:16]
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
        cwd = str(payload.get("cwd", "") or os.getcwd())
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
    if os.path.exists(os.path.join(cwd, DONE_MARKER)):
        return
    if first_offer(session_id):
        print(OFFER)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
