"""Polite HTTP fetching for every connector and register (spec §8.3, §14).

- obeys robots.txt (a host whose robots.txt can't be read is not fetched);
- waits FETCH_MIN_INTERVAL_SECONDS between requests to the same host;
- sends If-None-Match / If-Modified-Since when we know them;
- hashes every body: same SHA-256 as last time means `unchanged`;
- treats 401/403/429 and bot-challenge pages as `blocked` and never retries
  them or tries to get around them.
"""

from __future__ import annotations

import hashlib
import re
import time
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

ROBOTS_TOKEN = "ACAG-HansardWatch"
CHALLENGE_TITLES = ("just a moment", "attention required", "client challenge", "azure waf", "waf block page",
                    "access denied", "are you a robot", "security check")
# Strong markers for a short page with no title. A passive Cloudflare script on a normal page
# ("/cdn-cgi/challenge-platform/…") is not a challenge, so that path is not a marker.
CHALLENGE_MARKERS = ("captcha", "are you a robot", "please enable javascript and cookies", "cf-chl-", "_incapsula_")


def is_challenge(text: str) -> bool:
    low = text[:30_000].lower()
    title = re.search(r"<title[^>]*>(.*?)</title>", low, re.S)
    if title and any(t in title.group(1) for t in CHALLENGE_TITLES):
        return True
    return len(text) < 30_000 and any(m in low for m in CHALLENGE_MARKERS)


class Blocked(Exception):
    """The site refused us (status, challenge page or robots.txt). Stop fetching from it this run."""


@dataclass
class FetchResult:
    status: str                      # "changed" / "unchanged"
    body: bytes | None = None        # None when unchanged
    sha256: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    downloaded: bool = False         # True when a body came over the wire (not a 304)


class Fetcher:
    def __init__(self, user_agent: str, min_interval: float = 2.0,
                 transport: httpx.BaseTransport | None = None, sleep=time.sleep, clock=time.monotonic):
        self._client = httpx.Client(headers={"User-Agent": user_agent}, transport=transport,
                                    follow_redirects=True, timeout=60)
        self._min_interval = min_interval
        self._sleep, self._clock = sleep, clock
        self._last: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._blocked: dict[str, str] = {}
        self.requests = 0

    def close(self) -> None:
        self._client.close()

    def _wait(self, host: str) -> None:
        gap = self._clock() - self._last.get(host, float("-inf"))
        if gap < self._min_interval:
            self._sleep(self._min_interval - gap)
        self._last[host] = self._clock()

    def _get(self, url: str, headers: dict | None = None) -> httpx.Response:
        self._wait(urlsplit(url).netloc)
        self.requests += 1
        return self._client.get(url, headers=headers or {})

    def _allowed(self, url: str) -> None:
        parts = urlsplit(url)
        host = parts.netloc
        if host in self._blocked:
            raise Blocked(self._blocked[host])
        rp = self._robots.get(host)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self._get(f"{parts.scheme}://{host}/robots.txt")
            except httpx.HTTPError as e:
                self._block(host, f"robots.txt could not be read ({e.__class__.__name__})")
            if r.status_code in (401, 403):
                self._block(host, f"robots.txt refused (HTTP {r.status_code})")
            if r.status_code == 200 and is_challenge(r.text):
                self._block(host, "robots.txt answered with a bot challenge page")
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            if delay := rp.crawl_delay(ROBOTS_TOKEN):
                self._min_interval = max(self._min_interval, float(delay))
            self._robots[host] = rp
        if not rp.can_fetch(ROBOTS_TOKEN, url):
            raise Blocked(f"robots.txt disallows {parts.path}")

    def _block(self, host: str, reason: str):
        self._blocked[host] = reason
        raise Blocked(reason)

    def head(self, url: str) -> int:
        """Status code of a HEAD request, with the same robots.txt, spacing and blocking rules.
        Used to find which dated documents exist without downloading them (QLD)."""
        self._allowed(url)
        self._wait(urlsplit(url).netloc)
        self.requests += 1
        r = self._client.head(url)
        if r.status_code in (401, 403, 429):
            self._block(urlsplit(url).netloc, f"HTTP {r.status_code}")
        return r.status_code

    def fetch(self, url: str, *, etag: str | None = None, last_modified: str | None = None,
              previous_sha256: str | None = None) -> FetchResult:
        self._allowed(url)
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        r = self._get(url, headers)
        host = urlsplit(url).netloc
        if r.status_code == 304:
            return FetchResult("unchanged", etag=etag, last_modified=last_modified)
        if r.status_code in (401, 403, 429):
            self._block(host, f"HTTP {r.status_code}")
        r.raise_for_status()
        body = r.content
        if "html" in r.headers.get("content-type", "") and is_challenge(body[:30_000].decode("utf-8", "replace")):
            self._block(host, "bot challenge page")
        sha = hashlib.sha256(body).hexdigest()
        meta = dict(etag=r.headers.get("etag"), last_modified=r.headers.get("last-modified"), downloaded=True)
        if sha == previous_sha256:
            return FetchResult("unchanged", sha256=sha, **meta)
        return FetchResult("changed", body=body, sha256=sha, **meta)
