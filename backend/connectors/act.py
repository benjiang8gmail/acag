"""ACT Legislative Assembly (ACT-LA).

Source: hansard.act.gov.au (robots.txt allows everything; docs/sources.md §0a).

- Sitting days: the year index `/hansard/{assembly}/{yyyy}/debates(PDF).htm`, one
  cell per day with the PDF link and its page range. Green rows and "P" page
  numbers are proofs. Days that sat but aren't published yet have an empty link;
  they are listed with no document so the sync holds its watermark before them.
- Document: the day's PDF (1 request), keyed `pdf:ACT-LA:{date}` because the file
  name changes between proof and official versions.
- Text: the PDF's own contents pages give the outline of headings (indentation
  shows which entries sit under "Questions without notice:" and similar groups).
  Speeches cite `PDF#page=N`, using the printed page number from each page footer.
- Party is not printed in ACT Hansard; speaker side comes from a member map later.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, datetime

import httpx

from parsers.hansard_pdf import Heading, Rules, walk
from parsers.pdf import pdf_layout_lines, pdf_pages
from pipeline.fetch import Blocked, Fetcher

from .base import CouldNotCheck, DocumentRef, ParsedDocument, SittingDayRef

BASE = "https://www.hansard.act.gov.au/hansard"
ASSEMBLY = "11th-assembly"   # elected Oct 2024; change after the Oct 2028 election
SOURCE = "ACT-LA"
LOW_MATCH_NOTE = 0.9

RE_DAY_CELL = re.compile(r'<td>\s*<a\s+href="(?P<href>[^"]*)"\s*>\s*(?P<day>\d{1,2})\s+(?P<month>[A-Z][a-z]+)\s*</a>\s*'
                         r'<br\s*/?>\s*<span[^>]*>\s*(?P<pages>[^<]*?)\s*</span>')

_HON = r"(?:MR|MS|MRS|MISS|DR)"
_UPTOK = r"[A-Z][A-Z'’\-]+"
_UPNAME = rf"{_HON}\s+{_UPTOK}(?:\s+{_UPTOK})*"
_TIME = r"\d{1,2}[:.]\d{2}"
_NAME_TOK = r"[A-Z][A-Za-z’'\-]+"
RULES = Rules(
    main=re.compile(rf"^(?P<name>{_UPNAME})\s*(?:\((?P<inner>[^()]*(?:\([^()]*\)[^()]*)*)\))?\s*"
                    rf"(?:\((?P<time>{_TIME})\))?\s*(?P<sep>:|—)\s*(?P<rest>.*)$"),
    open_header=re.compile(rf"^{_UPNAME}\s*\([^)]*$"),
    name_bracket=re.compile(rf"^{_UPNAME}\s*\("),
    office=re.compile(rf"^(?P<office>(?:MR|MADAM) (?:ASSISTANT |DEPUTY |TEMPORARY |ACTING )?SPEAKER)"
                      rf"\s*(?:\((?P<who>[^)]*)\))?\s*(?:\((?P<time>{_TIME})\))?\s*:\s*(?P<rest>.*)$"),
    interjection=re.compile(r"^(?P<name>(?:Mr|Ms|Mrs|Miss|Dr) [A-Z][a-z’'][\w’'\-]*(?:[ -][A-Z][\w’'\-]+)*)\s*:\s*(?P<rest>.*)$"),
    procedural=re.compile(
        r"^(?:Question (?:resolved|put|agreed|negatived)|Motion(?: \(.{0,80}\))? (?:agreed to|negatived|withdrawn)"
        r"|Debate(?: \(.{0,80}\))? (?:adjourned|resumed|interrupted)|Bill(?:,.{0,40})? agreed to"
        r"|Clauses? .{0,80}agreed to|Leave granted|Ordered that|Sitting suspended|The Assembly adjourned"
        r"|Proposed new clauses?|Amendments? (?:agreed to|negatived)|Detail stage)\b.{0,200}$"),
    division_start=re.compile(r"^The Assembly voted—$"),
    # "Ayes, 16" then full names, sometimes two to a line ("Andrew Braddock Michael Pettersson").
    division_line=re.compile(rf"^(?:(?:Ayes|Noes),?\s*\d+|{_NAME_TOK}(?: {_NAME_TOK}){{1,3}}(?: {_NAME_TOK}(?: {_NAME_TOK}){{1,3}})?)$"),
    time=_TIME,
    stage_direction=re.compile(r"^.{0,80} interjecting—$"),
    qa_by_order=re.compile(r"^Questions without notice$", re.I),
    max_header_lines=4,
    ignore_line=re.compile(r"^Ministerial statements?$"),
    reply_header=re.compile(r"^(?P<name>(?:Mr|Ms|Mrs|Miss|Dr) [A-Z][\w’'\-]+(?: [A-Z][\w’'\-]+)*) \(in reply to [^)]*\):\s*(?P<rest>.*)$"),
)
RE_HEADER_LINE = re.compile(r"^(?:Legislative Assembly for the ACT|(?:\w+day, )?\d{1,2} \w+ \d{4})$")
RE_FOOTER_LINE = re.compile(r"^(?:PROOF|P?(?P<page>\d{1,5}))$")
RE_CONTENTS_ENTRY = re.compile(r"^(?P<title>.*?)(?:\s*\.{2,}\s*|\s+)(?P<page>\d{1,5})$")


def _proceeding_for(title: str) -> str | None:
    t = title.lower()
    if "ministerial statement" in t:
        return "Ministerial statements"
    if re.search(r"\bbill \d{4}", t):
        return "Bills"
    if "committee" in t:
        return "Committees"
    return None


class ACTConnector:
    code = "ACT"
    source_ids = (SOURCE,)

    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher
        self._years: dict[int, dict[date, tuple[str | None, str]]] = {}

    # ---- listing ------------------------------------------------------------

    def _year(self, year: int) -> dict[date, tuple[str | None, str]]:
        if year not in self._years:
            url = f"{BASE}/{ASSEMBLY}/{year}/debates(PDF).htm"
            try:
                html = self.fetcher.fetch(url).body.decode("utf-8", "replace")
            except Blocked:
                raise
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:   # the index appears with the year's first sitting
                    self._years[year] = {}
                    return self._years[year]
                raise CouldNotCheck(f"ACT index for {year}: HTTP {e.response.status_code}") from e
            except Exception as e:
                raise CouldNotCheck(f"ACT index for {year}: {e.__class__.__name__}: {e}") from e
            days = {}
            for m in RE_DAY_CELL.finditer(html):
                when = datetime.strptime(f"{m['day']} {m['month']} {year}", "%d %B %Y").date()
                href = m["href"].strip() or None
                version = "proof" if m["pages"].startswith("P") else "final" if href else "unknown"
                days[when] = (href, version)
            self._years[year] = days
        return self._years[year]

    def list_sitting_days(self, start: date, end: date) -> list[SittingDayRef]:
        return [SittingDayRef(SOURCE, d, version) for year in range(start.year, end.year + 1)
                for d, (_, version) in sorted(self._year(year).items()) if start <= d <= end]

    def list_documents(self, day: SittingDayRef) -> list[DocumentRef]:
        href, version = self._year(day.sitting_date.year).get(day.sitting_date, (None, "unknown"))
        if not href:
            return []   # sat, but not published yet
        return [DocumentRef(SOURCE, day.sitting_date, url=href, format="pdf", version_hint=version,
                            key=f"pdf:{SOURCE}:{day.sitting_date.isoformat()}", citation_url=href)]

    # ---- parsing ------------------------------------------------------------

    def parse(self, raw: bytes, ref: DocumentRef, fetch_part: Callable[[str], bytes]) -> ParsedDocument:
        pages = pdf_pages(raw)
        first = next((i for i, p in enumerate(pages) if "Legislative Assembly for the ACT" in p), 1)
        cover = pages[0] if pages else ""

        lines: list[tuple[int, str]] = []
        printed: list[int] = []
        proof = "EDITED PROOF TRANSCRIPT" in cover
        for i in range(first, len(pages)):
            body = [l.strip() for l in pages[i].splitlines() if l.strip()]
            while body and RE_HEADER_LINE.match(body[0]):
                body.pop(0)
            page = None
            while body and (m := RE_FOOTER_LINE.match(body[-1])):
                if m["page"]:
                    page = int(m["page"])
                else:
                    proof = True
                body.pop()
            page = page or (printed[-1] + 1 if printed else i + 1)
            printed.append(page)
            lines.extend((page, l) for l in body)

        outline = contents_outline(raw, list(range(1, first)), (min(printed, default=0), max(printed, default=0)))
        speeches, matched, total = walk(lines, outline, RULES, {}, ref.citation_url, min_matched=None)
        doc = ParsedDocument(speeches=speeches, version="proof" if proof else "final", method="pdf")
        if total and matched / total < LOW_MATCH_NOTE:
            doc.note = f"only {matched} of {total} contents headings found in the text; debate titles may be incomplete"
        return doc


def contents_outline(raw: bytes, pages: list[int], page_range: tuple[int, int]) -> list[Heading]:
    """The PDF's contents pages as an outline. Entries end with a page number; a line ending in
    ":" starts a group (e.g. "Questions without notice:"), and indented entries belong to it."""
    if not pages:
        return []
    rows = [(x, t) for _, x, t in pdf_layout_lines(raw, pages) if not RE_HEADER_LINE.match(t)]
    if not rows:
        return []
    left = min(x for x, _ in rows)
    outline: list[Heading] = []
    group: str | None = None
    pending: tuple[float, str] | None = None
    lo, hi = page_range
    for x, text in rows:
        if pending:
            x, text = pending[0], f"{pending[1]} {text}"
        m = RE_CONTENTS_ENTRY.match(text)
        if m and lo <= int(m["page"]) <= hi:
            title = m["title"].strip(" .")
            if x <= left + 5:
                group = None
            outline.append(Heading("topic", title, group or _proceeding_for(title) or title))
            pending = None
        elif text.endswith(":"):   # a group, top-level ("Questions without notice:") or nested
            group = text[:-1].strip()
            outline.append(Heading("proceeding", group))
            pending = None
        else:
            pending = (x, text)
    return outline
