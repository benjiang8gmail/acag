"""Member lists and speaker side (spec §9.4), checked against what Hansard itself prints."""
import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from connectors.act import ACTConnector
from connectors.base import DocumentRef
from connectors.nsw import parse_day_pdf
from connectors.qld import QLDConnector
from parsers.pdf import pdf_pages
from pipeline.members import Enricher, MemberIndex, speaker_side

FX = Path(__file__).parent / "fixtures" / "sources"
MEMBERS = Path(__file__).resolve().parents[2] / "config" / "members"


def chambers(code):
    return yaml.safe_load((MEMBERS / f"{code}.yaml").read_text())["chambers"]


def test_lists_fill_every_seat_with_their_source_recorded():
    sizes = {"NSW-LA": 93, "NSW-LC": 42, "ACT-LA": 25, "QLD-LA": 93}
    for code in ("NSW", "ACT", "QLD"):
        for chamber, data in chambers(code).items():
            assert len(data["members"]) == sizes[chamber], chamber
            assert data["source"].startswith("https://") and len(data["source_sha256"]) == 64
            assert data["source_kind"] == ("official" if code == "QLD" else "secondary")
    qld = [m["party"] for m in chambers("QLD")["QLD-LA"]["members"]]
    assert {p: qld.count(p) for p in set(qld)} == {"LNP": 53, "ALP": 36, "KAP": 2, "GRN": 1, "IND": 1}


def test_every_nsw_speaker_in_the_contents_is_a_listed_member():
    index = MemberIndex("NSW")
    for chamber in ("NSW-LA", "NSW-LC"):
        toc = ET.parse(FX / chamber / "2026-10-22-toc.xml").getroot()
        talkers = {(t.findtext("name").strip(), (t.findtext("electorate") or "").strip() or None)
                   for t in toc.iter("talker") if (t.findtext("name") or "").strip()}
        missing = {n for n, e in talkers if not index.lookup(chamber, n, e)}
        # Known gap: a new Council member not yet on the secondary list (docs/sources.md, members).
        assert missing <= {"The Hon. BERNARD GOVIND"}, missing


def test_every_act_member_voting_on_17_september_is_listed():
    lines = [l.strip() for p in pdf_pages((FX / "ACT-LA" / "2026-09-17-proof.pdf").read_bytes())
             for l in p.splitlines() if l.strip()]
    k = lines.index("The Assembly voted—")
    names = []
    for line in lines[k + 3:]:
        if not re.fullmatch(r"(?:[A-Z][A-Za-z’'\-]+ ){1,3}[A-Z][A-Za-z’'\-]+", line):
            break
        parts = line.split()
        names += [" ".join(parts[:2]), " ".join(parts[2:])] if len(parts) == 4 else [line]
    assert len(names) >= 20
    index = MemberIndex("ACT")
    assert [n for n in names if not index.lookup("ACT-LA", n)] == []


@pytest.mark.parametrize("day", ["2026-10-13", "2026-10-14"])
def test_qld_list_agrees_with_party_and_electorate_printed_in_hansard(day):
    doc = QLDConnector(None).parse((FX / "QLD-LA" / f"{day}.pdf").read_bytes(),
                                   DocumentRef("QLD-LA", date.fromisoformat(day), "U", "pdf", citation_url="U"), None)
    index = MemberIndex("QLD")
    checked = 0
    for s in doc.speeches:
        if s.party and s.electorate:
            m = index.lookup("QLD-LA", s.speaker_name, s.electorate)
            assert m and m["party"].upper() == s.party.upper() and m["electorate"] == s.electorate, s.speaker_name
            checked += 1
    assert checked > 50


@pytest.mark.parametrize("parliament,party,role,side", [
    ("NSW", "ALP", None, "government"), ("NSW", "LIB", None, "opposition"), ("NSW", "GRN", None, "crossbench"),
    ("NSW", "IND", None, "crossbench"), ("NSW", "LIB", "Leader of the Opposition", "opposition"),
    ("NSW", "IND", "Minister for Roads", "government"),       # a minister is government whatever the party
    ("NSW", None, None, "unknown"),
    ("QLD", "LNP", None, "government"), ("QLD", "ALP", None, "opposition"), ("QLD", "Grn", None, "crossbench"),
    ("QLD", "KAP", None, "crossbench"), ("QLD", "LNP", "Leader of the House", "government"),
    ("ACT", "ALP", None, "government"), ("ACT", "LIB", None, "opposition"), ("ACT", "GRN", None, "crossbench"),
    ("ACT", "LIB", "Shadow Minister for Health", "opposition"),
])
def test_speaker_side_rules(parliament, party, role, side):
    assert speaker_side(parliament, date(2026, 10, 22), party, role) == side


def _sides(parliament, chamber, when, speeches):
    e = Enricher(parliament)
    out = []
    for sp in speeches:
        if not sp.speaker_name or (sp.speaker_role or "").startswith("presiding officer"):
            continue
        o = SimpleNamespace(speaker_name=sp.speaker_name, speaker_role=sp.speaker_role,
                            electorate=sp.electorate, party=sp.party, speaker_side=None)
        e.apply(chamber, when, o)
        out.append(o)
    return out


def test_every_member_turn_gets_a_side_on_real_days():
    nsw = parse_day_pdf((FX / "NSW-LA" / "2026-10-22.pdf").read_bytes(),
                        ET.parse(FX / "NSW-LA" / "2026-10-22-toc.xml").getroot(), "U")
    act = ACTConnector(None).parse((FX / "ACT-LA" / "2026-09-17-proof.pdf").read_bytes(),
                                   DocumentRef("ACT-LA", date(2026, 9, 17), "U", "pdf", citation_url="U"), None).speeches
    qld = QLDConnector(None).parse((FX / "QLD-LA" / "2026-10-13.pdf").read_bytes(),
                                   DocumentRef("QLD-LA", date(2026, 10, 13), "U", "pdf", citation_url="U"), None).speeches
    for parliament, chamber, when, speeches, floor in [("NSW", "NSW-LA", date(2026, 10, 22), nsw, 1.0),
                                                      ("ACT", "ACT-LA", date(2026, 9, 17), act, 1.0),
                                                      ("QLD", "QLD-LA", date(2026, 10, 13), qld, 0.99)]:
        turns = _sides(parliament, chamber, when, speeches)
        known = sum(1 for t in turns if t.speaker_side != "unknown") / len(turns)
        assert known >= floor, (chamber, known)
    nsw_sides = {t.speaker_name: t.speaker_side for t in _sides("NSW", "NSW-LA", date(2026, 10, 22), nsw)}
    assert nsw_sides["Ms KELLIE SLOANE"] == "opposition"     # Leader of the Opposition (LIB)
    assert nsw_sides["Ms YASMIN CATLEY"] == "government"     # minister
    assert nsw_sides["Ms JENNY LEONG"] == "crossbench"       # Greens
