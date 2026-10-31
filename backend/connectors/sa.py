"""Parliament of South Australia: House of Assembly (SA-HA, `lh`) and Legislative Council (SA-LC, `uh`).

`hansardsearch.parliament.sa.gov.au`, where every document lives, answers each path with HTTP 403
from an Azure WAF (the page titles itself "Azure WAF") — `robots.txt`, the documented OpenAPI at
`/docs/api` and a real daily URL alike. So nothing is reachable from the build network and the
source is marked blocked there. `www.parliament.sa.gov.au` *is* reachable, but it carries only a
description of Hansard and links to that subdomain (docs/sources.md §SA, checked 31 Oct 2026).

From a network the site serves, this connector needs no listing page, because the day's table of
contents is addressed by date alone. Both URL shapes below are confirmed in the wild by public
search, not inferred:

- **Sitting days:** a HEAD request for each weekday's day TOC (200 = sat, 404 = no sitting), as for
  Queensland and WA. Hansard is published "after 4pm on the day following the sitting", so a 404 on
  a recent day may only mean "not out yet": the last SETTLE_DAYS days keep being re-checked
  (`settled_through`) and the watermark does not run past them.
- **Document:** `/daily/{lh|uh}/{YYYY-MM-DD}/download/toc`, the day's table of contents as XML,
  keyed `toc:{source}:{date}`. It lists the day's subjects, which are fetched as parts.
- **Parts:** `/daily/{lh|uh}/{YYYY-MM-DD}/extract/{n}/download`, one per subject, as for the NSW
  topic fragments. The numbering is the subject order within the day.
- **Terms:** copyright is held by the Attorney-General of SA; excerpts must be attributed, fair and
  accurate. The site asks that its APIs be used responsibly, so the usual spacing applies.

Not yet known, because no real South Australian file has been obtainable here: the TOC's own
element names, and the reader-facing day URL that speeches should cite (the per-subject pages are
`/daily/{house}/{date}/{n}`, so the anchor is expected to come from the TOC's subject numbers).
The reader is therefore written against the first real TOC (spec D6: no stand-in fixtures); until
then `parse` says so and the connector is not in `registry()`.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

from pipeline.fetch import Blocked, Fetcher

from .base import CouldNotCheck, DocumentRef, ParsedDocument, SittingDayRef

BASE = "https://hansardsearch.parliament.sa.gov.au/daily"
HOUSE = {"SA-HA": "lh", "SA-LC": "uh"}
SETTLE_DAYS = 3


def toc_url(source_id: str, d: date) -> str:
    return f"{BASE}/{HOUSE[source_id]}/{d.isoformat()}/download/toc"


def extract_url(source_id: str, d: date, n: int) -> str:
    return f"{BASE}/{HOUSE[source_id]}/{d.isoformat()}/extract/{n}/download"


class SAConnector:
    code = "SA"
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
                status = self.fetcher.head(toc_url(source_id, d))
            except Blocked:
                raise
            except Exception as e:
                raise CouldNotCheck(f"SA Hansard {source_id} for {d}: {e.__class__.__name__}: {e}") from e
            if status not in (200, 404):
                raise CouldNotCheck(f"SA Hansard {source_id} for {d}: HTTP {status}")
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
        # citation_url is left unset: the reader-facing day URL is not confirmed, and speech
        # anchors are expected to be /daily/{house}/{date}/{n} from the TOC's subject numbers.
        return [DocumentRef(day.source_id, day.sitting_date, url=toc_url(day.source_id, day.sitting_date),
                            format="xml", version_hint=day.version_hint,
                            key=f"toc:{day.source_id}:{day.sitting_date.isoformat()}")]

    # ---- parsing ------------------------------------------------------------

    def parse(self, raw: bytes, ref: DocumentRef, fetch_part: Callable[[str], bytes]) -> ParsedDocument:
        raise NotImplementedError("South Australia's reader is written against the first real day TOC; "
                                  "none could be obtained from the build network, where the site answers "
                                  "an Azure WAF challenge (docs/sources.md §SA)")
