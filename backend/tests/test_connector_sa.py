"""SA connector: the listing layer, which needs no fixture because every URL comes from the date.

No real South Australian document has been obtainable — hansardsearch.parliament.sa.gov.au answers
an Azure WAF challenge from this network (docs/sources.md §SA) — so the reader is still to be
written and these tests cover listing, blocking and refusal only. No network.

The two URL shapes asserted here were confirmed in the wild by public search, not inferred:
/daily/uh/2015-11-19/download/toc and /daily/uh/2025-02-06/extract/37/download.
"""
from datetime import date

import httpx
import pytest

from connectors.base import CouldNotCheck, DocumentRef, SittingDayRef, registry
from connectors.sa import SAConnector, extract_url, toc_url
from pipeline.fetch import Blocked, Fetcher

TUE = date(2026, 6, 9)       # both houses sat
WED = date(2026, 6, 10)      # the Council sat; the Assembly did not


class FixtureSite:
    """The day TOC endpoint: 9 June both houses, 10 June the Council only; all else 404."""

    def __init__(self):
        self.hits: list[tuple[str, str]] = []
        self.present = {toc_url("SA-HA", TUE), toc_url("SA-LC", TUE), toc_url("SA-LC", WED)}

    def handler(self, request):
        url = str(request.url)
        self.hits.append((request.method, url))
        if url.endswith("/robots.txt"):
            return httpx.Response(404)
        if url not in self.present:
            return httpx.Response(404)
        if request.method == "HEAD":
            return httpx.Response(200)
        return httpx.Response(200, content=b"<toc/>", headers={"Content-Type": "application/xml"})


@pytest.fixture
def site():
    return FixtureSite()


@pytest.fixture
def connector(site):
    return SAConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(site.handler)))


def test_every_url_comes_from_the_date_alone():
    assert toc_url("SA-LC", date(2015, 11, 19)) == \
        "https://hansardsearch.parliament.sa.gov.au/daily/uh/2015-11-19/download/toc"
    assert extract_url("SA-LC", date(2025, 2, 6), 37) == \
        "https://hansardsearch.parliament.sa.gov.au/daily/uh/2025-02-06/extract/37/download"
    assert toc_url("SA-HA", TUE) == "https://hansardsearch.parliament.sa.gov.au/daily/lh/2026-06-09/download/toc"


def test_sitting_days_are_found_by_probing_weekdays_per_house_without_downloading(connector, site):
    days = connector.list_sitting_days(date(2026, 6, 6), date(2026, 6, 12))   # Sat 6 – Fri 12
    assert days == [SittingDayRef("SA-HA", TUE), SittingDayRef("SA-LC", TUE), SittingDayRef("SA-LC", WED)]
    probes = [u for m, u in site.hits if m == "HEAD"]
    assert len(probes) == 10          # Mon–Fri x 2 houses; the weekend is not probed
    assert not any(m == "GET" and u.endswith("/toc") for m, u in site.hits)


def test_the_document_is_the_days_toc_and_a_house_that_did_not_sit_has_none(connector):
    [ref] = connector.list_documents(SittingDayRef("SA-LC", WED))
    assert ref == DocumentRef("SA-LC", WED, toc_url("SA-LC", WED), "xml", "unknown", "toc:SA-LC:2026-06-10", None)
    assert ref.citation_url is None   # the reader-facing day URL is not confirmed yet
    assert connector.list_documents(SittingDayRef("SA-HA", WED)) == []


def test_recent_days_stay_open_so_a_day_published_late_cannot_advance_the_watermark(connector):
    # SA publishes "after 4pm on the day following the sitting", so a fresh 404 is not "no sitting".
    assert connector.settled_through(date(2026, 10, 31)) == date(2026, 10, 28)


def test_a_probe_the_site_refuses_is_could_not_check_not_no_sittings():
    """The Azure WAF 403 must reach sync as blocked, and anything else as "could not check" —
    never as an empty calendar, which would move the watermark past real sitting days."""
    def answering(status, body=b""):
        def handler(request):
            if str(request.url).endswith("/robots.txt"):
                return httpx.Response(404)
            return httpx.Response(status, content=body)
        return SAConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(handler)))

    with pytest.raises(Blocked):
        answering(403, b"<html><head><title>Azure WAF</title></head></html>").list_sitting_days(TUE, TUE)
    with pytest.raises(CouldNotCheck, match="HTTP 500"):
        answering(500).list_sitting_days(TUE, TUE)


def test_the_reader_waits_for_a_real_toc_and_the_connector_is_not_registered_yet(connector):
    ref = DocumentRef("SA-HA", TUE, toc_url("SA-HA", TUE), "xml")
    with pytest.raises(NotImplementedError, match="real day TOC"):
        connector.parse(b"<toc/>", ref, lambda u: b"")
    assert "sa" not in registry()
