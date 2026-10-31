"""Parliament of NSW: Legislative Assembly (NSW-LA) and Legislative Council (NSW-LC).

Uses the public Hansard API at api.parliament.nsw.gov.au (no key; docs/sources.md §0a):

- `/api/hansard/search/year/{yyyy}`: sitting dates. Each date has one event per
  chamber with `TocDocId`, `PdfDocId` and `Uncorrected` (true = proof).
- `/api/hansard/search/daily/tableofcontents/{TocDocId}`: the day's structure
  (proceedings → topics with `uid`). `hansard.header/draft` is true for a proof.
- `/api/hansard/search/daily/fragment/{topic uid}`: one topic's text as XHTML.

The day's table of contents is the stored document. When it changes (new day,
or proof → final) the day's PDF is fetched and read in step with it: 2 requests
per chamber-day. If the PDF doesn't line up with the contents (fewer than 90% of
topic headings found), the connector falls back to fetching each topic's fragment
(about 245 requests). A re-check of an unchanged proof day costs one request.
Speeches cite the day's PDF at the page they start on.
Party is not in NSW Hansard; speaker side is set later from members data.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import date

from parsers.hansard_pdf import Heading, PdfParseUnreliable, Rules, norm, walk
from parsers.pdf import pdf_pages
from pipeline.fetch import Blocked, Fetcher

from .base import CouldNotCheck, DocumentRef, ParsedDocument, ParsedSpeech, SittingDayRef

API = "https://api.parliament.nsw.gov.au/api/hansard/search"
CHAMBERS = {"Legislative Assembly": "NSW-LA", "Legislative Council": "NSW-LC"}

# Speaker header spans at the start of a paragraph.
MAIN_TURN = {"MemberSpeech-H": "speech", "MemberQuestion-H": "question", "MemberAnswer-H": "answer"}
OTHER_TURN = {"MemberUpper-H", "MemberLower-H", "OfficeUpper-H"}
HEADER_PARTS = {"GeneralBold-H", "Electorate-H", "Time-H", "HiddenTime-H", "MinisterialTitles-H"}


def _cls(el: ET.Element) -> str:
    return el.get("class", "")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class NSWConnector:
    code = "NSW"
    source_ids = ("NSW-LA", "NSW-LC")

    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher
        self._years: dict[int, dict[tuple[str, date], dict]] = {}

    # ---- listing ------------------------------------------------------------

    def _year(self, year: int) -> dict[tuple[str, date], dict]:
        if year not in self._years:
            try:
                days = json.loads(self.fetcher.fetch(f"{API}/year/{year}").body)
            except Blocked:
                raise
            except Exception as e:  # network error, 5xx, or not JSON
                raise CouldNotCheck(f"NSW sitting list for {year}: {e.__class__.__name__}: {e}") from e
            events = {}
            for d in days:
                when = date.fromisoformat(d["date"])
                for ev in d.get("Events", []):
                    sid = CHAMBERS.get(ev.get("Chamber"))
                    if sid:
                        events[(sid, when)] = ev
            self._years[year] = events
        return self._years[year]

    def list_sitting_days(self, start: date, end: date) -> list[SittingDayRef]:
        out = []
        for year in range(start.year, end.year + 1):
            for (sid, when), ev in self._year(year).items():
                if start <= when <= end:
                    out.append(SittingDayRef(sid, when, "proof" if ev.get("Uncorrected") else "final"))
        return sorted(out, key=lambda d: (d.sitting_date, d.source_id))

    def list_documents(self, day: SittingDayRef) -> list[DocumentRef]:
        ev = self._year(day.sitting_date.year).get((day.source_id, day.sitting_date))
        if not ev:
            return []
        return [DocumentRef(
            day.source_id, day.sitting_date,
            url=f"{API}/daily/tableofcontents/{ev['TocDocId']}", format="xml",
            version_hint="proof" if ev.get("Uncorrected") else "final",
            key=f"toc:{day.source_id}:{day.sitting_date.isoformat()}",
            citation_url=f"{API}/daily/pdf/{ev['PdfDocId']}",
        )]

    # ---- parsing ------------------------------------------------------------

    def parse(self, raw: bytes, ref: DocumentRef, fetch_part: Callable[[str], bytes]) -> ParsedDocument:
        """The day's PDF, read in step with the table of contents: 1 request.
        If the PDF doesn't line up with the contents, fall back to one request per topic."""
        toc = ET.fromstring(raw)
        draft = (toc.findtext("hansard.header/draft") or "").strip().lower()
        doc = ParsedDocument(version="proof" if draft == "true" else "final" if draft == "false" else "unknown")
        if ref.citation_url:
            try:
                doc.speeches = parse_day_pdf(fetch_part(ref.citation_url), toc, ref.citation_url)
                doc.method = "pdf"
                return doc
            except PdfParseUnreliable as e:
                doc.note = f"day PDF not used ({e}); fetched topics one by one"
        doc.method = "fragments"
        return self._parse_fragments(toc, ref, fetch_part, doc)

    def _parse_fragments(self, toc: ET.Element, ref: DocumentRef, fetch_part, doc: ParsedDocument) -> ParsedDocument:
        for proceeding in toc.findall("proceeding"):
            ptype = _clean(proceeding.findtext("proceedinginfo/text") or "")
            for topic in proceeding.findall("topic"):
                uid = topic.get("uid")
                if not uid:
                    continue
                fragment = fetch_part(f"{API}/daily/fragment/{uid}")
                for s in parse_fragment(fragment, ptype):
                    s.seq = len(doc.speeches)
                    s.anchor_url = ref.citation_url
                    doc.speeches.append(s)
        return doc


def parse_fragment(raw: bytes, proceeding_type: str) -> list[ParsedSpeech]:
    """Split one topic's XHTML into speaker turns.

    A main turn (speech, question, answer) runs until the next main turn or
    heading. Interjections and presiding-officer remarks are their own turns.
    When the main speaker resumes after one, the text joins their turn again.
    """
    root = ET.fromstring(raw)
    body = next((e for e in root.iter() if _local(e.tag) == "body"), None)
    if body is None:
        return []
    turns: list[ParsedSpeech] = []
    main: ParsedSpeech | None = None   # the current speech, question or answer
    last: ParsedSpeech | None = None   # whoever spoke last; plain paragraphs continue their turn
    main_id: str | None = None
    member_id: str | None = None   # from the <a name="member" data-value> before a paragraph
    title = sub = None

    for el in body:
        tag, cls = _local(el.tag), _cls(el)
        if tag == "a" and el.get("name") == "member":
            member_id = el.get("data-value")
            continue
        if tag != "p":
            continue
        if cls == "SubDebate-H":
            title, sub, main, main_id, last = _clean("".join(el.itertext())), None, None, None, None
            continue
        if cls == "SubSubDebate-H":
            sub, main, main_id, last = _clean("".join(el.itertext())), None, None, None
            continue
        if cls.startswith("Division") or cls == "TableGrid-T":
            continue
        debate_title = f"{title} — {sub}" if title and sub else title
        holder = next((c for c in el if _local(c.tag) == "span"), None)
        head = next((c for c in holder if _local(c.tag) == "span" and
                     (_cls(c) in MAIN_TURN or _cls(c) in OTHER_TURN)), None) if holder is not None else None
        if head is None:
            text = _clean("".join(el.itertext()))
            if not text:
                continue
            if last is not None and cls != "NormalBold-P":
                last.text += "\n" + text
            else:
                last = ParsedSpeech(seq=0, text=text, debate_title=debate_title,
                                    proceeding_type=f"{proceeding_type} (procedural)")
                turns.append(last)
            continue

        kind = _cls(head)
        name, extra = _header_names(holder, head)
        text = _text_after_header(holder)
        pid = head.get("data-value") or member_id
        if kind in MAIN_TURN:
            main = ParsedSpeech(
                seq=0, text=text, debate_title=debate_title,
                proceeding_type=proceeding_type if MAIN_TURN[kind] == "speech" else f"{proceeding_type} ({MAIN_TURN[kind]})",
                speaker_name=name,
                speaker_role=_span_text(holder, "MinisterialTitles-H"),
                electorate=_span_text(holder, "Electorate-H"),
                start_time=(_span_text(holder, "Time-H") or "") + (_span_text(holder, "HiddenTime-H") or "") or None,
                speaker_id=pid,
            )
            main_id, last = pid, main
            turns.append(main)
        elif kind == "MemberUpper-H" and main is not None and pid and pid == main_id:
            main.text += "\n" + text
            last = main
        elif kind == "MemberUpper-H":
            # A member with the call who is not resuming a speech: e.g. in committee,
            # or tabling a document. Their contribution becomes the current turn.
            main = ParsedSpeech(seq=0, text=text, debate_title=debate_title,
                                proceeding_type=f"{proceeding_type} (statement)",
                                speaker_name=name, speaker_id=pid)
            main_id, last = pid, main
            turns.append(main)
        else:
            presiding = kind == "OfficeUpper-H"
            role = ("presiding officer" + (f" ({extra})" if extra else "")) if presiding else None
            last = ParsedSpeech(seq=0, text=text, debate_title=debate_title,
                                proceeding_type=f"{proceeding_type} ({'presiding' if presiding else 'interjection'})",
                                speaker_name=name, speaker_role=role, speaker_id=pid)
            turns.append(last)
        member_id = None
    return [t for t in turns if t.text]


def _header_names(holder: ET.Element, head: ET.Element) -> tuple[str, str | None]:
    """The speaker's name, which NSW sometimes splits over adjacent spans ("T" + "he CHAIR"),
    and any further name of the same class in brackets ("(The Hon. Rod Roberts)")."""
    kids = [c for c in holder if _local(c.tag) == "span"]
    i = kids.index(head)
    name = ""
    while i < len(kids) and _cls(kids[i]) == _cls(head):
        name += "".join(kids[i].itertext())
        if (kids[i].tail or "").strip():
            break
        i += 1
    extra, prev_joined = "", False
    for k in kids[i:]:
        if _cls(k) == _cls(head):
            extra += "".join(k.itertext())   # adjacent spans are one name split in pieces
            prev_joined = not (k.tail or "").strip()
        elif extra and prev_joined:
            break
    name = _clean(name).rstrip(":").strip()
    extra = _clean(extra).strip(":() ")
    return name, (extra if extra and extra != name else None)


def _span_text(holder: ET.Element, cls: str) -> str | None:
    for c in holder.iter():
        if _cls(c) == cls:
            return _clean("".join(c.itertext())) or None
    return None


def _text_after_header(holder: ET.Element) -> str:
    """Text of the paragraph without the speaker header: name, (electorate—title) (time):"""
    parts: list[str] = [holder.text or ""]
    for child in holder:
        if _cls(child) in MAIN_TURN or _cls(child) in OTHER_TURN or _cls(child) in HEADER_PARTS:
            parts.append(child.tail or "")
        else:
            parts.append("".join(child.itertext()) + (child.tail or ""))
    text = _clean("".join(parts))
    return re.sub(r"^[\s—–:)\-]+", "", text)


# ---- day PDF (the default text source: 1 request per chamber-day) -------------

MIN_HEADINGS_MATCHED = 0.9
_HON = r"(?:The Hon\.|Hon\.|Mr|Ms|Mrs|Miss|Dr)"
_UPTOK = r"(?:Mc|Mac)?[A-Z][A-Z'’\-]+"
_UPNAME = rf"{_HON}\s+{_UPTOK}(?:\s+{_UPTOK})*"
_TIME = r"\d{1,2}[:.]\d{2}"
PROCEDURAL = re.compile(
    r"^(?:Question|Motion|Amendments?|Bill|Debate|Consideration|Leave|Message|Pursuant|Business|Third reading)\b"
    r".{0,160}\b(?:agreed to|negatived|resolved|adjourned|resumed|interrupted|granted|read a (?:first|second|third) time"
    r"|introduced|passed|put|lapsed|withdrawn)\b.{0,60}\.$")
RULES = Rules(
    main=re.compile(rf"^(?P<name>{_UPNAME})\s*(?:\((?P<inner>[^()]*(?:\([^()]*\)[^()]*)*)\))?\s*"
                    rf"(?:\((?P<time>{_TIME})\))?\s*(?P<sep>:|—)\s*(?P<rest>.*)$"),
    open_header=re.compile(rf"^{_UPNAME}\s*\([^)]*$"),
    name_bracket=re.compile(rf"^{_UPNAME}\s*\("),
    office=re.compile(r"^(?P<office>(?:The\s+)?(?:TEMPORARY |DEPUTY |ASSISTANT |ACTING )?(?:SPEAKER|PRESIDENT|CHAIR|CLERK))"
                      r"\s*(?:\((?P<who>[^)]*)\))?\s*:\s*(?P<rest>.*)$"),
    interjection=re.compile(rf"^(?P<name>{_HON}\s+[A-Z][a-z][\w'’\-]*(?:\s+(?:[A-Z][\w'’\-]+|de|van|von))*)\s*:\s*(?P<rest>.*)$"),
    procedural=PROCEDURAL,
    division_start=re.compile(r"^The (?:House|Committee|Council) divided\.$"),
    # Assembly lists "Tesch, L"; Council lists bare surnames ("Ruddick").
    division_line=re.compile(r"^(?:(?:Ayes|Noes|Pairs|Majority|AYES|NOES|PAIRS|Contents|Not contents)\b.*"
                             r"|[A-Z][A-Za-z'’\-]+(?: [A-Z][A-Za-z'’\-]+)*(?:, [A-Z][A-Za-z]*)?(?: \(teller\))?)$"),
    time=_TIME,
)
# Page furniture printed at the top of every page: date, chamber (with "- PROOF"), "Page N".
RE_FURNITURE = re.compile(r"^(?:\w+day,? \d{1,2} \w+ \d{4}|Legislative (?:Assembly|Council)\s*-?\s*(?:PROOF)?|Page\s+(?P<page>\d+))$")
_norm = norm


def _toc_outline(toc: ET.Element) -> tuple[list[Heading], dict[str, tuple[str | None, str | None]]]:
    """Headings in the order the PDF prints them, plus a name → (member id, electorate) map."""
    outline, members = [], {}
    for proceeding in toc.findall("proceeding"):
        pname = _clean(proceeding.findtext("proceedinginfo/text") or "")
        outline.append(Heading("proceeding", pname))
        for topic in proceeding.findall("topic"):
            qa = {}
            for tag in ("question", "answer"):
                for el in topic.iter(tag):
                    mid = (el.findtext("talk.start/talker/id") or "").strip()
                    if mid:
                        qa.setdefault(mid, tag)
            outline.append(Heading("topic", _clean(topic.findtext("topicinfo/text") or ""), pname, qa))
            for sub in topic.findall("subproceeding"):
                outline.append(Heading("sub", _clean(sub.findtext("subproceedinginfo/text") or "")))
    for talker in toc.iter("talker"):
        name, mid = _clean(talker.findtext("name") or ""), (talker.findtext("id") or "").strip()
        if name and mid:
            members.setdefault(name.upper(), (mid, _clean(talker.findtext("electorate") or "") or None))
    return [h for h in outline if h.text], members


def parse_day_pdf(pdf: bytes, toc: ET.Element, citation_url: str | None) -> list[ParsedSpeech]:
    outline, members = _toc_outline(toc)
    lines: list[tuple[int, str]] = []
    pdf_page: dict[int, int] = {}
    for i, text in enumerate(pdf_pages(pdf)):
        page, body = None, [l.strip() for l in text.splitlines() if l.strip()]
        while body and (m := RE_FURNITURE.match(body[0])):
            page = int(m.group("page")) if m.group("page") else page
            body.pop(0)
        pdf_page.setdefault(page or i + 1, i + 1)
        lines.extend((page or i + 1, line) for line in body)
    speeches, _, _ = walk(lines, outline, RULES, members, citation_url, MIN_HEADINGS_MATCHED, pdf_page=pdf_page)
    return speeches
