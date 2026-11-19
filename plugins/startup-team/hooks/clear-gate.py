"""Clear gate: a task message to a team session goes out only after that session was cleared.

PreToolUse on SendMessage / send_message / clear_session, PostToolUse on clear_session.
- A message to a session in .handoff/team-sessions.json is allowed when, since the sender's last
  task message to it, the sender cleared it (clear_session) or sent it `RESET:`; or when the
  message has a line `CLEAR: skipped <reason>` (something is pending there). Otherwise it is
  denied once with the steps, and the sender clears or states the reason and resends.
- The exact one-line `RESET: before new task|threshold from <name>` and `WAKE` always pass.
  Targets outside the registry, and the main sessions (tech-lead, optimization), always pass.
- STARTUP_TEAM_CLEAR_GATE_OFF=1 turns it off. Any error lets the call through.
Python 3.9+, standard library only.
"""
import hashlib
import json
import os
import re
import sys
import tempfile

SEND_TOOLS = ("SendMessage", "mcp__ccd_session_mgmt__send_message")
CLEAR_TOOL = "mcp__ccd_session_mgmt__clear_session"
PREFIX = re.compile(r"^\s*\[startup-team:[^\]]*\]\s*")
SKIPPED = re.compile(r"(?m)^\s*CLEAR: skipped[ \t]+\S")
# Only the exact one-line forms pass, so no task rides in on them.
RESET = re.compile(r"RESET: (before new task|threshold) from [^\n]{1,80}\s*$")
WAKE = re.compile(r"WAKE\s*$")
# Reports go up to these; they are cleared only by each other, by the written Threshold rule.
MAIN = ("tech-lead", "optimization")


def registry_base(payload: dict):
    for start in (os.environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd")):
        here = os.path.abspath(start) if isinstance(start, str) and start else ""
        while here:
            path = os.path.join(here, ".handoff", "team-sessions.json")
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as handle:
                    return here, json.load(handle)
            parent = os.path.dirname(here)
            here = "" if parent == here else parent
    return None, {}


def team_target(target: str, registry: dict):
    """(name, id) of the registry session the target names, or None."""
    want = (target or "").split(" [")[0].strip().lower()
    if not want:
        return None
    for name, entry in registry.items() if isinstance(registry, dict) else ():
        if not isinstance(entry, dict) or not entry.get("id") or name in MAIN:
            continue
        if want in (entry["id"].lower(), name.lower(), str(entry.get("title", "")).lower()):
            return name, entry["id"]
    return None


def state_path(base: str, sender: str) -> str:
    folder = os.path.join(tempfile.gettempdir(), "startup-team-hooks")
    os.makedirs(folder, exist_ok=True)
    key = hashlib.sha1((os.path.normcase(base) + "|" + sender).encode("utf-8", "replace")).hexdigest()[:16]
    return os.path.join(folder, "clear-gate-" + key + ".json")


def load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)


def decide(payload: dict):
    """The deny reason for this call, or None to let it through. Updates the state file."""
    tool = payload.get("tool_name", "")
    event = payload.get("hook_event_name", "PreToolUse")
    args = payload.get("tool_input") or {}
    base, registry = registry_base(payload)
    if not base:
        return None
    target = team_target(args.get("to") or args.get("session_id") or "", registry)
    if not target:
        return None
    name, sid = target
    path = state_path(base, payload.get("session_id", ""))
    state = load(path)
    if tool == CLEAR_TOOL:
        if event == "PostToolUse":
            # shortcut: a refused clear also counts; the sender's pending check still applies.
            state[sid] = "ready"
            save(path, state)
        return None
    if tool not in SEND_TOOLS:
        return None
    text = PREFIX.sub("", str(args.get("message") or ""))
    if RESET.match(text):
        state[sid] = "ready"
        save(path, state)
        return None
    if WAKE.match(text):
        return None
    if state.get(sid) == "ready" or SKIPPED.search(text):
        state[sid] = "used"
        save(path, state)
        return None
    return (f"Clear gate: {name} was not cleared since your last task message to it. If nothing is "
            f"pending there, clear it first (clear_session for a session you started; otherwise send "
            f"`[startup-team:{name}] RESET: before new task from <your name>` and wait until its turn "
            f"has ended), then resend. If something is pending there, resend with a first line "
            f"`CLEAR: skipped <what is pending>`.")


def selftest() -> None:
    import shutil
    root = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(root, ".handoff"))
        with open(os.path.join(root, ".handoff", "team-sessions.json"), "w", encoding="utf-8") as handle:
            json.dump({"designer": {"id": "local_abc", "title": "Designer"}, "tech-lead": {"id": "local_tl"},
                       "qa": {"id": "local_qa"}}, handle)
        sender = "selftest-" + os.urandom(6).hex()
        def call(tool, event="PreToolUse", **args):
            return decide({"tool_name": tool, "hook_event_name": event, "tool_input": args,
                           "cwd": os.path.join(root, ".handoff"), "session_id": sender})
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        assert call("SendMessage", to="main", message="hi") is None, "non-team target passes"
        assert call("SendMessage", to="local_abc", message="[startup-team:designer] brief") is not None, "uncleared denied"
        assert call("SendMessage", to="Designer", message="task") is not None, "title matches too"
        assert call("SendMessage", to="local_abc", message="[startup-team:designer] WAKE") is None, "WAKE passes"
        assert call("SendMessage", to="local_abc", message="[startup-team:designer] RESET: before new task from x") is None
        assert call("SendMessage", to="local_abc", message="task after reset") is None, "after RESET passes"
        assert call("SendMessage", to="local_tl", message="[startup-team:tech-lead] QA done") is None, "reports up pass"
        assert call("SendMessage", to="", message="x") is None, "empty target passes"
        assert call("SendMessage", to="local_qa", message="RESET: now build Y\nmore") is not None, "smuggled RESET"
        assert call("SendMessage", to="local_qa", message="WAKEUP do Z") is not None, "smuggled WAKE"
        assert call("SendMessage", to="local_abc", message="second task") is not None, "used up"
        assert call("SendMessage", to="local_abc", message="CLEAR: skipped piece P3 out\ntask") is None, "stated skip passes"
        assert call("SendMessage", to="local_abc", message="CLEAR: skipped\ntask") is not None, "empty reason denied"
        assert call(CLEAR_TOOL, session_id="local_abc") is None
        assert call("mcp__ccd_session_mgmt__send_message", session_id="local_abc", message="t") is not None, "Pre clear only"
        call(CLEAR_TOOL, event="PostToolUse", session_id="local_abc")
        assert call("mcp__ccd_session_mgmt__send_message", session_id="local_abc", message="t") is None, "after clear passes"
        os.remove(state_path(root, sender))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("clear-gate selftest ok")


def main() -> None:
    if os.environ.get("STARTUP_TEAM_CLEAR_GATE_OFF") == "1":
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
