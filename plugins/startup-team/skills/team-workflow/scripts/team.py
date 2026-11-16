#!/usr/bin/env python3
"""startup-team tool: turn folders, shared agent memory, the learning loop and the plugin loadout.

All data lives in the project's git-ignored .handoff/ folder:
  .handoff/<stamp>-<slug>/            one folder per task (decision, answers, results, audit)
  .handoff/memory/agent-memory.jsonl  append-only shared memory
  .handoff/learned-proposals.jsonl    rules proposed for the shared team repository
  .handoff/private-words.txt          words that must never leave the project (one per line)

Usage:
  team.py turn new <slug>
  team.py memory add --kind K --text T [--source S] [--turn D] [--evidence E] [--for A] [--tags a,b]
  team.py memory query <words...>
  team.py memory digest [--for A] [--words w1 w2 ...]
  team.py memory done <id>
  team.py learn propose --text T --evidence E [--source S] [--agent A]
  team.py learn list
  team.py learn decide <id> 1|0
  team.py learn apply <id> --repo <clone of the team repository>
  team.py loadout inventory [--json] | plan --needs a,b | on|off <plugin> [--approved] [--by W] | selftest
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

KINDS = ("owner-answer", "fact", "open-item", "pointer", "learned", "setup-change")
SECRET = re.compile(
    r"(-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|\b(sk|pk|rk|ghp|gho|ghs|github_pat|xox[abprs])[-_][A-Za-z0-9_\-]{16,}"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\."
    r"|(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*\S{6,}"
    r"|\b[A-Fa-f0-9]{40,}\b)",
    re.I,
)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def root() -> Path:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except OSError:
        pass
    return Path.cwd()


def handoff() -> Path:
    r = root()
    h = r / ".handoff"
    h.mkdir(exist_ok=True)
    exclude = r / ".git" / "info" / "exclude"
    if exclude.parent.is_dir():
        text = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
        if ".handoff/" not in text.split():
            with exclude.open("a", encoding="utf-8") as f:
                f.write(("" if text.endswith("\n") or not text else "\n") + ".handoff/\n")
    return h


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def read(path: Path) -> list:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def next_id(rows: list, prefix: str) -> str:
    return f"{prefix}{len(rows) + 1:04d}"


def refuse_secret(text: str) -> None:
    if SECRET.search(text):
        sys.exit("refused: the text looks like it holds a secret. Never store one.")


def fmt(r: dict) -> str:
    extra = "".join(
        f" [{k}: {r[k]}]" for k in ("for", "tags", "turn", "evidence") if r.get(k)
    )
    return f"{r['id']} {r['date']} {r['kind']} ({r.get('source', '?')}): {r['text']}{extra}"


# ---- turn folders ----
def turn_new(a) -> None:
    slug = re.sub(r"[^a-z0-9]+", "-", a.slug.lower()).strip("-") or "task"
    d = handoff() / f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-{slug}"
    d.mkdir()
    (d / "decision.md").write_text("# Decision block\n\n(the tech lead's output goes here)\n", encoding="utf-8")
    (d / "answers.md").write_text("# Owner answers (verbatim, one per line, with the question id)\n", encoding="utf-8")
    print(d.as_posix())


# ---- memory ----
def mem_path() -> Path:
    return handoff() / "memory" / "agent-memory.jsonl"


def mem_add(a) -> None:
    refuse_secret(a.text)
    if a.kind != "owner-answer" and not a.evidence:
        sys.exit("refused: --evidence (a path, a command or a turn id) is required for this kind.")
    if a.kind == "owner-answer" and a.source not in ("main", "tech-lead"):
        sys.exit("refused: only main or tech-lead may record an owner answer.")
    rows = read(mem_path())
    row = {"id": next_id(rows, "M"), "date": now(), "kind": a.kind, "source": a.source, "text": a.text}
    for k, v in (("turn", a.turn), ("evidence", a.evidence), ("for", getattr(a, "for")), ("tags", a.tags)):
        if v:
            row[k] = v
    append(mem_path(), row)
    print(fmt(row))


def live(rows: list) -> list:
    closed = {r["closes"] for r in rows if r.get("closes")}
    return [r for r in rows if r["id"] not in closed and not r.get("closes")]


def mem_query(a) -> None:
    words = [w.lower() for w in a.words]
    hits = [r for r in live(read(mem_path())) if all(w in json.dumps(r, ensure_ascii=False).lower() for w in words)]
    for r in hits[-30:]:
        print(fmt(r))
    if not hits:
        print("no entries match.")


def mem_digest(a) -> None:
    rows = live(read(mem_path()))
    reader = getattr(a, "for")
    out = []

    def take(title, items, n):
        items = items[-n:] if n else items
        if items:
            out.append(f"## {title}")
            out.extend(fmt(r) for r in items)

    take("Open items", [r for r in rows if r["kind"] == "open-item"], 0)
    take("Latest owner answers", [r for r in rows if r["kind"] == "owner-answer"], 8)
    take("Facts", [r for r in rows if r["kind"] == "fact"], 8)
    take("Pointers", [r for r in rows if r["kind"] == "pointer"], 5)
    take(
        f"Learned (for {reader or 'all'})",
        [r for r in rows if r["kind"] == "learned" and r.get("for", "all") in ("all", reader)],
        10,
    )
    if a.words:
        seen = set(out)
        words = [w.lower() for w in a.words]
        hits = [r for r in rows if any(w in r["text"].lower() or w in r.get("tags", "").lower() for w in words)]
        hits = [r for r in hits if fmt(r) not in seen]
        take("Matches for this task", hits, 10)
    print("\n".join(out[:60]) if out else "shared memory is empty.")


def mem_done(a) -> None:
    rows = read(mem_path())
    if not any(r["id"] == a.id for r in rows):
        sys.exit(f"no entry {a.id}.")
    row = {"id": next_id(rows, "M"), "date": now(), "kind": "fact", "source": "main", "text": f"closed {a.id}", "closes": a.id}
    append(mem_path(), row)
    print(f"closed {a.id}")


# ---- learning loop ----
def learn_path() -> Path:
    return handoff() / "learned-proposals.jsonl"


def private_words() -> list:
    """Words that must never leave this project: the list the project keeps, plus its own names."""
    p = handoff() / "private-words.txt"
    if not p.exists():
        sys.exit(
            "refused: this project has no .handoff/private-words.txt yet. Create it first, one word "
            "or phrase per line: the project's name, its domains, hosts, brand terms and people. "
            "No rule leaves a project before that list exists."
        )
    words = [w.strip().lower() for w in p.read_text(encoding="utf-8").splitlines() if w.strip() and not w.startswith("#")]
    words.append(root().name.lower())
    try:
        out = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            words.append(out.stdout.strip().rstrip("/").rsplit("/", 1)[-1].removesuffix(".git").lower())
    except OSError:
        pass
    return sorted({w for w in words if len(w) >= 3})


def scrub(text: str) -> None:
    """Refuse text that is not generic enough to be shared across projects."""
    refuse_secret(text)
    problems = []
    if EMAIL.search(text):
        problems.append("an email address")
    if IPV4.search(text):
        problems.append("an IP address")
    if re.search(r"https?://|\b[\w-]+\.(com|app|io|net|org|dev|ai|co|website)\b", text, re.I):
        problems.append("a web address")
    if re.search(r"[A-Za-z]:\\|/(home|Users)/", text):
        problems.append("a local file path")
    low = text.lower()
    problems += [f'the private word "{w}"' for w in private_words() if w in low]
    if problems:
        sys.exit("refused: a shared rule must be generic. It contains " + ", ".join(problems) + ".")


def learn_propose(a) -> None:
    scrub(a.text)
    rows = read(learn_path())
    row = {"id": next_id(rows, "L"), "date": now(), "source": a.source, "agent": a.agent, "evidence": a.evidence, "text": a.text, "status": "proposed"}
    append(learn_path(), row)
    print(f"{row['id']} proposed for [{a.agent}]. Put it to the owner as a 1/0 question.")


def learn_state(rows: list) -> dict:
    state = {}
    for r in rows:
        if r.get("decides"):
            state[r["decides"]]["status"] = r["status"]
        else:
            state[r["id"]] = dict(r)
    return state


def learn_list(_a) -> None:
    state = learn_state(read(learn_path()))
    for r in state.values():
        print(f"{r['id']} [{r['status']}] {r['date']} ({r['source']} -> {r.get('agent', 'all')}): {r['text']}  [evidence: {r['evidence']}]")
    if not state:
        print("no proposals.")


def learn_decide(a) -> None:
    rows = read(learn_path())
    state = learn_state(rows)
    if a.id not in state:
        sys.exit(f"no proposal {a.id}.")
    status = "approved" if a.answer == "1" else "declined"
    append(learn_path(), {"id": next_id(rows, "L"), "date": now(), "decides": a.id, "status": status})
    print(f"{a.id} {status}.")
    if status == "approved":
        print(f"Next: team.py learn apply {a.id} --repo <path to a clone of the startup-team repository>")


def learn_apply(a) -> None:
    """Write an approved rule into a clone of the team repository and bump the plugin version."""
    rows = read(learn_path())
    state = learn_state(rows)
    if a.id not in state:
        sys.exit(f"no proposal {a.id}.")
    rule = state[a.id]
    if rule["status"] != "approved":
        sys.exit(f"refused: {a.id} is {rule['status']}. Only a rule the owner approved (1) is applied.")
    scrub(rule["text"])  # checked again: the private-word list may have grown since the proposal
    repo = Path(a.repo)
    plugin = repo / "plugins" / "startup-team"
    learned = plugin / "skills" / "team-workflow" / "LEARNED.md"
    manifest = plugin / ".claude-plugin" / "plugin.json"
    if not learned.exists() or not manifest.exists():
        sys.exit(f"refused: {repo} is not a clone of the startup-team repository.")
    if repo.resolve() == root().resolve() or str(repo.resolve()).startswith(str(root().resolve()) + "\\"):
        sys.exit("refused: the team repository must be a separate clone, outside this project.")
    line = f"- {datetime.date.today().isoformat()} [{rule.get('agent', 'all')}]: {rule['text']}"
    text = learned.read_text(encoding="utf-8")
    if rule["text"] in text:
        sys.exit("already in LEARNED.md.")
    learned.write_text(text.rstrip("\n") + "\n" + line + "\n", encoding="utf-8")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    major, minor, patch = (int(x) for x in data["version"].split("."))
    data["version"] = f"{major}.{minor}.{patch + 1}"
    manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    append(learn_path(), {"id": next_id(rows, "L"), "date": now(), "decides": a.id, "status": "applied"})
    print(f"{a.id} written to LEARNED.md; plugin version is now {data['version']}.")
    print(f"In {repo.as_posix()}: commit both files on a branch named learn/{a.id.lower()} (the message")
    print("must stay generic too). The owner merges it; the push guard checks it again.")


# ---- loadout: which plugins a session lists, and switching them for this project ----

TEAM_PLUGIN = "startup-team@"


def claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def same_path(a: str, b) -> bool:
    return os.path.normcase(os.path.normpath(str(a))) == os.path.normcase(os.path.normpath(str(b)))


def listed_chars(path: Path) -> tuple:
    """(description characters, hidden) from a skill, command or agent file's frontmatter."""
    try:
        t = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    except OSError:
        return 0, False
    m = re.match(r"---\s*\n(.*?)\n---", t, re.S)
    if not m:
        return 0, False
    d = re.search(r"^description:\s*(.*?)(?=^\S+:|\Z)", m.group(1), re.S | re.M)
    hidden = bool(re.search(r"^disable-model-invocation:\s*true", m.group(1), re.M))
    return (len(d.group(1).strip()) if d else 0), hidden


def enabled_map(proj: Path, home: Path) -> dict:
    """Explicit enabledPlugins values; local settings win over project, project over user."""
    out = {}
    for f in (home / "settings.json", proj / ".claude" / "settings.json", proj / ".claude" / "settings.local.json"):
        try:
            out.update(json.loads(f.read_text(encoding="utf-8")).get("enabledPlugins") or {})
        except (OSError, ValueError, AttributeError):
            pass
    return out


def inventory(proj: Path, home: Path) -> dict:
    plugins = []
    try:
        inst = json.loads((home / "plugins" / "installed_plugins.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        inst = None
    if inst is None:  # fall back to the CLI's own listing (names only)
        try:
            out = subprocess.run(["claude", "plugin", "list"], capture_output=True, text=True, timeout=60).stdout
        except (OSError, subprocess.SubprocessError):
            out = ""
        inst = {"plugins": {n: [{"scope": "?"}] for n in re.findall(r"\b([\w.-]+@[\w.-]+)\b", out)}}
    enabled = enabled_map(proj, home)
    for name, entries in sorted(inst.get("plugins", {}).items()):
        for e in entries:
            if e.get("projectPath") and not same_path(e["projectPath"], proj):
                continue
            r = Path(e.get("installPath") or "/nonexistent")
            sk = [listed_chars(p) for p in r.rglob("SKILL.md")] if r.is_dir() else []
            cm = [listed_chars(p) for p in r.glob("commands/*.md")]
            ag = [listed_chars(p) for p in r.glob("agents/*.md")]
            meta = {}
            try:
                meta = json.loads((r / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
            chars = sum(c for c, h in sk + cm if not h) + sum(c for c, _ in ag)
            plugins.append({
                "name": name, "scope": e.get("scope", "?"), "enabled": enabled.get(name, True),
                "skills": len(sk), "commands": len(cm), "agents": len(ag),
                "hooks": bool(list(r.rglob("hooks.json")) if r.is_dir() else False) or "hooks" in meta,
                "mcp": (r / ".mcp.json").exists() or "mcpServers" in meta,
                "tokens": chars // 4,
            })
    md = proj / "CLAUDE.md"
    try:
        sessions = {k: {"id": v.get("id"), "title": v.get("title")}
                    for k, v in json.loads((proj / ".handoff" / "team-sessions.json").read_text(encoding="utf-8")).items()}
    except (OSError, ValueError, AttributeError):
        sessions = {}
    return {"date": now(), "plugins": plugins,
            "claude_md_tokens": len(md.read_text(encoding="utf-8")) // 4 if md.exists() else 0,
            "sessions": sessions}


def always_on(proj: Path) -> set:
    md = proj / "CLAUDE.md"
    text = md.read_text(encoding="utf-8") if md.exists() else ""
    return {w.strip().strip("`") for line in re.findall(r"^ALWAYS ON:(.*)$", text, re.M) for w in line.split(",") if w.strip()}


def find_plugin(inv: dict, name: str):
    for p in inv["plugins"]:
        if p["name"] == name or p["name"].split("@")[0] == name:
            return p
    return None


def switch(action: str, name: str, proj: Path, home: Path, scope: str = "local", approved: bool = False,
           by: str = "main", run=None) -> tuple:
    """Return (exit code, message). Refusals are exit 2 and change nothing."""
    if scope != "local":
        return 2, "refused: only --scope local (this project) is switched"
    inv = inventory(proj, home)
    p = find_plugin(inv, name)
    if not p:
        return 2, f"refused: {name} is not installed for this project"
    if p["name"].startswith(TEAM_PLUGIN):
        return 2, "refused: the team's own plugin is never switched"
    al = always_on(proj)
    if action == "off" and (p["name"] in al or p["name"].split("@")[0] in al):
        return 2, f"refused: {p['name']} is on the project's ALWAYS ON line"
    if action == "off" and (p["hooks"] or p["mcp"]) and not approved:
        return 2, f"refused: {p['name']} has hooks or MCP servers; switching it off needs the owner's yes (--approved)"
    cmd = ["claude", "plugin", "enable" if action == "on" else "disable", p["name"], "--scope", "local"]
    code = (run or (lambda c: subprocess.run(c, cwd=proj).returncode))(cmd)
    if code != 0:
        return 1, f"failed: {' '.join(cmd)} exited {code}"
    append(proj / ".handoff" / "loadout" / "log.jsonl",
           {"date": now(), "action": action, "plugin": p["name"], "tokens": p["tokens"], "by": by})
    return 0, f"{action} {p['name']} (~{p['tokens']} tok {'added' if action == 'on' else 'saved'}; takes effect in a new or cleared session)"


def lo_inventory(a) -> None:
    proj = root()
    inv = inventory(proj, claude_home())
    out = handoff() / "loadout" / "inventory.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(inv, indent=1), encoding="utf-8")
    if a.json:
        print(json.dumps(inv, indent=1))
        return
    print(f"{'plugin':34} {'scope':6} {'on':3} {'skills':>6} {'cmds':>4} {'agents':>6} hooks mcp {'~tok':>6}")
    for p in inv["plugins"]:
        print(f"{p['name']:34} {p['scope']:6} {'yes' if p['enabled'] else 'no':3} {p['skills']:6} {p['commands']:4} "
              f"{p['agents']:6} {'yes' if p['hooks'] else '-':5} {'yes' if p['mcp'] else '-':3} {p['tokens']:6}")
    print(f"listed by enabled plugins: ~{sum(p['tokens'] for p in inv['plugins'] if p['enabled'])} tok; "
          f"CLAUDE.md ~{inv['claude_md_tokens']} tok; standing sessions: "
          + (", ".join(f"{k} ({v['title']})" for k, v in inv["sessions"].items()) or "none"))
    print(f"written: {out.as_posix()} (rough: characters / 4)")


def plan(inv: dict, needs: list, al: set) -> list:
    rows = []
    for p in inv["plugins"]:
        short = p["name"].split("@")[0]
        need = p["name"] in needs or short in needs
        if p["name"].startswith(TEAM_PLUGIN) or p["name"] in al or short in al:
            continue
        if need and not p["enabled"]:
            rows.append(("on", p, ""))
        elif not need and p["enabled"]:
            rows.append(("off", p, " (needs the owner's yes: hooks or MCP)" if p["hooks"] or p["mcp"] else ""))
    return rows


def lo_plan(a) -> None:
    proj = root()
    inv = inventory(proj, claude_home())
    rows = plan(inv, [n.strip() for n in a.needs.split(",") if n.strip()], always_on(proj))
    for act, p, note in rows:
        print(f"{act:3} {p['name']} ~{p['tokens']} tok{note}")
    saved = sum(p["tokens"] for act, p, _ in rows if act == "off") - sum(p["tokens"] for act, p, _ in rows if act == "on")
    print(f"{'nothing to switch' if not rows else 'rough saving'}: ~{saved} tok per session (nothing changed)")


def lo_switch(a) -> None:
    code, msg = switch(a.cmd, a.plugin, root(), claude_home(), a.scope, a.approved, a.by)
    print(msg)
    sys.exit(code)


def lo_selftest(_a) -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        home, proj = t / "home", t / "proj"

        def plug(name, skill_desc, hidden=False, hooks=False):
            r = t / "cache" / name
            (r / "skills" / "s").mkdir(parents=True)
            (r / "skills" / "s" / "SKILL.md").write_text(
                f"---\nname: s\ndescription: {skill_desc}\n" + ("disable-model-invocation: true\n" if hidden else "") + "---\nbody\n",
                encoding="utf-8")
            if hooks:
                (r / "hooks").mkdir()
                (r / "hooks" / "hooks.json").write_text("{}", encoding="utf-8")
            return {"scope": "local", "projectPath": str(proj), "installPath": str(r)}

        (home / "plugins").mkdir(parents=True)
        (proj / ".claude").mkdir(parents=True)
        (home / "plugins" / "installed_plugins.json").write_text(json.dumps({"plugins": {
            "startup-team@m": [plug("team", "x" * 40)],
            "light@m": [plug("light", "y" * 400)],
            "hidden@m": [plug("hidden", "z" * 400, hidden=True)],
            "hooked@m": [plug("hooked", "w" * 80, hooks=True)],
            "pinned@m": [plug("pinned", "v" * 80)],
            "elsewhere@m": [dict(plug("elsewhere", "u" * 80), projectPath=str(t / "other"))],
        }}), encoding="utf-8")
        (proj / ".claude" / "settings.local.json").write_text(json.dumps({"enabledPlugins": {"hidden@m": False}}), encoding="utf-8")
        (proj / "CLAUDE.md").write_text("# x\nALWAYS ON: pinned\n", encoding="utf-8")
        inv = inventory(proj, home)
        by = {p["name"]: p for p in inv["plugins"]}
        assert "elsewhere@m" not in by, "another project's plugin listed"
        assert by["light@m"]["tokens"] == 100 and by["hidden@m"]["tokens"] == 0, "cost counting"
        assert by["hooked@m"]["hooks"] and not by["light@m"]["hooks"], "hook detection"
        assert by["light@m"]["enabled"] and not by["hidden@m"]["enabled"], "enabled state"
        ran = []
        run = lambda c: ran.append(c) or 0
        assert switch("off", "startup-team", proj, home, run=run)[0] == 2
        assert switch("off", "light", proj, home, scope="user", run=run)[0] == 2
        assert switch("off", "pinned", proj, home, run=run)[0] == 2
        assert switch("off", "hooked", proj, home, run=run)[0] == 2
        assert switch("off", "nothere", proj, home, run=run)[0] == 2
        assert not ran, "a refusal ran a command"
        assert switch("off", "light", proj, home, run=run)[0] == 0
        assert switch("off", "hooked", proj, home, approved=True, run=run)[0] == 0
        assert ran[0] == ["claude", "plugin", "disable", "light@m", "--scope", "local"], ran[0]
        assert len(read(proj / ".handoff" / "loadout" / "log.jsonl")) == 2, "log lines"
        acts = {(act, p["name"]) for act, p, _ in plan(inv, ["hidden"], always_on(proj))}
        assert acts == {("on", "hidden@m"), ("off", "light@m"), ("off", "hooked@m")}, acts
    print("loadout selftest ok")


def main() -> None:
    p = argparse.ArgumentParser(description="startup-team: turn folders, shared memory, learning loop")
    sub = p.add_subparsers(dest="area", required=True)

    t = sub.add_parser("turn").add_subparsers(dest="cmd", required=True)
    tn = t.add_parser("new")
    tn.add_argument("slug")
    tn.set_defaults(fn=turn_new)

    m = sub.add_parser("memory").add_subparsers(dest="cmd", required=True)
    ma = m.add_parser("add")
    ma.add_argument("--kind", required=True, choices=KINDS)
    ma.add_argument("--text", required=True)
    ma.add_argument("--source", default="main")
    ma.add_argument("--turn")
    ma.add_argument("--evidence")
    ma.add_argument("--for")
    ma.add_argument("--tags")
    ma.set_defaults(fn=mem_add)
    mq = m.add_parser("query")
    mq.add_argument("words", nargs="+")
    mq.set_defaults(fn=mem_query)
    md = m.add_parser("digest")
    md.add_argument("--for")
    md.add_argument("--words", nargs="*", default=[])
    md.set_defaults(fn=mem_digest)
    mx = m.add_parser("done")
    mx.add_argument("id")
    mx.set_defaults(fn=mem_done)

    le = sub.add_parser("learn").add_subparsers(dest="cmd", required=True)
    lp = le.add_parser("propose")
    lp.add_argument("--text", required=True)
    lp.add_argument("--evidence", required=True)
    lp.add_argument("--source", default="main")
    lp.add_argument("--agent", default="all", choices=("all", "tech-lead", "architect", "designer", "executor", "qa", "auditor", "devops", "security", "skill-sub", "dispatcher", "messenger", "video", "activator"))
    lp.set_defaults(fn=learn_propose)
    lap = le.add_parser("apply")
    lap.add_argument("id")
    lap.add_argument("--repo", required=True)
    lap.set_defaults(fn=learn_apply)
    le.add_parser("list").set_defaults(fn=learn_list)
    ld = le.add_parser("decide")
    ld.add_argument("id")
    ld.add_argument("answer", choices=("0", "1"))
    ld.set_defaults(fn=learn_decide)

    lo = sub.add_parser("loadout").add_subparsers(dest="cmd", required=True)
    li = lo.add_parser("inventory")
    li.add_argument("--json", action="store_true")
    li.set_defaults(fn=lo_inventory)
    lpl = lo.add_parser("plan")
    lpl.add_argument("--needs", required=True)
    lpl.set_defaults(fn=lo_plan)
    for c in ("on", "off"):
        ls = lo.add_parser(c)
        ls.add_argument("plugin")
        ls.add_argument("--scope", default="local")
        ls.add_argument("--approved", action="store_true", help="the owner's yes, never given by an agent itself")
        ls.add_argument("--by", default="main")
        ls.set_defaults(fn=lo_switch)
    lo.add_parser("selftest").set_defaults(fn=lo_selftest)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
