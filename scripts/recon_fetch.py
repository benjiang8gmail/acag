"""Polite fetcher for Phase 0 source recon (spec §5, §12).

Rules it enforces, so recon can be re-run safely:
- reads and obeys each host's robots.txt before any other request;
- waits at least FETCH_MIN_INTERVAL_SECONDS between requests to the same host;
- sends the project User-Agent and nothing that imitates a browser;
- never retries a 401/403/429 or a bot-challenge page, and stops fetching
  from that host for the rest of the run (blocked means blocked);
- logs every request (url, status, headers of interest, sha256) to a JSONL file.

Usage:
    python scripts/recon_fetch.py URL OUT_PATH [--log LOG] [--max-bytes N]
    python scripts/recon_fetch.py --batch FILE.tsv [--log LOG]   # lines: URL<TAB>OUT_PATH
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

USER_AGENT = os.environ.get(
    "FETCH_USER_AGENT",
    "ACAG-HansardWatch/0.1 (Phase 0 source recon; +https://github.com/benjiang8gmail/acag)",
)
UA_TOKEN = "ACAG-HansardWatch"
MIN_INTERVAL = float(os.environ.get("FETCH_MIN_INTERVAL_SECONDS", "3"))
CHALLENGE_MARKERS = (
    "captcha", "cf-chl", "challenge-platform", "azwaf", "azure waf", "are you a robot",
    "client challenge", "just a moment...", "page blocked by waf",
    "access denied", "request unsuccessful. incapsula", "_incapsula_", "akamai",
    "bot detection", "please enable javascript and cookies",
)

_last: dict[str, float] = {}
_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
_blocked_hosts: dict[str, str] = {}


def _wait(host: str) -> None:
    gap = time.monotonic() - _last.get(host, 0)
    if gap < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - gap)
    _last[host] = time.monotonic()


def _open(url: str, timeout: int = 60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    return urllib.request.urlopen(req, timeout=timeout)


def robots_for(scheme: str, host: str, log) -> urllib.robotparser.RobotFileParser | None:
    if host in _robots:
        return _robots[host]
    url = f"{scheme}://{host}/robots.txt"
    _wait(host)
    rp = urllib.robotparser.RobotFileParser(url)
    entry = {"ts": _now(), "url": url, "kind": "robots"}
    try:
        with _open(url, 30) as r:
            body = r.read().decode("utf-8", "replace")
            entry.update(status=r.status, bytes=len(body))
            if any(m in body.lower() for m in CHALLENGE_MARKERS):
                rp.disallow_all = True
                _blocked_hosts[host] = "robots.txt answered with a bot challenge page"
                entry["result"] = "challenge_page"
            else:
                rp.parse(body.splitlines())
            entry["robots_excerpt"] = body[:4000]
    except urllib.error.HTTPError as e:
        entry["status"] = e.code
        if e.code in (401, 403):
            rp.disallow_all = True   # stdlib convention: robots refused -> treat as disallow
            snippet = e.read(4000).decode("utf-8", "replace").lower()
            _blocked_hosts[host] = f"robots.txt refused (HTTP {e.code})" + (
                ", bot challenge page" if any(m in snippet for m in CHALLENGE_MARKERS) else "")
            entry["result"] = "blocked"
            entry["server"] = e.headers.get("Server")
            entry["body_excerpt"] = snippet[:300]
        else:
            rp.allow_all = True      # 404 etc -> no robots rules
    except Exception as e:  # network/proxy failure: we could not check, so do not fetch
        entry["error"] = repr(e)
        rp = None
    log(entry)
    _robots[host] = rp
    return rp


def fetch(url: str, out: Path, log, max_bytes: int = 60_000_000) -> dict:
    parts = urlsplit(url)
    host = parts.netloc
    entry: dict = {"ts": _now(), "url": url, "out": str(out)}
    if host in _blocked_hosts:
        entry.update(result="skipped", reason=f"host blocked earlier: {_blocked_hosts[host]}")
        log(entry)
        return entry
    rp = robots_for(parts.scheme, host, log)
    if rp is None:
        entry.update(result="skipped", reason="robots.txt could not be checked")
        log(entry)
        return entry
    if not rp.can_fetch(UA_TOKEN, url):
        entry.update(result="disallowed_by_robots")
        log(entry)
        return entry
    delay = rp.crawl_delay(UA_TOKEN)
    if delay:
        entry["crawl_delay"] = delay
        global MIN_INTERVAL
        MIN_INTERVAL = max(MIN_INTERVAL, float(delay))
    _wait(host)
    try:
        with _open(url) as r:
            body = r.read(max_bytes + 1)
            entry.update(
                status=r.status,
                final_url=r.geturl(),
                content_type=r.headers.get("Content-Type"),
                etag=r.headers.get("ETag"),
                last_modified=r.headers.get("Last-Modified"),
                server=r.headers.get("Server"),
                bytes=len(body),
                truncated=len(body) > max_bytes,
            )
    except urllib.error.HTTPError as e:
        snippet = e.read(4000).decode("utf-8", "replace")
        entry.update(status=e.code, result="http_error", server=e.headers.get("Server"),
                     body_excerpt=snippet[:800])
        if e.code in (401, 403, 429) or any(m in snippet.lower() for m in CHALLENGE_MARKERS):
            _blocked_hosts[host] = f"HTTP {e.code}"
            entry["result"] = "blocked"
        log(entry)
        return entry
    except Exception as e:
        entry.update(result="error", error=repr(e))
        log(entry)
        return entry
    head = body[:20000].decode("utf-8", "replace").lower()
    if "html" in (entry.get("content_type") or "") and any(m in head for m in CHALLENGE_MARKERS) and len(body) < 30000:
        entry["result"] = "challenge_page"
        _blocked_hosts[host] = "bot challenge page"
        out = out.with_suffix(out.suffix + ".challenge.txt")
    else:
        entry["result"] = "ok"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body[:max_bytes])
    entry["sha256"] = hashlib.sha256(body[:max_bytes]).hexdigest()
    log(entry)
    return entry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--batch")
    ap.add_argument("--log", default="recon-log.jsonl")
    ap.add_argument("--max-bytes", type=int, default=60_000_000)
    a = ap.parse_args()

    def log(e: dict) -> None:
        with open(a.log, "a") as f:
            f.write(json.dumps(e) + "\n")
        short = {k: e.get(k) for k in ("url", "status", "result", "content_type", "bytes", "error", "reason") if e.get(k) is not None}
        print(json.dumps(short), flush=True)

    jobs = []
    if a.batch:
        for line in Path(a.batch).read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                u, o = line.split("\t")
                jobs.append((u.strip(), Path(o.strip())))
    else:
        jobs.append((a.url, Path(a.out)))
    for u, o in jobs:
        fetch(u, o, log, a.max_bytes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
