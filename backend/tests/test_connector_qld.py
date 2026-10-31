"""QLD connector against the real Record of Proceedings for 13 Oct 2026, saved from
documents.parliament.qld.gov.au on 31 Oct 2026 (backend/tests/fixtures/MANIFEST.md). No network."""
from datetime import date
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app import config, db
from app.db import Document, Source, Speech
from connectors.base import DocumentRef, SittingDayRef
from connectors.qld import QLDConnector, daily_url
from pipeline.fetch import Fetcher
from pipeline.sync import run_scan

FX = Path(__file__).parent / "fixtures" / "sources" / "QLD-LA"
D = date(2026, 10, 13)
URL = daily_url(D)


class FixtureSite:
    """The documents host: 13 Oct 2026 exists; every other date is a 404."""

    def __init__(self):
        self.body = (FX / "2026-10-13.pdf").read_bytes()
        self.hits: list[tuple[str, str]] = []

    def handler(self, request):
        url = str(request.url)
        self.hits.append((request.method, url))
        if url.endswith("/robots.txt"):
            return httpx.Response(404)
        if url != URL:
            return httpx.Response(404)
        tag = '"2766ec9c675bdd1:0"'
        if request.method == "HEAD":
            return httpx.Response(200, headers={"ETag": tag})
        if request.headers.get("if-none-match") == tag:
            return httpx.Response(304)
        return httpx.Response(200, content=self.body, headers={"ETag": tag})


@pytest.fixture
def site():
    return FixtureSite()


@pytest.fixture
def connector(site):
    return QLDConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(site.handler)))


@pytest.fixture(scope="module")
def oct13():
    ref = DocumentRef("QLD-LA", D, URL, "pdf", key="pdf:QLD-LA:2026-10-13", citation_url=URL)
    return QLDConnector(None).parse((FX / "2026-10-13.pdf").read_bytes(), ref, lambda u: b"")


# ---- listing ----------------------------------------------------------------

def test_sitting_days_are_found_by_probing_weekdays_without_downloading(connector, site):
    days = connector.list_sitting_days(date(2026, 10, 10), date(2026, 10, 16))
    assert days == [SittingDayRef("QLD-LA", D)]
    probes = [u for m, u in site.hits if m == "HEAD"]
    assert len(probes) == 5   # Mon–Fri only; Sat 10 and Sun 11 are not probed
    assert not any(m == "GET" and u.endswith(".pdf") for m, u in site.hits)


def test_document_and_recent_days_stay_open(connector):
    [ref] = connector.list_documents(SittingDayRef("QLD-LA", D))
    assert ref.url == URL and ref.key == "pdf:QLD-LA:2026-10-13" and ref.citation_url == URL
    assert connector.list_documents(SittingDayRef("QLD-LA", date(2026, 10, 14))) == []
    assert connector.settled_through(date(2026, 10, 31)) == date(2026, 10, 28)


# ---- the day PDF ------------------------------------------------------------

def test_proof_flag_contents_and_pages(oct13):
    assert oct13.version == "proof" and oct13.method == "pdf" and oct13.note is None
    first_named = next(s for s in oct13.speeches if s.speaker_name)
    assert (first_named.speaker_name, first_named.page) == ("Mr SPEAKER", "3041")
    assert all(s.anchor_url == f"{URL}#page={s.page}" for s in oct13.speeches)


def test_headers_carry_party_electorate_role_and_time(oct13):
    crandon = next(s for s in oct13.speeches if s.speaker_name == "Mr CRANDON" and s.start_time)
    assert (crandon.electorate, crandon.party, crandon.start_time) == ("Coomera", "LNP", "12:28")
    assert crandon.text.startswith("I rise to make a contribution to the Home")
    rowan = next(s for s in oct13.speeches if s.speaker_name == "Dr ROWAN" and s.speaker_role)
    # "(Moggill—LNP) (Leader of the House) (11.16 am), by leave, without notice:"
    assert (rowan.electorate, rowan.party, rowan.speaker_role, rowan.start_time) == \
        ("Moggill", "LNP", "Leader of the House", "11:16")
    assert {s.party for s in oct13.speeches if s.party} == {"LNP", "ALP", "Grn", "Ind"}


def test_question_time_with_points_of_order_and_interjections(oct13):
    qt = [s for s in oct13.speeches if s.debate_title == "Child Safety System"][:8]
    assert [(s.speaker_name, s.proceeding_type.split("(")[-1].rstrip(")")) for s in qt] == [
        ("Mr MILES", "question"), ("Ms CAMM", "answer"), ("Mr de BRENNI", "statement"),
        ("Mr SPEAKER", "presiding"), ("Dr ROWAN", "statement"), ("Mr SPEAKER", "presiding"),
        ("Ms CAMM", "answer"), ("Mr Mander", "interjection")]
    assert qt[0].start_time == "10:15"
    assert "Mr Bleijie interjected." in qt[2].text   # a stage direction stays in the record


def test_divisions_attendance_and_furniture_are_not_speech(oct13):
    text = "\n".join(s.text for s in oct13.speeches)
    assert "AYES, 52" not in text and "Baillie, Barounis" not in text
    assert "Asif, Bailey, Baillie" not in text             # closing attendance roll
    assert "13 Oct 2026\n" not in text and "____" not in text
    assert any(s.text.startswith("Division: Question put") for s in oct13.speeches)


def test_cover_sign_off_does_not_join_the_contents():
    """14 Oct 2026: the cover's sign-off block (Speaker, Clerk, reporter) sits just above the
    contents' continuation; joining them derailed heading matching (27 of 55) before the fix."""
    url = daily_url(date(2026, 10, 14))
    doc = QLDConnector(None).parse((FX / "2026-10-14.pdf").read_bytes(),
                                   DocumentRef("QLD-LA", date(2026, 10, 14), url, "pdf", citation_url=url), lambda u: b"")
    assert doc.note is None and doc.version == "proof"
    assert not any("NJ LAURIE" in (s.debate_title or "") for s in doc.speeches)
    assert sum(1 for s in doc.speeches if s.proceeding_type == "QUESTIONS WITHOUT NOTICE (question)") >= 10


@pytest.mark.parametrize("day", [date(2026, 10, 13), date(2026, 10, 14)])
def test_no_speaker_header_is_left_inside_speech_text(day):
    """Headers like "Hon. G GRACE (McConnel—ALP) (12.03 pm):" or a minister's title over five lines
    must start a turn, never be swallowed into the previous one."""
    import re
    url = daily_url(day)
    doc = QLDConnector(None).parse((FX / f"{day.isoformat()}.pdf").read_bytes(),
                                   DocumentRef("QLD-LA", day, url, "pdf", citation_url=url), lambda u: b"")
    header = re.compile(r"(?:Mr|Ms|Mrs|Dr|Hon\.) [A-Z][A-Za-z.]* ?(?:de )?[A-Z]{2,}[A-Z'’\-]* \([^()]*—(?:LNP|ALP|KAP|Grn|Ind)\)")
    assert not [line for s in doc.speeches for line in s.text.split("\n") if header.search(line)]


# ---- through the sync engine ------------------------------------------------

def test_sync_keeps_recent_days_open_and_rechecks_cheaply(tmp_path, monkeypatch, site):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "")
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text("sources:\n  - {id: QLD-LA, parliament: QLD, chamber: Legislative Assembly, "
                         "connector: qld, enabled: true, status: ok}\n")
    monkeypatch.setattr("pipeline.sync.SOURCES_YAML", yaml_path)
    config.get_settings.cache_clear()
    db.reset_engine()
    from app.main import migrate
    migrate()
    try:
        with db.session() as s:
            s.add(Source(id="QLD-LA", parliament="QLD", chamber="Legislative Assembly", connector="qld",
                         enabled=True, watermark_date=date(2026, 10, 12)))
            s.commit()
        fetcher = Fetcher("test", min_interval=0, transport=httpx.MockTransport(site.handler))
        today = date(2026, 10, 16)
        run = run_scan(today=today, connectors=[QLDConnector(fetcher)], fetcher=fetcher)
        qld = run.per_source_json["QLD-LA"]
        assert qld["status"] == "ok" and qld["new_documents"] == 1 and qld["methods"] == {"pdf": 1}
        with db.session() as s:
            assert s.get(Source, "QLD-LA").watermark_date == date(2026, 10, 13)   # today − 3: 14–16 Oct stay open
            assert s.scalar(select(Document.doc_key)) == "pdf:QLD-LA:2026-10-13"
            assert s.scalar(select(Speech.party).where(Speech.speaker_name == "Mr CRANDON", Speech.party.is_not(None))) == "LNP"

        site.hits.clear()
        run = run_scan(today=today, connectors=[QLDConnector(fetcher)], fetcher=fetcher)
        qld = run.per_source_json["QLD-LA"]
        assert qld["not_modified"] == 1 and qld["speeches_to_analyse"] == 0
        # 14, 15 and 16 Oct probed again (HEAD), and 13 Oct, still a proof, rechecked with a 304.
        assert sorted(m for m, u in site.hits if not u.endswith("robots.txt")) == ["GET", "HEAD", "HEAD", "HEAD", "HEAD"]
    finally:
        db.reset_engine()
        config.get_settings.cache_clear()
