"""Phase 0 config must cover every chamber, office and parliament the spec
names, and the files must agree with each other (spec §5, §9.2, §9.4, §14)."""
from pathlib import Path

import yaml

CONFIG = Path(__file__).resolve().parents[2] / "config"
PARLIAMENTS = {"CTH", "NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"}
OFFICES = {"ANAO", "AONSW", "VAGO", "QAO", "SAAGD", "OAGWA", "AUDTAS", "ACTAO", "NTAGO"}


def load(name):
    return yaml.safe_load((CONFIG / name).read_text())


def test_fifteen_chambers_across_nine_parliaments():
    sources = load("sources.yaml")["sources"]
    ids = [s["id"] for s in sources]
    assert len(ids) == 15 == len(set(ids))
    assert {s["parliament"] for s in sources} == PARLIAMENTS
    assert {"ACT-LA", "NT-LA", "VIC-LA"} <= set(ids)
    # Nothing is enabled until a real fixture exists and the connector passes (Phase 2).
    assert not any(s["enabled"] for s in sources)


def test_nine_offices_link_to_real_chambers():
    offices = load("offices.yaml")["offices"]
    source_ids = {s["id"] for s in load("sources.yaml")["sources"]}
    assert {o["code"] for o in offices} == OFFICES
    for o in offices:
        assert o["auditor_general"], o["code"]
        assert set(o["sources"]) <= source_ids, o["code"]
        assert o["jurisdiction"] in PARLIAMENTS


def test_lexicon_covers_every_office_and_matches_offices_yaml():
    lex = load("lexicon.yaml")
    offices = {o["code"]: o for o in load("offices.yaml")["offices"]}
    assert set(lex["offices"]) == OFFICES
    assert set(lex["auditors_general"]) == OFFICES
    assert set(lex["attribution"]) == PARLIAMENTS
    assert set(lex["attribution"].values()) == OFFICES
    for code, ag in lex["auditors_general"].items():
        surname = ag["current"]["name"].split()[-1]
        assert surname in offices[code]["auditor_general"], code
        assert any(surname in form for form in ag["refer_as"]), code
    assert set(lex["committees"]) == PARLIAMENTS
    assert set(lex["integrity_bodies"]) == PARLIAMENTS
    assert "Auditor General" in lex["generic_terms"]  # WA spelling, no hyphen


def test_governments_cover_every_parliament_with_a_current_period():
    gov = load("governments.yaml")["parliaments"]
    source_ids = {s["id"] for s in load("sources.yaml")["sources"]}
    assert set(gov) == PARLIAMENTS
    for code, p in gov.items():
        assert set(p["chambers"]) <= source_ids, code
        current = [x for x in p["periods"] if x["to"] is None]
        assert len(current) == 1, code
        c = current[0]
        assert c["government"] and c["opposition"], code
        assert not set(c["government"]) & set(c["opposition"]), code
