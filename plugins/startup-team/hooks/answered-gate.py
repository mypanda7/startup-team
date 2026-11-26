"""Answered gate: no redundant build / green-light question (owner, 2026-11-25).

The owner's answers to a proposal's or plan's questions are its green light. A question that asks
the owner to approve a build ("1 = yes, build", "Build it ...?", "green light") is denied unless it
is about something the owner has NOT answered yet (it starts with `New:`); a `Verify:` / `Clarify:`
question checks an answer and never asks for a build. In a session started from another session
(CLAUDE_CODE_CHILD_SESSION=1) AskUserQuestion is denied: the app shows that dialog in the parent;
the session asks with its `wrap_up` question instead (owner, 2026-11-25). No question passes between sessions
(owner, 2026-11-25, P41): a message to another session (SendMessage, send_message) that carries an owner
question for it to ask, or a dialog that asks one on another session's behalf, is denied.
PreToolUse on AskUserQuestion, the app's wrap_up question and the session messaging tools.
STARTUP_TEAM_ANSWERED_GATE_OFF=1 turns it off. Any error lets the call through.
Python 3.9+, standard library only.
"""
import json
import os
import re
import sys

BUILD = re.compile(r"(?i)(\b1\s*=\s*(yes,?\s*)?build\b|\bbuild (it|from it|this|as (shown|planned))\b"
                   r"|\b(give|your) green[ -]?light\b|\bgreen[ -]?light (for|to|on)\b"
                   r"|\bapprove (the |this )?(design|proposal|plan|build)\b|\b(design|proposal|plan) approved\b"
                   r"|\b(go ahead|proceed) with (the |this )?(build|plan|design|proposal)\b"
                   r"|\b(start|ready to|ok to|okay to) (build|implement)\w*\b|\bstart building\b)")
# Only `New:` (a part the owner has not answered) may ask for a build; Verify:/Clarify: check an answer.
NEW = re.compile(r"(?i)^\s*(\*\*)?new:")
# A question handed to another session to ask the owner, or asked here for another session (P41).
RELAY = re.compile(r"(?i)(\b(ask|put|pass|relay|forward|check)\w* (it |this |that |this question |the question |these )?(to |with )?(the )?owner\b"
                   r"|\b(owner|open) question (for|from) \w+\b|\bquestion for the owner\b|\bneeds? the owner'?s? (answer|1)\b"
                   r"|\bon behalf of\b|^\s*(request|question) from \w+|\b\w+ (asks|is asking|wants to know)\s*:)")
SEND = ("SendMessage", "mcp__ccd_session_mgmt__send_message", "mcp__ccd_session__send_message")


def texts(tool: str, args: dict):
    """(question, [option labels and descriptions]) pairs the owner would see."""
    if tool == "AskUserQuestion":
        for q in args.get("questions") or []:
            opts = [str(o.get(k, "")) for o in q.get("options") or [] for k in ("label", "description")]
            yield str(q.get("question", "")), opts
    elif args.get("ask"):
        yield str(args.get("ask")), [str(a.get("label", "")) for a in args.get("actions") or []]


def nested(env=None) -> bool:
    """A session the app started from another session (its dialogs show in the parent)."""
    return (env if env is not None else os.environ).get("CLAUDE_CODE_CHILD_SESSION") == "1"


def decide(payload: dict, env=None):
    tool = str(payload.get("tool_name", ""))
    if tool in SEND:
        args = payload.get("tool_input") or {}
        body = " ".join(str(args.get(k, "")) for k in ("message", "text", "content", "prompt"))
        # A RULE / RESET notice with no `?` only states a rule (QA P41 N1); anything else that matches is a relay.
        notice = re.match(r"\s*(RULE|RESET):", body) and "?" not in body
        if RELAY.search(body) and not notice:
            return ("Answered gate (owner, 2026-11-25): \"MAKE SURE that no questions are passed between sessions\". "
                    "Do not send an owner question to another session to ask. Ask it yourself, in this session "
                    "(a sub session: `wrap_up` with `ask`, buttons and `blocked: true`). To another session say only "
                    "\"<this session> has an open question\".")
        return None
    if tool != "AskUserQuestion" and not tool.endswith("__wrap_up"):
        return None
    if tool == "AskUserQuestion" and nested(env):
        return ("Answered gate (owner, 2026-11-25): this session was started from another session, and the app "
                "shows its question dialog in the parent as \"Request from ...\". Ask the owner here with "
                "`mcp__ccd_turn__wrap_up` instead: `ask` (one question), 1-2 `actions` buttons, `blocked: true`; "
                "without wrap_up, type the question with numbered options.")
    for question, opts in texts(tool, payload.get("tool_input") or {}):
        if RELAY.search(question):
            return ("Answered gate (owner, 2026-11-25): no question passes between sessions. This asks a question "
                    "for another session; that session asks it in its own session. Send it back there.")
        if NEW.match(question):
            continue
        if BUILD.search(question) or any(BUILD.search(o) for o in opts):
            return ("Answered gate (owner, 2026-11-25): \"do not ask me questions that have already been answered\". "
                    "The owner's answers to the proposal's or plan's questions are its green light: do not ask "
                    "for a build 1/0. Mark it approved (`APPROVED <YYYY-MM-DD>: <the owner's answers>` / "
                    "`GREEN LIGHT: APPROVED BY ANSWERS (<quotes>)`) and go on. Ask only about a part the owner "
                    "has not answered, starting the question with `New:` and naming that part, or check an "
                    "answer with `Verify:` / `Clarify:`.")
    return None


def selftest() -> None:
    def ask(q, *labels):
        return decide({"tool_name": "AskUserQuestion", "tool_input": {"questions": [
            {"question": q, "options": [{"label": l, "description": ""} for l in labels]}]}}, env={})
    assert ask("Build it: the list moves into a side panel?", "1 = yes, build", "0 = change")
    assert ask("Ready?", "1 = build as shown", "0 = change"), "build in options"
    assert ask("Give the green light for the side panel?", "Yes", "No")
    assert ask("New: the panel heading was never asked. Use \"Filters\"?", "Filters", "Browse") is None
    assert ask("Verify: you chose 'From the widest size'. Still right?", "Yes", "No") is None
    assert ask("Verify (still waiting): the hint would read X. Build it?", "1 = yes, build"), "verify+build"
    q = {"tool_name": "AskUserQuestion", "tool_input": {"questions": [{"question": "Phones?", "options": []}]}}
    assert decide(q, env={"CLAUDE_CODE_CHILD_SESSION": "1"}), "nested dialog denied"
    assert decide(q, env={}) is None, "top-level dialog passes"
    assert decide({"tool_name": "mcp__ccd_turn__wrap_up", "tool_input": {"ask": "Phones?"}},
                  env={"CLAUDE_CODE_CHILD_SESSION": "1"}) is None, "nested wrap_up passes"
    assert ask("Phones: keep the strip or move it?", "Keep the strip (Recommended)", "Move it") is None
    assert ask("Finish the team setup now?", "Finish setup", "Not now") is None
    assert decide({"tool_name": "mcp__ccd_turn__wrap_up", "tool_input": {"ask": "Build from it?",
                   "actions": [{"label": "1 = yes, build"}]}}, env={})
    assert decide({"tool_name": "mcp__ccd_turn__wrap_up", "tool_input": {"ask": "Push startup-team to main?",
                   "actions": [{"label": "Yes, push"}]}}, env={}) is None
    for miss in ("Go ahead with the build?", "Shall I start building?", "Is the design approved?",
                 "Ready to build?", "Proceed with the plan?", "OK to implement?"):
        assert ask(miss, "Yes", "No"), miss
    assert ask("Should the green light indicator on the status badge be shown?", "Yes", "No") is None
    assert decide({"tool_name": "Bash", "tool_input": {"command": "echo build it"}}) is None
    for relay in ("Please ask the owner: keep the strip?", "Open question for Designer: which line?",
                  "Designer asks: which line?", "Pass this to the owner: 1 or 0?"):
        assert decide({"tool_name": "SendMessage", "tool_input": {"to": "x", "message": relay}}), relay
    assert decide({"tool_name": "SendMessage", "tool_input": {"to": "x", "message": "Designer has an open question"}}) is None
    assert decide({"tool_name": "SendMessage", "tool_input": {"message": "You have an open question: ask it in your session"}}) is None
    assert decide({"tool_name": "mcp__ccd_session_mgmt__send_message", "tool_input": {"message": "RULE: never re-ask"}}) is None
    for ok in ("RULE: never ask the owner a question that is already answered.",
               "RESET: before new task. Sub sessions ask the owner with wrap_up."):
        assert decide({"tool_name": "SendMessage", "tool_input": {"message": ok}}) is None, ok
    for miss in ("Ask owner: which?", "Check with the owner whether X?", "Put this question to the owner: A or B?",
                 "Please ask the owner whether to keep the strip.", "RULE: ask the owner: A or B?"):
        assert decide({"tool_name": "SendMessage", "tool_input": {"message": miss}}), miss
    assert ask("Request from Designer: which line?", "A", "B"), "asked for another session"
    assert ask("The Designer asks: which line?", "A", "B"), "asked for another session"
    print("answered-gate selftest ok")


def main() -> None:
    if os.environ.get("STARTUP_TEAM_ANSWERED_GATE_OFF") == "1":
        return
    try:
        reason = decide(json.load(sys.stdin))
    except Exception:
        return
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))


if __name__ == "__main__":
    selftest() if sys.argv[1:2] == ["selftest"] else main()
