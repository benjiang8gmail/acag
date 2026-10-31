"""Tasmania connector against the Parliament's own document search (search.parliament.tas.gov.au),
saved 31 Oct 2026 (backend/tests/fixtures/MANIFEST.md). No network."""
import re
from datetime import date
from pathlib import Path
from urllib.parse import unquote_plus

import httpx
import pytest

from connectors.base import CouldNotCheck, SittingDayRef
from connectors.base import DocumentRef
from connectors.tas import HOST, TASConnector, parse_docx, search_url
from pipeline.fetch import Fetcher

FX = Path(__file__).parent / "fixtures" / "sources"
SEP10 = date(2026, 9, 10)


def kind(s):
    m = re.search(r"\((\w+)\)$", s.proceeding_type or "")
    return m.group(1) if m else "speech"


class Site:
    def __init__(self):
        self.hits = []

    def handler(self, request):
        url = unquote_plus(str(request.url))
        self.hits.append(url)
        if url.endswith("/robots.txt"):
            return httpx.Response(404)
        if url.endswith("/quicksearch/2026/sittingdays.html"):
            return httpx.Response(200, content=(FX / "TAS" / "sittingdays-2026.html").read_bytes())
        if "IW_FIELD_ADVANCE_PHRASE=Thursday 10 September 2026" in url:
            return httpx.Response(200, content=(FX / "TAS" / "search-2026-09-10.html").read_bytes())
        if "IW_FIELD_ADVANCE_PHRASE=" in url:   # any other date: not indexed yet
            return httpx.Response(200, content=(FX / "TAS" / "search-2026-10-30-not-indexed.html").read_bytes())
        return httpx.Response(404)


@pytest.fixture
def connector():
    return TASConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(Site().handler)), today=date(2026, 10, 31))


@pytest.fixture(scope="module")
def ha():
    return parse_docx((FX / "TAS-HA" / "2026-09-10.docx").read_bytes(), search_url(SEP10))


@pytest.fixture(scope="module")
def lc():
    return parse_docx((FX / "TAS-LC" / "2026-09-10.docx").read_bytes(), search_url(SEP10))


def test_calendar_search_and_pending_days(connector):
    days = connector.list_sitting_days(date(2026, 9, 8), date(2026, 10, 30))
    assert SittingDayRef("TAS-HA", SEP10) in days and SittingDayRef("TAS-LC", SEP10) in days
    # 27–30 Oct are on the calendar but not indexed yet: listed for both chambers with no document (pending).
    assert SittingDayRef("TAS-HA", date(2026, 10, 30)) in days
    assert connector.list_documents(SittingDayRef("TAS-HA", date(2026, 10, 30))) == []
    [ref] = connector.list_documents(SittingDayRef("TAS-HA", SEP10))
    assert ref.url.startswith(f"{HOST}/search/isysquery/") and ref.url.endswith("HA%20Thursday%2010%20September%202026.docx")
    assert ref.key == "docx:TAS-HA:2026-09-10" and ref.citation_url == search_url(SEP10)


def test_old_unindexed_calendar_days_are_given_up():
    c = TASConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(Site().handler)), today=date(2026, 12, 31))
    days = c.list_sitting_days(date(2026, 9, 8), date(2026, 9, 9))   # unindexed and > 30 days old
    assert days == []


class EmptySite(Site):
    """What the site answered on 31 Oct 2026, hours after serving the fixtures: HTTP 200, no body."""

    def __init__(self, empty):
        super().__init__()
        self.empty = empty

    def handler(self, request):
        r = super().handler(request)
        if r.status_code == 200 and self.empty in unquote_plus(str(request.url)):
            return httpx.Response(200, content=b"")
        return r


@pytest.mark.parametrize("empty", ["/sittingdays.html", "IW_FIELD_ADVANCE_PHRASE="])
def test_an_empty_page_is_could_not_check_not_no_sittings(empty):
    c = TASConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(EmptySite(empty).handler)),
                     today=date(2026, 10, 31))
    with pytest.raises(CouldNotCheck, match="empty page"):
        c.list_sitting_days(date(2026, 9, 1), date(2026, 10, 31))


def test_a_calendar_with_no_dates_is_could_not_check():
    def handler(request):
        if str(request.url).endswith("/robots.txt"):
            return httpx.Response(404)
        return httpx.Response(200, content=b"<html><body>Sitting days</body></html>")
    c = TASConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(handler)), today=date(2026, 10, 31))
    with pytest.raises(CouldNotCheck, match="no sitting dates"):
        c.list_sitting_days(date(2026, 9, 1), date(2026, 10, 31))


def test_next_years_calendar_not_up_yet_is_no_sittings_that_year():
    c = TASConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(Site().handler)), today=date(2026, 12, 20))
    days = c.list_sitting_days(date(2026, 12, 1), date(2027, 1, 31))   # 2027 calendar 404s
    assert {d.sitting_date for d in days} <= {date(2026, 12, d) for d in (1, 2, 3, 7, 8, 9, 10)}
    with pytest.raises(CouldNotCheck, match="HTTP 404"):               # but this year's must exist
        TASConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(Site().handler)),
                     today=date(2025, 6, 1))._year(2025)


def test_draft_flag_sections_topics_and_times(ha):
    assert ha.version == "proof" and ha.method == "docx"
    q = next(s for s in ha.speeches if s.debate_title == "Budget - Scale of Cuts")
    assert (q.speaker_name, kind(q), q.start_time) == ("Mr WILLIE", "question", "10:01")
    assert q.proceeding_type.startswith("QUESTIONS")


def test_question_time_supplementary_answers_and_points_of_order(ha):
    qt = [s for s in ha.speeches if s.debate_title == "Budget - Scale of Cuts" and kind(s) != "presiding"]
    assert [(s.speaker_name, kind(s)) for s in qt[:7]] == [
        ("Mr WILLIE", "question"), ("Mr ABETZ", "answer"), ("Mr WILLIE", "statement"), ("Mr ABETZ", "answer"),
        ("Mr Willie", "interjection"), ("Mr WILLIE", "question"), ("Mr ABETZ", "answer")]
    assert qt[1].speaker_role == "Treasurer" and qt[2].text.startswith("Point of order")


def test_council_headers_with_electorate_role_and_by_leave(lc):
    rattray = [s for s in lc.speeches if s.speaker_name == "Ms RATTRAY"]
    assert all(s.electorate == "McIntyre" for s in rattray if s.speaker_role)
    assert any(s.text.startswith("Mr President, I table the document") for s in rattray)   # "(by leave)" header
    palmer = next(s for s in lc.speeches if s.speaker_name == "Ms PALMER")
    assert kind(palmer) == "answer" and palmer.speaker_role == "Minister For Education"


def test_no_turn_header_left_in_text(ha, lc):
    for doc in (ha, lc):
        assert not [s for s in doc.speeches if re.search(r"(?:^|\n)(?:Mr|Ms|Mrs|Dr|Prof) [A-Z][\w’'\-]+ (?:\([^)]*\) )?- ", s.text)]
        assert not [s for s in doc.speeches if not s.speaker_name and "(procedural)" not in (s.proceeding_type or "")]


def test_member_lists_give_sides_for_nearly_every_turn(ha, lc):
    from pipeline.members import Enricher
    e = Enricher("TAS")
    for chamber, doc, floor in (("TAS-HA", ha, 0.99), ("TAS-LC", lc, 1.0)):
        turns = [s for s in doc.speeches if s.speaker_name and kind(s) != "presiding"]
        for s in turns:
            e.apply(chamber, SEP10, s)
        assert sum(1 for s in turns if s.speaker_side != "unknown") / len(turns) >= floor, chamber
    abetz = next(s for s in ha.speeches if s.speaker_name == "Mr ABETZ")
    willie = next(s for s in ha.speeches if s.speaker_name == "Mr WILLIE")
    assert (abetz.speaker_side, willie.speaker_side) == ("government", "opposition")
    rattray = next(s for s in lc.speeches if s.speaker_name == "Ms RATTRAY" and s.speaker_role)
    assert rattray.speaker_side == "government"   # "Leader for the Government in the Legislative Council"


def test_a_tasmanian_pdf_is_refused_clearly_rather_than_read_as_a_word_file():
    """The Parliament also publishes each day as a static PDF; importing one by hand must say
    plainly that its reader is still to be written, not fail inside the .docx unzipper."""
    c = TASConnector(None)
    ref = DocumentRef("TAS-LC", date(2026, 5, 21), "https://www.parliament.tas.gov.au/x.pdf", "pdf")
    with pytest.raises(NotImplementedError, match="daily Hansard PDF"):
        c.parse(b"%PDF-1.7 not a word file", ref, lambda u: b"")
    docx_ref = DocumentRef("TAS-HA", SEP10, "u", "docx")
    with pytest.raises(NotImplementedError):   # named .docx but not a Word file (e.g. a saved error page)
        c.parse(b"<html>challenge</html>", docx_ref, lambda u: b"")
    assert c.parse((FX / "TAS-HA" / "2026-09-10.docx").read_bytes(), docx_ref, lambda u: b"").method == "docx"
