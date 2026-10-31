"""NT connector against the real Draft Daily Hansard for 22 Oct 2026, read through the
Territory Stories endpoints its robots.txt allows (/api/full_record, /api/content), saved
31 Oct 2026 (backend/tests/fixtures/MANIFEST.md). No network."""
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import unquote

import httpx
import pytest

from connectors.base import SittingDayRef
from connectors.nt import API, NTConnector, known_days, parse_pages
from pipeline.fetch import Fetcher
from pipeline.members import Enricher

FX = Path(__file__).parent / "fixtures" / "sources" / "NT-LA"
D = date(2026, 10, 22)
PAGES = json.loads((FX / "2026-10-22-pages.json").read_text())["pages"]


@pytest.fixture(scope="module")
def day():
    return parse_pages(PAGES, "https://hdl.handle.net/10070/1052298")


def kind(s):
    m = re.search(r"\((question|answer|interjection|presiding|procedural|statement)\)$", s.proceeding_type or "")
    return m.group(1) if m else "speech"


def test_days_come_from_the_config_list():
    assert known_days()[D] == "10070/1052298"


def test_connector_reads_record_then_each_page_through_allowed_endpoints():
    record = (FX / "full_record-10070-1052298.json").read_bytes()
    hits = []

    def handler(request):
        url = unquote(str(request.url))
        hits.append(url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nDisallow: /*.pdf$\nDisallow: /api/\nAllow: /api/content\nAllow: /api/full_record\n")
        if "/api/full_record" in url:
            return httpx.Response(200, content=record)
        n = int(re.search(r"page=(\d+)", url).group(1))
        return httpx.Response(200, content=json.dumps(PAGES[n]).encode())

    fetcher = Fetcher("test", min_interval=0, transport=httpx.MockTransport(handler))
    conn = NTConnector(fetcher)
    [ref] = conn.list_documents(SittingDayRef("NT-LA", D))
    assert ref.url == f"{API}/full_record?handle=10070/1052298" and ref.citation_url == "https://hdl.handle.net/10070/1052298"
    doc = conn.parse(fetcher.fetch(ref.url).body, ref, lambda u: fetcher.fetch(u).body)
    assert doc.version == "proof" and doc.method == "territory_stories" and len(doc.speeches) > 200
    assert not any(".pdf" in h for h in hits)                       # never the disallowed PDFs
    assert sum(1 for h in hits if "/api/content" in h) == 83


def test_question_time_questions_and_answers_by_office(day):
    qt = [s for s in day if s.debate_title == "Policing in Remote Communities"]
    assert (qt[0].speaker_name, kind(qt[0])) == ("Ms UIBO", "question")
    assert (qt[1].speaker_name, qt[1].speaker_role, kind(qt[1])) == ("CHIEF MINISTER", "Chief Minister", "answer")
    assert qt[1].text.startswith("Madam Speaker, I am happy to get a question about policing")
    assert kind(next(s for s in qt if s.text.startswith("A point of order"))) == "statement"


def test_ministers_portfolios_members_and_the_chair(day):
    edgington = next(s for s in day if s.speaker_name == "Mr EDGINGTON")
    assert edgington.speaker_role == "Minister (Health)" and edgington.page == "1"
    assert edgington.debate_title == "PRIVATE HOSPITALS AMENDMENT BILL"
    assert any(s.speaker_name == "Madam SPEAKER" and kind(s) == "presiding" for s in day)
    assert any(s.speaker_name == "Members" and kind(s) == "interjection" for s in day)


def test_page_headers_never_leak_into_speech(day):
    text = "\n".join(s.text for s in day)
    assert "Daily Hansard  Thursday 22 October 2026" not in text and "Meeting No 69" not in text
    assert not [s for s in day if re.match(r"^(?:Mr|Ms|Mrs|Dr) [A-Z]{2,}.*\):", s.text)]


def test_sides_from_the_member_list_and_offices(day):
    e = Enricher("NT")
    by_name = {}
    for s in day:
        if s.speaker_name and kind(s) != "presiding":
            e.apply("NT-LA", D, s)
            by_name.setdefault(s.speaker_name, s.speaker_side)
    assert by_name["CHIEF MINISTER"] == "government" and by_name["Mr EDGINGTON"] == "government"
    assert by_name["Ms UIBO"] == "opposition"
    turns = [s for s in day if s.speaker_name and kind(s) not in ("presiding",) and s.speaker_name != "Members"]
    assert sum(1 for s in turns if s.speaker_side != "unknown") / len(turns) >= 0.95
