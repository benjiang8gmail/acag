"""Parliament of NSW: Legislative Assembly (NSW-LA) and Legislative Council (NSW-LC).

Uses the public Hansard API at api.parliament.nsw.gov.au (no key; docs/sources.md §0a):

- `/api/hansard/search/year/{yyyy}`: sitting dates. Each date has one event per
  chamber with `TocDocId`, `PdfDocId` and `Uncorrected` (true = proof).
- `/api/hansard/search/daily/tableofcontents/{TocDocId}`: the day's structure
  (proceedings → topics with `uid`). `hansard.header/draft` is true for a proof.
- `/api/hansard/search/daily/fragment/{topic uid}`: one topic's text as XHTML.

The day's table of contents is the stored document; its fragments are fetched
only when it changes (new day, or proof → final). That keeps a re-check of a
proof day to one request. Speeches cite the day's PDF, which is public.
Party is not in NSW Hansard; speaker side is set later from members data.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import date

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
        toc = ET.fromstring(raw)
        draft = (toc.findtext("hansard.header/draft") or "").strip().lower()
        doc = ParsedDocument(version="proof" if draft == "true" else "final" if draft == "false" else "unknown")
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
        name = _clean("".join(head.itertext())).rstrip(":")
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
        else:
            role = "presiding officer" if kind == "OfficeUpper-H" else None
            suffix = "presiding" if kind == "OfficeUpper-H" else "interjection" if main is not None else "statement"
            turn = ParsedSpeech(seq=0, text=text, debate_title=debate_title,
                                proceeding_type=f"{proceeding_type} ({suffix})",
                                speaker_name=name, speaker_role=role, speaker_id=pid)
            turns.append(turn)
            last = turn
            if main is None and suffix == "statement":
                main, main_id = turn, pid
        member_id = None
    return [t for t in turns if t.text]


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
