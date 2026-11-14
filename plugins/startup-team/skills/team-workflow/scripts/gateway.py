"""startup-team gateway: send a delegated piece to an OpenAI-compatible endpoint and keep a ledger.

  gateway.py health
  gateway.py launch --brief <file> --out <file> [--model <name>] [--max-brief-kb n]
  gateway.py list [--last n]
  gateway.py log <id>
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
.handoff/private-words.txt that is missing or lists no word, or a brief holding one of its words
or an email address; a brief that is empty, not UTF-8 or over the size limit; an --out that exists
or whose folder does not.
Ledger: <project>/.handoff/gateway/ledger.jsonl. Python 3.9+, standard library only.
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
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
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
    words_file = project / ".handoff" / "private-words.txt"
    if not words_file.exists():
        raise Refused(".handoff/private-words.txt must exist before anything is sent")
    try:
        lines = words_file.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError:
        raise Refused(".handoff/private-words.txt is not UTF-8")
    words = [(n, w.strip()) for n, w in enumerate(lines, 1) if w.strip() and not w.strip().startswith("#")]
    if not words:
        raise Refused(".handoff/private-words.txt lists no word; an empty list guards nothing")
    low = text.lower()
    for n, word in words:
        if word.lower() in low:
            # Names the line number only, so the private word itself is not echoed.
            raise Refused(f"the brief holds private word line {n} of .handoff/private-words.txt")
    if EMAIL.search(text):
        raise Refused("the brief holds something shaped like an email address")


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
    row = {"id": task_id, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "model_asked": a.model,
           "model_answered": None, "status": "refused", "tokens": None, "brief": a.brief,
           "out": a.out, "error_class": None, "error": None}
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
        check_brief(project, text, a.max_brief_kb)
        out = Path(a.out)
        if out.exists():
            raise Refused("the --out file already exists; it is never overwritten")
        if not out.parent.resolve().is_dir():
            raise Refused("the --out file's folder does not exist")
        row["brief_bytes"] = len(text.encode("utf-8"))
    except Refused as e:
        row.update(error_class="guard", error=scrub(str(e)))
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
        if not isinstance(answer, str) or not answer:
            raise Failed("worker", "the answer content was empty or not text")
        answer = scrub(answer)
        try:
            out.write_text(answer, encoding="utf-8")
        except OSError as e:
            raise Failed("worker", f"could not write --out ({type(e).__name__})")
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        model = data.get("model")
        row.update(status="done", model_answered=model if isinstance(model, str) else None,
                   tokens=usage.get("total_tokens"), out_bytes=len(answer.encode("utf-8")))
        append_ledger(project, row)
        print(task_id)
        return 0
    except Failed as e:
        row.update(status="failed", error_class=e.error_class, error=scrub(str(e)))
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
    li = sub.add_parser("list")
    li.add_argument("--last", type=int, default=20)
    lo = sub.add_parser("log")
    lo.add_argument("id")
    sub.add_parser("selftest")
    # The common options may also come after the command.
    for sp in (he, la, li, lo):
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
    return {"health": cmd_health, "launch": cmd_launch, "list": cmd_list, "log": cmd_log}[a.cmd](a)


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
            if n:
                self.rfile.read(n)
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
        assert "line 1" in refused(check_brief, project, "about acmewidget")
        msg = refused(check_brief, project, "Summarise the ACMEWIDGET docs")
        assert "acmewidget" not in msg.lower()
        # email, empty brief, size limit (N4)
        assert "email" in refused(check_brief, project, "write to someone@example.org")
        assert "empty" in refused(check_brief, project, "  \n ")
        assert "over 1 KB" in refused(check_brief, project, "x" * 2000, 1)
        check_brief(project, "Summarise this public README in five lines.")
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
