#!/usr/bin/env python3
"""startup-team tool: turn folders, shared agent memory, the learning loop and the plugin loadout.

All data lives in the project's .handoff/ folder (git-ignored unless the project tracks it):
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
  team.py records index | find <words...> [--kind K] [--last N] | check-commit | selftest
  team.py conversations build | selftest
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


def handoff_tracked(r: Path) -> bool:
    """True when the project tracks .handoff/ in git (then records must not be hidden)."""
    try:
        out = subprocess.run(["git", "-C", str(r), "ls-files", "--", ".handoff"], capture_output=True, text=True)
    except OSError:
        return False
    return out.returncode == 0 and bool(out.stdout.strip())


def handoff(r: Path = None) -> Path:
    r = r or root()
    h = r / ".handoff"
    h.mkdir(exist_ok=True)
    exclude = r / ".git" / "info" / "exclude"
    if exclude.parent.is_dir() and not handoff_tracked(r):
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


# ---- records: a searchable index of the record files, so sessions open only what they need ----

RECORD_KINDS = ("decision", "answers", "brief", "result", "qa", "audit", "plan", "devops")
SKIP_DIRS = {"memory", "gateway", "loadout"}
STOP = set("""this that with from have will what when where which there their them they then than
into only must also each been were your here more some such over just like does done none line
file files said says name names para make made after before under same other these those about
need needs used uses using owner piece pieces team session sessions""".split())


def record_kind(rel: Path) -> str:
    if rel.parts[0] == "checkpoints":
        return "checkpoint"
    stem = rel.stem.lower()
    return next((k for k in RECORD_KINDS if stem == k or stem.startswith(k + "-")), "other")


def record_row(h: Path, f: Path) -> dict:
    rel = f.relative_to(h)
    text = f.read_text(encoding="utf-8", errors="replace")
    title = next((l.strip().lstrip("#").strip() for l in text.splitlines() if l.strip()), "")[:100]
    if SECRET.search(title) or EMAIL.search(title):
        title = "[title withheld]"
    # blank whole secret and email matches before splitting, so no part of a value becomes a keyword
    clean = SECRET.sub(" ", EMAIL.sub(" ", text))
    words = [w for w in re.findall(r"[a-z][a-z0-9-]{3,}", clean.lower()) if w not in STOP]
    keys = [w for w, _ in sorted(((w, words.count(w)) for w in set(words)), key=lambda x: (-x[1], x[0]))[:12]]
    return {"path": rel.as_posix(), "turn": "" if rel.parts[0] == "checkpoints" else rel.parts[0],
            "kind": record_kind(rel), "title": title, "keywords": keys,
            "size": f.stat().st_size, "mtime": int(f.stat().st_mtime)}


def records_index(h: Path) -> list:
    """Rebuild .handoff/records-index.jsonl, re-reading only files whose modified time changed."""
    old = {r["path"]: r for r in read(h / "records-index.jsonl")}
    rows = []
    for f in sorted(h.rglob("*.md")):
        rel = f.relative_to(h)
        if len(rel.parts) < 2 or rel.parts[0] in SKIP_DIRS:
            continue
        r = old.get(rel.as_posix())
        rows.append(r if r and r.get("mtime") == int(f.stat().st_mtime) else record_row(h, f))
    (h / "records-index.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return rows


def records_find(h: Path, words: list, kind: str = None, last: int = None, limit: int = 5) -> list:
    rows = records_index(h)
    if kind:
        rows = [r for r in rows if r["kind"] == kind]
    if last:  # only the n newest turn folders (checkpoints always count)
        turns = sorted({r["turn"] for r in rows if r["turn"]})[-last:]
        rows = [r for r in rows if not r["turn"] or r["turn"] in turns]
    q = [w.lower() for w in words]
    scored = []
    for r in rows:
        hay = (r["path"] + " " + r["title"]).lower()
        s = sum(3 * (w in hay) + 2 * any(k.startswith(w) for k in r["keywords"]) for w in q)
        if s:
            scored.append((s, r["mtime"], r))
    return [r for _, _, r in sorted(scored, key=lambda x: (-x[0], -x[1]))[:limit]]


def rec_index(_a) -> None:
    rows = records_index(handoff())
    print(f"{len(rows)} record files indexed in .handoff/records-index.jsonl")


def rec_find(a) -> None:
    hits = records_find(handoff(), a.words, a.kind, a.last)
    try:  # a console that cannot show a character prints "?" instead of failing
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    for r in hits:
        print(f".handoff/{r['path']}  [{r['kind']}]  {r['title']}")
    if not hits:
        print("no record matches")
        sys.exit(4)


def rec_selftest(_a) -> None:
    import os as _os
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp)
        (h / "20260101-0900-alpha").mkdir()
        (h / "20260102-0900-beta").mkdir()
        (h / "checkpoints").mkdir()
        (h / "memory").mkdir()
        (h / "20260101-0900-alpha" / "decision.md").write_text("# Decision\nwidget widget widget gateway\n", encoding="utf-8")
        (h / "20260102-0900-beta" / "result-P1.md").write_text("PIECE: widget fix\nwidget sprocket\n", encoding="utf-8")
        (h / "20260102-0900-beta" / "qa-final.md").write_text("token = abcdef1234567890\nsprocket\n", encoding="utf-8")
        (h / "checkpoints" / "developer.md").write_text("Developer checkpoint\nnext: sprocket\n", encoding="utf-8")
        (h / "memory" / "notes.md").write_text("widget\n", encoding="utf-8")
        rows = {r["path"]: r for r in records_index(h)}
        assert "memory/notes.md" not in rows, "memory folder indexed"
        assert len(rows) == 4, rows.keys()
        assert rows["20260101-0900-alpha/decision.md"]["kind"] == "decision"
        assert rows["20260102-0900-beta/result-P1.md"]["kind"] == "result"
        assert rows["20260102-0900-beta/qa-final.md"]["kind"] == "qa"
        assert rows["checkpoints/developer.md"]["kind"] == "checkpoint" and rows["checkpoints/developer.md"]["turn"] == ""
        assert rows["20260102-0900-beta/qa-final.md"]["title"] == "[title withheld]", "secret in title"
        assert rows["20260101-0900-alpha/decision.md"]["keywords"][0] == "widget"
        # secret shapes: no part of the value may reach the title or the keywords
        vals = ["zqvalpwdxyzz", "zqvalapikeyzz", "zqvalghptokenzz0123456789", "deadbeef" * 5]
        shapes = (f"password={vals[0]}\napi_key: {vals[1]}\nghp_{vals[2]}\n{vals[3]}\n" * 3 + "mail zq@example.com\n")
        for name, text in (("body", "harmless title\n" + shapes), ("title", f"password={vals[0]} ghp_{vals[2]}\n" + shapes)):
            f = h / "20260102-0900-beta" / f"other-{name}.md"
            f.write_text(text, encoding="utf-8")
            r = record_row(h, f)
            blob = (r["title"] + " " + " ".join(r["keywords"])).lower()
            for v in vals + ["example"]:
                assert not any(part in blob for part in (v.lower(), v.lower()[4:12])), (name, v, r)
            f.unlink()
        assert len(records_find(h, ["widget"])) == 2
        hits = records_find(h, ["gateway"])
        assert [r["path"] for r in hits] == ["20260101-0900-alpha/decision.md"], hits
        assert records_find(h, ["sprocket", "fix"])[0]["path"] == "20260102-0900-beta/result-P1.md", "title match ranks first"
        assert [r["path"] for r in records_find(h, ["widget"], kind="result")] == ["20260102-0900-beta/result-P1.md"]
        assert all(r["turn"] != "20260101-0900-alpha" for r in records_find(h, ["widget"], last=1))
        assert records_find(h, ["nothingmatches"]) == []
        f = h / "20260102-0900-beta" / "result-P1.md"
        f.write_text("PIECE: gear fix\n", encoding="utf-8")
        _os.utime(f, (f.stat().st_atime, f.stat().st_mtime + 5))
        assert {r["path"]: r for r in records_index(h)}["20260102-0900-beta/result-P1.md"]["title"] == "PIECE: gear fix"
    rec_git_selftest()
    print("records selftest ok")


BLOCKED_STAGED = re.compile(r"(^|/)(gateway/maps/|\.private(/|$)|\.env(\.|$)|settings\.local\.json$)")


def commit_problems(r: Path) -> list:
    """Problems in the staged change of a records commit: names outside .handoff/, blocked names, secret shapes."""
    git = ["git", "-C", str(r)]
    names = subprocess.run(git + ["diff", "--cached", "--name-only"], capture_output=True, text=True).stdout.splitlines()
    out = []
    for n in filter(None, names):
        if not n.startswith(".handoff/"):
            out.append(f"outside .handoff/: {n}")
        elif BLOCKED_STAGED.search(n):
            out.append(f"blocked name: {n}")
    diff = subprocess.run(git + ["diff", "--cached", "-U0"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    fname = ""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            fname = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("+") and SECRET.search(GIT_SHA.sub("gitsha", line) if GIT_WORD.search(line) else line):
            out.append(f"secret shape in {fname}")  # the value itself is never printed
        elif line.startswith("+"):
            m = GATEWAY_NONE.match(line[1:])
            if m and not m.group(1).lower().startswith(GATEWAY_REASONS):
                out.append(f"GATEWAY reason not allowed in {fname}: {m.group(1)[:60] or '(none)'}")
    return sorted(set(out))


# A full git commit id (40 lowercase hex) on a line that talks about git is not a secret.
GIT_SHA = re.compile(r"\b[0-9a-f]{40}\b")
GIT_WORD = re.compile(r"\b(git|commit|sha|ls-remote|push|merge|rev-parse|HEAD|origin)\b", re.I)

# The allowed reasons for skipping the gateway (SKILL.md "Delegation first", Record line).
GATEWAY_NONE = re.compile(r"\s*GATEWAY:\s*none\b:?\s*(.*)$", re.I)
GATEWAY_REASONS = ("not delegable", "gateway refused", "gateway unreachable", "failed twice")


def rec_check_commit(_a) -> None:
    probs = commit_problems(root())
    for x in probs:
        print(x)
    if probs:
        print("STOP: do not commit; tell the owner")
        sys.exit(5)
    print("staged records ok")


def rec_git_selftest() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        r = Path(tmp)
        git = ["git", "-C", tmp, "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(git + ["init", "-q"], check=True)
        handoff(r)
        ex = r / ".git" / "info" / "exclude"
        assert ".handoff/" in ex.read_text(encoding="utf-8").split(), "untracked project: exclude added"
        ex.write_text("", encoding="utf-8")
        (r / ".handoff" / "a.md").write_text("note\n", encoding="utf-8")
        subprocess.run(git + ["add", ".handoff/a.md"], check=True)
        subprocess.run(git + ["commit", "-qm", "x"], check=True)
        handoff(r)
        assert ".handoff/" not in ex.read_text(encoding="utf-8").split(), "tracked project: exclude skipped"
        assert commit_problems(r) == []
        (r / ".handoff" / "gateway" / "maps").mkdir(parents=True)
        (r / ".handoff" / "gateway" / "maps" / "m.json").write_text("{}\n", encoding="utf-8")
        (r / "out.txt").write_text("x\n", encoding="utf-8")
        (r / ".handoff" / "b.md").write_text("api_key = zqvalsecret123\n", encoding="utf-8")
        subprocess.run(git + ["add", "-f", ".handoff", "out.txt"], check=True)
        probs = commit_problems(r)
        assert "blocked name: .handoff/gateway/maps/m.json" in probs, probs
        assert "outside .handoff/: out.txt" in probs, probs
        assert "secret shape in .handoff/b.md" in probs, probs
        assert not any("zqvalsecret" in x for x in probs)
        (r / ".handoff" / "c.md").write_text(
            "GATEWAY: none: not delegable (running tests)\nGATEWAY: none: failed twice\n"
            "GATEWAY: none: gateway unreachable (worker)\nGATEWAY: 2026-ab12 copy pass\n", encoding="utf-8")
        (r / ".handoff" / "d.md").write_text("GATEWAY: none: small change, nothing to draft\n", encoding="utf-8")
        (r / ".handoff" / "e.md").write_text("GATEWAY: none\n", encoding="utf-8")
        subprocess.run(git + ["add", "-f", ".handoff"], check=True)
        probs = commit_problems(r)
        assert not any("c.md" in x for x in probs), probs
        assert "GATEWAY reason not allowed in .handoff/d.md: small change, nothing to draft" in probs, probs
        assert "GATEWAY reason not allowed in .handoff/e.md: (none)" in probs, probs
        sha = "330e1a47f7908561464c89a7ca89f29670d2ba92"
        (r / ".handoff" / "f.md").write_text(f"- `git push`: ls-remote: {sha}\n", encoding="utf-8")
        (r / ".handoff" / "g.md").write_text(f"note {sha}\n", encoding="utf-8")
        (r / ".handoff" / "h.md").write_text(f"commit token = {sha}\n", encoding="utf-8")
        subprocess.run(git + ["add", "-f", ".handoff"], check=True)
        probs = commit_problems(r)
        assert "secret shape in .handoff/f.md" not in probs, probs
        assert "secret shape in .handoff/g.md" in probs, "a bare 40-hex with no git word still counts"
        assert "secret shape in .handoff/h.md" in probs, "token = <value> still counts on a git line"


# ---- conversations: per-session, per-day chat files plus a hand-kept SUMMARY.md ----

CHAT_CUT = 3000  # shortcut: long replies are cut at 3000 chars; the transcript holds the rest
SUMMARY_TEMPLATE = """# Conversation summary (read this first, open a sub file only when the task needs it)

Last updated <date>. One entry per task. Paths are relative to `.handoff/`.
- **Chat** = what the owner typed and each reply, in `conversations/<session>-<date>.md`.
- **Records** = the task's turn folder (`decision.md`, `answers.md`, `result-*.md`, `qa-*.md`, `audit.md`).
- Search instead of reading whole files: Grep `conversations/` for a word, or `team.py records find <words>`.

## Where things stand
- (what is live, what is committed but not shipped, what waits on the owner)

## Tasks, oldest first
| # | When | Asked for | Outcome | Chat | Records |
|---|------|-----------|---------|------|---------|

## Keeping this current
At each task's close: run `team.py conversations build`, add one row above and update "Where things
stand". Keep this file under about 60 lines.
"""


def transcripts_dir(proj: Path) -> Path:
    # Claude Code names a project's transcript folder after its path, every non-alphanumeric as "-"
    return claude_home() / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(proj.resolve()))


def chat_text(content):
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None  # a tool result, not a message
        content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content or ""


def owner_said(raw: str) -> str:
    cmd = re.search(r"<command-name>(.*?)</command-name>", raw, re.S)
    if cmd:
        args = re.search(r"<command-args>(.*?)</command-args>", raw, re.S)
        return (cmd.group(1) + " " + (args.group(1) if args else "")).strip()
    raw = re.sub(r"<(system-reminder|pasted_content[^>]*)>.*?</\1>", "", raw, flags=re.S).strip()
    return "" if raw.startswith(("<", "[Request interrupted")) else raw


def chat_clean(s: str) -> str:
    s = EMAIL.sub("[REDACTED]", SECRET.sub("[REDACTED]", s.strip()))
    return s if len(s) <= CHAT_CUT else s[:CHAT_CUT] + "\n[cut: the rest is in the transcript]"


def conversations_build(proj: Path, src: Path):
    """Write .handoff/conversations/<session>-<YYYYMMDD>.md; return (files, owner messages) or None."""
    if not src.is_dir():
        return None
    out = proj / ".handoff" / "conversations"
    out.mkdir(parents=True, exist_ok=True)
    turns = sorted(p.name for p in (proj / ".handoff").iterdir() if p.is_dir() and re.match(r"\d{8}-\d{4}", p.name))
    files, owner_count = {}, 0
    for path in sorted(src.glob("*.jsonl")):
        title, entries, reply = "session", [], None
        for line in path.open(encoding="utf-8", errors="replace"):
            try:
                d = json.loads(line)
                if d.get("type") == "custom-title":
                    title = d.get("customTitle") or title
                if d.get("isSidechain") or d.get("type") not in ("user", "assistant"):
                    continue
                when = datetime.datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).astimezone()
                content = d["message"].get("content")
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
            if d["type"] == "assistant":
                for b in content if isinstance(content, list) else []:
                    if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip():
                        reply = (when, "Reply", b["text"])  # keep only the turn's last text
                continue
            raw = chat_text(content)
            if raw is None:
                continue
            if reply:  # a new message closes the previous turn
                entries.append(reply)
                reply = None
            human = (d.get("origin") or {}).get("kind") == "human" and not d.get("isMeta")
            said = owner_said(raw) if human else ""
            if said:
                entries.append((when, "OWNER", said))
        if reply:
            entries.append(reply)
        if not any(who == "OWNER" for _, who, _ in entries):
            continue  # a session the owner never typed in
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "session"
        for when, who, said in entries:
            key = f"{slug}-{when:%Y%m%d}.md"
            files.setdefault(key, [f"# {title}, {when:%Y-%m-%d}\nTranscript: {path}\n"]).append(
                f"\n## {when:%H:%M} {who}\n{chat_clean(said)}\n")
            owner_count += who == "OWNER"
    for name, parts in files.items():
        started = [t for t in turns if t.startswith(name[-11:-3])]
        if started:
            parts.insert(1, "Turn folders started this day: " + ", ".join(started) + "\n")
        (out / name).write_text("".join(parts), encoding="utf-8")
    summary = out / "SUMMARY.md"
    if not summary.exists():
        summary.write_text(SUMMARY_TEMPLATE.replace("<date>", datetime.date.today().isoformat()), encoding="utf-8")
    return len(files), owner_count


def conv_build(_a) -> None:
    proj = root()
    src = transcripts_dir(proj)
    got = conversations_build(proj, src)
    if got is None:
        print(f"no transcript folder for this project ({src.as_posix()}); nothing written")
        return
    print(f"{got[0]} files, {got[1]} owner messages -> .handoff/conversations/")


def conv_selftest(_a) -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        proj, src = t / "proj", t / "transcripts"
        (proj / ".handoff" / "20260301-0900-demo").mkdir(parents=True)
        src.mkdir()
        assert conversations_build(proj, t / "missing") is None and not (proj / ".handoff" / "conversations").exists()
        ts = "2026-03-01T10:00:00Z"

        def u(content, human=True, **kw):
            return dict({"type": "user", "timestamp": ts, "origin": {"kind": "human"} if human else {},
                         "message": {"content": content}}, **kw)

        def a(text):
            return {"type": "assistant", "timestamp": ts, "message": {"content": [{"type": "text", "text": text}]}}

        rows = [{"type": "custom-title", "customTitle": "Demo Chat"},
                u("please ask-all-users and fix the widget <system-reminder>hidden rule</system-reminder>"),
                a("first draft reply"),
                u([{"type": "tool_result", "content": "tool output here"}], human=False),
                a("final reply one"),
                u("<command-name>/demo-cmd</command-name><command-args>now</command-args>"),
                a("x" * 4000),
                u("my password=hunter2secret and ghp_abcdefghijklmnopqrstuvwxyz"),
                a("noted"),
                dict(a("sidechain text"), isSidechain=True)]
        (src / "s1.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows) + "not json\n", encoding="utf-8")
        (src / "s2.jsonl").write_text(json.dumps(a("no owner here")) + "\n", encoding="utf-8")
        assert conversations_build(proj, src) == (1, 3)
        out = proj / ".handoff" / "conversations"
        day = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
        body = (out / f"demo-chat-{day:%Y%m%d}.md").read_text(encoding="utf-8")
        assert "ask-all-users" in body and "hidden rule" not in body, "owner kept, reminder dropped"
        assert "tool output" not in body and "first draft" not in body and "final reply one" in body
        assert "/demo-cmd now" in body and "sidechain" not in body
        assert "hunter2" not in body and "abcdefghijklmnop" not in body and "[REDACTED]" in body
        assert "[cut: the rest is in the transcript]" in body and "x" * 3001 not in body
        if day.strftime("%Y%m%d") == "20260301":
            assert "Turn folders started this day: 20260301-0900-demo" in body
        assert "| # | When | Asked for | Outcome | Chat | Records |" in (out / "SUMMARY.md").read_text(encoding="utf-8")
        (out / "SUMMARY.md").write_text("hand-kept\n", encoding="utf-8")
        conversations_build(proj, src)
        assert (out / "SUMMARY.md").read_text(encoding="utf-8") == "hand-kept\n", "SUMMARY.md changed"
    print("conversations selftest ok")


# --- git: the repeated git steps as one command each (owner, 2026-11-23: scripts save tokens) ---
FIXTURE = "<redacted-fixture>"


def run_git(repo, *args, check=True) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and out.returncode:
        raise SystemExit(f"git {' '.join(a for a in args if not a.startswith('user.'))[:60]} failed: {(out.stderr or out.stdout).strip()[:200]}")
    return out.stdout


def redact_fixtures(path: Path) -> int:
    """Replace secret shapes in one record file with a placeholder; returns the count (values never printed).
    A full git commit id on a line that talks about git stays, as in commit_problems."""
    count = 0
    def swap(m, git_line):
        nonlocal count
        if git_line and GIT_SHA.fullmatch(m.group(0)):
            return m.group(0)
        count += 1
        return FIXTURE
    text = path.read_text(encoding="utf-8")
    new = "".join(SECRET.sub(lambda m, g=bool(GIT_WORD.search(l)): swap(m, g), l) for l in text.splitlines(True))
    if count:
        path.write_text(new, encoding="utf-8")
    return count


def git_records_commit(a) -> None:
    r = root()
    files = [f for f in a.files if f]
    if not files:
        raise SystemExit("no files given")
    run_git(r, "add", "--", *files)
    if commit_problems(r):
        # Records quote test values; a placeholder keeps the record and keeps any real value out of git.
        for n in filter(None, run_git(r, "diff", "--cached", "--name-only").splitlines()):
            f = r / n
            if n.startswith(".handoff/") and f.is_file():
                c = redact_fixtures(f)
                if c:
                    print(f"redacted {c} secret shape(s) in {n}")
                    run_git(r, "add", "--", n)
    probs = commit_problems(r)
    if probs:
        for x in probs:
            print(x)
        print("STOP: do not commit; tell the owner")
        sys.exit(5)
    name = run_git(r, "log", "-1", "--format=%an").strip()
    mail = run_git(r, "log", "-1", "--format=%ae").strip()
    msg = a.message + ("\n\n" + a.trailer if a.trailer else "")
    run_git(r, "-c", f"user.name={name}", "-c", f"user.email={mail}", "commit", "-q", "-m", msg)
    print("committed " + run_git(r, "rev-parse", "--short", "HEAD").strip() + " (local, not pushed)")


def word_hits(text: str, words_file) -> int:
    words = [w.strip().lower() for w in Path(words_file).read_text(encoding="utf-8").splitlines() if w.strip()] if words_file else []
    low = text.lower()
    return sum(low.count(w) for w in words)


def added_lines(diff: str) -> str:
    return "\n".join(l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))


def push_checked(repo: Path, sha: str, branch: str, words_file, dry_run: bool) -> str:
    """Push one exact commit to origin/<branch>: fast-forward only, blocked names and private words checked first."""
    if words_file and not Path(words_file).is_file():
        raise SystemExit(f"STOP: words file not found: {words_file}")
    sha = run_git(repo, "rev-parse", "--verify", sha + "^{commit}").strip()
    run_git(repo, "fetch", "-q", "origin", branch)
    base = f"origin/{branch}"
    if subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", base, sha]).returncode:
        raise SystemExit(f"STOP: not a fast-forward of {base}")
    names = run_git(repo, "diff", "--name-only", base, sha).splitlines()
    blocked = [n for n in names if BLOCKED_STAGED.search(n)]
    if blocked:
        raise SystemExit("STOP: blocked file(s) in the range: " + ", ".join(blocked[:5]))
    text = added_lines(run_git(repo, "diff", base, sha)) + "\n" + run_git(repo, "log", "--format=%B", f"{base}..{sha}")
    hits = word_hits(text, words_file)
    if hits:
        raise SystemExit(f"STOP: {hits} private-word hit(s); nothing pushed")
    n = run_git(repo, "rev-list", "--count", f"{base}..{sha}").strip()
    if dry_run:
        print(f"ready: {sha[:7]} ({n} commit(s)) fast-forward of {base}, 0 private-word hits (dry run, nothing pushed)")
        return sha
    run_git(repo, "push", "-q", "origin", f"{sha}:refs/heads/{branch}")
    remote = run_git(repo, "ls-remote", "origin", f"refs/heads/{branch}").split()[:1]
    if remote != [sha]:
        raise SystemExit(f"STOP: ls-remote {branch} does not show the pushed commit")
    print(f"pushed {sha[:7]} ({n} commit(s)) to {branch}; ls-remote {sha}")
    return sha


def plugin_update(project) -> None:
    for cmd in (["claude", "plugin", "marketplace", "update", "startup-team"],
                ["claude", "plugin", "update", "startup-team@startup-team"]):
        out = subprocess.run(cmd, cwd=project, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(("ok: " if out.returncode == 0 else "FAILED: ") + " ".join(cmd[1:]))


def git_push_team(a) -> None:
    """Push the team repo to main (only after the owner's push word), then update the project's plugin copy."""
    push_checked(Path(a.repo), a.sha, "main", a.words, a.dry_run)
    if a.project and not a.dry_run:
        plugin_update(a.project)


def git_push_project(a) -> None:
    """Push the project repo's branch (only after the owner's push word for this project)."""
    repo = Path(a.repo).resolve() if a.repo else root()
    branch = a.branch or run_git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    push_checked(repo, a.sha or "HEAD", branch, a.words, a.dry_run)


def bump_patch(repo: Path):
    found = sorted(repo.glob("plugins/*/.claude-plugin/plugin.json")) or sorted(repo.glob(".claude-plugin/plugin.json"))
    if len(found) != 1:
        raise SystemExit("STOP: --bump needs exactly one plugin.json")
    text = found[0].read_text(encoding="utf-8")
    m = re.search(r'"version":\s*"(\d+)\.(\d+)\.(\d+)"', text)
    if not m:
        raise SystemExit("STOP: no version in plugin.json")
    ver = f"{m.group(1)}.{m.group(2)}.{int(m.group(3)) + 1}"
    found[0].write_text(text[:m.start(1)] + ver + text[m.end(3):], encoding="utf-8")
    return found[0].relative_to(repo).as_posix(), ver


def git_commit_team(a) -> None:
    """One local commit in the team repo: given files only, optional patch bump, private words and secrets checked."""
    repo = Path(a.repo)
    files = [Path(os.path.normpath(f.replace("\\", "/"))).as_posix() for f in a.files if f]
    msg = a.message
    # Checked before anything is staged or bumped, so a STOP changes nothing.
    mine = lambda n: any(n == f or n.startswith(f + "/") for f in files) or (a.bump and n.endswith(".claude-plugin/plugin.json"))
    extra = [n for n in run_git(repo, "diff", "--cached", "--name-only").splitlines() if not mine(n)]
    if extra:
        raise SystemExit("STOP: other staged files, commit nothing: " + ", ".join(extra[:5]))
    if a.bump:
        pj, ver = bump_patch(repo)
        files.append(pj)
        msg = f"{msg} ({ver})"
    run_git(repo, "add", "--", *files)
    staged = run_git(repo, "diff", "--cached", "--name-only").splitlines()
    blocked = [n for n in staged if BLOCKED_STAGED.search(n)]
    added = added_lines(run_git(repo, "diff", "--cached"))
    hits = word_hits(added + "\n" + msg, a.words)
    shaped = any(SECRET.search(GIT_SHA.sub("gitsha", l) if GIT_WORD.search(l) else l) for l in added.splitlines())
    if blocked or hits or shaped:
        why = [x for x in (blocked and "blocked name", hits and f"{hits} private-word hit(s)", shaped and "secret shape") if x]
        run_git(repo, "reset", "-q", "--", *files, check=False)
        print("STOP: " + "; ".join(why) + "; nothing committed, files unstaged")
        sys.exit(5)
    name = run_git(repo, "log", "-1", "--format=%an").strip()
    mail = run_git(repo, "log", "-1", "--format=%ae").strip()
    full = msg + ("\n\n" + a.trailer if a.trailer else "")
    run_git(repo, "-c", f"user.name={name}", "-c", f"user.email={mail}", "commit", "-q", "-m", full)
    print("committed " + run_git(repo, "rev-parse", "--short", "HEAD").strip() + " (local, not pushed)")


def git_status_line(a) -> None:
    """One line: branch, ahead/behind origin, changed and untracked counts."""
    repo = Path(a.repo).resolve() if a.repo else root()
    if not a.no_fetch:
        run_git(repo, "fetch", "-q", "origin", check=False)
    br = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    ab = run_git(repo, "rev-list", "--left-right", "--count", f"HEAD...origin/{br}", check=False).split()
    st = run_git(repo, "status", "--porcelain").splitlines()
    unt = sum(l.startswith("??") for l in st)
    ahead, behind = (ab + ["?", "?"])[:2]
    head = run_git(repo, "rev-parse", "--short", "HEAD").strip()
    print(f"{repo.name}: {br}, ahead {ahead}, behind {behind} of origin; {len(st) - unt} changed, {unt} untracked; HEAD {head}")


def git_sync(a) -> None:
    """Bring the branch up to origin: fast-forward only; never merges, rebases, stashes or switches."""
    repo = Path(a.repo).resolve() if a.repo else root()
    br = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    run_git(repo, "fetch", "-q", "origin", br)
    out = subprocess.run(["git", "-C", str(repo), "merge", "--ff-only", "-q", f"origin/{br}"], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(f"STOP: {br} cannot fast-forward to origin/{br} (local commits or changes in the way); nothing changed")
    print(f"{repo.name}: {br} at {run_git(repo, 'rev-parse', '--short', 'HEAD').strip()} (fast-forward only)")


def chain_setup_change(a) -> None:
    """Memory entry, exclude fix and every selftest for one setup change, one line each."""
    r = root()
    a.kind, a.turn, a.tags = "setup-change", None, None
    setattr(a, "for", None)
    mem_add(a)
    ex = r / ".git" / "info" / "exclude"
    if ex.exists() and handoff_tracked(r):
        lines = ex.read_text(encoding="utf-8").splitlines()
        keep = [l for l in lines if l.strip() not in (".handoff", ".handoff/")]
        if keep != lines:
            ex.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
    plug = Path(__file__).resolve().parents[3]
    me = str(Path(__file__).resolve())
    tests = [[me, "records", "selftest"], [me, "git", "selftest"], [me, "loadout", "selftest"], [me, "conversations", "selftest"],
             [str(plug / "hooks" / "notes.py"), "selftest"], [str(plug / "hooks" / "clear-gate.py"), "selftest"],
             [str(Path(me).with_name("gateway.py")), "selftest"]]
    bad = 0
    for t in tests:
        if not Path(t[0]).exists():
            continue
        out = subprocess.run([sys.executable, *t], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
        bad += out.returncode != 0
        print(("ok " if out.returncode == 0 else "FAIL ") + Path(t[0]).name + " " + " ".join(t[1:]))
    if bad:
        sys.exit(6)


def git_selftest() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "x.md"
        sha = "a" * 40
        f.write_text("token = abc123abc123abc123abc123\ncommit " + sha + "\nplain\n", encoding="utf-8")
        assert redact_fixtures(f) == 1, "one fixture redacted"
        t = f.read_text(encoding="utf-8")
        assert FIXTURE in t and "abc123abc123" not in t and sha in t, "value gone, git sha kept"
        assert redact_fixtures(f) == 0, "second run changes nothing"
        f.write_text(sha + "\n", encoding="utf-8")
        assert redact_fixtures(f) == 1, "bare sha (no git word) redacted, as the check flags it"
        o, c = Path(tmp) / "o.git", Path(tmp) / "c"
        subprocess.run(["git", "init", "-q", "--bare", str(o)], check=True)
        subprocess.run(["git", "init", "-q", str(c)], check=True)
        g = ["git", "-C", str(c), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(g + ["checkout", "-q", "-b", "main"], check=True)
        subprocess.run(g + ["remote", "add", "origin", str(o)], check=True)
        (c / "plugins" / "p" / ".claude-plugin").mkdir(parents=True)
        (c / "plugins" / "p" / ".claude-plugin" / "plugin.json").write_text('{"version": "1.2.3"}', encoding="utf-8")
        subprocess.run(g + ["add", "."], check=True)
        subprocess.run(g + ["commit", "-qm", "init"], check=True)
        subprocess.run(g + ["push", "-q", "origin", "main"], capture_output=True, check=True)
        words = Path(tmp) / "w.txt"
        words.write_text("secretbrand\n", encoding="utf-8")
        (c / "a.txt").write_text("hello\n", encoding="utf-8")
        ns = argparse.Namespace
        git_commit_team(ns(repo=str(c), files=["./a.txt"], message="add a", bump=True, words=str(words), trailer=""))
        (c / "sub").mkdir()
        (c / "sub" / "s.txt").write_text("s\n", encoding="utf-8")
        git_commit_team(ns(repo=str(c), files=["sub\\s.txt"], message="add s", bump=False, words=str(words), trailer=""))
        assert "sub/s.txt" in run_git(c, "ls-files"), "backslash path committed"
        assert '"1.2.4"' in (c / "plugins/p/.claude-plugin/plugin.json").read_text(encoding="utf-8"), "bumped"
        (c / "b.txt").write_text("our secretbrand here\n", encoding="utf-8")
        try:
            git_commit_team(ns(repo=str(c), files=["b.txt"], message="b", bump=False, words=str(words), trailer=""))
            raise AssertionError("private word committed")
        except SystemExit as e:
            assert e.code == 5, "private word stops the commit"
        subprocess.run(g + ["reset", "-q", "--", "b.txt"], check=True)
        (c / "a.txt").write_text("hello again\n", encoding="utf-8")
        subprocess.run(g + ["add", "b.txt"], check=True)
        try:
            git_commit_team(ns(repo=str(c), files=["a.txt"], message="a2", bump=False, words=str(words), trailer=""))
            raise AssertionError("other staged file committed")
        except SystemExit as e:
            assert "other staged" in str(e), "other staged file is a STOP"
        assert run_git(c, "diff", "--cached", "--name-only").split() == ["b.txt"], "given file not staged by a STOP"
        subprocess.run(g + ["reset", "-q", "--", "b.txt"], check=True)
        subprocess.run(g + ["checkout", "-q", "--", "a.txt"], check=True)
        push_checked(c, "HEAD", "main", str(words), False)
        assert run_git(o, "rev-parse", "main").strip() == run_git(c, "rev-parse", "HEAD").strip(), "pushed"
        try:
            push_checked(c, "HEAD", "main", str(Path(tmp) / "none.txt"), True)
            raise AssertionError("missing words file passed")
        except SystemExit as e:
            assert "words file" in str(e), "missing words file is a STOP"


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

    rc = sub.add_parser("records").add_subparsers(dest="cmd", required=True)
    rc.add_parser("index").set_defaults(fn=rec_index)
    rf = rc.add_parser("find")
    rf.add_argument("words", nargs="+")
    rf.add_argument("--kind", choices=RECORD_KINDS + ("checkpoint", "other"))
    rf.add_argument("--last", type=int, help="only the N newest turn folders")
    rf.set_defaults(fn=rec_find)
    rc.add_parser("check-commit").set_defaults(fn=rec_check_commit)
    rc.add_parser("selftest").set_defaults(fn=rec_selftest)

    g = sub.add_parser("git").add_subparsers(dest="cmd", required=True)
    gr = g.add_parser("records-commit", help="stage, check (placeholders for quoted test values), commit locally")
    gr.add_argument("files", nargs="+")
    gr.add_argument("--message", "-m", required=True)
    gr.add_argument("--trailer", default="Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    gr.set_defaults(fn=git_records_commit)
    gp = g.add_parser("push-team", help="only after the owner's push word")
    gp.add_argument("sha")
    gp.add_argument("--repo", required=True)
    gp.add_argument("--words", required=True, help="the project's private-words file")
    gp.add_argument("--project", help="project folder whose local plugin copy is updated after the push")
    gp.add_argument("--dry-run", action="store_true")
    gp.set_defaults(fn=git_push_team)
    gc = g.add_parser("commit-team", help="one local commit in the team repo")
    gc.add_argument("files", nargs="+")
    gc.add_argument("--repo", required=True)
    gc.add_argument("--message", "-m", required=True)
    gc.add_argument("--words", required=True, help="the project's private-words file")
    gc.add_argument("--bump", action="store_true", help="raise the plugin's patch version and add it")
    gc.add_argument("--trailer", default="Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    gc.set_defaults(fn=git_commit_team)
    gq = g.add_parser("push-project", help="only after the owner's push word for this project")
    gq.add_argument("sha", nargs="?")
    gq.add_argument("--repo")
    gq.add_argument("--branch")
    gq.add_argument("--words")
    gq.add_argument("--dry-run", action="store_true")
    gq.set_defaults(fn=git_push_project)
    gs = g.add_parser("status", help="one line per repo")
    gs.add_argument("--repo")
    gs.add_argument("--no-fetch", action="store_true")
    gs.set_defaults(fn=git_status_line)
    gy = g.add_parser("sync", help="fast-forward the branch to origin, nothing else")
    gy.add_argument("--repo")
    gy.set_defaults(fn=git_sync)
    g.add_parser("selftest").set_defaults(fn=lambda _a: (git_selftest(), print("git selftest ok")))

    ch = sub.add_parser("chain").add_subparsers(dest="cmd", required=True)
    cs = ch.add_parser("setup-change", help="memory entry + exclude fix + every selftest")
    cs.add_argument("--text", required=True)
    cs.add_argument("--evidence", required=True)
    cs.add_argument("--source", default="optimization")
    cs.set_defaults(fn=chain_setup_change)

    cv = sub.add_parser("conversations").add_subparsers(dest="cmd", required=True)
    cv.add_parser("build").set_defaults(fn=conv_build)
    cv.add_parser("selftest").set_defaults(fn=conv_selftest)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
