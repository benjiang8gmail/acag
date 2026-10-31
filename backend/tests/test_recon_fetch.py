"""The Phase 0 recon fetcher must stay polite: obey robots.txt, never fetch when
robots.txt could not be checked, and stop at the first block or bot challenge."""
import importlib.util
import io
import urllib.error
from email.message import Message
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "recon_fetch.py"


@pytest.fixture
def rf(monkeypatch):
    spec = importlib.util.spec_from_file_location("recon_fetch", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "MIN_INTERVAL", 0)
    return mod


class _Resp(io.BytesIO):
    def __init__(self, body: bytes, url: str, ctype="text/html", status=200):
        super().__init__(body)
        self.status, self._url = status, url
        self.headers = Message()
        self.headers["Content-Type"] = ctype

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_error(url, code, body=b""):
    return urllib.error.HTTPError(url, code, "x", Message(), io.BytesIO(body))


def _site(routes):
    calls = []

    def opener(url, timeout=60):
        calls.append(url)
        r = routes.get(url)
        if isinstance(r, Exception):
            raise r
        if r is None:
            raise _http_error(url, 404)
        return _Resp(r, url)

    return opener, calls


def test_obeys_robots_disallow(rf, monkeypatch, tmp_path):
    opener, calls = _site({"https://h.example/robots.txt": b"User-agent: *\nDisallow: /hansard/\n"})
    monkeypatch.setattr(rf, "_open", opener)
    logs = []
    e = rf.fetch("https://h.example/hansard/day", tmp_path / "x.html", logs.append)
    assert e["result"] == "disallowed_by_robots"
    assert calls == ["https://h.example/robots.txt"]
    assert not (tmp_path / "x.html").exists()


def test_does_not_fetch_when_robots_unreachable(rf, monkeypatch, tmp_path):
    opener, calls = _site({"https://h.example/robots.txt": OSError("Tunnel connection failed: 403")})
    monkeypatch.setattr(rf, "_open", opener)
    e = rf.fetch("https://h.example/page", tmp_path / "x.html", lambda _: None)
    assert e["result"] == "skipped"
    assert calls == ["https://h.example/robots.txt"]


def test_saves_allowed_page_with_hash(rf, monkeypatch, tmp_path):
    opener, _ = _site({"https://h.example/robots.txt": b"", "https://h.example/day.xml": b"<hansard/>"})
    monkeypatch.setattr(rf, "_open", opener)
    e = rf.fetch("https://h.example/day.xml", tmp_path / "day.xml", lambda _: None)
    assert e["result"] == "ok"
    assert (tmp_path / "day.xml").read_bytes() == b"<hansard/>"
    assert len(e["sha256"]) == 64


def test_stops_at_first_block(rf, monkeypatch, tmp_path):
    opener, calls = _site({
        "https://h.example/robots.txt": b"",
        "https://h.example/a": _http_error("https://h.example/a", 403, b"Access denied"),
    })
    monkeypatch.setattr(rf, "_open", opener)
    assert rf.fetch("https://h.example/a", tmp_path / "a", lambda _: None)["result"] == "blocked"
    assert rf.fetch("https://h.example/b", tmp_path / "b", lambda _: None)["result"] == "skipped"
    assert "https://h.example/b" not in calls


def test_challenge_page_is_not_saved_as_fixture(rf, monkeypatch, tmp_path):
    opener, _ = _site({
        "https://h.example/robots.txt": b"",
        "https://h.example/a": b"<html>Please complete the captcha</html>",
    })
    monkeypatch.setattr(rf, "_open", opener)
    e = rf.fetch("https://h.example/a", tmp_path / "a.html", lambda _: None)
    assert e["result"] == "challenge_page"
    assert not (tmp_path / "a.html").exists()


def test_robots_served_as_challenge_blocks_the_host(rf, monkeypatch, tmp_path):
    challenge = b"<!DOCTYPE html><html><head><title>Client Challenge</title></head></html>"
    opener, calls = _site({"https://h.example/robots.txt": challenge, "https://h.example/a.pdf": challenge})
    monkeypatch.setattr(rf, "_open", opener)
    e = rf.fetch("https://h.example/a.pdf", tmp_path / "a.pdf", lambda _: None)
    assert e["result"] == "disallowed_by_robots"
    assert calls == ["https://h.example/robots.txt"]
    assert not (tmp_path / "a.pdf").exists()


def test_passive_cloudflare_script_on_a_normal_page_is_not_a_challenge(rf, monkeypatch, tmp_path):
    page = (b"<html><head><title>Index of /origxml</title></head><body><a href='senate_debates/'>senate_debates/</a>"
            b"<script>var u='/cdn-cgi/challenge-platform/scripts/precursor/main.js'</script></body></html>")
    opener, _ = _site({"https://h.example/robots.txt": b"", "https://h.example/origxml/": page})
    monkeypatch.setattr(rf, "_open", opener)
    assert rf.fetch("https://h.example/origxml/", tmp_path / "x.html", lambda _: None)["result"] == "ok"
