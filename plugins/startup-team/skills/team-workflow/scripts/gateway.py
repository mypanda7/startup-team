"""startup-team gateway: send a delegated piece to an OpenAI-compatible endpoint and keep a ledger.

  gateway.py health
  gateway.py launch --brief <file> --out <file> [--job <type>] [--terms <file>] [--model <name>] [--max-brief-kb n]
  gateway.py review <id> pass|fail [--note <text>]   (sends nothing; appends a review row)
  gateway.py scores [--job <type>] [--last n]        (sends nothing; per job and model)
  gateway.py pick --job <type>                       (sends nothing; prints one model name)
  gateway.py list [--last n]
  gateway.py log <id>
  gateway.py mask --brief <file> --out <file> [--terms <file>]      (sends nothing)
  gateway.py unmask --map <task id | file> --in <file> --out <file>  (sends nothing)
  gateway.py selftest

Common options (or environment), accepted before or after the command:
  --base-url <url>      TEAM_GATEWAY_URL      the endpoint, e.g. http://localhost:<port>
  --key-env <NAME>      TEAM_GATEWAY_KEY_ENV  the NAME of the variable that holds the key
  --allow-host <host>                         a non-local host the project's CLAUDE.md names
  --project <folder>                          default: the current folder
  --timeout <seconds>                         default 120

The key is read from that variable at call time and is never printed, logged or written; it is
scrubbed from error text and from the answer. Redirects are never followed and no proxy is used.
Guards refuse before any network call (exit 2, error class "guard"): a non-local host that is not
allowed; a key variable that is unset, empty or holds whitespace or control characters; a
.handoff/private-words.txt that is missing or lists no word; a brief that still holds a private
word, an email address or secret-shaped text after masking, or holds a placeholder bracket; a brief that is empty, not UTF-8 or over the size limit; an --out that exists
or whose folder does not.
Masking, always on for launch: every private word (.handoff/private-words.txt), email-shaped and
secret-shaped string and every --terms line is replaced by an opaque placeholder like ⟦a7f3-1⟧
(a random tag per task and a number; the type is kept only in the map) before the guards run and
before anything is sent. The map stays in .handoff/gateway/maps/<task id>.json and is never sent
or printed; the answer gets the real values back (only exact bracketed placeholders) before --out
is written. A map not used for --keep-maps-days days (default 7) is deleted at the next launch.
The --model value is checked like the brief (private words, emails, secret shapes); it is never
masked.
Ledger: <project>/.handoff/gateway/ledger.jsonl. Python 3.9+, standard library only. Launch rows
carry a `job` type; review rows ({"kind": "review", id, verdict, note, time}) are only ever appended.
pick: among models with >= 3 reviewed launches for the job, the highest pass rate, ties -> the lower
median tokens of passed answers. About 1 pick in 5 (from that job's own launch count, so it is
deterministic) explores a model with < 3 reviews for that job instead. No data: "auto".
scores --last n: the reviewed, pass and median columns cover only each job+model's last n reviewed
launches (ledger order); launches stay all-time.
"""
import argparse
import contextlib
import http.client
import io
import json
import os
import re
import secrets
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
EMAIL = re.compile(r"[\w.%+-]+@[\w-]+(?:\.[\w-]+)*\.[^\W\d_]{2,}")  # Unicode letters in both parts
PH_OPEN, PH_CLOSE = "\u27e6", "\u27e7"  # ⟦ ⟧: rare in normal text, so a placeholder can't collide
PH_TYPES = ("SECRET", "EMAIL", "PRIVATE", "TERM")  # overlap priority, highest first
# Opaque placeholders: ⟦<4 hex tag>-<n>⟧. They hold no word a list could hold, and the guards skip them.
PH_ANY = re.compile("\u27e6\\s*([0-9a-fA-F]{4})-(\\d+)\\s*\u27e7")
# A safety net, not a scanner: shapes of common secrets. It misses split, encoded or unusual ones.
SECRET_SHAPES = (
    ("a private-key header", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("a secret, password, token or key assignment",
     re.compile(r"(?i)\b[\w-]*(?:secret|password|passwd|token|key)[\w-]*\s*[=:]\s*\S+")),
    ("a bearer token", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{6,}")),
    ("a URL with a user and password", re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@\S*")),
    ("a known key prefix", re.compile(r"(?<![A-Za-z0-9])(sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9]{8,}|"
                                      r"gho_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,}|xox[bp]-[A-Za-z0-9-]{8,}|"
                                      r"AIza[0-9A-Za-z_-]{20,}|AKIA[0-9A-Z]{12,})")),
)
MIN_REVIEWS = 3   # reviewed launches a model needs for a job before pick trusts its score
EXPLORE_EVERY = 5  # one pick in this many explores an under-reviewed model
LONG_TOKEN = re.compile(r"[A-Za-z0-9+/_=-]{40,}")
_SEEN_KEYS = set()  # every key value read this run, so any output can be scrubbed of it


class Refused(Exception):
    """A guard refused the call; nothing was sent."""


class Failed(Exception):
    def __init__(self, error_class: str, text: str):
        super().__init__(text)
        self.error_class = error_class


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # urllib then raises HTTPError with the 3xx code, and nothing is re-sent


# No proxy handler from the environment and no redirect following: the key goes to one host only.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)


def scrub(text: str) -> str:
    for k in sorted(_SEEN_KEYS, key=len, reverse=True):
        if k:
            text = text.replace(k, "<key>")
    return text


def ledger_path(project: Path) -> Path:
    folder = project / ".handoff" / "gateway"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "ledger.jsonl"


def append_ledger(project: Path, row: dict) -> None:
    with ledger_path(project).open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_ledger(project: Path) -> list:
    """Every valid JSON-object line; a line that is not UTF-8 or not an object is skipped."""
    p = ledger_path(project)
    if not p.exists():
        return []
    rows = []
    for raw in p.read_bytes().splitlines():
        try:
            row = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def job_type(text) -> str:
    return " ".join(str(text or "").lower().split()) or "general"


def score_table(rows: list, last: int = 0) -> dict:
    """{(job, model): {"launches", "reviewed", "passed", "tokens": [tokens of passed answers]}}.

    Counts answered launches by the model that actually answered; the latest review of an id wins.
    last > 0: reviewed/passed/tokens cover only the last `last` reviewed launches of each key."""
    verdicts = {r.get("id"): r.get("verdict") for r in rows if r.get("kind") == "review"}
    table, seen = {}, {}
    for r in rows:
        if r.get("kind") == "review" or r.get("status") != "done":
            continue
        key = (job_type(r.get("job")), r.get("model_answered") or r.get("model_asked") or "auto")
        table.setdefault(key, {"launches": 0, "reviewed": 0, "passed": 0, "tokens": []})["launches"] += 1
        v = verdicts.get(r.get("id"))
        if v in ("pass", "fail"):
            seen.setdefault(key, []).append((v, r.get("tokens")))
    for key, reviews in seen.items():
        s = table[key]
        for v, tokens in reviews[-last:] if last > 0 else reviews:
            s["reviewed"] += 1
            if v == "pass":
                s["passed"] += 1
                if isinstance(tokens, (int, float)):
                    s["tokens"].append(tokens)
    return table


def median(values: list):
    v = sorted(values)
    if not v:
        return None
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2


def pick_model(rows: list, job: str) -> str:
    job = job_type(job)
    table = score_table(rows)
    last = {}
    for r in rows:
        if r.get("kind") != "review" and r.get("model_asked"):
            last[r["model_asked"]] = r
    down = {m for m, r in last.items() if r.get("status") == "failed" and r.get("error_class") == "model"}
    table = {k: v for k, v in table.items() if k[1] not in down}
    trusted = [(m, s) for (j, m), s in table.items() if j == job and s["reviewed"] >= MIN_REVIEWS]
    best = min(trusted, key=lambda ms: (-ms[1]["passed"] / ms[1]["reviewed"],
                                        median(ms[1]["tokens"]) if ms[1]["tokens"] else float("inf"),
                                        ms[0]), default=(None,))[0]
    launches = sum(1 for r in rows if r.get("kind") != "review" and "status" in r and job_type(r.get("job")) == job)
    if launches % EXPLORE_EVERY == EXPLORE_EVERY - 1:
        reviewed = {m: s["reviewed"] for (j, m), s in table.items() if j == job}
        fresh = sorted(m for m in {m for (_, m) in table} - {"auto"} if reviewed.get(m, 0) < MIN_REVIEWS)
        if fresh:
            return fresh[(launches // EXPLORE_EVERY) % len(fresh)]
        return "auto"
    return best or "auto"


def get_key(key_env: str) -> str:
    """The key, or Refused. The message names the variable, never its value."""
    if not key_env:
        raise Refused("no key variable named (--key-env or TEAM_GATEWAY_KEY_ENV)")
    raw = os.environ.get(key_env, "")
    key = raw.strip()
    _SEEN_KEYS.update({raw, key} - {""})
    if not key:
        raise Refused(f"the key variable {key_env} is unset or empty")
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in key):
        raise Refused(f"the key variable {key_env} holds whitespace or control characters")
    return key


def check_host(base_url: str, allow_host: str) -> None:
    parsed = urllib.parse.urlparse(base_url or "")
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise Refused("no usable base URL (--base-url or TEAM_GATEWAY_URL)")
    host = parsed.hostname.lower()
    if host not in LOCAL_HOSTS and host != (allow_host or "").lower():
        raise Refused(f"host {host} is not local and not allowed with --allow-host")


def check_brief(project: Path, text: str, max_kb: float = 200) -> None:
    if not text.strip():
        raise Refused("the brief is empty")
    if len(text.encode("utf-8")) > max_kb * 1024:
        raise Refused(f"the brief is over {max_kb:g} KB (raise it with --max-brief-kb)")
    check_text(project, text, "the brief")


def check_text(project: Path, text: str, what: str) -> None:
    """Refuse a private word, an email or a secret shape in text; placeholders are skipped."""
    text = PH_ANY.sub(" ", text)
    for kind, shape in SECRET_SHAPES:
        if shape.search(text):
            raise Refused(f"{what} holds something shaped like a secret ({kind})")
    for m in LONG_TOKEN.finditer(text):
        tok = m.group(0)
        if any(c.isdigit() for c in tok) and any(c.isalpha() for c in tok):
            raise Refused(f"{what} holds something shaped like a secret (a long token-like string)")
    low = text.lower()
    for n, word in private_words(project):
        if word.lower() in low:
            # Names the line number only, so the private word itself is not echoed.
            raise Refused(f"{what} holds private word line {n} of .handoff/private-words.txt")
    if EMAIL.search(text):
        raise Refused(f"{what} holds something shaped like an email address")


def read_list(f: Path, label: str, min_len: int = 1) -> list:
    """[(line, entry)] of a utf-8-sig list file, skipping blanks and # comments."""
    try:
        lines = f.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError:
        raise Refused(f"{label} is not UTF-8")
    return [(n, w.strip()) for n, w in enumerate(lines, 1)
            if len(w.strip()) >= min_len and not w.strip().startswith("#")]


def private_words(project: Path) -> list:
    f = project / ".handoff" / "private-words.txt"
    if not f.exists():
        raise Refused(".handoff/private-words.txt must exist before anything is sent")
    words = read_list(f, ".handoff/private-words.txt")
    if not words:
        raise Refused(".handoff/private-words.txt lists no word; an empty list guards nothing")
    return words


def _flex(term: str) -> str:
    """A term as a pattern that also matches across spaces and line breaks."""
    return r"\s+".join(re.escape(t) for t in term.split())


def mask(project: Path, text: str, terms=(), tag: str = ""):
    """(masked text, {"<tag>-<n>": value}, {"<tag>-<n>": type}, {type: count}, tag).

    Overlapping hits merge into one; one placeholder per distinct value."""
    tag = (tag or secrets.token_hex(2)).lower()
    if PH_OPEN in text or PH_CLOSE in text:
        raise Refused("the brief holds a placeholder bracket; remove it before sending")
    spans = []
    for _, shape in SECRET_SHAPES:
        spans += [(m.start(), m.end(), "SECRET") for m in shape.finditer(text)]
    for m in LONG_TOKEN.finditer(text):
        if any(c.isdigit() for c in m.group(0)) and any(c.isalpha() for c in m.group(0)):
            spans.append((m.start(), m.end(), "SECRET"))
    spans += [(m.start(), m.end(), "EMAIL") for m in EMAIL.finditer(text)]
    for kind, entries in (("PRIVATE", [w for _, w in private_words(project)]), ("TERM", list(terms))):
        for entry in entries:
            spans += [(m.start(), m.end(), kind) for m in re.finditer(_flex(entry), text, re.I) if m.end() > m.start()]
    merged = []
    for start, end, kind in sorted(spans):
        if merged and start < merged[-1][1]:
            last = merged[-1]
            top = min(last[2], kind, key=PH_TYPES.index)
            merged[-1] = (last[0], max(last[1], end), top)
        else:
            merged.append((start, end, kind))
    mapping, types, by_value, counts, parts, pos = {}, {}, {}, {k: 0 for k in PH_TYPES}, [], 0
    for start, end, kind in merged:
        value = text[start:end]
        if value not in by_value:
            counts[kind] += 1
            name = f"{tag}-{len(mapping) + 1}"
            by_value[value] = name
            mapping[name] = value
            types[name] = kind
        parts += [text[pos:start], PH_OPEN + by_value[value] + PH_CLOSE]
        pos = end
    parts.append(text[pos:])
    return "".join(parts), mapping, types, {k: v for k, v in counts.items() if v}, tag


def unmask(answer: str, mapping: dict, tag: str):
    """(answer with real values back, [what could not be restored]).

    Only exact bracketed placeholders are restored. A bare look-alike (the tag without brackets),
    an unknown placeholder or a lone bracket is left as it is and reported."""
    unrestored = []

    def put_back(m):
        name = f"{m.group(1).lower()}-{m.group(2)}"
        if name in mapping:
            return PH_OPEN + "\x00" + str(list(mapping).index(name)) + PH_CLOSE  # restored below
        unrestored.append(m.group(0))
        return m.group(0)
    staged = PH_ANY.sub(put_back, answer)
    rest = staged
    for u in unrestored:
        rest = rest.replace(u, " ")
    rest = re.sub("\u27e6\x00\\d+\u27e7", " ", rest)
    leftover = re.compile("[\u27e6\u27e7]|(?<![0-9A-Za-z])" + re.escape(tag) + "-\\d+(?!\\d)", re.I)
    unrestored += [m.group(0) for m in leftover.finditer(rest)]
    names = list(mapping)
    out = re.sub("\u27e6\x00(\\d+)\u27e7", lambda m: mapping[names[int(m.group(1))]], staged)
    return out, unrestored


def read_terms(path: str) -> list:
    if not path:
        return []
    f = Path(path)
    if not f.is_file():
        raise Refused("the --terms file does not exist")
    return [w for _, w in read_list(f, "the --terms file", min_len=2)]


def maps_dir(project: Path) -> Path:
    d = project / ".handoff" / "gateway" / "maps"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_map(project: Path, map_id: str, tag: str, mapping: dict, types: dict) -> None:
    (maps_dir(project) / f"{map_id}.json").write_text(
        json.dumps({"tag": tag, "placeholders": mapping, "types": types}, ensure_ascii=False), encoding="utf-8")


def touch_map(path: Path) -> None:
    """A map's last-used time is its file's modification time."""
    try:
        os.utime(path, None)
    except OSError:
        pass


def expire_maps(project: Path, keep_days: float) -> int:
    """Delete maps not used for keep_days days; returns how many. Their contents are never read."""
    cutoff = time.time() - keep_days * 86400
    deleted = 0
    for f in maps_dir(project).glob("*.json"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1
        except OSError:
            pass
    return deleted


def request(base_url: str, path: str, key: str, body=None, timeout: float = 120.0):
    url = base_url.rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if 300 <= e.code < 400:
            raise Failed("gateway-down", f"redirect HTTP {e.code} refused; nothing was re-sent")
        try:
            detail = scrub(e.read().decode("utf-8", "replace")[:300])
        except (OSError, http.client.HTTPException):
            detail = ""
        if e.code in (401, 403):
            raise Failed("auth", f"HTTP {e.code}")
        if e.code == 429:
            raise Failed("rate-limit", f"HTTP 429 {detail}")
        if e.code < 500 and "model" in detail.lower():
            raise Failed("model", f"HTTP {e.code} {detail}")
        raise Failed("worker", f"HTTP {e.code} {detail}")
    except http.client.HTTPException as e:
        raise Failed("worker", f"broken reply ({type(e).__name__})")
    except (urllib.error.URLError, OSError) as e:
        raise Failed("gateway-down", scrub(str(getattr(e, "reason", e))))
    try:
        return json.loads(raw)
    except ValueError:
        raise Failed("worker", "the answer was not JSON")


def cmd_health(a) -> int:
    try:
        check_host(a.base_url, a.allow_host)
        key = get_key(a.key_env)
    except Refused as e:
        print(f"refused: {e}")
        return 2
    try:
        data = request(a.base_url, "/v1/models", key, timeout=a.timeout)
    except Failed as e:
        print("auth" if e.error_class == "auth" else f"down {e}")
        return 1
    models = data.get("data") if isinstance(data, dict) else None
    print(f"ok {len(models) if isinstance(models, list) else 0}")
    return 0


def cmd_launch(a) -> int:
    project = Path(a.project)
    task_id = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
    row = {"id": task_id, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "model_asked": None,
           "model_answered": None, "status": "refused", "tokens": None, "brief": a.brief,
           "out": a.out, "error_class": None, "error": None, "job": job_type(a.job)}
    try:
        check_host(a.base_url, a.allow_host)
        key = get_key(a.key_env)
        brief_file = Path(a.brief)
        if not brief_file.is_file():
            raise Refused("the brief file does not exist")
        try:
            text = brief_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise Refused("the brief file is not UTF-8")
        if not text.strip():
            raise Refused("the brief is empty")
        check_text(project, a.model, "the --model value")
        row["model_asked"] = a.model  # recorded only once it is known to hold nothing identifying
        row["maps_deleted"] = expire_maps(project, a.keep_maps_days)
        masked, mapping, types, counts, tag = mask(project, text, read_terms(a.terms))
        row["masked"] = counts
        check_brief(project, masked, a.max_brief_kb)
        out = Path(a.out)
        if out.exists():
            raise Refused("the --out file already exists; it is never overwritten")
        if not out.parent.resolve().is_dir():
            raise Refused("the --out file's folder does not exist")
        row["brief_bytes"] = len(text.encode("utf-8"))
        write_map(project, task_id, tag, mapping, types)
    except Refused as e:
        row.update(error_class="guard", error=scrub(str(e)))
        append_ledger(project, row)
        print(f"{task_id} refused: {e}")
        return 2
    try:
        data = request(a.base_url, "/v1/chat/completions", key,
                       {"model": a.model, "messages": [{"role": "user", "content": masked}]}, a.timeout)
        try:
            answer = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise Failed("worker", "the answer had no message content")
        if not isinstance(answer, str) or not answer:
            raise Failed("worker", "the answer content was empty or not text")
        answer, unrestored = unmask(answer, mapping, tag)
        answer = scrub(answer)
        row["unrestored"] = unrestored
        try:
            out.write_text(answer, encoding="utf-8")
        except OSError as e:
            raise Failed("worker", f"could not write --out ({type(e).__name__})")
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        model = data.get("model")
        row.update(status="done", model_answered=model if isinstance(model, str) else None,
                   tokens=usage.get("total_tokens"), out_bytes=len(answer.encode("utf-8")))
        append_ledger(project, row)
        print(task_id + (f" ({len(unrestored)} placeholder(s) not restored; see log)" if unrestored else ""))
        return 0
    except Failed as e:
        row.update(status="failed", error_class=e.error_class, error=scrub(str(e)))
        append_ledger(project, row)
        print(f"{task_id} failed: {e.error_class}")
        return 1


def project_gateway(project: Path):
    """(base url, key variable name) from the project's CLAUDE.md gateway section, or ("", "")."""
    try:
        text = (project / "CLAUDE.md").read_text(encoding="utf-8")
    except OSError:
        return "", ""
    url = re.search(r"Base URL:\s*(https?://[^\s`(]+)", text)
    key = re.search(r"Key variable:\s*`?([A-Z][A-Z0-9_]+)`?", text)
    return (url.group(1).rstrip(".,") if url else ""), (key.group(1) if key else "")


def cmd_ask(a) -> int:
    """One call: write the brief, pick the model from the scores, launch, retry once on `auto`, print the answer."""
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to a code page
    project = Path(a.project)
    url, key_env = project_gateway(project)
    a.base_url = a.base_url or url
    a.key_env = a.key_env or key_env
    folder = project / ".handoff" / "gateway"
    folder.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", a.name or job_type(a.job)).strip("-")[:40] or "ask"
    stem = f"{stem}-{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}"
    if a.text:
        brief = folder / f"{stem}.brief.txt"
        brief.write_text(a.text, encoding="utf-8")
    elif a.brief:
        brief = Path(a.brief)
    else:
        print("refused: give --text or --brief")
        return 2
    terms = Path(a.terms) if a.terms else folder / f"{stem}.terms.txt"
    if not a.terms:
        terms.write_text("", encoding="utf-8")
    model = a.model or pick_model(read_ledger(project), a.job)
    tries = [model] + (["auto"] if model != "auto" else [])
    for n, m in enumerate(tries):
        out = folder / f"{stem}{'' if n == 0 else '-' + str(n + 1)}.out.txt"
        la = argparse.Namespace(**vars(a))
        la.brief, la.out, la.model, la.terms = str(brief), str(out), m, str(terms)
        rc = cmd_launch(la)
        if rc == 0:
            print("--- answer (" + str(out.relative_to(project)).replace("\\", "/") + ") ---")
            print(out.read_text(encoding="utf-8"))
            print("--- review it: gateway.py review <id> pass|fail --note ...")
            return 0
        if rc == 2:
            return rc
    print("failed twice: do the part here and record `GATEWAY: none: failed twice`")
    return 1


def cmd_list(a) -> int:
    for r in [r for r in read_ledger(Path(a.project)) if r.get("kind") != "review"][-a.last:]:
        print(f"{r.get('id')} {r.get('time')} {r.get('status')} {r.get('model_answered') or r.get('model_asked')} "
              f"tokens={r.get('tokens')} out={r.get('out')}")
    return 0


def cmd_log(a) -> int:
    for r in read_ledger(Path(a.project)):
        if r.get("id") == a.id and r.get("kind") != "review":
            for k in ("id", "time", "status", "job", "model_asked", "model_answered", "tokens", "brief",
                      "brief_bytes", "masked", "maps_deleted", "out", "out_bytes", "error_class", "error"):
                print(f"{k}: {r.get(k)}")
            print(f"unrestored: {len(r.get('unrestored') or [])}")
            return 0
    print(f"no task {a.id}")
    return 1


def cmd_review(a) -> int:
    """Append a review row for an answered launch. Old rows are never edited."""
    project = Path(a.project)
    note = " ".join((a.note or "").split())
    if len(note) > 200:
        print("refused: the note is over 200 characters")
        return 2
    if not any(r.get("id") == a.id and r.get("kind") != "review" and r.get("status") == "done"
               for r in read_ledger(project)):
        print(f"refused: no answered launch {a.id}")
        return 2
    append_ledger(project, {"kind": "review", "id": a.id, "verdict": a.verdict, "note": note,
                            "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"{a.id} {a.verdict}")
    return 0


def cmd_scores(a) -> int:
    rows = sorted(score_table(read_ledger(Path(a.project)), a.last).items())
    if a.job:
        rows = [r for r in rows if r[0][0] == job_type(a.job)]
    print(f"{'job':<14} {'model':<32} {'launches':>8} {'reviewed':>8} {'pass':>5} {'med.tok':>8}")
    for (job, model), s in rows:
        rate = f"{100 * s['passed'] / s['reviewed']:.0f}%" if s["reviewed"] else "-"
        med = median(s["tokens"])
        med_text = "-" if med is None else f"{med:g}"
        print(f"{job:<14} {model:<32} {s['launches']:>8} {s['reviewed']:>8} {rate:>5} {med_text:>8}")
    return 0


def cmd_pick(a) -> int:
    print(pick_model(read_ledger(Path(a.project)), a.job))
    return 0


def cmd_mask(a) -> int:
    """Mask a brief locally, write the masked text and its map, and run the guards. Sends nothing."""
    project = Path(a.project)
    task_id = "mask-" + time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
    try:
        brief, out = Path(a.brief), Path(a.out)
        if not brief.is_file():
            raise Refused("the brief file does not exist")
        if out.exists():
            raise Refused("the --out file already exists; it is never overwritten")
        try:
            text = brief.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise Refused("the brief file is not UTF-8")
        masked, mapping, types, counts, tag = mask(project, text, read_terms(a.terms))
        check_brief(project, masked, a.max_brief_kb)
    except Refused as e:
        print(f"refused: {e}")
        return 2
    out.write_text(masked, encoding="utf-8")
    write_map(project, task_id, tag, mapping, types)
    print(f"{task_id} masked {counts or 'nothing'}; guards ok")
    return 0


def cmd_unmask(a) -> int:
    """Put the real values back into a file from a map. Sends nothing."""
    project = Path(a.project)
    m = Path(a.map)
    if not m.is_file():
        m = maps_dir(project) / f"{a.map}.json"
    out = Path(a.out)
    if not m.is_file() or not Path(a.in_file).is_file():
        print("refused: no such map or --in file")
        return 2
    if out.exists():
        print("refused: the --out file already exists; it is never overwritten")
        return 2
    data = json.loads(m.read_text(encoding="utf-8"))
    touch_map(m)
    text, unrestored = unmask(Path(a.in_file).read_text(encoding="utf-8"), data.get("placeholders", {}),
                              str(data.get("tag", "")))
    out.write_text(text, encoding="utf-8")
    print(f"restored; {len(unrestored)} placeholder(s) not restored")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="startup-team gateway to an OpenAI-compatible endpoint")
    p.add_argument("--base-url", default=os.environ.get("TEAM_GATEWAY_URL", ""))
    p.add_argument("--key-env", default=os.environ.get("TEAM_GATEWAY_KEY_ENV", ""))
    p.add_argument("--allow-host", default="")
    p.add_argument("--project", default=os.getcwd())
    p.add_argument("--timeout", type=float, default=120.0)
    sub = p.add_subparsers(dest="cmd", required=True)
    he = sub.add_parser("health")
    la = sub.add_parser("launch")
    la.add_argument("--brief", required=True)
    la.add_argument("--out", required=True)
    la.add_argument("--model", default="auto")
    la.add_argument("--max-brief-kb", type=float, default=200)
    la.add_argument("--terms", default="")
    la.add_argument("--keep-maps-days", type=float, default=7)
    la.add_argument("--job", default="general")
    ak = sub.add_parser("ask", help="one call: brief, pick, launch, retry on auto, print the answer")
    ak.add_argument("--job", required=True)
    ak.add_argument("--text", default="")
    ak.add_argument("--brief", default="")
    ak.add_argument("--terms", default="")
    ak.add_argument("--name", default="")
    ak.add_argument("--model", default="")
    ak.add_argument("--max-brief-kb", type=float, default=200)
    ak.add_argument("--keep-maps-days", type=float, default=7)
    rv = sub.add_parser("review")
    rv.add_argument("id")
    rv.add_argument("verdict", choices=("pass", "fail"))
    rv.add_argument("--note", default="")
    sc = sub.add_parser("scores")
    sc.add_argument("--job", default="")
    sc.add_argument("--last", type=int, default=0)
    pk = sub.add_parser("pick")
    pk.add_argument("--job", required=True)
    ma = sub.add_parser("mask")
    ma.add_argument("--brief", required=True)
    ma.add_argument("--out", required=True)
    ma.add_argument("--terms", default="")
    ma.add_argument("--max-brief-kb", type=float, default=200)
    um = sub.add_parser("unmask")
    um.add_argument("--map", required=True)
    um.add_argument("--in", dest="in_file", required=True)
    um.add_argument("--out", required=True)
    li = sub.add_parser("list")
    li.add_argument("--last", type=int, default=20)
    lo = sub.add_parser("log")
    lo.add_argument("id")
    sub.add_parser("selftest")
    # The common options may also come after the command.
    for sp in (he, la, ak, li, lo, ma, um, rv, sc, pk):
        sp.add_argument("--base-url", dest="base_url_late")
        sp.add_argument("--key-env", dest="key_env_late")
        sp.add_argument("--allow-host", dest="allow_host_late")
        sp.add_argument("--project", dest="project_late")
        sp.add_argument("--timeout", type=float, dest="timeout_late")
    a = p.parse_args(argv)
    for name in ("base_url", "key_env", "allow_host", "project", "timeout"):
        late = getattr(a, name + "_late", None)
        if late:
            setattr(a, name, late)
    if a.cmd == "selftest":
        return selftest()
    return {"health": cmd_health, "launch": cmd_launch, "list": cmd_list, "log": cmd_log,
            "mask": cmd_mask, "unmask": cmd_unmask, "review": cmd_review, "scores": cmd_scores,
            "pick": cmd_pick, "ask": cmd_ask}[a.cmd](a)


def run(argv=None) -> int:
    """main() behind a catch-all: one scrubbed line, never a traceback."""
    try:
        return main(argv)
    except SystemExit:
        raise
    except Exception as e:  # last line of defence: the key must never reach a traceback
        print("error: " + scrub(f"{type(e).__name__}: {e}"))
        return 1


# ---------------------------------------------------------------- selftest (127.0.0.1 stubs only)
def _stub(behaviour: dict):
    """A loopback HTTP server; behaviour["kind"] picks the reply. Returns (server, port, counter)."""
    from http.server import BaseHTTPRequestHandler, HTTPServer
    counter = [0]

    class H(BaseHTTPRequestHandler):
        def _go(self):
            counter[0] += 1
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if n else b""
            behaviour.setdefault("bodies", []).append(body)
            kind = behaviour["kind"]
            if kind == "redirect":
                self.send_response(behaviour["code"])
                self.send_header("Location", behaviour["location"])
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if kind == "truncated":
                self.send_response(200)
                self.send_header("Content-Length", "1000")
                self.end_headers()
                self.wfile.write(b'{"choices": [')
                return
            bodies = {
                "ok": {"data": [{"id": "a"}], "model": "m", "usage": {"total_tokens": 3},
                       "choices": [{"message": {"content": "fine"}}]},
                "list_content": {"choices": [{"message": {"content": ["a", "b"]}}]},
                "no_choices": {"choices": []},
                "echo_key": {"choices": [{"message": {"content": "got " + self.headers.get("Authorization", "")}}]},
            }
            if kind == "echo_brief":
                sent = json.loads(body.decode("utf-8"))["messages"][0]["content"]
                bodies[kind] = {"choices": [{"message": {"content": sent}}]}
            if kind == "fixed":
                bodies[kind] = {"choices": [{"message": {"content": behaviour["answer"]}}]}
            raw = b"not json at all" if kind == "bad_json" else json.dumps(bodies[kind]).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        do_GET = _go
        do_POST = _go

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1], counter


def selftest() -> int:
    """Assert-based. Network only to 127.0.0.1 stubs it starts and stops itself."""
    dummy = "dummy-SELFTEST-key-7f3a91"
    env = "TEAM_GATEWAY_SELFTEST_KEY"
    os.environ[env] = dummy
    servers = []
    buf = io.StringIO()
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        (project / ".handoff").mkdir()
        words = project / ".handoff" / "private-words.txt"

        def refused(fn, *args) -> str:
            try:
                fn(*args)
            except Refused as e:
                return str(e)
            raise AssertionError(f"{fn.__name__} did not refuse")

        def gw(*args) -> int:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                return run(list(args) + ["--project", str(project), "--key-env", env])

        # private-words file: missing, empty, comments only (U1), BOM (B3)
        assert "must exist" in refused(check_brief, project, "a clean brief")
        words.write_text("", encoding="utf-8")
        assert "lists no word" in refused(check_brief, project, "a clean brief")
        words.write_text("# only a comment\n\n   \n", encoding="utf-8")
        assert "lists no word" in refused(check_brief, project, "a clean brief")
        words.write_text("AcmeWidget\n# list\n", encoding="utf-8-sig")
        assert "line 1 of .handoff/private-words.txt" in refused(check_brief, project, "about acmewidget")
        msg = refused(check_brief, project, "Summarise the ACMEWIDGET docs")
        assert "acmewidget" not in msg.lower()
        # email, empty brief, size limit (N4)
        assert "email" in refused(check_brief, project, "write to someone@example.org")
        assert "empty" in refused(check_brief, project, "  \n ")
        assert "over 1 KB" in refused(check_brief, project, "x" * 2000, 1)
        check_brief(project, "Summarise this public README in five lines.")
        # secret shapes
        for shaped in ("-----BEGIN RSA PRIVATE KEY-----", "password = hunter22", "API_KEY: abc123",
                       "token=xyz", "secret: s3", "passwd=pw", "use sk-abcdefghijk1", "ghp_abcdefgh1234",
                       "gho_abcdefgh1234", "AKIAABCDEFGHIJKL", "x " + "a1B2" * 11):
            assert "shaped like a secret" in refused(check_brief, project, shaped), shaped
        check_brief(project, "Count the tokens in this passage and keep the secret of good copy short.")
        check_brief(project, "See https://example.com/docs/getting-started/install-guide for steps.")
        # host
        assert "not local" in refused(check_host, "http://example.com:8080", "")
        for ok in ("http://localhost:8080", "http://127.0.0.1:8080", "http://[::1]:8080"):
            check_host(ok, "")
        check_host("https://gw.example.net", "gw.example.net")
        # key (B2): unset, newline, inner space
        assert "unset or empty" in refused(get_key, "TEAM_GATEWAY_SELFTEST_UNSET")
        assert get_key(env) == dummy
        os.environ[env] = dummy + "\n"
        assert get_key(env) == dummy  # stripped, so the header is valid
        os.environ[env] = "dum my"
        assert "whitespace or control" in refused(get_key, env)
        os.environ[env] = "dum\x07my"
        assert "whitespace or control" in refused(get_key, env)
        os.environ[env] = dummy

        brief = project / "brief.txt"
        brief.write_text("Summarise this public README.", encoding="utf-8")
        target_behaviour = {"kind": "ok"}
        target, tport, tcount = _stub(target_behaviour)
        front_behaviour = {"kind": "ok"}
        front, fport, fcount = _stub(front_behaviour)
        servers += [target, front]
        base = f"http://127.0.0.1:{fport}"

        # B1: a redirect to another host name is never followed, for every 3xx
        for code in (301, 302, 303, 307, 308):
            front_behaviour.update(kind="redirect", code=code, location=f"http://localhost:{tport}/v1/models")
            assert gw("health", "--base-url", base) == 1
            assert gw("launch", "--base-url", base, "--brief", str(brief), "--out", str(project / f"r{code}.txt")) == 1
        assert tcount[0] == 0, "a redirect reached the second host"

        # B4: refused before sending, then odd replies fail cleanly with a ledger line
        before = fcount[0]
        front_behaviour.update(kind="ok")
        bad = project / "latin1.txt"
        bad.write_bytes("caf\xe9".encode("latin-1"))
        assert gw("launch", "--base-url", base, "--brief", str(bad), "--out", str(project / "b1.txt")) == 2
        assert gw("launch", "--base-url", base, "--brief", str(brief), "--out", str(project / "nope" / "b2.txt")) == 2
        (project / "exists.txt").write_text("keep", encoding="utf-8")
        assert gw("launch", "--base-url", base, "--brief", str(brief), "--out", str(project / "exists.txt")) == 2
        assert fcount[0] == before, "a refused launch reached the stub"
        for i, kind in enumerate(("list_content", "truncated", "bad_json", "no_choices")):
            front_behaviour.update(kind=kind)
            assert gw("launch", "--base-url", base, "--brief", str(brief), "--out", str(project / f"odd{i}.txt")) == 1
            assert read_ledger(project)[-1]["error_class"] == "worker", kind
        # N5: the key echoed into the answer is scrubbed before --out is written
        front_behaviour.update(kind="echo_key")
        assert gw("launch", "--base-url", base, "--brief", str(brief), "--out", str(project / "echo.txt")) == 0
        assert "<key>" in (project / "echo.txt").read_text(encoding="utf-8")
        # masking: values never leave, come back byte-exact, overlaps merge, line breaks, repeats
        words.write_text("AcmeWidget\nAcme\nProject Nimbus\nHostCo\n", encoding="utf-8")
        terms = project / "terms.txt"
        terms.write_text("Jane Roe\nAcmeWidget Pro\n", encoding="utf-8")
        values = ["AcmeWidget Pro", "acmewidget", "Acme", "project\nNIMBUS", "preHostCoTech", "jane@example.org",
                  "password = hunter22", "Jane  Roe", "ghp_abcdefgh1234"]
        secret_brief = ("Plan for AcmeWidget Pro, made by acmewidget and Acme; see project\nNIMBUS and "
                        "preHostCoTech. Mail jane@example.org, password = hunter22, owner Jane  Roe, "
                        "token ghp_abcdefgh1234. Again: Acme and jane@example.org.\n")
        sb = project / "secret_brief.txt"
        sb.write_text(secret_brief, encoding="utf-8")
        masked, mapping, types, counts, tag = mask(project, secret_brief, read_terms(str(terms)))
        low = masked.lower()
        for v in values:
            assert v.lower() not in low, v
        assert "acme" not in low and "hostco" not in low and "nimbus" not in low
        assert list(mapping.values()).count("Acme") == 1  # the same value twice -> one placeholder
        assert list(mapping.values()).count("jane@example.org") == 1
        assert all(PH_ANY.fullmatch(PH_OPEN + n + PH_CLOSE) for n in mapping)  # opaque: tag-number only
        assert "private" not in low and "email" not in low and "secret_" not in low  # B2: no type words sent
        assert unmask(masked, mapping, tag) == (secret_brief, [])  # byte-exact round trip
        front_behaviour.update(kind="echo_brief", bodies=[])
        assert gw("launch", "--base-url", base, "--brief", str(sb), "--out", str(project / "m1.txt"),
                  "--terms", str(terms)) == 0
        assert (project / "m1.txt").read_text(encoding="utf-8") == secret_brief
        sent = b"".join(front_behaviour["bodies"]).decode("utf-8")
        sent_text = json.loads(sent)["messages"][0]["content"]
        for v in list(mapping.values()) + ["AcmeWidget", "Acme", "HostCo", "Nimbus", "hunter22", "jane@"]:
            assert v.lower() not in sent.lower() and v.lower() not in sent_text.lower(), v
        # a brief that is all private data sends only placeholders
        allp = project / "all_private.txt"
        allp.write_text("AcmeWidget HostCo jane@example.org", encoding="utf-8")
        front_behaviour.update(kind="echo_brief", bodies=[])
        assert gw("launch", "--base-url", base, "--brief", str(allp), "--out", str(project / "m2.txt")) == 0
        only = json.loads(front_behaviour["bodies"][0].decode("utf-8"))["messages"][0]["content"]
        assert PH_ANY.sub("", only).strip() == "", only
        # N6: a bare look-alike (brackets dropped) is left as it is and reported, never guessed
        name = next(iter(mapping))
        assert unmask(f"see {name} now", mapping, tag) == (f"see {name} now", [name])
        assert unmask("const TERM_1 = 5", mapping, tag) == ("const TERM_1 = 5", [])
        # an unknown placeholder or a lone bracket in the answer is reported, not crashed
        front_behaviour.update(kind="fixed", answer="Result for \u27e6ffff-99\u27e7 and \u27e6 half")
        assert gw("launch", "--base-url", base, "--brief", str(sb), "--out", str(project / "m3.txt")) == 0
        assert len(read_ledger(project)[-1]["unrestored"]) == 2, read_ledger(project)[-1]["unrestored"]
        # B2: list words that look like type names mask and send normally
        words.write_text("private\nemail\nterm\nmail\n", encoding="utf-8")
        tw = project / "typewords.txt"
        tw.write_text("Our private beta: email the term sheet by mail.", encoding="utf-8")
        front_behaviour.update(kind="echo_brief", bodies=[])
        assert gw("launch", "--base-url", base, "--brief", str(tw), "--out", str(project / "m6.txt")) == 0
        assert (project / "m6.txt").read_text(encoding="utf-8") == tw.read_text(encoding="utf-8")
        body = json.loads(front_behaviour["bodies"][0].decode("utf-8"))["messages"][0]["content"].lower()
        assert not any(w in body for w in ("private", "email", "term", "mail")), body
        assert read_ledger(project)[-1]["unrestored"] == []
        words.write_text("AcmeWidget\nAcme\nProject Nimbus\nHostCo\n", encoding="utf-8")
        # B3: Unicode emails are masked whole
        for addr in ("j\u00e9r\u00f4me@example.org", "jane@b\u00fccher.de", "\u00e5sa.str\u00f6m@f\u00f6retag.se"):
            m_text, m_map, *_ = mask(project, f"Contact {addr} please.")
            assert addr in m_map.values() and addr.split("@")[0][:3] not in m_text, (addr, m_text)
        # N4: more secret shapes are masked (and refused if they were ever sent unmasked)
        for shaped in ("SECRET_KEY=abc123", "apikey=zz99", "api-key: zz99", "my_token: t0k3n",
                       "Authorization: Bearer abc123def456", "postgres://admin:hunter2@db.local/app",
                       "xoxb-12345678-abcdef", "xoxp-12345678-abcdef", "AIza" + "B" * 30,
                       "github_pat_ABCDEFGH1234"):
            m_text, m_map, *_ = mask(project, "Config: " + shaped + " end")
            assert not any(part in m_text for part in (shaped,)), shaped
            assert "shaped like a secret" in refused(check_text, project, shaped, "x"), shaped
        # B1: the --model value is checked, never masked; a hit refuses with 0 requests
        before = fcount[0]
        for model in ("AcmeWidget-model", "jane@example.org", "sk-abcdefghijk1"):
            assert gw("launch", "--base-url", base, "--brief", str(brief), "--out", str(project / "mm.txt"),
                      "--model", model) == 2, model
            assert read_ledger(project)[-1]["model_asked"] is None
        assert fcount[0] == before
        # guards after masking: a placeholder bracket or an oversize masked brief refuses, 0 requests
        br = project / "bracket.txt"
        br.write_text("a \u27e6 b", encoding="utf-8")
        assert gw("launch", "--base-url", base, "--brief", str(br), "--out", str(project / "m4.txt")) == 2
        assert gw("launch", "--base-url", base, "--brief", str(sb), "--out", str(project / "m5.txt"),
                  "--max-brief-kb", "0.05") == 2
        assert fcount[0] == before
        # mask / unmask commands send nothing and round-trip
        assert gw("mask", "--brief", str(sb), "--out", str(project / "masked.txt")) == 0
        map_id = sorted(maps_dir(project).glob("mask-*.json"))[-1]
        assert gw("unmask", "--map", str(map_id), "--in", str(project / "masked.txt"),
                  "--out", str(project / "unmasked.txt")) == 0
        assert (project / "unmasked.txt").read_text(encoding="utf-8") == secret_brief
        assert fcount[0] == before
        # retention: a map unused for 8 days is deleted at the next launch, one used 1 day ago is kept,
        # and unmask refreshes a map's last-used time
        old_map, new_map = maps_dir(project) / "old.json", maps_dir(project) / "new.json"
        for f, days in ((old_map, 8), (new_map, 1)):
            f.write_text("{}", encoding="utf-8")
            os.utime(f, (time.time() - days * 86400,) * 2)
        os.utime(map_id, (time.time() - 30 * 86400,) * 2)
        assert gw("unmask", "--map", str(map_id), "--in", str(project / "masked.txt"),
                  "--out", str(project / "unmasked2.txt")) == 0
        front_behaviour.update(kind="ok")
        assert gw("launch", "--base-url", base, "--brief", str(brief), "--out", str(project / "m7.txt")) == 0
        assert not old_map.exists() and new_map.exists() and map_id.exists()
        assert read_ledger(project)[-1]["maps_deleted"] == 1
        os.utime(new_map, (time.time() - 3 * 86400,) * 2)
        assert gw("launch", "--base-url", base, "--brief", str(brief), "--out", str(project / "m8.txt"),
                  "--keep-maps-days", "2") == 0
        assert not new_map.exists()
        assert "acme" not in buf.getvalue().lower(), "a private value reached the printed output"
        words.write_text("AcmeWidget\n# list\n", encoding="utf-8")

        # N6: --timeout after every command
        front_behaviour.update(kind="ok")
        assert gw("health", "--base-url", base, "--timeout", "5") == 0
        assert gw("list", "--timeout", "5") == 0

        # B2: the catch-all prints one scrubbed line, never a traceback
        global request
        real_request = request

        def boom(*args, **kwargs):
            raise ValueError("Invalid header value b'Bearer " + dummy + "'")
        request = boom
        try:
            assert gw("health", "--base-url", base) == 1
        finally:
            request = real_request

        # B5: corrupt ledger lines are skipped by list and log
        with ledger_path(project).open("ab") as f:
            f.write(b'123\n[1, 2]\n"text"\nnull\n\xff\xfe broken\n{"id": "t-ok", "status": "done"}\n')
        assert gw("list") == 0
        assert gw("log", "t-ok") == 0
        assert gw("log", "no-such-id") == 1

        # review: appends, never edits, refuses an unknown or unanswered id and a long note
        ok_id = next(r["id"] for r in read_ledger(project) if r.get("status") == "done")
        bad_id = next(r["id"] for r in read_ledger(project) if r.get("status") == "refused")
        before_rows = ledger_path(project).read_bytes()
        assert gw("review", ok_id, "pass", "--note", "fine") == 0
        assert ledger_path(project).read_bytes().startswith(before_rows)
        last = read_ledger(project)[-1]
        assert (last["kind"], last["id"], last["verdict"], last["note"]) == ("review", ok_id, "pass", "fine")
        n = len(read_ledger(project))
        assert gw("review", "no-such-id", "pass") == 2
        assert gw("review", bad_id, "fail") == 2
        assert gw("review", ok_id, "fail", "--note", "x" * 201) == 2
        assert len(read_ledger(project)) == n
        assert gw("list") == 0 and gw("log", ok_id) == 0  # review rows don't break list / log
        front_behaviour.update(kind="ok")
        assert gw("launch", "--base-url", base, "--brief", str(brief), "--out", str(project / "j1.txt"),
                  "--job", " Code-Draft ") == 0
        assert read_ledger(project)[-1]["job"] == "code-draft"
        assert gw("scores") == 0 and gw("scores", "--job", "code-draft") == 0 and gw("pick", "--job", "x") == 0

        # scores and pick on hand-made ledgers (no network)
        def L(i, job, model, tokens=1, status="done"):
            return {"id": f"t{i}", "status": status, "job": job, "model_answered": model, "tokens": tokens}

        def R(i, v="pass"):
            return {"kind": "review", "id": f"t{i}", "verdict": v}
        rows = [L(1, "copy", "a", 100), L(2, "copy", "a", 300), L(3, "copy", "a", 200), L(4, "copy", "a", 50),
                R(1), R(2), R(3, "fail"), R(3), R(4, "fail"),
                L(5, "copy", "b", 10), L(6, "copy", "b", 20), L(7, "copy", "b", 30), L(8, None, "c", 5),
                R(5), R(6, "fail"), R(7), L(9, "copy", "a", 9, "failed"), L(10, "copy", "a", 9, "refused"),
                L(11, "copy", "a", 9, "failed")]
        t = score_table(rows)
        assert t[("copy", "a")] == {"launches": 4, "reviewed": 4, "passed": 3, "tokens": [100, 300, 200]}
        assert median(t[("copy", "a")]["tokens"]) == 200 and median([1, 2, 3, 4]) == 2.5
        assert t[("copy", "b")]["reviewed"] == 3 and t[("general", "c")]["launches"] == 1
        # --last 2: only a's last two reviewed launches (t3 pass, t4 fail); launches stay all-time
        assert score_table(rows, 2)[("copy", "a")] == {"launches": 4, "reviewed": 2, "passed": 1, "tokens": [200]}
        assert score_table(rows, 10) == t and gw("scores", "--last", "10") == 0
        # best: 10 copy launch rows (10 % 5 == 0, no exploration); a 75% beats b 67%; job case/space ignored
        assert pick_model(rows, " COPY ") == "a"
        assert pick_model(rows, "never-seen") == "auto"  # no data for the job
        assert pick_model([], "plan") == "auto"
        # exploration: 14 copy launch rows (14 % 5 == 4) -> c, the one model with < 3 reviews for copy
        more = rows + [L(20 + i, "copy", "a", 1, "failed") for i in range(4)]
        assert pick_model(more, "copy") == "c"
        # tie at 3/3 passes each -> the lower median tokens of passed answers wins (6 launches)
        tie = [L(i, "plan", m, tok) for i, (m, tok) in enumerate(
            [("x", 100), ("x", 100), ("x", 100), ("y", 50), ("y", 60), ("y", 70)])] + [R(i) for i in range(6)]
        assert pick_model(tie, "plan") == "y"
        # exploration counts the job's own launches: 9 launches in all, only 6 for plan -> no exploring
        assert pick_model(tie + [L(30 + i, "q", "x") for i in range(3)], "plan") == "y"
        nine = tie + [L(40 + i, "plan", "x", 1, "failed") for i in range(3)]  # 9 plan launches
        # exploring with every seen model already at 3 reviews -> "auto"
        assert pick_model(nine, "plan") == "auto"
        # exploring with an under-reviewed model seen under another job -> that model
        assert pick_model(nine + [L(50, "q", "z")], "plan") == "z"

        for s in servers:
            s.shutdown()
            s.server_close()
        out = buf.getvalue() + ledger_path(project).read_bytes().decode("utf-8", "replace")
        for f in project.glob("*.txt"):
            out += f.read_text(encoding="utf-8", errors="replace")
        assert dummy not in out, "the key leaked into output, the ledger or a file"
        assert "Traceback" not in out
    del os.environ[env]
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(run())
