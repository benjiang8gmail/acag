"""Federal connector against APH's official Hansard XML as republished by OpenAustralia
(data.openaustralia.org.au/origxml), saved 31 Oct 2026 (backend/tests/fixtures/MANIFEST.md). No network."""
from datetime import date
from pathlib import Path

import httpx
import pytest

from connectors.base import SittingDayRef
from connectors.cth import BASE, CTHConnector, parse_xml
from pipeline.fetch import Fetcher
from pipeline.members import speaker_side

FX = Path(__file__).parent / "fixtures" / "sources"
HOR = FX / "CTH-HOR" / "2026-10-29.xml"
SEN = FX / "CTH-SEN" / "2026-10-15.xml"


def listing(rows):
    return "".join(f'<img src="/icons/text.gif"> <a href="{d}.xml">{d}.xml</a>  {d} 09:05  {size}  \n' for d, size in rows).encode()


class Mirror:
    def __init__(self):
        self.routes = {
            f"{BASE}/senate_debates/": listing([("2026-10-14", "1.7M"), ("2026-10-15", "1.2M"), ("2026-10-16", "0")]),
            f"{BASE}/representatives_debates/": listing([("2026-10-28", "1.7M"), ("2026-10-29", "1.0M"), ("2026-10-30", "0")]),
        }

    def handler(self, request):
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(404)
        return httpx.Response(200, content=self.routes[url]) if url in self.routes else httpx.Response(404)


@pytest.fixture
def connector():
    return CTHConnector(Fetcher("test", min_interval=0, transport=httpx.MockTransport(Mirror().handler)))


@pytest.fixture(scope="module")
def house():
    return parse_xml(HOR.read_bytes(), "U")


@pytest.fixture(scope="module")
def senate():
    return parse_xml(SEN.read_bytes(), "U")


def test_listing_skips_empty_files(connector):
    days = connector.list_sitting_days(date(2026, 10, 1), date(2026, 10, 31))
    assert days == [SittingDayRef("CTH-SEN", date(2026, 10, 14)), SittingDayRef("CTH-SEN", date(2026, 10, 15)),
                    SittingDayRef("CTH-HOR", date(2026, 10, 28)), SittingDayRef("CTH-HOR", date(2026, 10, 29))]
    [ref] = connector.list_documents(SittingDayRef("CTH-HOR", date(2026, 10, 29)))
    assert ref.url == f"{BASE}/representatives_debates/2026-10-29.xml" and ref.key == "xml:CTH-HOR:2026-10-29"
    assert connector.list_documents(SittingDayRef("CTH-SEN", date(2026, 10, 16))) == []


def test_proof_flag_pages_and_federation_chamber(house):
    assert house.version == "proof" and house.method == "xml"
    assert all(s.page for s in house.speeches)
    assert any(s.proceeding_type.startswith("Federation Chamber: ") for s in house.speeches)


def test_question_time_with_interjections_and_the_chair(house):
    qt = [s for s in house.speeches if s.proceeding_type.startswith("QUESTIONS WITHOUT NOTICE")][:6]
    kinds = [(s.speaker_name, s.proceeding_type.split("(")[-1].rstrip(")")) for s in qt]
    assert kinds[0] == ("Mr KENNEDY", "question")
    assert ("Mr ALBANESE", "answer") in kinds and ("The SPEAKER", "presiding") in kinds
    pm = next(s for s in qt if s.speaker_name == "Mr ALBANESE")
    assert (pm.party, pm.speaker_role, pm.electorate) == ("ALP", "Prime Minister", "Grayndler")
    chair = next(s for s in qt if s.speaker_name == "The SPEAKER")
    assert chair.speaker_role == "presiding officer (Milton Dick)"
    kennedy = next(s for s in house.speeches if s.speaker_name == "Mr Kennedy")
    assert kennedy.proceeding_type.endswith("(interjection)") and kennedy.party == "LP"


def test_senate_questions_supplementaries_and_ministers(senate):
    qt = [s for s in senate.speeches if s.proceeding_type.startswith("QUESTIONS WITHOUT NOTICE")]
    wong = next(s for s in qt if s.speaker_name == "Senator WONG")
    assert wong.speaker_role.startswith("Minister for Foreign Affairs") and wong.proceeding_type.endswith("(answer)")
    assert qt[0].speaker_name == "Senator BLYTH" and qt[0].text.startswith("My question is to the Minister")
    assert sum(1 for s in senate.speeches if s.proceeding_type.endswith("(interjection)")) > 20


def test_no_speaker_header_left_in_text(house, senate):
    import re
    for doc in (house, senate):
        assert not [s for s in doc.speeches if re.match(r"^(?:Senator|Mr|Ms|Mrs|Dr|The) [A-Z]{2,}", s.text)]
        assert not [s for s in doc.speeches if s.speaker_name and s.speaker_name.endswith(":")]


def test_party_codes_give_sides(house):
    when = date(2026, 10, 29)
    sides = {s.speaker_name: speaker_side("CTH", when, s.party, s.speaker_role) for s in house.speeches}
    assert sides["Mr ALBANESE"] == "government" and sides["Mr KENNEDY"] == "opposition"   # LP
    assert sides["The SPEAKER"] == "unknown"                                              # the chair
    assert speaker_side("CTH", when, "AG", None) == "crossbench" and speaker_side("CTH", when, "ON", None) == "crossbench"
