"""Reading a day of Hansard from PDF text, guided by an outline of its headings.

Shared by the PDF-based connectors (NSW, ACT; QLD next). Each parliament supplies:
- the page lines with their printed page numbers (page furniture already removed);
- an outline of headings in print order (NSW: the API's table of contents;
  ACT: the PDF's own contents pages);
- `Rules`: regular expressions for its speaker headers, presiding officers,
  interjections, procedural lines and division lists.

Turn rules (the same as the NSW XML parser):
- A main header (name with electorate, role or time in brackets) starts a turn.
- "NAME: …" continues the main speaker's turn if it is them; otherwise it is a
  member with the call (a statement), which becomes the current turn.
- Presiding officers and title-case interjections are their own turns.
- Procedural lines start a procedural turn; division lists are skipped.
- Plain lines continue whoever spoke last.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from connectors.base import ParsedSpeech

from .pdf import join_lines


class PdfParseUnreliable(Exception):
    """The PDF didn't line up with its outline well enough to trust."""


@dataclass(frozen=True)
class Heading:
    kind: str                       # proceeding / topic / sub
    text: str
    proceeding: str | None = None   # for topics: the proceeding they sit under
    qa: dict = field(default_factory=dict, hash=False, compare=False)  # member id → "question" / "answer"


@dataclass
class Rules:
    main: re.Pattern            # groups: name, inner (optional), time (optional), sep, rest
    open_header: re.Pattern     # a header whose bracket is still open at the end of the line
    name_bracket: re.Pattern    # a line starting with a member's name and "("
    office: re.Pattern          # groups: office, who (optional), time (optional), rest
    interjection: re.Pattern    # groups: name, rest
    procedural: re.Pattern
    division_start: re.Pattern  # the line that opens a division list
    division_line: re.Pattern
    time: str = r"\d{1,2}[:.]\d{2}"
    stage_direction: re.Pattern | None = None   # kept in the last turn's text, e.g. "Mr Cain interjecting—"
    qa_by_order: re.Pattern | None = None       # proceedings where question/answer follow speaking order
    max_header_lines: int = 3                   # long ministerial titles can wrap a header over several lines
    ignore_line: re.Pattern | None = None       # labels with no content, e.g. ACT "Ministerial statement"
    reply_header: re.Pattern | None = None      # written answers, e.g. ACT "Dr Paterson (in reply to …):"; groups name, rest
    # Parses a `main` match into {electorate, role, party, time}, or None when it is not a main header.
    # Without it, the default reads one "(electorate—role)" bracket and one "(time)" bracket.
    header_fields: Callable[[re.Match], dict | None] | None = None


RE_POINT_OF_ORDER = re.compile(r"^(?:(?:Mr|Madam) (?:Deputy |Assistant )?Speaker|(?:On a |I rise to a )?point of order)\b", re.I)


def _default_fields(m: re.Match, rules: "Rules") -> dict | None:
    """One "(electorate—role)" bracket and one "(time)" bracket (NSW, ACT)."""
    inner, when = m.group("inner"), m.group("time")
    if not (inner or when or m.group("sep") == "—"):
        return None
    if inner and re.fullmatch(rules.time, inner.strip()) and not when:
        inner, when = None, inner.strip()
    electorate, role = (inner.split("—", 1) + [None])[:2] if inner else (None, None)
    return {"electorate": _clean(electorate) if electorate else None, "role": _clean(role) if role else None,
            "time": when.replace(".", ":") if when else None}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _tidy_brackets(s: str) -> str:
    return re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", s))


def walk(lines: list[tuple[int, str]], outline: list[Heading], rules: Rules,
         members: dict[str, tuple[str | None, str | None]], citation_url: str | None,
         min_matched: float | None = 0.9) -> tuple[list[ParsedSpeech], int, int]:
    """Returns (speeches, topic headings matched, topic headings in the outline).

    With `min_matched` set, raises PdfParseUnreliable when too few topic headings line up."""
    long_lines = sorted(len(l) for _, l in lines if len(l) > 40)
    width = long_lines[len(long_lines) // 2] if long_lines else 100
    members = dict(members)

    turns: list[tuple[ParsedSpeech, list[str]]] = []
    main = last = None
    main_name = None
    k, matched = 0, 0
    topics_total = sum(1 for h in outline if h.kind == "topic")
    proceeding = title = sub = ""
    qa: dict[str, str] = {}
    order_qa: dict[str, str] = {}   # questioner / answerer by speaking order, for qa_by_order proceedings
    in_division = False
    parties: dict[str, str] = {}    # learned from headers that print party (QLD)

    def debate_title():
        return f"{title} — {sub}" if title and sub else title or None

    def ptype(suffix: str | None = None):
        if suffix:
            return f"{proceeding} ({suffix})" if proceeding else suffix
        return proceeding or None

    def qa_kind(name: str, mid: str | None, first: str = "") -> str | None:
        if mid and mid in qa:
            return qa[mid]
        if rules.qa_by_order and proceeding and rules.qa_by_order.match(proceeding):
            if RE_POINT_OF_ORDER.match(first):
                return None   # a point of order, not part of the question and answer
            if "q" not in order_qa:
                order_qa["q"] = name
            elif "a" not in order_qa and name != order_qa["q"]:
                order_qa["a"] = name
            return "answer" if order_qa.get("a") == name else "question"
        return None

    def start(speech: ParsedSpeech, first: str):
        turns.append((speech, [first] if first else []))
        return turns[-1]

    i = 0
    while i < len(lines):
        page, line = lines[i]
        # 1. A heading from the outline, in order. Topic titles are distinctive, so they may
        #    be found well ahead; generic labels only close by.
        hit = None
        for j in range(k, min(k + 40, len(outline))):
            if j - k > 3 and outline[j].kind != "topic":
                continue
            # A contents entry may add a qualifier the body prints separately, e.g. "(Ministerial statement)".
            targets = {norm(outline[j].text), norm(re.sub(r"\s*\([^()]*\)\s*$", "", outline[j].text))}
            longest = max(len(t) for t in targets)
            for span in (1, 2, 3, 4):
                joined = norm(" ".join(l for _, l in lines[i:i + span]))
                if joined in targets:
                    hit = (j, span)
                    break
                if len(joined) >= longest:
                    break
            if hit:
                break
        if hit:
            j, span = hit
            h = outline[j]
            k = j + 1
            if h.kind == "proceeding":
                proceeding, title, sub = h.text, "", ""
            elif h.kind == "topic":
                title, sub, qa, proceeding = h.text, "", h.qa, h.proceeding or proceeding
                order_qa = {}
                matched += 1
            else:
                sub = h.text
            main = last = main_name = None
            in_division = False
            i += span
            continue

        if rules.ignore_line is not None and rules.ignore_line.match(line):
            i += 1
            continue
        if rules.reply_header is not None and re.match(r"^(?:Mr|Ms|Mrs|Miss|Dr) [A-Z][\w’'\- ]+ \(in reply to", line):
            joined, used = line, 1
            while not rules.reply_header.match(joined) and used < 5 and i + used < len(lines):
                joined += " " + lines[i + used][1]
                used += 1
            if m := rules.reply_header.match(joined):
                name = _clean(m.group("name"))
                mid, electorate = members.get(name.upper(), (None, None))
                sp = ParsedSpeech(seq=0, text="", debate_title=debate_title(), proceeding_type=ptype("answer"),
                                  speaker_name=name, speaker_id=mid, electorate=electorate, page=str(page))
                main = last = start(sp, m.group("rest"))
                main_name = name.upper()
                i += used
                continue

        # 2. Speaker headers, possibly wrapped over two or three lines.
        header, used = line, 1
        while (rules.open_header.match(header) or (rules.name_bracket.match(header) and not rules.main.match(header))) \
                and used < rules.max_header_lines and i + used < len(lines):
            header += " " + lines[i + used][1]
            used += 1
        header = _tidy_brackets(header)

        if m := rules.office.match(header):
            who = _clean(m.group("who") or "") or None
            sp = ParsedSpeech(seq=0, text="", debate_title=debate_title(), proceeding_type=ptype("presiding"),
                              speaker_name=_clean(m.group("office")),
                              speaker_role="presiding officer" + (f" ({who})" if who else ""), page=str(page))
            when = m.groupdict().get("time")
            sp.start_time = when.replace(".", ":") if when else None
            last = start(sp, m.group("rest"))
            in_division = False
            i += used
            continue

        m = rules.main.match(header)
        fields = (rules.header_fields or _default_fields)(m, rules) if m else None
        if fields is not None:
            name = _clean(m.group("name"))
            mid, known_electorate = members.get(name.upper(), (None, None))
            electorate = fields.get("electorate") or known_electorate
            members.setdefault(name.upper(), (mid, electorate))
            if fields.get("party"):
                parties[name.upper()] = fields["party"]
            sp = ParsedSpeech(seq=0, text="", debate_title=debate_title(),
                              proceeding_type=ptype(qa_kind(name.upper(), mid, m.group("rest"))),
                              speaker_name=name, speaker_id=mid, speaker_role=fields.get("role"),
                              party=parties.get(name.upper()), electorate=electorate,
                              start_time=fields.get("time"), page=str(page))
            main = last = start(sp, m.group("rest"))
            main_name = name.upper()
            in_division = False
            i += used
            continue

        line = _tidy_brackets(line)
        if m := rules.main.match(line):   # "NAME: …" with no brackets
            name = _clean(m.group("name"))
            if main is not None and name.upper() == main_name:
                main[1].append(m.group("rest"))
                last = main
            else:
                mid, electorate = members.get(name.upper(), (None, None))
                sp = ParsedSpeech(seq=0, text="", debate_title=debate_title(),
                                  proceeding_type=ptype(qa_kind(name.upper(), mid, m.group("rest")) or "statement"),
                                  speaker_name=name, speaker_id=mid, electorate=electorate,
                                  party=parties.get(name.upper()), page=str(page))
                main = last = start(sp, m.group("rest"))
                main_name = name.upper()
            in_division = False
            i += 1
            continue
        if m := rules.interjection.match(line):
            name = _clean(m.group("name"))
            mid, _ = members.get(name.upper(), (None, None))
            sp = ParsedSpeech(seq=0, text="", debate_title=debate_title(), proceeding_type=ptype("interjection"),
                              speaker_name=name, speaker_id=mid, party=parties.get(name.upper()), page=str(page))
            last = start(sp, m.group("rest"))
            i += 1
            continue

        # 3. Divisions, procedural lines, and everything else.
        if rules.division_start.match(line):
            in_division = True
            last = start(ParsedSpeech(seq=0, text="", debate_title=debate_title(),
                                      proceeding_type=ptype("procedural"), page=str(page)), line)
            main = main_name = None
            i += 1
            continue
        if in_division and rules.division_line.match(line):
            i += 1
            continue
        if in_division and not rules.procedural.match(line):
            in_division = False   # "Motion negatived." can sit among the lists; anything else ends them
        if rules.stage_direction is not None and rules.stage_direction.match(line) and last is not None:
            last[1].append(line)
        elif last is None or rules.procedural.match(line) or (line.startswith("[") and last is not main):
            last = start(ParsedSpeech(seq=0, text="", debate_title=debate_title(),
                                      proceeding_type=ptype("procedural"), page=str(page)), line)
            main = main_name = None
        else:
            last[1].append(line)
        i += 1

    if min_matched is not None and topics_total and matched / topics_total < min_matched:
        raise PdfParseUnreliable(f"matched {matched} of {topics_total} topic headings")
    out = []
    for sp, body in turns:
        sp.text = join_lines(body, width)
        if sp.text:
            sp.seq = len(out)
            sp.anchor_url = f"{citation_url}#page={sp.page}" if citation_url and sp.page else citation_url
            out.append(sp)
    return out, matched, topics_total
