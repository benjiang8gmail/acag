"""WA connector: the listing layer, which needs no fixture because every URL comes from the date.

No real WA daily Hansard PDF has been obtainable — www.parliament.wa.gov.au answers an Azure WAF
challenge from this network (docs/sources.md §WA) — so the PDF reader is still to be written and
these tests cover listing, blocking and refusal only. No network.
"""
from datetime import date

import httpx
import pytest

from connectors.base import CouldNotCheck, DocumentRef, SittingDayRef, registry
from connectors.wa import WAConnector, daily_url
from pipeline.fetch import Blocked, Fetcher

TUE = date(2026, 6, 9)       # both houses sat
WED = date(2026, 6, 10)      # the Council sat; the Assembly did not


class FixtureSite:
    """The dated PDF endpoint: 9 June both houses, 10 June the Council only; all else 404."""

    def __init__(self):
        self.hits: list[tuple[str, str]] = []
        self.present = {daily_url("WA-LA", TUE), daily_url("WA-LC", TUE), daily_url("WA-LC", WED)}

    def handler(self, request):
        url = str(request.url)
        self.hits.append((request.method, url))
        if url.endswith("/robots.txt"):
            return httpx.Response(404)
        if url not in self.present:
            return httpx.Response(404)
        if request.method == "HEAD":
            return httpx.Response(200)
        return httpx.Response(200, content=b"%PDF-1.7 pretend", headers={"Content-Type": "application/pdf"})


def make(site, **kw):
    return WAConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(site.handler), **kw))


@pytest.fixture
def site():
    return FixtureSite()


@pytest.fixture
def connector(site):
    return make(site)


def test_every_url_comes_from_the_date_alone():
    assert daily_url("WA-LA", TUE) == "https://www.parliament.wa.gov.au/hansard/daily/lh/2026-06-09/pdf/download"
    assert daily_url("WA-LC", TUE) == "https://www.parliament.wa.gov.au/hansard/daily/uh/2026-06-09/pdf/download"


def test_sitting_days_are_found_by_probing_weekdays_per_house_without_downloading(connector, site):
    days = connector.list_sitting_days(date(2026, 6, 6), date(2026, 6, 12))   # Sat 6 – Fri 12
    assert days == [SittingDayRef("WA-LA", TUE), SittingDayRef("WA-LC", TUE), SittingDayRef("WA-LC", WED)]
    probes = [u for m, u in site.hits if m == "HEAD"]
    assert len(probes) == 10          # Mon–Fri x 2 houses; the weekend is not probed
    assert not any(m == "GET" and u.endswith("/download") for m, u in site.hits)


def test_documents_are_the_days_pdf_and_a_house_that_did_not_sit_has_none(connector):
    [ref] = connector.list_documents(SittingDayRef("WA-LC", WED))
    assert ref == DocumentRef("WA-LC", WED, daily_url("WA-LC", WED), "pdf", "unknown",
                              "pdf:WA-LC:2026-06-10", daily_url("WA-LC", WED))
    assert connector.list_documents(SittingDayRef("WA-LA", WED)) == []


def test_recent_days_stay_open_so_an_unpublished_day_cannot_advance_the_watermark(connector):
    assert connector.settled_through(date(2026, 10, 31)) == date(2026, 10, 28)


def test_a_probe_the_site_refuses_is_could_not_check_not_no_sittings():
    """An Azure WAF 403 must reach sync as blocked, and anything else as "could not check" —
    never as an empty calendar, which would move the watermark past real sitting days."""
    def answering(status, body=b""):
        def handler(request):
            if str(request.url).endswith("/robots.txt"):
                return httpx.Response(404)
            return httpx.Response(status, content=body)
        return WAConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(handler)))

    waf = answering(403, b"<html><head><title>Azure WAF</title></head></html>")
    with pytest.raises(Blocked):
        waf.list_sitting_days(TUE, TUE)

    with pytest.raises(CouldNotCheck, match="HTTP 500"):
        answering(500).list_sitting_days(TUE, TUE)


def test_the_reader_waits_for_a_real_pdf_and_the_connector_is_not_registered_yet(connector):
    ref = DocumentRef("WA-LA", TUE, daily_url("WA-LA", TUE), "pdf")
    with pytest.raises(NotImplementedError, match="real daily"):
        connector.parse(b"%PDF-1.7 pretend", ref, lambda u: b"")
    assert "wa" not in registry()
