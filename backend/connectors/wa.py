"""Parliament of Western Australia: Legislative Assembly (WA-LA) and Legislative Council (WA-LC).

`www.parliament.wa.gov.au` answers every path with HTTP 403 from an Azure WAF (the page titles
itself "Azure WAF"), including `robots.txt` and the PDF endpoint below, so nothing is reachable
from the build network and the source is marked blocked there (docs/sources.md §WA, re-checked
31 Oct 2026). From a network the site serves, this connector needs nothing else: unlike Victoria,
every URL is derived from the date alone.

- **Sitting days:** a HEAD request for each weekday's full-day PDF (200 = sat, 404 = no sitting),
  as for Queensland. The sitting calendar is behind the same WAF, and this needs no listing page.
  A 404 on a recent day may only mean "not published yet", so the last SETTLE_DAYS days keep being
  re-checked (`settled_through`), and the watermark does not run past them.
- **Document:** `/hansard/daily/{lh|uh}/{YYYY-MM-DD}/pdf/download`, the whole day in one PDF,
  keyed `pdf:{source}:{date}`. `lh` is the Assembly, `uh` the Council.
- **Proof/final:** the day's PDF is published within about 3 hours of the house rising and carries
  "uncorrected draft — not to be quoted or distributed" until it is corrected, so the version is
  read from the document itself once the reader exists.
- **Not covered here:** estimates committees (`esta`, `estb`) and the pre-Nov-2024 system, which
  is one PDF per date in the old Lotus Domino site.

The PDF reader is written and tested against the first real WA daily PDF (spec D6: no stand-in
fixtures). Until then `parse` says so, and the connector is not in `registry()`.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

from pipeline.fetch import Blocked, Fetcher

from .base import CouldNotCheck, DocumentRef, ParsedDocument, SittingDayRef

BASE = "https://www.parliament.wa.gov.au/hansard/daily"
HOUSE = {"WA-LA": "lh", "WA-LC": "uh"}
SETTLE_DAYS = 3


def daily_url(source_id: str, d: date) -> str:
    return f"{BASE}/{HOUSE[source_id]}/{d.isoformat()}/pdf/download"


class WAConnector:
    code = "WA"
    source_ids = tuple(HOUSE)

    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher
        self._found: dict[tuple[str, date], bool] = {}

    def settled_through(self, today: date) -> date:
        return today - timedelta(days=SETTLE_DAYS)

    # ---- listing ------------------------------------------------------------

    def _exists(self, source_id: str, d: date) -> bool:
        key = (source_id, d)
        if key not in self._found:
            try:
                status = self.fetcher.head(daily_url(source_id, d))
            except Blocked:
                raise
            except Exception as e:
                raise CouldNotCheck(f"WA daily Hansard {source_id} for {d}: {e.__class__.__name__}: {e}") from e
            if status not in (200, 404):
                raise CouldNotCheck(f"WA daily Hansard {source_id} for {d}: HTTP {status}")
            self._found[key] = status == 200
        return self._found[key]

    def list_sitting_days(self, start: date, end: date) -> list[SittingDayRef]:
        days, d = [], start
        while d <= end:
            if d.weekday() < 5:   # neither house sits at weekends
                days += [SittingDayRef(sid, d) for sid in HOUSE if self._exists(sid, d)]
            d += timedelta(days=1)
        return days

    def list_documents(self, day: SittingDayRef) -> list[DocumentRef]:
        if not self._exists(day.source_id, day.sitting_date):
            return []
        url = daily_url(day.source_id, day.sitting_date)
        return [DocumentRef(day.source_id, day.sitting_date, url=url, format="pdf",
                            version_hint=day.version_hint,
                            key=f"pdf:{day.source_id}:{day.sitting_date.isoformat()}", citation_url=url)]

    # ---- parsing ------------------------------------------------------------

    def parse(self, raw: bytes, ref: DocumentRef, fetch_part: Callable[[str], bytes]) -> ParsedDocument:
        raise NotImplementedError("Western Australia's PDF reader is written against the first real daily "
                                  "Hansard PDF; none could be obtained from the build network, where the "
                                  "site answers an Azure WAF challenge (docs/sources.md §WA)")
