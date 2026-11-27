"""Keep a project's notes in front of the session. One script, three modes (argv[1]):

  session-start  (SessionStart)      point at the notes index; print its "router" section if it has one
  first-prompt   (UserPromptSubmit)  once per session: remind to read the relevant note first; does the
                                     session-start job itself when that hook did not fire (the role
                                     and summary lines even for another session's message); also passes
                                     on a pending "update the notes" reminder left by the stop mode
  stop           (Stop)              once per session: if files changed since the session began and no
                                     note did, tell the owner and leave a reminder for the next prompt

The notes folder is the one named by a line "NOTES: <folder>" in the project's rules file
(default .claude/operating-rules.md, or STARTUP_TEAM_RULES_FILE). No such line or folder: prints
nothing. STARTUP_TEAM_NOTES_OFF=1 turns it off.

Python 3.9+, standard library only. Never blocks: always exits 0 and swallows every error.
"""
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid

DEFAULT_FILE = ".claude/operating-rules.md"
ROUTER_MAX_CHARS = 1500
ROUTER_LINE_MAX = 150
NOT_THE_OWNER = ("<task-notification>", "[SYSTEM NOTIFICATION", "Another Claude session sent a message")
INDEX_NAMES = ("index.md", "readme.md")
NOT_CODE = (".md", ".txt", ".lock", ".log")
UPDATE_LINE = (
    "Notes reminder: files changed this session but nothing under {notes}/ did. If the work fixed a "
    "root cause, found a non-obvious invariant or settled a design decision, record it in the "
    "relevant note (and the index, for a new note). Skip for style, typo or pure refactor changes."
)


def find_notes(payload: dict):
    """Return (project root, notes folder as written, absolute folder) or None."""
    name = os.environ.get("STARTUP_TEAM_RULES_FILE") or DEFAULT_FILE
    for root in (os.environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd"), os.getcwd()):
        if not root or not isinstance(root, str):
            continue
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = re.sub(r"<!--.*?-->", "", handle.read(200000), flags=re.S)
        for line in text.splitlines():
            found = re.match(r"^\s*(?:[-*]\s+)?NOTES:\s*(.+)$", line)
            if not found:
                continue
            value = found.group(1).strip().strip("`\"' ")
            if not value or "<" in value:
                return None
            folder = os.path.normpath(os.path.join(root, value))
            if os.path.isdir(folder):
                return root, value.replace("\\", "/").rstrip("/"), folder
            return None
        return None
    return None


def marker(kind: str, session_id: str) -> str:
    folder = os.path.join(tempfile.gettempdir(), "startup-team-hooks")
    os.makedirs(folder, exist_ok=True)
    digest = hashlib.sha1(session_id.encode("utf-8", "replace")).hexdigest()[:16]
    return os.path.join(folder, "notes-" + kind + "-" + digest)


def git(root: str, *args: str) -> str:
    """Output of a read-only git command, or "" when git or the repository is missing."""
    try:
        done = subprocess.run(
            ("git", "-c", "core.quotepath=off") + args, cwd=root, capture_output=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.decode("utf-8", "replace") if done.returncode == 0 else ""


def index_of(folder: str) -> str:
    for name in sorted(os.listdir(folder)):
        if name.lower() in INDEX_NAMES:
            return name
    return ""


def start_text(shown: str, folder: str) -> str:
    index = index_of(folder)
    if not index:
        count = sum(1 for name in os.listdir(folder) if name.lower().endswith(".md"))
        if not count:
            return ""
        return (
            "Project notes: " + shown + "/ holds " + str(count) + " note(s). Open the one for a "
            "subsystem before you change or debug it: it records the known fix, invariant or gotcha."
        )
    lines = [
        "Project notes: the index is " + shown + "/" + index + ". Open it, or the note for a "
        "subsystem, before you change or debug that subsystem: do not rediscover a recorded fix."
    ]
    with open(os.path.join(folder, index), encoding="utf-8", errors="replace") as handle:
        text = handle.read(200000)
    router, level, size = [], 0, 0
    for line in text.splitlines():
        head = re.match(r"^(#+)\s+(.*)$", line)
        if head and level and len(head.group(1)) <= level:
            break
        if head and not level and "router" in head.group(2).lower():
            level = len(head.group(1))
            continue
        if level and line.strip():
            line = line.rstrip()
            if len(line) > ROUTER_LINE_MAX:
                line = line[:ROUTER_LINE_MAX] + "..."
            size += len(line) + 1
            if size > ROUTER_MAX_CHARS:
                router.append("(cut: the rest is in the index)")
                break
            router.append(line)
    if router:
        lines.append("Topic router:")
        lines.extend(router)
    return "\n".join(lines)


def record_start(root: str, session_id: str) -> None:
    """Remember that the pointer was given, and the commit the session began on."""
    if not session_id:
        return
    try:
        with open(marker("start", session_id), "w", encoding="utf-8") as handle:
            handle.write(git(root, "rev-parse", "HEAD").strip())
    except OSError:
        pass


SUMMARY_LINE = ("Past context: read .handoff/conversations/SUMMARY.md first; open its sub files only when "
                "the task needs them. On the first turn after a start, a clear or a restart that carries a real request (never one a RESET, RULE or WAKE message started: those stay silent), start your reply with a "
                "short `Read from summary:` block (at most 5 lines: the last task, its state, anything open). "
                "Then check for pending tasks (the summary's open items, your checkpoint, the open task boards): when there are any, name each in one short line and ask the owner once, at the end of that turn, whether they want more information on them (owner, 2026-11-27; a top-level session: the question dialog; a sub session: its `wrap_up` question); none: say so in one line. Then carry on.")


PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def role_line(base: str, host_id: str) -> str:
    """The team role this session holds by .handoff/team-sessions.json, as one line, or ""."""
    try:
        with open(os.path.join(base, ".handoff", "team-sessions.json"), encoding="utf-8") as handle:
            registry = json.load(handle)
    except (OSError, ValueError):
        return ""
    for name, entry in registry.items() if isinstance(registry, dict) and host_id else ():
        if isinstance(entry, dict) and entry.get("id") == host_id:
            brief = os.path.join(PLUGIN_DIR, "sessions", name + "-session.md")
            return (f"Team role: this is the {name} session ({entry.get('title', name)}). Read {brief} first, "
                    f"then .handoff/checkpoints/{name}.md.")
    return ""


def team_lines(payload: dict, session_id: str) -> list:
    """The role line and the summary line for this session."""
    for base in (os.environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd")):
        if not isinstance(base, str) or not os.path.isdir(os.path.join(base, ".handoff")):
            continue
        # the desktop app's own session id is the one the registry records
        role = role_line(base, os.environ.get("CLAUDE_CODE_HOST_SESSION_ID") or session_id)
        summary = os.path.isfile(os.path.join(base, ".handoff", "conversations", "SUMMARY.md"))
        return [line for line in (role, SUMMARY_LINE if summary else "") if line]
    return []


def fresh(transcript: str) -> bool:
    """True when the conversation has no assistant turn yet: a new, emptied or missing transcript."""
    try:
        with open(transcript, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict) and entry.get("type") == "assistant":
                    return False
    except OSError:
        pass
    return True


def given_marker(payload: dict, session_id: str) -> str:
    """Marker that the role lines were given: per transcript when the host names one, else per id."""
    key = str(payload.get("transcript_path", "") or "") or session_id
    return marker("given", key) if key else ""


def session_start(payload: dict, session_id: str) -> None:
    for line in team_lines(payload, session_id):
        print(line)
    given = given_marker(payload, session_id)
    if given:
        try:
            with open(given, "w"):
                pass
        except OSError:
            pass
    found = find_notes(payload)
    if not found:
        return
    root, shown, folder = found
    text = start_text(shown, folder)
    if text:
        record_start(root, session_id)
        print(text)


def first_prompt(payload: dict, session_id: str) -> None:
    head = str(payload.get("prompt", "") or "").lstrip()
    # After a clear SessionStart may not fire: give the role and summary lines on the first prompt of
    # a fresh conversation, also when another session sent it, so a cleared session reads its brief.
    transcript = str(payload.get("transcript_path", "") or "")
    given = given_marker(payload, session_id)
    show = False
    if transcript:
        if os.path.exists(given):
            # SessionStart gave them for this conversation; a later clear shows them again
            with contextlib.suppress(OSError):
                os.remove(given)
        else:
            show = fresh(transcript)
    elif given and not os.path.exists(given):
        # shortcut: no transcript path means once per session id; a reused id gets nothing after a clear
        show = True
        with contextlib.suppress(OSError), open(given, "w"):
            pass
    if show:
        lines = team_lines(payload, session_id)
        if lines:
            print("\n".join(lines))
    if head.startswith(NOT_THE_OWNER) or "<agent-message from=" in head[:400]:
        return
    found = find_notes(payload)
    if not found:
        return
    root, shown, folder = found
    out = []
    if session_id:
        pending = marker("pending", session_id)
        if os.path.exists(pending):
            os.remove(pending)
            out.append(UPDATE_LINE.format(notes=shown))
        done = marker("first", session_id)
        if not os.path.exists(done):
            with open(done, "w"):
                pass
            if not os.path.exists(marker("start", session_id)):
                # SessionStart did not fire in this host (it happens after a clear): do its job now.
                text = start_text(shown, folder)
                if text:
                    record_start(root, session_id)
                    out.append(text)
            elif start_text(shown, folder):
                out.append(
                    "Notes: before non-trivial work, read the note in " + shown + "/ for the "
                    "subsystem this request touches."
                )
    if out:
        print("\n".join(out))


def stop(payload: dict, session_id: str) -> None:
    if payload.get("stop_hook_active") or not session_id:
        return
    found = find_notes(payload)
    if not found:
        return
    root, shown, folder = found
    said = marker("stop", session_id)
    if os.path.exists(said):
        return
    base = ""
    try:
        with open(marker("start", session_id), encoding="utf-8") as handle:
            base = handle.read().strip()
    except OSError:
        pass
    top = git(root, "rev-parse", "--show-toplevel").strip()
    if not top:
        return
    # Tracked files that differ from the commit the session began on: committed or not.
    names = git(top, "diff", "--name-only", base or "HEAD").splitlines()
    if not names and base:
        names = git(top, "diff", "--name-only", "HEAD").splitlines()
    prefix = os.path.relpath(folder, top).replace("\\", "/").rstrip("/") + "/"
    notes_changed = any(n.startswith(prefix) for n in names) or bool(
        git(top, "status", "--porcelain", "--", prefix).strip()
    )
    code_changed = any(
        not n.startswith(prefix)
        and not n.startswith((".claude/", ".handoff/"))
        and not n.lower().endswith(NOT_CODE)
        for n in names
    )
    if not code_changed or notes_changed:
        return
    with open(said, "w"):
        pass
    with open(marker("pending", session_id), "w"):
        pass
    # A Stop hook cannot reach the model without blocking it, so this goes to the owner now and
    # to the model with the next prompt (first-prompt mode reads the pending marker).
    print(json.dumps({"systemMessage": UPDATE_LINE.format(notes=shown)}))


def selftest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        assert role_line(tmp, "local_a") == "", "missing registry"
        os.makedirs(os.path.join(tmp, ".handoff"))
        with open(os.path.join(tmp, ".handoff", "team-sessions.json"), "w", encoding="utf-8") as handle:
            json.dump({"qa": {"id": "local_a", "title": "QA Engineer"}}, handle)
        line = role_line(tmp, "local_a")
        assert "qa session" in line and "qa-session.md" in line and ".handoff/checkpoints/qa.md" in line, line
        assert role_line(tmp, "local_b") == "" and role_line(tmp, "") == "", "unknown id"
        # After a clear SessionStart may not fire: the first prompt of a fresh transcript, even from
        # another session, gives the role line, after every clear, also with the same session id.
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        os.environ["CLAUDE_CODE_HOST_SESSION_ID"] = "local_a"
        sid = "selftest-" + uuid.uuid4().hex
        other = "Another Claude session sent a message: RESET: before new task"
        user = json.dumps({"type": "user"}) + "\n"
        reply = json.dumps({"type": "assistant"}) + "\n"
        paths = [os.path.join(tmp, name + ".jsonl") for name in ("one", "two", "three", "four")]
        made = []

        def write(path, text):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)

        def run(mode, session_id, transcript, prompt=other):
            payload = {"cwd": tmp, "prompt": prompt, "transcript_path": transcript}
            made.append(given_marker(payload, session_id))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                (first_prompt if mode == "first" else session_start)(payload, session_id)
            return out.getvalue()
        try:
            role = "Team role: this is the qa session"
            assert role in run("first", sid, paths[0]), "no role line for a missing transcript"
            write(paths[0], user + reply)
            assert run("first", sid, paths[0]) == "", "role line in a conversation that has replies"
            write(paths[1], "not json\n" + user)
            assert role in run("first", sid, paths[1]), "no role line after clear 1 (new transcript)"
            write(paths[1], user + reply)
            assert run("first", sid, paths[1]) == ""
            write(paths[1], "")
            assert role in run("first", sid, paths[1], "hello"), "no role line after clear 2 (emptied)"
            write(paths[2], user)
            assert role in run("start", sid, paths[2])
            assert run("first", sid, paths[2]) == "", "role line twice after SessionStart"
            write(paths[2], "")
            assert role in run("first", sid, paths[2]), "no role line after a clear that follows a start"
            write(paths[3], user)
            assert role in run("first", "", paths[3]), "no role line without a payload session id"
            assert role in run("first", sid, ""), "no role line without a transcript path"
            assert run("first", sid, "") == "", "id fallback gives the role line twice"
        finally:
            for path in made:
                if path and os.path.exists(path):
                    os.remove(path)
    print("notes selftest ok")


def main() -> None:
    if os.environ.get("STARTUP_TEAM_NOTES_OFF") == "1":
        return
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
        if not isinstance(payload, dict):
            payload = {}
    except ValueError:
        payload = {}
    session_id = str(payload.get("session_id", "") or "")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if mode == "session-start":
        session_start(payload, session_id)
    elif mode == "first-prompt":
        first_prompt(payload, session_id)
    elif mode == "stop":
        stop(payload, session_id)


if __name__ == "__main__" and sys.argv[1:2] == ["selftest"]:
    selftest()
elif __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
