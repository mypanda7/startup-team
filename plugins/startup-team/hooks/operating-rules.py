"""Re-surface a project's own non-negotiable rules on every prompt, in tiers.

A reminder given once at session start fades in a long session, so this runs per prompt:
- the session's first prompt gets the FULL block (the first section of the rules file);
- later prompts get the two-line DIGEST;
- every prompt gets a pointer to the project note that best matches the prompt.

The project provides the file (default .claude/operating-rules.md, or the path in
STARTUP_TEAM_RULES_FILE, relative to the project root). In it:
  first section      the full block (the text under the first heading, up to the next heading)
  DIGEST: <text>     the short form; up to two such lines
  NOTES: <folder>    where the project's notes live, relative to the project root
  ROUTE: <words> -> <note file>   optional: prompt words (comma separated) that lead to one note
HTML comments and unfilled "<placeholder>" lines are ignored. No file, or nothing filled in:
prints nothing. STARTUP_TEAM_RULES_OFF=1 turns it off.

Python 3.9+, standard library only. Never blocks: always exits 0 and swallows every error.
"""
import hashlib
import json
import os
import re
import sys
import tempfile

DEFAULT_FILE = ".claude/operating-rules.md"
FULL_MAX_CHARS = 1500
DIGEST_MAX_LINES = 2
LINE_MAX_CHARS = 200
MAX_NOTES_SCANNED = 300
NOT_THE_OWNER = ("<task-notification>", "[SYSTEM NOTIFICATION", "Another Claude session sent a message")
INDEX_NAMES = ("index.md", "readme.md")
DIRECTIVE = re.compile(r"^\s*(?:[-*]\s+)?(DIGEST|NOTES|ROUTE):\s*(.*)$")
PLACEHOLDER = re.compile(r"^(?:[-*]\s+)?<[^<>]*>$")


def find_rules(payload: dict):
    """Return (project root, rules file path), or (None, None) when the project has none."""
    name = os.environ.get("STARTUP_TEAM_RULES_FILE") or DEFAULT_FILE
    for root in (os.environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd"), os.getcwd()):
        if root and isinstance(root, str):
            path = os.path.join(root, name)
            if os.path.isfile(path):
                return root, path
    return None, None


def parse_rules(path: str) -> dict:
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read(200000)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    rules = {"full": [], "digest": [], "notes": "", "routes": []}
    section = 0  # 0 = before any heading, 1 = the first section, 2 = past it
    for raw in text.splitlines():
        line = raw.rstrip()
        found = DIRECTIVE.match(line)
        if found:
            key, value = found.group(1), found.group(2).strip()
            if not value or PLACEHOLDER.match(value) or "<" in value and ">" in value:
                continue
            if key == "DIGEST":
                rules["digest"].append(value[:LINE_MAX_CHARS])
            elif key == "NOTES" and not rules["notes"]:
                rules["notes"] = value.strip("`\"' ")
            elif key == "ROUTE" and "->" in value:
                words, target = value.rsplit("->", 1)
                keys = [w.strip().lower() for w in words.split(",") if w.strip()]
                if keys and target.strip():
                    rules["routes"].append((keys, target.strip().strip("`\"' ")))
            continue
        if line.lstrip().startswith("#"):
            section = 1 if section == 0 and not rules["full"] else 2
            continue
        if section < 2 and line.strip() and not PLACEHOLDER.match(line.strip()):
            rules["full"].append(line)
    rules["digest"] = rules["digest"][:DIGEST_MAX_LINES]
    return rules


def words_of(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 4}


def same_word(a: str, b: str) -> bool:
    if a == b:
        return True
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    return len(short) >= 5 and long_.startswith(short)


def relevant_notes(root: str, rules: dict, prompt: str) -> list:
    """Best matching note paths for this prompt, most relevant first."""
    if not rules["notes"]:
        return []
    folder = os.path.normpath(os.path.join(root, rules["notes"]))
    if not os.path.isdir(folder):
        return []
    shown = rules["notes"].replace("\\", "/").rstrip("/")
    lower = prompt.lower()
    hits = []
    for keys, target in rules["routes"]:
        if any(re.search(r"(?<![a-z0-9])" + re.escape(k), lower) for k in keys):
            if os.path.isfile(os.path.join(folder, target)) and target not in hits:
                hits.append(target)
    asked = words_of(prompt)
    scored = []
    for name in sorted(os.listdir(folder))[:MAX_NOTES_SCANNED]:
        if not name.lower().endswith(".md") or name.lower() in INDEX_NAMES or name in hits:
            continue
        tokens = words_of(os.path.splitext(name)[0]) - {"notes", "note", "todo", "misc"}
        score = sum(1 for t in tokens if any(same_word(t, w) for w in asked))
        if score:
            scored.append((-score, name))
    hits.extend(name for _, name in sorted(scored))
    return [shown + "/" + name.replace("\\", "/") for name in hits]


def first_time(session_id: str) -> bool:
    """True on this session's first prompt. Fails open (True) on any error."""
    if not session_id:
        return True
    try:
        folder = os.path.join(tempfile.gettempdir(), "startup-team-hooks")
        os.makedirs(folder, exist_ok=True)
        name = "rules-" + hashlib.sha1(session_id.encode("utf-8", "replace")).hexdigest()[:16]
        marker = os.path.join(folder, name)
        if os.path.exists(marker):
            return False
        with open(marker, "w"):
            pass
    except OSError:
        pass
    return True


def main() -> None:
    if os.environ.get("STARTUP_TEAM_RULES_OFF") == "1":
        return
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
        if not isinstance(payload, dict):
            payload = {}
    except ValueError:
        payload = {}
    prompt = str(payload.get("prompt", "") or "")
    head = prompt.lstrip()
    # Quiet unless the prompt is the owner's (or a brief): agent reports and notifications get nothing.
    if head.startswith(NOT_THE_OWNER) or "<agent-message from=" in head[:400]:
        return
    root, path = find_rules(payload)
    if not path:
        return
    rules = parse_rules(path)
    shown = os.path.relpath(path, root).replace("\\", "/")
    notes = relevant_notes(root, rules, prompt)
    out = []
    if not (rules["full"] or rules["digest"]):
        pass  # the file only names the notes folder: just the note pointer below
    elif first_time(str(payload.get("session_id", "") or "")):
        block = "\n".join(rules["full"] or rules["digest"])
        if len(block) > FULL_MAX_CHARS:
            block = block[:FULL_MAX_CHARS].rstrip() + "\n(cut: the rest is in " + shown + ")"
        out.append("Project operating rules (" + shown + "; read before acting):")
        out.append(block)
        notes = notes[:3]
    else:
        if rules["digest"]:
            out.append("Project rules: " + "\n".join(rules["digest"]))
        else:
            out.append("Project rules: shown in full earlier this session (" + shown + ").")
        notes = notes[:1]
    if notes:
        out.append("Relevant note, open before acting: " + ", ".join(notes[:3]))
    if out:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        print("\n".join(out))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
