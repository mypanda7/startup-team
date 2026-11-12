"""Keep a project's notes in front of the session. One script, three modes (argv[1]):

  session-start  (SessionStart)      point at the notes index; print its "router" section if it has one
  first-prompt   (UserPromptSubmit)  once per session: remind to read the relevant note first; does the
                                     session-start job itself when that hook did not fire; also passes
                                     on a pending "update the notes" reminder left by the stop mode
  stop           (Stop)              once per session: if files changed since the session began and no
                                     note did, tell the owner and leave a reminder for the next prompt

The notes folder is the one named by a line "NOTES: <folder>" in the project's rules file
(default .claude/operating-rules.md, or STARTUP_TEAM_RULES_FILE). No such line or folder: prints
nothing. STARTUP_TEAM_NOTES_OFF=1 turns it off.

Python 3.9+, standard library only. Never blocks: always exits 0 and swallows every error.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

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


def session_start(payload: dict, session_id: str) -> None:
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


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
