"""Parliament of Tasmania: House of Assembly (TAS-HA) and Legislative Council (TAS-LC).

www.parliament.tas.gov.au answers scripts with a Cloudflare challenge. The Parliament's own
document search, search.parliament.tas.gov.au (no robots.txt rules), serves the same Hansard:

- Sitting days: `/search/quicksearch/{yyyy}/sittingdays.html`, a calendar whose sitting dates
  link to a search for that date (1 request per year).
- Documents: `/Search/search/search?IW_FIELD_ADVANCE_PHRASE={Weekday D Month YYYY}&IW_DATABASE=Hansard`
  lists the day's transcripts (1 request per calendar date), each with a download link to the
  original Word file ("HA Thursday 10 September 2026.docx"). Recent days appear only once
  indexed (a few days): until then a calendar date has no hits and is held as pending; a date
  still unindexed after GIVE_UP_DAYS is treated as no sitting.
- An empty answer (HTTP 200 with no body, as the site gave on 31 Oct 2026 after serving the same
  pages earlier that day) or a calendar with no sitting dates is "could not check", never "no
  sittings", so the watermark stays put until the site answers again.
- Text: the .docx itself. Word heading styles give sections and topics; speaker turns open with
  a bold name and " - "; Question Time is "Mr WILLIE question to TREASURER, Mr ABETZ" … "ANSWER".
  "Preliminary Transcript" marks a draft.
- Citations: the date search URL (stable; the document links inside it are per-query).
  The .docx has no page numbers.
"""

from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import date, datetime, timedelta
from urllib.parse import quote_plus

import httpx

from pipeline.fetch import Blocked, Fetcher

from .base import CouldNotCheck, DocumentRef, ParsedDocument, ParsedSpeech, SittingDayRef

HOST = "https://search.parliament.tas.gov.au"
PREFIX = {"TAS-HA": "HA", "TAS-LC": "LC"}
GIVE_UP_DAYS = 30
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

_HON = r"(?:Mr|Ms|Mrs|Miss|Dr|Prof|Madam)"
_NAME = rf"{_HON}\s+[A-Z][\w’'\-]+(?:\s+[A-Z][\w’'\-]+)?"
RE_TURN = re.compile(rf"^(?P<name>The (?:DEPUTY )?SPEAKER|(?:Mr|Madam) (?:DEPUTY )?(?:PRESIDENT|SPEAKER|CHAIR)|CHAIR|The CHAIR|{_NAME})"
                     r"\s*(?:\((?P<inner>[^()]*)\))?(?:\s*\([^()]*\))*\s+[-–]\s+(?P<rest>.*)$")   # "(McIntyre - …) (by leave) -"
RE_QUESTION = re.compile(rf"^(?P<asker>{_NAME}) question to (?P<office>.+?),\s+(?P<minister>{_NAME})$")
RE_TIME = re.compile(r"^\[(?P<h>\d{1,2})\.(?P<m>\d{2})\s*(?P<ap>[ap])\.m\.\]$")
RE_STAGE = re.compile(r"^(?:Members|Government members|Opposition members|An honourable member|[A-Z][\w’' ]{0,40}) interjecting\.?$")
RE_PROCEDURAL = re.compile(r"^(?:Motion agreed to|Motion negatived|Question agreed to|Question negatived|Bill read|Bill agreed to"
                           r"|Debate adjourned|Sitting suspended|The House adjourned|The Council adjourned|Leave granted"
                           r"|The (?:Speaker|President), .{0,60} took the Chair|Clauses? .{0,60}agreed to|Amendments? (?:agreed to|negatived))\b")


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def phrase(d: date) -> str:
    return f"{d:%A} {d.day} {d:%B} {d.year}"


def search_url(d: date) -> str:
    return f"{HOST}/Search/search/search?IW_FIELD_ADVANCE_PHRASE={quote_plus(phrase(d))}&IW_DATABASE=Hansard&IW_SORT=-9"


class TASConnector:
    code = "TAS"
    source_ids = tuple(PREFIX)

    def __init__(self, fetcher: Fetcher, today: date | None = None):
        self.fetcher = fetcher
        self.today = today or datetime.now().date()
        self._calendar: dict[int, list[date]] = {}
        self._docs: dict[date, dict[str, str]] = {}

    def _get(self, url: str, what: str, missing_ok: bool = False) -> str | None:
        try:
            body = self.fetcher.fetch(url).body
        except Blocked:
            raise
        except httpx.HTTPStatusError as e:
            if missing_ok and e.response.status_code == 404:
                return None
            raise CouldNotCheck(f"Tasmania {what}: HTTP {e.response.status_code}") from e
        except Exception as e:
            raise CouldNotCheck(f"Tasmania {what}: {e.__class__.__name__}: {e}") from e
        if not body or not body.strip():
            raise CouldNotCheck(f"Tasmania {what}: the site returned an empty page")
        return body.decode("utf-8", "replace")

    def _year(self, year: int) -> list[date]:
        if year not in self._calendar:
            html = self._get(f"{HOST}/search/quicksearch/{year}/sittingdays.html", f"sitting calendar {year}",
                             missing_ok=year > self.today.year)   # next year's calendar may not be up yet
            days = set()
            for p in re.findall(r"IW_FIELD_ADVANCE_PHRASE=([^&\"]+)", html or ""):
                try:
                    days.add(datetime.strptime(re.sub(r"\s+", " ", p.replace("+", " ").replace("%20", " ")).strip(), "%A %d %B %Y").date())
                except ValueError:
                    continue
            if html is not None and not days:
                raise CouldNotCheck(f"Tasmania sitting calendar {year}: no sitting dates found (page layout changed?)")
            self._calendar[year] = sorted(days)
        return self._calendar[year]

    def _day_docs(self, d: date) -> dict[str, str]:
        """{chamber: .docx URL} for the date's transcripts; {} until the day is indexed."""
        if d not in self._docs:
            html = self._get(search_url(d), f"search for {phrase(d)}")
            docs: dict[str, str] = {}
            want = {sid: f"{p} {phrase(d)}.docx" for sid, p in PREFIX.items()}
            for href in re.findall(r'href="(/search/isysquery/[^"]+/doc/[^"]+\.docx)"', html):
                name = re.sub(r"%20", " ", href.rsplit("/", 1)[1])
                for sid, filename in want.items():
                    if name == filename and sid not in docs:
                        docs[sid] = HOST + href
            self._docs[d] = docs
        return self._docs[d]

    def list_sitting_days(self, start: date, end: date) -> list[SittingDayRef]:
        out = []
        for year in range(start.year, end.year + 1):
            for d in self._year(year):
                if not (start <= d <= end):
                    continue
                docs = self._day_docs(d)
                if docs:
                    out += [SittingDayRef(sid, d) for sid in PREFIX if sid in docs]
                elif (self.today - d).days <= GIVE_UP_DAYS:
                    out += [SittingDayRef(sid, d) for sid in PREFIX]   # not indexed yet: pending
        return out

    def list_documents(self, day: SittingDayRef) -> list[DocumentRef]:
        url = self._day_docs(day.sitting_date).get(day.source_id)
        if not url:
            return []
        return [DocumentRef(day.source_id, day.sitting_date, url=url, format="docx",
                            key=f"docx:{day.source_id}:{day.sitting_date.isoformat()}",
                            citation_url=search_url(day.sitting_date))]

    def parse(self, raw: bytes, ref: DocumentRef, fetch_part: Callable[[str], bytes]) -> ParsedDocument:
        return parse_docx(raw, ref.citation_url)


def _paragraphs(raw: bytes) -> list[tuple[str, str, str]]:
    """(style, text, leading bold text) for each non-empty paragraph."""
    root = ET.fromstring(zipfile.ZipFile(io.BytesIO(raw)).read("word/document.xml"))
    out = []
    for p in root.iter(W + "p"):
        st = p.find(f"{W}pPr/{W}pStyle")
        style = st.get(W + "val") if st is not None else ""
        runs = [(r.find(f"{W}rPr/{W}b") is not None, "".join(t.text or "" for t in r.iter(W + "t"))) for r in p.iter(W + "r")]
        text = _clean("".join(t for _, t in runs))
        bold = ""
        for b, t in runs:
            if not t.strip() and not bold:
                continue
            if not b:
                break
            bold += t
        if text:
            out.append((style, text, _clean(bold)))
    return out


def parse_docx(raw: bytes, citation_url: str | None) -> ParsedDocument:
    paras = _paragraphs(raw)
    head = " ".join(t for _, t, _ in paras[:8]).lower()
    doc = ParsedDocument(version="proof" if "preliminary transcript" in head or "draft transcript" in head else "final",
                         method="docx")
    section = topic = None
    main = last = None
    when = None
    pending_answer: tuple[str, str] | None = None   # (minister, office) for the next "ANSWER"
    qa: dict[str, str] = {}                          # asker → question, minister → answer, per question topic

    def start(name, kind, text, role=None, electorate=None):
        nonlocal last
        s = ParsedSpeech(seq=len(doc.speeches), text=text, debate_title=topic or section,
                         proceeding_type=f"{section} ({kind})" if kind else section, speaker_name=name,
                         speaker_role=role, electorate=electorate, start_time=when, anchor_url=citation_url)
        doc.speeches.append(s)
        last = s
        return s

    started = False
    for style, text, bold in paras:
        if style == "Heading1":
            section, topic, main, last, started = text, None, None, None, True
            continue
        if style == "Heading2":
            if not started:            # the date heading at the top
                started = True
                continue
            if text != "Supplementary Question":
                topic, qa = text, {}
            main = last = None
            continue
        if not started:
            continue
        if m := RE_TIME.match(text):
            h = int(m["h"]) % 12 + (12 if m["ap"] == "p" else 0)
            when = f"{h:02d}:{m['m']}"
            if last is not None and not last.text and last.start_time is None:
                last.start_time = when     # "[10.01 a.m.]" follows the question line
            continue
        if m := RE_QUESTION.match(text):
            asker, minister = _clean(m["asker"]), _clean(m["minister"])
            main = start(asker, "question", "")
            pending_answer = (minister, _clean(m["office"]))
            qa = {asker.upper(): "question", minister.upper(): "answer"}
            continue
        if text == "ANSWER" and pending_answer:
            minister, office = pending_answer
            main = start(minister, "answer", "", role=office.title())
            continue
        if (m := RE_TURN.match(text)) and (m["inner"] or (bold and text.startswith(bold.split(" - ")[0].strip()[:3]))):
            name, rest, inner = _clean(m["name"]), m["rest"], m["inner"]
            electorate = role = None
            if inner:
                electorate, _, role = (x.strip() for x in inner.partition(" - "))
                role = role or None
            if re.match(r"^(?:The |Mr |Madam )?(?:DEPUTY )?(?:SPEAKER|PRESIDENT|CHAIR)$", name):
                start(name, "presiding", rest, role="presiding officer")
                continue
            surname = name.split()[-1]
            if surname.isupper() or surname.startswith(("Mc", "O'", "O’")) and surname[2:].isupper():
                if main is not None and main.speaker_name.upper() == name.upper():
                    main.text = (main.text + "\n" + rest).strip()
                    last = main
                else:
                    kind = None if inner else "statement"
                    if name.upper() in qa and not re.match(r"^(?:A |On a )?point of order", rest, re.I):
                        kind = qa[name.upper()]      # supplementary question, or the minister's answer
                    main = start(name, kind, rest, role=role, electorate=electorate)
            else:
                start(name, "interjection", rest)
            continue
        if RE_STAGE.match(text) and last is not None:
            last.text = (last.text + "\n" + text).strip()
            continue
        if last is None or RE_PROCEDURAL.match(text):
            start(None, "procedural", text)
            main = None
            continue
        last.text = (last.text + "\n" + text).strip()
    doc.speeches = [s for s in doc.speeches if s.text]
    for i, s in enumerate(doc.speeches):
        s.seq = i
    return doc
