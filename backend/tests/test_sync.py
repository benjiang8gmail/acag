"""Sync rules from spec §8 and the Phase 2 definition of done, tested with a fake
parliament served over a mock HTTP transport.

The fake parliament is a test double, not a fixture of any real source. Real
connectors get their own tests against real fixtures (docs/sources.md).
"""
from datetime import date

import httpx
import pytest
from sqlalchemy import func, select

from app import config, db
from app.db import Document, ScanRun, SittingDay, Source, Speech
from connectors.base import CouldNotCheck, DocumentRef, ParsedDocument, ParsedSpeech, SittingDayRef
from pipeline.fetch import Fetcher
from pipeline.sync import ScanInProgress, months_ago, run_scan

TODAY = date(2026, 10, 31)
HOST = "https://hansard.example"


class FakeSite:
    """Serves documents with ETags and honours If-None-Match, like a well-behaved server."""

    def __init__(self):
        self.docs: dict[str, bytes] = {}
        self.robots = b"User-agent: *\nDisallow: /private/\n"
        self.honour_conditional = True
        self.refuse = False
        self.broken: set[str] = set()
        self.hits: list[str] = []

    def etag(self, url):
        return f'"{hash(self.docs[url]) & 0xFFFFFFFF:x}"'

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.hits.append(url)
        if self.refuse:
            return httpx.Response(403, text="Access denied")
        if url.endswith("/robots.txt"):
            return httpx.Response(200, content=self.robots)
        if url in self.broken:
            return httpx.Response(500)
        if url not in self.docs:
            return httpx.Response(404)
        tag = self.etag(url)
        if self.honour_conditional and request.headers.get("if-none-match") == tag:
            return httpx.Response(304)
        return httpx.Response(200, content=self.docs[url], headers={"ETag": tag, "Content-Type": "text/plain"})

    def doc_hits(self):
        return [u for u in self.hits if not u.endswith("robots.txt")]


class FakeConnector:
    """Two chambers. A document is lines of "proof|final" then "speaker|text"."""
    code = "FK"
    source_ids = ("FK-LA", "FK-LC")

    def __init__(self, site: FakeSite):
        self.site = site
        self.calendar: dict[str, list[date]] = {"FK-LA": [], "FK-LC": []}
        self.calendar_down = False

    def list_sitting_days(self, start, end):
        if self.calendar_down:
            raise CouldNotCheck("calendar returned 500")
        return [SittingDayRef(sid, d) for sid, ds in self.calendar.items() for d in ds if start <= d <= end]

    def url(self, sid, d):
        return f"{HOST}/{sid}/{d.isoformat()}.txt"

    def list_documents(self, day):
        url = self.url(day.source_id, day.sitting_date)
        if url not in self.site.docs and url not in self.site.broken:
            return []   # sat, but not published yet
        return [DocumentRef(day.source_id, day.sitting_date, url, "txt")]

    def parse(self, raw, ref, fetch_part):
        version, *lines = raw.decode().splitlines()
        speeches = [ParsedSpeech(seq=i, speaker_name=ln.split("|")[0], text=ln.split("|")[1]) for i, ln in enumerate(lines)]
        return ParsedDocument(speeches=speeches, version=version)

    def sit(self, sid, d, version="proof", speeches=("A|Hello", "B|The Auditor-General's report")):
        self.calendar[sid].append(d)
        self.site.docs[self.url(sid, d)] = "\n".join([version, *speeches]).encode()


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "")
    config.get_settings.cache_clear()
    db.reset_engine()
    from app.main import migrate
    migrate()
    with db.session() as s:
        for sid in FakeConnector.source_ids:
            s.add(Source(id=sid, parliament="FK", chamber=sid, connector="fake", enabled=True))
        s.commit()
    site = FakeSite()
    conn = FakeConnector(site)
    fetcher = Fetcher("test-agent", min_interval=0, transport=httpx.MockTransport(site.handler))

    def scan(today=TODAY):
        return run_scan(trigger="cli", today=today, connectors=[conn], fetcher=fetcher)

    yield site, conn, scan, tmp_path
    db.reset_engine()
    config.get_settings.cache_clear()


def count(model, *where):
    with db.session() as s:
        return s.scalar(select(func.count()).select_from(model).where(*where))


def source(sid):
    with db.session() as s:
        return s.get(Source, sid)


def test_months_ago_keeps_the_same_date():
    assert months_ago(date(2026, 10, 31), 2) == date(2026, 8, 31)
    assert months_ago(date(2026, 4, 30), 2) == date(2026, 2, 28)
    assert months_ago(date(2026, 1, 15), 2) == date(2025, 11, 15)


def test_first_run_backfills_two_months_and_stores_raw_files(env):
    site, conn, scan, data = env
    conn.sit("FK-LA", date(2026, 8, 30))        # before the window: ignored
    conn.sit("FK-LA", date(2026, 8, 31))        # first day of the window
    conn.sit("FK-LA", date(2026, 10, 28), version="final")
    conn.sit("FK-LC", date(2026, 9, 15))
    run = scan()
    assert run.status == "done"
    assert count(SittingDay) == 3 and count(Document) == 3 and count(Speech) == 6
    assert run.per_source_json["FK-LA"]["new_documents"] == 2
    assert run.per_source_json["FK-LA"]["speeches_to_analyse"] == 4
    assert source("FK-LA").watermark_date == TODAY and source("FK-LA").status == "ok"
    assert len(list((data / "raw" / "FK-LA").rglob("*.txt"))) == 2


def test_immediate_rerun_makes_no_downloads_and_needs_no_analysis(env):
    site, conn, scan, _ = env
    conn.sit("FK-LA", date(2026, 10, 27))                   # proof: rechecked
    conn.sit("FK-LA", date(2026, 10, 28), version="final")  # final: never fetched again
    scan()
    site.hits.clear()
    run = scan()
    la = run.per_source_json["FK-LA"]
    assert la["new_documents"] == la["changed_documents"] == 0
    assert la["unchanged_downloads"] == 0 and la["not_modified"] == 1
    assert la["speeches_to_analyse"] == 0 and la["llm_calls"] == 0
    assert site.doc_hits() == [conn.url("FK-LA", date(2026, 10, 27))]  # only the proof, answered 304
    assert count(Document) == 2


def test_server_ignoring_conditional_headers_still_creates_nothing(env):
    site, conn, scan, _ = env
    conn.sit("FK-LA", date(2026, 10, 27))
    scan()
    site.honour_conditional = False
    run = scan()
    assert run.per_source_json["FK-LA"]["unchanged_downloads"] == 1
    assert run.per_source_json["FK-LA"]["speeches_to_analyse"] == 0
    assert count(Document) == 1


def test_new_day_processes_only_that_day(env):
    site, conn, scan, _ = env
    conn.sit("FK-LA", date(2026, 10, 20), version="final")
    scan(date(2026, 10, 25))
    conn.sit("FK-LA", date(2026, 10, 29), version="final")
    site.hits.clear()
    run = scan()
    assert site.doc_hits() == [conn.url("FK-LA", date(2026, 10, 29))]
    assert run.per_source_json["FK-LA"]["new_days"] == 1


def test_proof_to_final_with_edits_re_derives_only_changed_speeches(env):
    site, conn, scan, _ = env
    d = date(2026, 10, 27)
    conn.sit("FK-LA", d, speeches=("A|Hello", "B|The Auditor-Generals report", "C|Unchanged words"))
    scan()
    site.docs[conn.url("FK-LA", d)] = b"final\nA|Hello\nB|The Auditor-General's report\nC|Unchanged words"
    run = scan()
    la = run.per_source_json["FK-LA"]
    assert la["changed_documents"] == 1 and la["speeches_to_analyse"] == 1
    with db.session() as s:
        old, new = s.scalars(select(Document).order_by(Document.id)).all()
        assert old.superseded_by == new.id and new.version == "final"
        assert s.scalar(select(SittingDay.version)) == "final"
    # Once final, the day is no longer rechecked.
    site.hits.clear()
    scan()
    assert site.doc_hits() == []


def test_recess_is_no_sittings_not_an_error(env):
    _, conn, scan, _ = env
    run = scan()
    assert run.per_source_json["FK-LA"]["status"] == "no_sittings"
    assert source("FK-LA").status == "no_sittings" and source("FK-LA").watermark_date == TODAY


def test_unreadable_calendar_is_an_error_and_keeps_the_watermark(env):
    _, conn, scan, _ = env
    conn.calendar_down = True
    run = scan()
    assert run.per_source_json["FK-LA"]["status"] == "error"
    assert source("FK-LA").status == "error" and source("FK-LA").watermark_date is None


def test_failed_day_holds_the_watermark_before_it(env):
    site, conn, scan, _ = env
    conn.sit("FK-LA", date(2026, 10, 10), version="final")
    conn.sit("FK-LA", date(2026, 10, 20), version="final")
    site.broken.add(conn.url("FK-LA", date(2026, 10, 20)))   # 500: this day fails
    conn.sit("FK-LA", date(2026, 10, 27), version="final")
    run = scan()
    assert run.per_source_json["FK-LA"]["errors"] == 1
    assert source("FK-LA").watermark_date == date(2026, 10, 19)
    assert count(Document) == 2   # the days either side were still stored


def test_blocked_site_is_marked_blocked_and_not_retried(env):
    site, conn, scan, _ = env
    conn.sit("FK-LA", date(2026, 10, 27))
    conn.sit("FK-LA", date(2026, 10, 28))
    site.refuse = True
    run = scan()
    assert run.per_source_json["FK-LA"]["status"] == "blocked"
    assert source("FK-LA").status == "blocked"
    assert len(site.hits) == 1   # robots.txt refused; nothing else was requested


def test_robots_disallow_is_obeyed(env):
    site, conn, scan, _ = env
    site.robots = b"User-agent: ACAG-HansardWatch\nDisallow: /\n"
    conn.sit("FK-LA", date(2026, 10, 27))
    run = scan()
    assert run.per_source_json["FK-LA"]["status"] == "blocked"
    assert site.doc_hits() == []


def test_disabled_sources_are_not_scanned(env):
    site, conn, scan, _ = env
    with db.session() as s:
        s.get(Source, "FK-LC").enabled = False
        s.commit()
    conn.sit("FK-LC", date(2026, 10, 27))
    run = scan()
    assert "FK-LC" not in run.per_source_json and site.doc_hits() == []


def test_one_scan_at_a_time(env):
    _, _, scan, _ = env
    with db.session() as s:
        s.add(ScanRun(trigger="manual", status="running"))
        s.commit()
    with pytest.raises(ScanInProgress):
        scan()


def test_speeches_are_full_text_searchable(env):
    _, conn, scan, _ = env
    conn.sit("FK-LA", date(2026, 10, 27), speeches=("A|We support the hospital audit", "B|Nothing to see"))
    scan()
    with db.session() as s:
        rows = s.connection().exec_driver_sql(
            "SELECT speaker_name FROM speeches_fts WHERE speeches_fts MATCH 'audit'").all()
    assert rows == [("A",)]


def test_seeded_sources_match_config(env):
    from connectors.base import registry
    from pipeline.sync import seed_sources
    with db.session() as s:
        seed_sources(s)
        real = s.scalars(select(Source).where(Source.parliament != "FK")).all()
    assert len(real) == 15
    assert {r.connector for r in real if r.enabled} <= set(registry())


def test_robots_served_as_a_challenge_page_blocks_the_source(env):
    site, conn, scan, _ = env
    site.robots = b"<!DOCTYPE html><html><head><title>Just a moment...</title></head></html>"
    conn.sit("FK-LA", date(2026, 10, 27))
    run = scan()
    assert run.per_source_json["FK-LA"]["status"] == "blocked"
    assert site.doc_hits() == []


def test_unpublished_sitting_day_holds_the_watermark_until_it_appears(env):
    site, conn, scan, _ = env
    conn.sit("FK-LA", date(2026, 10, 20), version="final")
    conn.calendar["FK-LA"].append(date(2026, 10, 27))          # sat, transcript not published yet
    run = scan()
    la = run.per_source_json["FK-LA"]
    assert la["days_pending"] == 1 and la["errors"] == 0 and la["status"] == "ok"
    assert source("FK-LA").watermark_date == date(2026, 10, 26)
    site.docs[conn.url("FK-LA", date(2026, 10, 27))] = b"proof\nA|Now published"
    run = scan()
    assert run.per_source_json["FK-LA"]["new_documents"] == 1
    assert source("FK-LA").watermark_date == TODAY
