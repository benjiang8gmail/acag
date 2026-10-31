"""Parliament of Victoria: Legislative Assembly (VIC-LA) and Legislative Council (VIC-LC).

Where things stand (re-checked 31 Oct 2026, docs/sources.md §VIC):

- www.parliament.vic.gov.au, which lists the sitting days (Browse Hansard) and serves the daily
  PDFs, answers scripts with HTTP 403 from Cloudflare, even for robots.txt. The polite fetcher
  treats that as blocked and does not try again in the run.
- hansard.parliament.vic.gov.au is the Hansard search engine only, and its robots.txt disallows
  the search and result paths (`/search/`, `/isysquery/`), so it is not used.
- The web archives that might hold copies either run their own bot check (the National
  Library's) or are unreachable from the build network (Internet Archive, Common Crawl).

So, as for the NT, the sitting days come from a staff-kept list, `config/vic_hansard.yaml`: one
line per chamber and sitting day with the PDF link as shown on Browse Hansard
(https://www.parliament.vic.gov.au/parliamentary-activity/hansard/hansard-debate). From a network
the Parliament's site accepts (the pilot's Australian office), the scanner fetches those PDFs
through the polite fetcher. From a blocked network the source is marked blocked. Files downloaded
by hand go in with `make import` (spec §9.11) and need no listing at all.

The PDF link has the shape `/{cache}/globalassets/hansard-daily-pdfs/hansard-{house}-{docid}/
hansard-{house}-{docid}.pdf` (house 2145855009 = Assembly, 974425065 = Council); the `{cache}`
segment changes between crawls, so links are copied from the page, never built.

The PDF reader itself is written and tested against the first real daily PDF (spec D6: no
stand-in fixtures). Until then `parse` says so.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from urllib.parse import urlsplit

import yaml

from app.config import REPO_ROOT

from .base import DocumentRef, ParsedDocument, SittingDayRef

DAYS_FILE = REPO_ROOT / "config" / "vic_hansard.yaml"
HOST = "www.parliament.vic.gov.au"
HOUSES = {"VIC-LA": "2145855009", "VIC-LC": "974425065"}
BROWSE_URL = f"https://{HOST}/parliamentary-activity/hansard/hansard-debate"


def known_days(path=DAYS_FILE) -> list[dict]:
    """The listed days, validated: chamber, date, an https link on the Parliament's own host."""
    data = yaml.safe_load(path.read_text()) if path.exists() else None
    out = []
    for i, row in enumerate((data or {}).get("days") or []):
        chamber = row.get("chamber")
        if chamber not in HOUSES:
            raise ValueError(f"vic_hansard.yaml day {i + 1}: chamber must be one of {sorted(HOUSES)}")
        pdf = str(row.get("pdf") or "")
        parts = urlsplit(pdf)
        if parts.scheme != "https" or parts.netloc != HOST or not parts.path.lower().endswith(".pdf"):
            raise ValueError(f"vic_hansard.yaml day {i + 1}: pdf must be an https PDF link on {HOST}, got {pdf!r}")
        when = row.get("date")
        when = when if isinstance(when, date) else date.fromisoformat(str(when))
        proof = row.get("proof")
        out.append({"chamber": chamber, "date": when, "pdf": pdf,
                    "version": "unknown" if proof is None else ("proof" if proof else "final")})
    return out


class VICConnector:
    code = "VIC"
    source_ids = tuple(HOUSES)

    def __init__(self, fetcher):
        self.fetcher = fetcher

    def list_sitting_days(self, start: date, end: date) -> list[SittingDayRef]:
        return [SittingDayRef(d["chamber"], d["date"], d["version"])
                for d in sorted(known_days(), key=lambda d: (d["date"], d["chamber"])) if start <= d["date"] <= end]

    def list_documents(self, day: SittingDayRef) -> list[DocumentRef]:
        for d in known_days():
            if d["chamber"] == day.source_id and d["date"] == day.sitting_date:
                return [DocumentRef(day.source_id, day.sitting_date, url=d["pdf"], format="pdf",
                                    version_hint=d["version"], key=f"pdf:{day.source_id}:{day.sitting_date.isoformat()}",
                                    citation_url=d["pdf"])]
        return []

    def parse(self, raw: bytes, ref: DocumentRef, fetch_part: Callable[[str], bytes]) -> ParsedDocument:
        raise NotImplementedError("Victoria's PDF reader is written against the first real daily Hansard PDF; "
                                  "none could be obtained from the build network (docs/sources.md §VIC)")
