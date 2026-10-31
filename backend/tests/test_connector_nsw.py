"""NSW connector against real fixtures saved from api.parliament.nsw.gov.au on
31 Oct 2026 (backend/tests/fixtures/MANIFEST.md). No network."""
from datetime import date
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app import config, db
from app.db import Document, SittingDay, Source, Speech
from connectors.base import SittingDayRef
from connectors.nsw import API, NSWConnector, parse_fragment
from pipeline.fetch import Fetcher
from pipeline.sync import run_scan

FX = Path(__file__).parent / "fixtures" / "sources"
LA = FX / "NSW-LA"
EMPTY_FRAGMENT = b"<hansard><chamber.xscript><fragment.text><body/></fragment.text></chamber.xscript></hansard>"
D = date(2026, 10, 22)


def fragment(uid, ptype):
    return parse_fragment((LA / f"2026-10-22-fragment-{uid}.xml").read_bytes(), ptype)


class FixtureSite:
    """Serves the saved files at their real API URLs. Fragments we did not save are
    served as empty stubs so a whole day can be walked; tests never assert on them."""

    def __init__(self):
        self.routes = {
            f"{API}/year/2026": (FX / "NSW" / "year-2026.json").read_bytes(),
            f"{API}/daily/tableofcontents/HANSARD-1323879322-170879": (LA / "2026-10-22-toc.xml").read_bytes(),
        }
        for f in LA.glob("2026-10-22-fragment-*.xml"):
            uid = "HANSARD-1323879322-" + f.stem.rsplit("-", 1)[1]
            self.routes[f"{API}/daily/fragment/{uid}"] = f.read_bytes()
        self.hits = []

    def handler(self, request):
        url = str(request.url)
        self.hits.append(url)
        if url.endswith("/robots.txt"):
            return httpx.Response(404)
        if url in self.routes:
            body = self.routes[url]
            tag = f'"{hash(body) & 0xFFFFFFFF:x}"'
            if request.headers.get("if-none-match") == tag:
                return httpx.Response(304)
            return httpx.Response(200, content=body, headers={"ETag": tag})
        if "/daily/fragment/" in url:
            return httpx.Response(200, content=EMPTY_FRAGMENT)
        return httpx.Response(404)


@pytest.fixture
def site():
    return FixtureSite()


@pytest.fixture
def connector(site):
    return NSWConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(site.handler)))


# ---- listing ----------------------------------------------------------------

def test_lists_both_chambers_with_proof_flag(connector):
    days = connector.list_sitting_days(date(2026, 10, 20), date(2026, 10, 31))
    assert SittingDayRef("NSW-LA", D, "proof") in days
    assert SittingDayRef("NSW-LC", D, "proof") in days
    assert {d.source_id for d in days} == {"NSW-LA", "NSW-LC"}
    early = connector.list_sitting_days(date(2026, 2, 4), date(2026, 2, 5))
    assert all(d.version_hint == "final" for d in early) and len(early) == 4


def test_recess_is_an_empty_list_not_an_error(connector):
    assert connector.list_sitting_days(date(2026, 1, 1), date(2026, 1, 31)) == []


def test_document_is_the_day_toc_with_stable_key_and_pdf_citation(connector):
    [ref] = connector.list_documents(SittingDayRef("NSW-LA", D, "proof"))
    assert ref.url == f"{API}/daily/tableofcontents/HANSARD-1323879322-170879"
    assert ref.key == "toc:NSW-LA:2026-10-22"
    assert ref.citation_url == f"{API}/daily/pdf/HANSARD-1323879322-171125"


# ---- fragments (golden checks on real text) ----------------------------------

def test_bill_second_reading_speech():
    procedural, speech, presiding = fragment("170878", "Bills")
    assert procedural.text.startswith("Bill introduced on motion by Ms Jenny Leong")
    assert speech.speaker_name == "Ms JENNY LEONG" and speech.speaker_id == "107"
    assert speech.electorate == "Newtown" and speech.start_time == "10:18:08"
    assert speech.proceeding_type == "Bills"
    assert speech.debate_title == "Residential Tenancies Amendment (Rent Control) Bill 2026 — Second Reading Speech"
    assert speech.text.startswith("I move:\nThat this bill be now read a second time.")
    assert presiding.speaker_role == "presiding officer"


def test_question_time_question_answer_and_interjections():
    turns = fragment("170887", "Question Time")
    q, a = turns[0], turns[1]
    assert (q.speaker_name, q.speaker_id, q.proceeding_type) == ("Ms KELLIE SLOANE", "2288", "Question Time (question)")
    assert q.text.startswith("My question is directed to the Minister for Police")
    assert a.speaker_role == "Minister for Police and Counter-terrorism, and Minister for the Hunter"
    assert a.proceeding_type == "Question Time (answer)"
    # The minister resumes after the Speaker and an interjection: her words rejoin the answer.
    assert "I apologise, Attorney." in a.text
    assert not any(t.speaker_id == "128" for t in turns[2:])
    daley = next(t for t in turns if t.speaker_name == "Mr Michael Daley")
    assert daley.proceeding_type == "Question Time (interjection)" and daley.text == "Stop being so relevant!"


def test_tabled_document_statement():
    [s] = fragment("170902", "Documents")
    assert s.debate_title == "Transport for NSW — Reports"
    assert s.proceeding_type == "Documents (statement)"
    assert s.text.startswith("In accordance with section 133A of the Road Transport Act 2013")
    assert "Review of the Average Speed Camera Light Vehicle Trial: Outcomes report" in s.text


def test_written_statement_drops_the_dash_after_the_electorate():
    [s] = fragment("170973", "Written Community Recognition Statements")
    assert s.speaker_name == "Mr ROY BUTLER" and s.electorate == "Barwon"
    assert s.text.startswith("Congratulations to Marg Symes")


def test_motion_debate_keeps_each_speaker_whole():
    turns = fragment("170915", "Motions")
    speeches = [t for t in turns if t.proceeding_type == "Motions"]
    names = [t.speaker_name for t in speeches]
    assert names[:4] == ["Mr TIM CRAKANTHORP", "Mr DAVID LAYZELL", "Mr CLAYTON BARR", "Mr MATT CROSS"]
    # Each contribution is one speech; the mover speaks again only to close the debate.
    assert len(names) == len(set(names)) + 1 and names[-1] == "Mr TIM CRAKANTHORP"
    assert speeches[-1].text.startswith("In reply:")
    assert all(len(t.text) > 500 for t in speeches)
    assert not any("DivisionThreeColumn" in t.text for t in turns)


def test_whole_day_walks_every_topic_in_order(connector, site):
    [ref] = connector.list_documents(SittingDayRef("NSW-LA", D, "proof"))
    parts = []

    def fetch_part(url):
        parts.append(url)
        return connector.fetcher.fetch(url).body

    doc = connector.parse((LA / "2026-10-22-toc.xml").read_bytes(), ref, fetch_part)
    assert doc.version == "proof"
    assert len(parts) == 244 and parts[0].endswith("HANSARD-1323879322-170878")
    assert [s.seq for s in doc.speeches] == list(range(len(doc.speeches)))
    assert all(s.anchor_url == ref.citation_url for s in doc.speeches)
    assert any(s.speaker_name == "Ms KELLIE SLOANE" for s in doc.speeches)


# ---- through the sync engine ------------------------------------------------

def test_sync_stores_the_day_then_a_recheck_costs_one_request(tmp_path, monkeypatch, site):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "")
    sources_yaml = tmp_path / "sources.yaml"
    sources_yaml.write_text("sources:\n  - {id: NSW-LA, parliament: NSW, chamber: Legislative Assembly, "
                            "connector: nsw, enabled: true, status: ok}\n")
    monkeypatch.setattr("pipeline.sync.SOURCES_YAML", sources_yaml)
    config.get_settings.cache_clear()
    db.reset_engine()
    from app.main import migrate
    migrate()
    with db.session() as s:
        s.add(Source(id="NSW-LA", parliament="NSW", chamber="Legislative Assembly", connector="nsw",
                     enabled=True, watermark_date=date(2026, 10, 21)))
        s.commit()
    fetcher = Fetcher("test", min_interval=0, transport=httpx.MockTransport(site.handler))
    try:
        run = run_scan(today=D, connectors=[NSWConnector(fetcher)], fetcher=fetcher)
        la = run.per_source_json["NSW-LA"]
        assert la["status"] == "ok" and la["new_documents"] == 1 and la["parts_fetched"] == 244
        with db.session() as s:
            assert s.scalar(select(SittingDay.version)) == "proof"
            doc = s.scalar(select(Document))
            assert doc.doc_key == "toc:NSW-LA:2026-10-22"
            sloane = s.scalar(select(Speech).where(Speech.speaker_id == "2288"))
            assert sloane.speaker_name == "Ms KELLIE SLOANE"

        site.hits.clear()
        run = run_scan(today=D, connectors=[NSWConnector(fetcher)], fetcher=fetcher)
        la = run.per_source_json["NSW-LA"]
        assert la["parts_fetched"] == 0 and la["speeches_to_analyse"] == 0 and la["not_modified"] == 1
        assert [h.rsplit("/", 1)[-1] for h in site.hits] == ["2026", "HANSARD-1323879322-170879"]
    finally:
        db.reset_engine()
        config.get_settings.cache_clear()
