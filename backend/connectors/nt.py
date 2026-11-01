"""Legislative Assembly of the Northern Territory (NT-LA).

The Parliament's site (parliament.nt.gov.au) answers scripts with a Cloudflare challenge.
Its Hansard is published in Territory Stories (Library & Archives NT, CC BY 4.0), whose
robots.txt disallows `*.pdf`, `/search/` and `/api/` except `/api/content` and
`/api/full_record`. So this connector uses only those two endpoints:

- Sitting days: `config/nt_hansard.yaml`, one line per day with its Territory Stories
  handle. Territory Stories offers no allowed way to list a collection (search is
  disallowed; its sitemaps are unordered and carry no titles), so staff add each new
  day's handle until the Parliament's own listing is reachable from the pilot network.
- Document: `/api/full_record?handle=…` (title, date, page count, licence), keyed
  `ts:NT-LA:{date}`. "Draft Daily Hansard" = proof; "Debates and Questions" = final.
  Whether it changed is decided by `fingerprint`, not the raw bytes: every response embeds
  recommendations, scores and a query time that differ from one request to the next.
- Text: `/api/content?handle=…&page=N` for each page (about 80 per day), via fetch_part.
  The text layer drops apostrophes and dashes ("governments commitment"), so quotes
  match this text, not always the PDF to the letter.
- Speeches cite the Territory Stories record (https://hdl.handle.net/10070/…) and page.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import date
from urllib.parse import quote

import yaml

from app.config import REPO_ROOT
from parsers.hansard_pdf import Heading, Rules, walk

from .base import DocumentRef, ParsedDocument, SittingDayRef

SOURCE = "NT-LA"
DAYS_FILE = REPO_ROOT / "config" / "nt_hansard.yaml"
API = "https://territorystories.nt.gov.au/api"

_UPTOK = r"(?:Mc|Mac)?[A-Z][A-Z'’\-]+"
_UPNAME = rf"(?:Mr|Ms|Mrs|Miss|Dr)\s+(?:[A-Z]{{1,3}}\.?\s+)?{_UPTOK}(?:\s+{_UPTOK})*"
_OFFICES = r"(?:DEPUTY )?CHIEF MINISTER|MINISTER FOR [A-Z ,&’'\-]+|ATTORNEY-GENERAL[A-Z ,&’'\-]*|TREASURER"
RULES = Rules(
    main=re.compile(rf"^(?P<name>{_UPNAME}|{_OFFICES})\s*(?:\((?P<inner>[^()]*)\))?\s*(?P<time>)(?P<sep>:)\s*(?P<rest>.*)$"),
    open_header=re.compile(rf"^{_UPNAME}\s*\([^)]*$"),
    name_bracket=re.compile(rf"^{_UPNAME}\s*\("),
    office=re.compile(r"^(?P<office>(?:Madam|Mr) (?:DEPUTY )?SPEAKER)\s*(?:\((?P<who>[^)]*)\))?\s*:\s*(?P<rest>.*)$"),
    interjection=re.compile(r"^(?P<name>(?:Mr|Ms|Mrs|Miss|Dr) [A-Z][a-z’'][\w’'\-]*(?:[ -][A-Z][\w’'\-]+)*|Members|A member|Government members|Opposition members)\s*:\s*(?P<rest>.*)$"),
    procedural=re.compile(r"^(?:Motion agreed to|Motion negatived|Question agreed to|Question negatived|Bill read|Debate adjourned"
                          r"|Madam Speaker .{0,60}took the Chair|Mr Speaker .{0,60}took the Chair|The Assembly adjourned|Leave granted"
                          r"|Ordered that|Amendments? (?:agreed to|negatived))\b.{0,200}$"),
    division_start=re.compile(r"^The Assembly divided"),
    division_line=re.compile(r"^(?:(?:Ayes|Noes)\s*\d*|(?:(?:Mr|Ms|Mrs|Miss|Dr) [A-Z][\w’'\-]+\s*)+)$"),
    time=r"$^",   # NT headers carry no time
    stage_direction=None,
    header_fields=lambda m, rules: _fields(m),
    qa_by_order=re.compile(r"^QUESTION TIME$"),
)
RE_QUESTION = re.compile(rf"^(?P<name>{_UPNAME}) to (?P<office>[A-Z][A-Z ,&’'\-]+)$")


def _fields(m: re.Match) -> dict | None:
    """'(Gwoja)' is an electorate; '(Health)' is a minister's portfolio."""
    inner = (m.group("inner") or "").strip()
    if not inner:
        return None
    if inner.startswith("question to "):
        return {}                                          # a question in Question Time
    if inner == "answer":
        return {"role": m.group("name").title()}           # answered by the office asked ("Chief Minister")
    if inner.lower() in _electorates():
        return {"electorate": inner}
    if re.search(r"Opposition|Shadow|Leader|Whip|Speaker", inner):
        return {"role": inner}                             # "(Opposition Leader)"
    return {"role": f"Minister ({inner})"}                 # "(Health)": ministers are styled by portfolio


def _electorates() -> set[str]:
    from pipeline.members import MemberIndex
    return {(mm.get("electorate") or "").lower() for mm in MemberIndex("NT").by_chamber.get(SOURCE, [])}
RE_PAGE_HEADER = re.compile(r"^Daily Hansard\b.*Meeting No \d+$|^(?:Draft )?Debates and Questions\b.*$")
RE_PAGE_NO = re.compile(r"^\d{1,4}$")
RE_HEADING = re.compile(r"^[A-Z0-9][A-Z0-9 ,’'&()\-–—/:.]{3,}$")


def known_days() -> dict[date, str]:
    data = yaml.safe_load(DAYS_FILE.read_text()) if DAYS_FILE.exists() else None
    return {date.fromisoformat(str(d["date"])): str(d["handle"]) for d in (data or {}).get("days") or []}


class NTConnector:
    code = "NT"
    source_ids = (SOURCE,)

    def __init__(self, fetcher):
        self.fetcher = fetcher

    def list_sitting_days(self, start: date, end: date) -> list[SittingDayRef]:
        return [SittingDayRef(SOURCE, d) for d in sorted(known_days()) if start <= d <= end]

    def list_documents(self, day: SittingDayRef) -> list[DocumentRef]:
        handle = known_days().get(day.sitting_date)
        if not handle:
            return []
        return [DocumentRef(SOURCE, day.sitting_date, url=f"{API}/full_record?handle={handle}", format="json",
                            key=f"ts:{SOURCE}:{day.sitting_date.isoformat()}",
                            citation_url=f"https://hdl.handle.net/{handle}")]

    def fingerprint(self, raw: bytes) -> bytes:
        """What decides whether the day changed: the record's own fields (title, `modified`,
        page list, file), without what Territory Stories varies on every request — the six
        `related` records it recommends, relevance scores (`resume`) and the query `time`.
        Hashing the whole response made every scan re-read all ~80 pages of an unchanged day."""
        record = dict(json.loads(raw)["results"][0])
        for volatile in ("related", "resume"):
            record.pop(volatile, None)
        return json.dumps(record, sort_keys=True, ensure_ascii=False).encode()

    def parse(self, raw: bytes, ref: DocumentRef, fetch_part: Callable[[str], bytes]) -> ParsedDocument:
        record = json.loads(raw)["results"][0]
        title = record.get("title") or ""
        version = "proof" if title.lower().startswith("draft") else "final" if "debates and questions" in title.lower() else "unknown"
        handle = quote(record["handle"], safe="")
        pages = [json.loads(fetch_part(f"{API}/content?handle={handle}&group=0&page={n}") or b'""')
                 for n in range(len(record.get("pages") or []))]
        return ParsedDocument(speeches=parse_pages(pages, ref.citation_url), version=version, method="territory_stories")


def parse_pages(pages: list[str], citation_url: str | None) -> list:
    lines: list[tuple[int, str]] = []
    page, expect_number = 1, False
    for i, text in enumerate(pages):
        for l in (x.strip() for x in (text or "").splitlines()):
            if not l:
                continue
            if RE_PAGE_HEADER.match(l):          # the running header can fall mid-chunk
                expect_number = True
                continue
            if expect_number and RE_PAGE_NO.match(l):
                page, expect_number = int(l), False
                continue
            expect_number = False
            lines.append((page, l))

    # Question Time: "Policing in Remote Communities" / "Ms UIBO to CHIEF MINISTER" / question /
    # "ANSWER" / answer by the office asked. Rewrite as headers the shared reader understands,
    # and make each question's topic a heading.
    qt_topics, office = set(), None
    for k, (pg, l) in enumerate(lines):
        if m := RE_QUESTION.match(l):
            office = m["office"].strip()
            lines[k] = (pg, f"{m['name']} (question to {office}):")
            if k:
                qt_topics.add(k - 1)
        elif l == "ANSWER" and office:
            lines[k] = (pg, f"{office} (answer):")

    # No contents pages: capitalised lines (bills, debates) and question topics are the headings.
    outline = []
    for k, (_, l) in enumerate(lines):
        if k in qt_topics:
            outline.append(Heading("topic", l, "QUESTION TIME"))
        elif RE_HEADING.match(l) and not RULES.office.match(l) and not RULES.main.match(l) \
                and sum(c.isalpha() for c in l) >= 4:
            outline.append(Heading("topic", l, l))
    speeches, _, _ = walk(lines, outline, RULES, {}, citation_url, min_matched=None)
    return speeches
