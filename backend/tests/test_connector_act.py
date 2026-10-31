"""ACT connector against real fixtures saved from hansard.act.gov.au on 31 Oct 2026
(backend/tests/fixtures/MANIFEST.md). No network."""
from datetime import date
from pathlib import Path
from urllib.parse import unquote

import httpx
import pytest
from sqlalchemy import select

from app import config, db
from app.db import Document, SittingDay, Source, Speech
from connectors.act import ASSEMBLY, BASE, ACTConnector
from connectors.base import SittingDayRef
from pipeline.fetch import Fetcher
from pipeline.sync import run_scan

FX = Path(__file__).parent / "fixtures" / "sources" / "ACT-LA"
INDEX = f"{BASE}/{ASSEMBLY}/2026/debates(PDF).htm"
PROOF_URL = f"{BASE}/{ASSEMBLY}/2026/PDF/tP260917.pdf"
D = date(2026, 9, 17)


class FixtureSite:
    def __init__(self):
        self.routes = {INDEX: (FX / "2026-debates-index.html").read_bytes(),
                       PROOF_URL: (FX / "2026-09-17-proof.pdf").read_bytes()}
        self.hits = []

    def handler(self, request):
        url = unquote(str(request.url))   # httpx sends "debates%28PDF%29.htm"
        self.hits.append(url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if url in self.routes:
            body = self.routes[url]
            tag = f'"{hash(body) & 0xFFFFFFFF:x}"'
            if request.headers.get("if-none-match") == tag:
                return httpx.Response(304)
            return httpx.Response(200, content=body, headers={"ETag": tag})
        return httpx.Response(404)


@pytest.fixture
def site():
    return FixtureSite()


@pytest.fixture
def connector(site):
    return ACTConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(site.handler)))


@pytest.fixture(scope="module")
def sep17():
    c = ACTConnector(None)
    from connectors.base import DocumentRef
    ref = DocumentRef("ACT-LA", D, PROOF_URL, "pdf", "proof", key="pdf:ACT-LA:2026-09-17", citation_url=PROOF_URL)
    return c.parse((FX / "2026-09-17-proof.pdf").read_bytes(), ref, lambda url: b"")


# ---- listing ----------------------------------------------------------------

def test_index_lists_published_proofs_and_unpublished_days(connector):
    days = connector.list_sitting_days(date(2026, 9, 1), date(2026, 10, 31))
    assert SittingDayRef("ACT-LA", D, "proof") in days
    assert SittingDayRef("ACT-LA", date(2026, 10, 27), "proof") in days
    # Sat on 28 and 29 Oct, not published yet: listed, but with no document.
    assert SittingDayRef("ACT-LA", date(2026, 10, 28), "unknown") in days
    assert connector.list_documents(SittingDayRef("ACT-LA", date(2026, 10, 28))) == []
    assert len(connector.list_sitting_days(date(2026, 1, 1), date(2026, 12, 31))) == 33


def test_document_is_the_day_pdf_with_a_stable_key(connector):
    [ref] = connector.list_documents(SittingDayRef("ACT-LA", D, "proof"))
    assert ref.url == PROOF_URL and ref.citation_url == PROOF_URL
    assert ref.key == "pdf:ACT-LA:2026-09-17" and ref.version_hint == "proof"


def test_recess_is_empty_and_a_missing_year_index_means_no_sittings(connector):
    assert connector.list_sitting_days(date(2026, 7, 1), date(2026, 8, 31)) == []
    assert connector.list_sitting_days(date(2027, 1, 1), date(2027, 1, 31)) == []   # index 404s until the year's first sitting


# ---- the day PDF ------------------------------------------------------------

def test_proof_version_pages_and_no_low_match_note(sep17):
    assert sep17.version == "proof" and sep17.method == "pdf" and sep17.note is None
    first = sep17.speeches[0]
    assert (first.speaker_name, first.speaker_role, first.start_time, first.page) == \
        ("MR SPEAKER", "presiding officer (Mr Hanson)", "10:00", "2751")
    assert first.anchor_url == f"{PROOF_URL}#page=2751"
    assert all(s.page and s.anchor_url.endswith(f"#page={s.page}") for s in sep17.speeches)


def test_ministerial_statement_header_wrapped_over_lines(sep17):
    cheyne = next(s for s in sep17.speeches if s.speaker_name == "MS CHEYNE" and s.proceeding_type == "Ministerial statements")
    assert cheyne.electorate == "Ginninderra" and "Attorney-General" in cheyne.speaker_role
    assert cheyne.start_time == "10:01"
    assert cheyne.debate_title.startswith("Coroner’s report—inquest into the death of Paul Edward Storey")
    assert cheyne.text.startswith("Let me begin by first acknowledging Mr Paul Edward Storey’s")


def test_question_time_questions_supplementaries_and_answers(sep17):
    qt = [s for s in sep17.speeches if s.debate_title == "Canberra Hospital—proposed acute palliative care unit"]
    assert [(s.speaker_name, s.proceeding_type.split("(")[-1].rstrip(")")) for s in qt] == [
        ("MR PARTON", "question"), ("DR PATERSON", "answer"), ("MR PARTON", "question"),
        ("DR PATERSON", "answer"), ("MRS MORRIS", "question"), ("DR PATERSON", "answer")]
    assert qt[0].text.startswith("My question is to the Minister for Health.")


def test_roles_interjections_and_written_answers(sep17):
    parton = next(s for s in sep17.speeches if s.speaker_name == "MR PARTON" and s.speaker_role)
    assert parton.speaker_role == "Leader of the Opposition"
    cheyne = [s for s in sep17.speeches if s.speaker_name == "Ms Cheyne" and not s.proceeding_type.endswith("(answer)")]
    assert len(cheyne) >= 3 and all(s.proceeding_type.endswith("(interjection)") for s in cheyne)
    written = [s for s in sep17.speeches if s.proceeding_type == "Questions without notice taken on notice (answer)"]
    assert {s.speaker_name for s in written} >= {"Dr Paterson", "Ms Stephen-Smith", "Ms Orr"}
    assert next(s for s in written if s.debate_title == "Bushfires—community fire units").speaker_name == "Dr Paterson"


def test_page_furniture_and_division_lists_are_not_speech(sep17):
    text = "\n".join(s.text for s in sep17.speeches)
    assert "Legislative Assembly for the ACT" not in text and "Ayes, 16" not in text
    assert "Suzanne Orr\nMarisa Paterson" not in text
    assert not any(s.text.strip() in {"PROOF", "Ministerial statement"} for s in sep17.speeches)


def test_another_day_lines_up_with_its_contents():
    from connectors.base import DocumentRef
    url = f"{BASE}/{ASSEMBLY}/2026/PDF/P260224.pdf"
    doc = ACTConnector(None).parse((FX / "2026-02-24-proof-P.pdf").read_bytes(),
                                   DocumentRef("ACT-LA", date(2026, 2, 24), url, "pdf", citation_url=url), lambda u: b"")
    assert doc.note is None and doc.version == "proof"
    assert sum(1 for s in doc.speeches if s.proceeding_type == "Questions without notice (question)") > 40
    assert not any(not s.speaker_name and "(procedural)" not in (s.proceeding_type or "") for s in doc.speeches)


# ---- through the sync engine ------------------------------------------------

@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "")
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text("sources:\n  - {id: ACT-LA, parliament: ACT, chamber: Legislative Assembly, "
                         "connector: act, enabled: true, status: ok}\n")
    monkeypatch.setattr("pipeline.sync.SOURCES_YAML", yaml_path)
    config.get_settings.cache_clear()
    db.reset_engine()
    from app.main import migrate
    migrate()
    yield
    db.reset_engine()
    config.get_settings.cache_clear()


def _source(watermark):
    with db.session() as s:
        s.add(Source(id="ACT-LA", parliament="ACT", chamber="Legislative Assembly", connector="act",
                     enabled=True, watermark_date=watermark))
        s.commit()


def test_sync_stores_the_day_then_a_recheck_costs_two_requests(store, site):
    _source(date(2026, 9, 16))
    fetcher = Fetcher("test", min_interval=0, transport=httpx.MockTransport(site.handler))
    run = run_scan(today=D, connectors=[ACTConnector(fetcher)], fetcher=fetcher)
    act = run.per_source_json["ACT-LA"]
    assert act["status"] == "ok" and act["new_documents"] == 1 and act["methods"] == {"pdf": 1}
    with db.session() as s:
        assert s.scalar(select(SittingDay.version)) == "proof"
        assert s.scalar(select(Document.doc_key)) == "pdf:ACT-LA:2026-09-17"
        assert s.scalar(select(Speech).where(Speech.speaker_name == "MR PARTON")).page is not None
    site.hits.clear()
    run = run_scan(today=D, connectors=[ACTConnector(fetcher)], fetcher=fetcher)
    act = run.per_source_json["ACT-LA"]
    assert act["not_modified"] == 1 and act["speeches_to_analyse"] == 0
    assert [h.rsplit("/", 1)[-1] for h in site.hits] == ["debates(PDF).htm", "tP260917.pdf"]


def test_sync_holds_the_watermark_before_unpublished_days(store, site):
    _source(date(2026, 10, 27))
    fetcher = Fetcher("test", min_interval=0, transport=httpx.MockTransport(site.handler))
    run = run_scan(today=date(2026, 10, 31), connectors=[ACTConnector(fetcher)], fetcher=fetcher)
    act = run.per_source_json["ACT-LA"]
    assert act["days_pending"] == 2 and act["errors"] == 0 and act["status"] == "ok"
    with db.session() as s:
        assert s.get(Source, "ACT-LA").watermark_date == date(2026, 10, 27)
