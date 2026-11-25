"""Keep a running session on the installed startup-team version (owner: instructions stay aligned
across the setup, on every computer).

A session loads the plugin once, at its start. When the plugin is updated later (here or on
another computer, by `claude plugin update`), this UserPromptSubmit hook sees that the installed
version differs from the one this session loaded and tells the session, once per version, to
re-read its brief and the team-workflow skill from the installed folder and follow those.

Python 3.9+, standard library only. Never blocks: always exits 0 and swallows every error.
"""
import json
import os
import re
import sys
import tempfile

PLUGIN = "startup-team"


def loaded_version(root: str) -> str:
    """The version folder this session's plugin copy runs from (…/startup-team/<version>)."""
    name = os.path.basename(os.path.normpath(root))
    return name if re.fullmatch(r"\d+(\.\d+)*", name) else ""


def installed(home: str, project: str):
    """(version, installPath) of the startup-team copy for this project: local scope first, then user."""
    try:
        with open(os.path.join(home, "plugins", "installed_plugins.json"), encoding="utf-8") as f:
            plugins = json.load(f).get("plugins", {})
    except (OSError, ValueError):
        return "", ""
    norm = lambda p: os.path.normcase(os.path.normpath(p or ""))
    best = None
    for key, entries in plugins.items():
        if key.split("@")[0] != PLUGIN:
            continue
        for e in entries:
            if e.get("scope") in ("local", "project") and norm(e.get("projectPath")) == norm(project):
                return e.get("version", ""), e.get("installPath", "")
            if e.get("scope") == "user" and best is None:
                best = (e.get("version", ""), e.get("installPath", ""))
    return best or ("", "")


def notice(old: str, new: str, path: str) -> str:
    p = path.replace("\\", "/")
    return (f"startup-team was updated to {new}; this session loaded {old}. Align now, before anything else:\n"
            f"- re-read {p}/sessions/<your role>-session.md (your role: the `.handoff/team-sessions.json` entry\n"
            f"  with this session's id, else your title) and {p}/skills/team-workflow/SKILL.md, and follow them\n"
            f"  instead of the copy you loaded; read any agent, command or skill from {p} when you use it;\n"
            f"- tell the owner in one line: \"Aligned with startup-team {new}; a restart also loads its hooks.\"")


def decide(old: str, new: str, path: str, marker: str) -> str:
    """The notice to print, or "" (same version, unknown, or already shown for this version)."""
    if not old or not new or old == new or os.path.exists(marker):
        return ""
    return notice(old, new, path)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    home = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    project = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    old = loaded_version(root)
    new, path = installed(home, project)
    sid = re.sub(r"[^A-Za-z0-9_-]", "", str(data.get("session_id", "")))[:64] or "nosession"
    marker = os.path.join(tempfile.gettempdir(), f"startup-team-sync-{sid}-{new}")
    text = decide(old, new, path, marker)
    if text:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}}))
        open(marker, "w").close()


def selftest() -> None:
    with tempfile.TemporaryDirectory() as t:
        home, proj = os.path.join(t, "home"), os.path.join(t, "proj")
        os.makedirs(os.path.join(home, "plugins"))
        with open(os.path.join(home, "plugins", "installed_plugins.json"), "w", encoding="utf-8") as f:
            json.dump({"plugins": {"startup-team@startup-team": [
                {"scope": "local", "projectPath": proj, "version": "0.11.55", "installPath": "/c/0.11.55"},
                {"scope": "local", "projectPath": os.path.join(t, "other"), "version": "0.9.0", "installPath": "/c/0.9.0"}],
                "other@m": [{"scope": "local", "projectPath": proj, "version": "9.9.9", "installPath": "/x"}]}}, f)
        assert installed(home, proj) == ("0.11.55", "/c/0.11.55"), installed(home, proj)
        assert loaded_version("/cache/startup-team/startup-team/0.11.54") == "0.11.54"
        assert loaded_version("/repo/plugins/startup-team") == ""
        m = os.path.join(t, "marker")
        assert "updated to 0.11.55" in decide("0.11.54", "0.11.55", "/c/0.11.55", m)
        assert decide("0.11.55", "0.11.55", "/c/0.11.55", m) == "", "same version"
        assert decide("", "0.11.55", "/c/0.11.55", m) == "", "dev copy"
        open(m, "w").close()
        assert decide("0.11.54", "0.11.55", "/c/0.11.55", m) == "", "shown twice"
    print("version-sync selftest ok")


if __name__ == "__main__":
    try:
        selftest() if sys.argv[1:] == ["--selftest"] else main()
    except Exception:
        pass
    sys.exit(0)
