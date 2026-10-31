"""Parliament of Australia: Senate (CTH-SEN) and House of Representatives (CTH-HOR),
including the Federation Chamber (in the House file).

aph.gov.au and parlinfo.aph.gov.au answer scripts with an Azure WAF block page, even
for robots.txt (docs/sources.md §0a). The same official Hansard XML that APH publishes
is republished by OpenAustralia at data.openaustralia.org.au/origxml/ (no robots.txt
rules; updated each weekday morning), and that is what this connector reads:

- Sitting days: the directory listings `senate_debates/` and `representatives_debates/`
  (2 requests). Every weekday has a file; a 0-byte file means no sitting (or that the
  mirror couldn't get the day — it can't tell us which).
- Document: one XML file per chamber per day, keyed `xml:{source}:{date}`. When APH
  revises a day (proof → official) the mirror re-dates the file; conditional GETs see it.
- Text: APH's own XML. `talker` gives member id, electorate, party and page; header
  spans give the printed name, ministerial title and time; `<proof>1</proof>` marks a proof.
- Citations: the mirrored XML file, plus the printed Hansard page on every speech.
  This is a third-party copy of the official record: it lags APH by about a day.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import date

from pipeline.fetch import Blocked, Fetcher

from .base import CouldNotCheck, DocumentRef, ParsedDocument, ParsedSpeech, SittingDayRef

BASE = "https://data.openaustralia.org.au/origxml"
FOLDERS = {"CTH-SEN": "senate_debates", "CTH-HOR": "representatives_debates"}
RE_LISTING = re.compile(r'href="(?P<d>\d{4}-\d{2}-\d{2})\.xml">.*?</a>\s+\S+ \S+\s+(?P<size>\S+)')
HEADER_SPANS = {"HPS-MemberSpeech", "HPS-MemberContinuation", "HPS-MemberInterjecting", "HPS-MemberQuestion",
                "HPS-MemberAnswer", "HPS-OfficeSpeech", "HPS-OfficeContinuation", "HPS-OfficeInterjecting",
                "HPS-Electorate", "HPS-MinisterialTitles", "HPS-Time"}
NAME_SPANS = ("HPS-MemberSpeech", "HPS-MemberContinuation", "HPS-MemberInterjecting", "HPS-MemberQuestion",
              "HPS-MemberAnswer", "HPS-OfficeSpeech", "HPS-OfficeContinuation", "HPS-OfficeInterjecting")
TURNS = {"speech": None, "question": "question", "answer": "answer"}
XSCRIPTS = {"chamber.xscript": "", "fedchamb.xscript": "Federation Chamber: ", "answers.to.questions": "Answers to questions: "}
RE_PRESIDING = re.compile(r"\((The (?:DEPUTY |ACTING |TEMPORARY )?(?:SPEAKER|PRESIDENT|CHAIR))\)|^(?:The )?(?:DEPUTY |ACTING )?(?:SPEAKER|PRESIDENT)\b")


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


class CTHConnector:
    code = "CTH"
    source_ids = tuple(FOLDERS)

    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher
        self._listing: dict[str, dict[date, bool]] = {}

    def _days(self, sid: str) -> dict[date, bool]:
        if sid not in self._listing:
            try:
                html = self.fetcher.fetch(f"{BASE}/{FOLDERS[sid]}/").body.decode("utf-8", "replace")
            except Blocked:
                raise
            except Exception as e:
                raise CouldNotCheck(f"OpenAustralia listing for {sid}: {e.__class__.__name__}: {e}") from e
            self._listing[sid] = {date.fromisoformat(m["d"]): m["size"] != "0" for m in RE_LISTING.finditer(html)}
            if not self._listing[sid]:
                raise CouldNotCheck(f"OpenAustralia listing for {sid} had no dated files")
        return self._listing[sid]

    def list_sitting_days(self, start: date, end: date) -> list[SittingDayRef]:
        return [SittingDayRef(sid, d) for sid in FOLDERS for d, sat in sorted(self._days(sid).items())
                if sat and start <= d <= end]

    def list_documents(self, day: SittingDayRef) -> list[DocumentRef]:
        if not self._days(day.source_id).get(day.sitting_date):
            return []
        url = f"{BASE}/{FOLDERS[day.source_id]}/{day.sitting_date.isoformat()}.xml"
        return [DocumentRef(day.source_id, day.sitting_date, url=url, format="xml",
                            key=f"xml:{day.source_id}:{day.sitting_date.isoformat()}", citation_url=url)]

    def parse(self, raw: bytes, ref: DocumentRef, fetch_part: Callable[[str], bytes]) -> ParsedDocument:
        return parse_xml(raw, ref.citation_url)


def parse_xml(raw: bytes, citation_url: str | None) -> ParsedDocument:
    root = ET.fromstring(raw.lstrip(b"\xef\xbb\xbf").strip())
    proof = (root.findtext("session.header/proof") or "").strip()
    doc = ParsedDocument(version="proof" if proof == "1" else "final" if proof == "0" else "unknown", method="xml")
    for xscript in root:
        prefix = XSCRIPTS.get(xscript.tag)
        if prefix is None:
            continue
        for debate in xscript.iter("debate"):
            dtitle = _clean(debate.findtext("debateinfo/title") or "")
            _walk(debate, prefix + dtitle, dtitle, None, doc, citation_url)
    for i, s in enumerate(doc.speeches):
        s.seq = i
    return doc


def _walk(el: ET.Element, proceeding: str, title: str, sub: str | None, doc: ParsedDocument, cite) -> None:
    for child in el:
        tag = child.tag
        if tag in ("subdebate.1", "subdebate.2"):
            t = _clean(child.findtext("subdebateinfo/title") or "")
            if tag == "subdebate.1":
                _walk(child, proceeding, title, t, doc, cite)
            else:
                _walk(child, proceeding, title, f"{sub} — {t}" if sub else t, doc, cite)
        elif tag in TURNS:
            _turns(child, TURNS[tag], proceeding, sub or title, doc, cite)


def _turns(el: ET.Element, kind: str | None, proceeding: str, debate_title: str, doc: ParsedDocument, cite) -> None:
    """A speech's text holds every turn in it: interjections, the chair and the speaker resuming
    are paragraphs that open with their own name span. The <interjection>/<continue> children
    are empty markers that carry those speakers' details (party, electorate) by member id."""
    talkers = {}
    for t in el.iter("talker"):
        talkers.setdefault(_clean(t.findtext("name.id") or ""), t)
    body = el.find("talk.text")
    main_talker = el.find("talk.start/talker")
    if body is None or main_talker is None:
        return
    main = current = None
    for i, p in enumerate(body.iter("p")):
        lead = _leading_name(p)
        if i == 0 or lead:
            if i == 0:
                talker, k = main_talker, kind
            else:
                cls, href = lead
                talker = talkers.get(href)
                if talker is None:   # (an Element with no children is falsy, so no `or` here)
                    talker = main_talker
                k = "interjection" if cls.endswith("Interjecting") else "continuation" if cls.endswith("Continuation") else "statement"
            turn = _turn(talker, p, proceeding, debate_title, k, cite)
            if turn is None:
                continue
            if k == "continuation" and main and turn.speaker_id == main.speaker_id:
                main.text += "\n" + turn.text      # the main speaker resumes after an interruption
                current = main
                continue
            if k == "continuation":
                turn.proceeding_type = turn.proceeding_type.replace("(continuation)", "(statement)")
            doc.speeches.append(turn)
            current = turn
            if i == 0:
                main = turn
        elif current is not None:
            text = _para_text(p, first=False)
            if text:
                current.text += "\n" + text


def _leading_name(p: ET.Element) -> tuple[str, str] | None:
    """(span class, member id) when the paragraph opens with a speaker's name."""
    def first(e: ET.Element):
        if (e.text or "").strip():
            return None
        for c in e:
            cls = c.get("class", "")
            if cls in NAME_SPANS:
                return cls, ""
            if c.tag == "a" and c.get("type", "").startswith(("Member", "Office")):
                inner = next((x.get("class") for x in c.iter("span") if x.get("class") in NAME_SPANS), None)
                return (inner or c.get("type")), c.get("href", "")
            found = first(c)
            if found is not None or (c.tail or "").strip() or (c.text or "").strip():
                return found
        return None
    return first(p)


def _turn(talker: ET.Element, p: ET.Element, proceeding: str, debate_title: str, kind: str | None, cite) -> ParsedSpeech | None:
    printed, role, when = None, None, _clean(talker.findtext("time.stamp") or "") or None
    for span in p.iter("span"):
        cls = span.get("class", "")
        if cls in NAME_SPANS and printed is None:
            printed = _clean("".join(span.itertext())).rstrip(":").strip()
        elif cls == "HPS-MinisterialTitles" and role is None:
            role = _clean("".join(span.itertext()))
        elif cls == "HPS-Time" and not when:
            when = _clean("".join(span.itertext()))
    text = _para_text(p, first=True)
    if not text:
        return None
    meta = _clean(talker.findtext("name") or "")
    suffix = kind
    if RE_PRESIDING.search(meta) or (printed and RE_PRESIDING.match(printed)):
        holder = re.sub(r"\s*\(.*\)$", "", meta)                     # "Dick, Milton MP"
        last, _, first = holder.partition(",")
        who = _clean(f"{first.replace(' MP', '').replace('Sen ', '')} {last}")
        role, suffix = (f"presiding officer ({who})" if who else "presiding officer"), "presiding"
    return ParsedSpeech(
        seq=0, text=text, debate_title=debate_title or None,
        proceeding_type=f"{proceeding} ({suffix})" if suffix else proceeding or None,
        speaker_name=printed or meta or None, speaker_id=_clean(talker.findtext("name.id") or "") or None,
        speaker_role=role, party=_clean(talker.findtext("party") or "") or None,
        electorate=_clean(talker.findtext("electorate") or "") or None,
        start_time=when, page=_clean(talker.findtext("page.no") or "") or None,
        anchor_url=cite)


def _para_text(p: ET.Element, first: bool) -> str:
    parts: list[str] = []

    def walk(e: ET.Element):
        skip = e.get("class", "") in HEADER_SPANS or (e.tag == "a" and e.get("type", "").startswith(("Member", "Office")))
        if not skip and e.text:
            parts.append(e.text)
        if not skip:
            for c in e:
                walk(c)
        if e.tail:
            parts.append(e.tail)

    if p.text:
        parts.append(p.text)
    for c in p:
        walk(c)
    text = _clean("".join(parts))
    return re.sub(r"^[\s()—–:,]+", "", text) if first else text
