"""startup-team gateway: send a delegated piece to an OpenAI-compatible endpoint and keep a ledger.

  gateway.py health
  gateway.py launch --brief <file> --out <file> [--model <name>] [--timeout <s>]
  gateway.py list [--last n]
  gateway.py log <id>
  gateway.py selftest

Common options (or environment):
  --base-url <url>      TEAM_GATEWAY_URL      the endpoint, e.g. http://localhost:<port>
  --key-env <NAME>      TEAM_GATEWAY_KEY_ENV  the NAME of the variable that holds the key
  --allow-host <host>                         a non-local host the project's CLAUDE.md names
  --project <folder>                          default: the current folder

The key is read from that variable at call time and is never printed, logged or written.
Guards refuse before any network call (exit 2, error class "guard"): a non-local host that is not
allowed, a brief holding a word from .handoff/private-words.txt (the file must exist) or an email
address, an unset key variable, an existing --out file.
Ledger: <project>/.handoff/gateway/ledger.jsonl. Python 3.9+, standard library only.
"""
import argparse
import contextlib
import io
import json
import os
import re
import secrets
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class Refused(Exception):
    """A guard refused the call; nothing was sent."""


class Failed(Exception):
    def __init__(self, error_class: str, text: str):
        super().__init__(text)
        self.error_class = error_class


def ledger_path(project: Path) -> Path:
    folder = project / ".handoff" / "gateway"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "ledger.jsonl"


def append_ledger(project: Path, row: dict) -> None:
    with ledger_path(project).open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_ledger(project: Path) -> list:
    p = ledger_path(project)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def get_key(key_env: str) -> str:
    """The key, or Refused. The message names the variable, never its value."""
    if not key_env:
        raise Refused("no key variable named (--key-env or TEAM_GATEWAY_KEY_ENV)")
    key = os.environ.get(key_env, "")
    if not key.strip():
        raise Refused(f"the key variable {key_env} is unset or empty")
    return key


def check_host(base_url: str, allow_host: str) -> None:
    parsed = urllib.parse.urlparse(base_url or "")
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise Refused("no usable base URL (--base-url or TEAM_GATEWAY_URL)")
    host = parsed.hostname.lower()
    if host not in LOCAL_HOSTS and host != (allow_host or "").lower():
        raise Refused(f"host {host} is not local and not allowed with --allow-host")


def check_brief(project: Path, text: str) -> None:
    words_file = project / ".handoff" / "private-words.txt"
    if not words_file.exists():
        raise Refused(".handoff/private-words.txt must exist before anything is sent")
    low = text.lower()
    for n, line in enumerate(words_file.read_text(encoding="utf-8").splitlines(), 1):
        word = line.strip()
        if word and not word.startswith("#") and word.lower() in low:
            # Names the line number only, so the private word itself is not echoed.
            raise Refused(f"the brief holds private word line {n} of .handoff/private-words.txt")
    if EMAIL.search(text):
        raise Refused("the brief holds something shaped like an email address")


def scrub(text: str, key: str) -> str:
    return text.replace(key, "<key>") if key else text


def request(base_url: str, path: str, key: str, body=None, timeout: float = 60.0):
    url = base_url.rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        detail = scrub(e.read().decode("utf-8", "replace")[:300], key)
        if e.code in (401, 403):
            raise Failed("auth", f"HTTP {e.code}")
        if e.code == 429:
            raise Failed("rate-limit", f"HTTP 429 {detail}")
        if e.code >= 500:
            raise Failed("worker", f"HTTP {e.code} {detail}")
        if "model" in detail.lower():
            raise Failed("model", f"HTTP {e.code} {detail}")
        raise Failed("worker", f"HTTP {e.code} {detail}")
    except (urllib.error.URLError, OSError) as e:
        raise Failed("gateway-down", scrub(str(getattr(e, "reason", e)), key))
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
    row = {"id": task_id, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "model_asked": a.model,
           "model_answered": None, "status": "refused", "tokens": None, "brief": a.brief,
           "out": a.out, "error_class": None, "error": None}
    key = ""
    try:
        check_host(a.base_url, a.allow_host)
        key = get_key(a.key_env)
        brief_file = Path(a.brief)
        if not brief_file.is_file():
            raise Refused("the brief file does not exist")
        text = brief_file.read_text(encoding="utf-8")
        check_brief(project, text)
        if Path(a.out).exists():
            raise Refused("the --out file already exists; it is never overwritten")
        row["brief_bytes"] = len(text.encode("utf-8"))
    except Refused as e:
        row.update(error_class="guard", error=str(e))
        append_ledger(project, row)
        print(f"{task_id} refused: {e}")
        return 2
    try:
        data = request(a.base_url, "/v1/chat/completions", key,
                       {"model": a.model, "messages": [{"role": "user", "content": text}]}, a.timeout)
        try:
            answer = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise Failed("worker", "the answer had no message content")
        if not answer:
            raise Failed("worker", "the answer was empty")
        Path(a.out).write_text(answer, encoding="utf-8")
        usage = data.get("usage") or {}
        row.update(status="done", model_answered=data.get("model"), tokens=usage.get("total_tokens"),
                   out_bytes=len(answer.encode("utf-8")))
        append_ledger(project, row)
        print(task_id)
        return 0
    except Failed as e:
        row.update(status="failed", error_class=e.error_class, error=scrub(str(e), key))
        append_ledger(project, row)
        print(f"{task_id} failed: {e.error_class}")
        return 1


def cmd_list(a) -> int:
    for r in read_ledger(Path(a.project))[-a.last:]:
        print(f"{r.get('id')} {r.get('time')} {r.get('status')} {r.get('model_answered') or r.get('model_asked')} "
              f"tokens={r.get('tokens')} out={r.get('out')}")
    return 0


def cmd_log(a) -> int:
    for r in read_ledger(Path(a.project)):
        if r.get("id") == a.id:
            for k in ("id", "time", "status", "model_asked", "model_answered", "tokens", "brief",
                      "brief_bytes", "out", "out_bytes", "error_class", "error"):
                print(f"{k}: {r.get(k)}")
            return 0
    print(f"no task {a.id}")
    return 1


def selftest() -> int:
    """Assert-based, no network: guards, ledger round trip, the key never in output."""
    dummy = "dummy-SELFTEST-key-7f3a91"
    env_name = "TEAM_GATEWAY_SELFTEST_KEY"
    os.environ[env_name] = dummy
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        (project / ".handoff").mkdir()

        def refused(fn, *args) -> str:
            try:
                fn(*args)
            except Refused as e:
                return str(e)
            raise AssertionError(f"{fn.__name__} did not refuse")

        # (b) the private-words file must exist
        assert "must exist" in refused(check_brief, project, "a clean brief")
        (project / ".handoff" / "private-words.txt").write_text("# list\nAcmeWidget\n", encoding="utf-8")
        # (a) host
        assert "not local" in refused(check_host, "http://example.com:8080", "")
        check_host("http://localhost:8080", "")
        check_host("http://127.0.0.1:8080", "")
        check_host("http://[::1]:8080", "")
        check_host("https://gw.example.net", "gw.example.net")
        # (b) private word, case-insensitive, not echoed
        msg = refused(check_brief, project, "Summarise the acmewidget docs")
        assert "line 2" in msg and "acmewidget" not in msg.lower()
        # (c) email
        assert "email" in refused(check_brief, project, "write to someone@example.org about it")
        check_brief(project, "Summarise this public README in five lines.")
        # (d) key
        assert "unset or empty" in refused(get_key, "TEAM_GATEWAY_SELFTEST_UNSET")
        assert get_key(env_name) == dummy
        # ledger round trip
        append_ledger(project, {"id": "t1", "status": "done"})
        append_ledger(project, {"id": "t2", "status": "failed"})
        assert [r["id"] for r in read_ledger(project)] == ["t1", "t2"]
        # the key never appears in any output, the ledger included
        buf = io.StringIO()
        brief = project / "brief.txt"
        brief.write_text("hello acmewidget", encoding="utf-8")
        common = ["--project", str(project), "--key-env", env_name]
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            main(["health", "--base-url", "http://example.com"] + common)
            main(["launch", "--base-url", "http://127.0.0.1:9", "--brief", str(brief),
                  "--out", str(project / "o.txt")] + common)
            main(["list"] + common)
        out = buf.getvalue() + ledger_path(project).read_text(encoding="utf-8")
        assert dummy not in out, "the key leaked into output"
        assert "refused" in out
    del os.environ[env_name]
    print("selftest ok")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="startup-team gateway to an OpenAI-compatible endpoint")
    p.add_argument("--base-url", default=os.environ.get("TEAM_GATEWAY_URL", ""))
    p.add_argument("--key-env", default=os.environ.get("TEAM_GATEWAY_KEY_ENV", ""))
    p.add_argument("--allow-host", default="")
    p.add_argument("--project", default=os.getcwd())
    p.add_argument("--timeout", type=float, default=120.0)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    la = sub.add_parser("launch")
    la.add_argument("--brief", required=True)
    la.add_argument("--out", required=True)
    la.add_argument("--model", default="auto")
    la.add_argument("--timeout", type=float, dest="timeout_launch")
    li = sub.add_parser("list")
    li.add_argument("--last", type=int, default=20)
    lo = sub.add_parser("log")
    lo.add_argument("id")
    sub.add_parser("selftest")
    # Common options may also come after the command.
    for sp in (la, li, lo, sub.choices["health"]):
        sp.add_argument("--base-url", dest="base_url_late")
        sp.add_argument("--key-env", dest="key_env_late")
        sp.add_argument("--allow-host", dest="allow_host_late")
        sp.add_argument("--project", dest="project_late")
    a = p.parse_args(argv)
    for name in ("base_url", "key_env", "allow_host", "project"):
        late = getattr(a, name + "_late", None)
        if late:
            setattr(a, name, late)
    if getattr(a, "timeout_launch", None):
        a.timeout = a.timeout_launch
    if a.cmd == "selftest":
        return selftest()
    return {"health": cmd_health, "launch": cmd_launch, "list": cmd_list, "log": cmd_log}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
