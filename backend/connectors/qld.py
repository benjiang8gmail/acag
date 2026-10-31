"""Queensland Legislative Assembly (QLD-LA).

Source: documents.parliament.qld.gov.au (robots.txt 404, so no rules; docs/sources.md §0a).
The main site, with the sitting calendar, answers scripts with an Azure WAF challenge,
so sitting days are found from the documents host itself:

- Sitting days: a HEAD request for each weekday's
  `/events/han/{YYYY}/{YYYY_MM_DD}_DAILY.pdf` (200 = sat; 404 = no Record of
  Proceedings). A 404 on a recent day may only mean "not published yet", so the
  connector keeps re-checking the last SETTLE_DAYS days (`settled_through`).
  The Assembly does not sit at weekends; weekends are not probed.
- Document: the day's PDF (1 request), keyed `pdf:QLD-LA:{date}`. The cover reads
  "RECORD OF PROCEEDINGS (PROOF)" until the corrected version replaces it.
- Text: the PDF's own "Table of Contents" pages give the outline: capitalised entries
  are sections (QUESTIONS WITHOUT NOTICE), mixed-case entries are topics.
  Speaker headers print party: "Mr CRANDON (Coomera—LNP) (12.28 pm):".
- Speeches carry the printed page number from the running header and cite `PDF#page=N` at
  that page's place in the file (printed pages run on through the year).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, timedelta

from parsers.hansard_pdf import Heading, Rules, walk
from parsers.pdf import pdf_pages
from pipeline.fetch import Blocked, Fetcher

from .base import CouldNotCheck, DocumentRef, ParsedDocument, SittingDayRef

BASE = "https://documents.parliament.qld.gov.au/events/han"
SOURCE = "QLD-LA"
SETTLE_DAYS = 3
LOW_MATCH_NOTE = 0.9

_HON = r"(?:Mr|Ms|Mrs|Miss|Dr|Hon\.?)"
_UPTOK = r"(?:Mc|Mac)?[A-Z][A-Z'’\-]+"
# "Mr CRANDON", "Ms McMILLAN", "Mr de BRENNI", "Hon. AJ PERRETT", "Hon. G GRACE", "Hon. MC de BRENNI", "Mr B. JAMES"
_UPNAME = rf"{_HON}\s+(?:(?:[A-Z]{{1,3}}\.?|{_UPTOK})\s+)*(?:(?:de|van|von|di|da)\s+)?{_UPTOK}"
_TIME12 = r"(?P<h>\d{1,2})\.(?P<m>\d{2})\s*(?P<ap>am|pm)"
RE_TIME12 = re.compile(rf"^{_TIME12}$")
_TITLE_NAME = r"(?:Mr|Ms|Mrs|Miss|Dr) (?:[A-Z]\. )?(?:(?:de|van|von) )?[A-Z][a-z’'][\w’'\-]*(?:[ -][A-Z][\w’'\-]+)*"
_SURNAME = r"(?:[A-Z]\. )?(?:(?:de|van|von) )?[A-Z][\w’'\-]+"


def _fields(m: re.Match) -> dict | None:
    """'(Coomera—LNP) (Leader of the House) (11.16 am)' → electorate, party, role, time."""
    brackets = re.findall(r"\(([^()]*)\)", m.group("brackets") or "")
    if not brackets:
        return None
    out: dict = {}
    roles = []
    for b in (x.strip() for x in brackets):
        if t := RE_TIME12.match(b):
            h = int(t["h"]) % 12 + (12 if t["ap"] == "pm" else 0)
            out["time"] = f"{h:02d}:{t['m']}"
        elif "—" in b and "electorate" not in out:
            electorate, party = b.split("—", 1)
            out["electorate"], out["party"] = electorate.strip(), party.strip()
        else:
            roles.append(b)
    if roles:
        out["role"] = "; ".join(roles)
    return out


RULES = Rules(
    main=re.compile(rf"^(?P<name>{_UPNAME})\s*(?P<brackets>(?:\([^()]*\)\s*)*)(?P<tail>,[^:()]{{0,80}})?:\s*(?P<rest>.*)$"),
    open_header=re.compile(rf"^{_UPNAME}\s*(?:\([^()]*\)\s*)*\([^)]*$"),
    name_bracket=re.compile(rf"^{_UPNAME}\s*\("),
    office=re.compile(r"^(?P<office>(?:Mr|Madam|Mrs|Ms) (?:DEPUTY |ACTING |TEMPORARY )?SPEAKER)"
                      r"\s*(?:\((?P<who>[^)]*)\))?\s*:\s*(?P<rest>.*)$"),
    interjection=re.compile(rf"^(?P<name>{_TITLE_NAME})\s*:\s*(?P<rest>.*)$"),
    procedural=re.compile(
        r"^(?:Resolved in the (?:affirmative|negative)|Question put|Motion agreed to|Motion negatived"
        r"|Amendments? (?:agreed to|negatived)|Bill(?:, as amended,)? (?:read|agreed|passed)|Clauses? .{0,80}agreed to"
        r"|Debate, on motion of .{0,120}adjourned|Consideration in detail|Sitting suspended|The House adjourned"
        r"|Leave granted|Leave not granted)\b.{0,200}$"),
    division_start=re.compile(r"^Division: "),
    # "AYES, 52:", "LNP, 52—Baillie, Barounis, …", then comma-separated surname lines ending "," or "."
    division_line=re.compile(rf"^(?:(?:AYES|NOES|PAIRS)[, ]+\d+:?|[A-Za-z]+, \d+—.*|{_SURNAME}(?:, {_SURNAME})*[,.]?)$"),
    time=_TIME12,
    stage_direction=re.compile(r"^.{0,80} interjected\.$"),
    qa_by_order=re.compile(r"^QUESTIONS WITHOUT NOTICE$", re.I),
    max_header_lines=5,   # ministers' titles can run over several lines
    ignore_line=re.compile(r"^_{3,}$"),
    header_fields=lambda m, rules: _fields(m),
)
NOT_HEADINGS = ("Tabled paper", "Division:", "Resolved in the", "ATTENDANCE")
RE_TIME_FIRST = re.compile(r"^\(\d{1,2}\.\d{2}\s*[ap]m\):")
RE_DATE_LINE = re.compile(r"^\d{1,2} [A-Z][a-z]{2} \d{4}$")
RE_PAGE_LINE = re.compile(r"^\d{1,5}$")
RE_CONTENTS_TITLE = re.compile(r"^Table of Contents\b")
RE_CONTENTS_ENTRY = re.compile(r"^(?P<title>.*?)\s*\.{2,}\s*(?P<page>\d{1,5})$")


def daily_url(d: date) -> str:
    return f"{BASE}/{d.year}/{d.strftime('%Y_%m_%d')}_DAILY.pdf"


class QLDConnector:
    code = "QLD"
    source_ids = (SOURCE,)

    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher
        self._found: dict[date, bool] = {}

    def settled_through(self, today: date) -> date:
        return today - timedelta(days=SETTLE_DAYS)

    # ---- listing ------------------------------------------------------------

    def _exists(self, d: date) -> bool:
        if d not in self._found:
            try:
                status = self.fetcher.head(daily_url(d))
            except Blocked:
                raise
            except Exception as e:
                raise CouldNotCheck(f"QLD Record of Proceedings for {d}: {e.__class__.__name__}: {e}") from e
            if status not in (200, 404):
                raise CouldNotCheck(f"QLD Record of Proceedings for {d}: HTTP {status}")
            self._found[d] = status == 200
        return self._found[d]

    def list_sitting_days(self, start: date, end: date) -> list[SittingDayRef]:
        days, d = [], start
        while d <= end:
            if d.weekday() < 5 and self._exists(d):
                days.append(SittingDayRef(SOURCE, d))
            d += timedelta(days=1)
        return days

    def list_documents(self, day: SittingDayRef) -> list[DocumentRef]:
        if not self._exists(day.sitting_date):
            return []
        url = daily_url(day.sitting_date)
        return [DocumentRef(SOURCE, day.sitting_date, url=url, format="pdf", version_hint=day.version_hint,
                            key=f"pdf:{SOURCE}:{day.sitting_date.isoformat()}", citation_url=url)]

    # ---- parsing ------------------------------------------------------------

    def parse(self, raw: bytes, ref: DocumentRef, fetch_part: Callable[[str], bytes]) -> ParsedDocument:
        pages = pdf_pages(raw)
        proof = "(PROOF)" in (pages[0] if pages else "")
        contents = [i for i, p in enumerate(pages[:12]) if RE_CONTENTS_TITLE.match(p.strip())]
        first_body = (contents[-1] + 1) if contents else 1

        lines: list[tuple[int, str]] = []
        printed: list[int] = []
        pdf_page: dict[int, int] = {}   # printed page → page in the PDF file
        for i in range(first_body, len(pages)):
            body = [l.strip() for l in pages[i].splitlines() if l.strip()]
            head, page = body[:3], None
            if sum(1 for l in head if RE_DATE_LINE.match(l)) == 1 and sum(1 for l in head if RE_PAGE_LINE.match(l)) == 1:
                page = int(next(l for l in head if RE_PAGE_LINE.match(l)))
                body = body[3:]   # date, page number and the running title (section or "Legislative Assembly")
            page = page or (printed[-1] + 1 if printed else i + 1)
            printed.append(page)
            pdf_page.setdefault(page, i + 1)
            if "ATTENDANCE" in body:   # the closing roll of members present: not speech
                lines.extend((page, l) for l in body[:body.index("ATTENDANCE")])
                break
            lines.extend((page, l) for l in body)

        # pdfminer occasionally prints a header's time ahead of the name:
        # "(3.12 pm): Listening" / "Mr McCALLUM (Bundamba—ALP)". Put them back in order.
        for i in range(len(lines) - 1):
            if RE_TIME_FIRST.match(lines[i][1]) and RULES.name_bracket.match(lines[i + 1][1]) \
                    and ":" not in lines[i + 1][1]:
                lines[i], lines[i + 1] = lines[i + 1], lines[i]

        # The contents start on the cover, below "Subject / Page", and continue on "Table of Contents" pages.
        cover_contents = re.split(r"\nSubject\s*\n\s*Page\s*\n", pages[0], maxsplit=1)[1:] if pages else []
        outline = contents_outline(cover_contents + [pages[i] for i in contents],
                                   (min(printed, default=0), max(printed, default=0)))
        speeches, matched, total = walk(lines, outline, RULES, {}, ref.citation_url, min_matched=None, pdf_page=pdf_page)
        doc = ParsedDocument(speeches=speeches, version="proof" if proof else "final", method="pdf")
        if total and matched / total < LOW_MATCH_NOTE:
            doc.note = f"only {matched} of {total} contents headings found in the text; debate titles may be incomplete"
        return doc


def contents_outline(pages: list[str], page_range: tuple[int, int]) -> list[Heading]:
    """Capitalised entries are sections; mixed-case entries under them are topics.
    A section with no topics becomes a topic itself. Notes that the contents list but the
    body doesn't print as headings ("Tabled paper:", "Division:", the attendance roll) are skipped."""
    entries, pending = [], ""
    lo, hi = page_range
    for text in pages:
        pending = ""   # an unfinished entry at the foot of a page is page furniture (e.g. the cover's sign-off)
        for line in (l.strip() for l in text.splitlines() if l.strip()):
            if RE_CONTENTS_TITLE.match(line):
                continue
            joined = f"{pending} {line}".strip() if pending else line
            m = RE_CONTENTS_ENTRY.match(joined)
            if m and lo <= int(m["page"]) <= hi:
                entries.append(re.sub(r"\s+", " ", m["title"]).strip(" ."))
                pending = ""
            else:
                pending = joined
    outline: list[Heading] = []
    section = None
    entries = [t for t in entries if not t.startswith(NOT_HEADINGS)]
    for i, title in enumerate(entries):
        letters = re.sub(r"[^A-Za-z]", "", title)
        if letters and letters.isupper():
            section = title
            nxt = entries[i + 1] if i + 1 < len(entries) else ""
            nxt_letters = re.sub(r"[^A-Za-z]", "", nxt)
            if nxt and not nxt_letters.isupper():
                outline.append(Heading("proceeding", title))
            else:
                outline.append(Heading("topic", title, title))
        else:
            outline.append(Heading("topic", title, section))
    return outline
