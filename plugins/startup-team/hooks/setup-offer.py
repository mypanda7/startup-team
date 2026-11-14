"""Offer to set up the team's standing sessions on the first owner prompt of a session.

Prints the offer once per session until the project has `.handoff/team-setup-done` or
`.handoff/team-setup-started`, which /startup-team:start-team creates. An owner who answers 0
sees it again in the next session. The per-session marker is set only when the offer prints.

`session-start` mode (the SessionStart backup): when neither marker exists, prints JSON with a
one-line notice for the owner (`systemMessage`) and the offer as context for Claude
(`hookSpecificOutput.additionalContext`), so the question is asked on the first prompt.

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
STARTED_MARKER = os.path.join(".handoff", "team-setup-started")

NOTICE = ("startup-team is installed but the team isn't set up: reply 1 to create the AI Tech Lead "
          "and its sub sessions")

OFFER = """Team setup (startup-team): before anything else this turn, say "startup-team installed
successfully." and ask the owner, as the only question:
"Create the AI Tech Lead session and its six sub sessions (Business Analyst, Designer, Developer,
QA Engineer, DevOps, Security) and turn on the companion plugins?"
- First choice: if this session has a tool that asks the owner a question with clickable options
  (in Claude Code: AskUserQuestion), ask it there with exactly two options: "Set up now" (= 1:
  creates the sessions and turns on the companion plugins) and "Not now" (= 0: asks again next
  session).
- Back-up: with no such tool, or when the call fails, is refused or is dismissed without a choice,
  ask it as text ending "1 = yes, 0 = no." and wait. A typed 1/yes or 0/no counts either way; any
  other free-text answer from the dialog is the owner's own words.
The agents, sub-agents and skills already came with the package; 1 creates the sessions and turns
on the companion plugins.
Do not start the owner's request until they answer.
- On 1 ("Set up now"): run /startup-team:start-team on that owner turn. It starts the six sub sessions and a new
  session titled "AI Tech Lead" and turns on the companion plugins (a copy the project already has
  stays in use); tell the owner to carry on in AI Tech Lead, and send it their request.
- On 0 ("Not now"): carry on with their request; the offer returns in the next session.
Ask at most once in this session: once it was asked (answered or not), never ask it again here.
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


def set_up(cwd: str) -> bool:
    """True when setup is done or under way in this project."""
    return any(os.path.exists(os.path.join(cwd, m)) for m in (DONE_MARKER, STARTED_MARKER))


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
    if sys.argv[1:2] == ["session-start"]:
        if not set_up(cwd):
            context = (
                "On the owner's first message in this session, follow this. Only the owner's own "
                "message counts: a message that starts with \"[startup-team:\", a cross-session "
                "message, an agent report or a task notification is not; then ignore this.\n" + OFFER
            )
            print(json.dumps({
                "systemMessage": NOTICE,
                "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context},
            }))
        return
    text = prompt.strip()
    # "/" is a slash command; "<" covers pasted terminal output (<bash-input>, <bash-stdout>, ...).
    if not text or text[0] in "/<":
        return
    if text.lower().startswith("[startup-team:"):
        return
    if text.startswith(NOT_THE_OWNER) or "<agent-message from=" in text[:400]:
        return
    if set_up(cwd):
        return
    # Only reached when the offer would print, so a skipped prompt never uses up the session's turn.
    if first_offer(session_id):
        print(OFFER)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
