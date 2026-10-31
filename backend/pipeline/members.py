"""Member lists and speaker side (spec §9.4).

- `MemberIndex` matches a Hansard speaker ("Ms JENNY LEONG", "MS CHEYNE", "Hon. G GRACE",
  "Mr Michael Daley") to a member in config/members/{parliament}.yaml, whose party it gives.
  config/members/overrides.yaml wins over generated entries.
- `speaker_side` is computed in code, never by the model: a minister (or other government
  office-holder) is government whatever their party; otherwise the party is compared with
  the government and opposition of the day in config/governments.yaml; anyone else is
  crossbench; no party means unknown.
"""

from __future__ import annotations

import re
from datetime import date
from functools import lru_cache

import yaml

from app.config import REPO_ROOT

MEMBERS_DIR = REPO_ROOT / "config" / "members"
GOVERNMENTS = REPO_ROOT / "config" / "governments.yaml"

HONORIFIC = re.compile(r"^(?:(?:The\s+)?Hon\.?|Mr|Ms|Mrs|Miss|Dr|Madam)\s+", re.I)
GOVERNMENT_ROLE = re.compile(
    r"\b(?:Minister|Premier|Treasurer|Attorney[- ]General|Parliamentary Secretary|Cabinet Secretary"
    r"|Leader of the House|Leader of the Government|Manager of Government Business|Government Whip"
    r"|Special Minister of State|Vice-President of the Executive Council|Chief Minister)\b", re.I)
OPPOSITION_ROLE = re.compile(r"\b(?:Leader of the Opposition|Opposition Leader|Shadow|Manager of Opposition Business|Opposition Whip)\b", re.I)
# Party spellings in Hansard or member lists → codes used in governments.yaml.
CANONICAL = {"GRN": "GRN", "GREENS": "GRN", "AG": "GRN", "IND": "IND", "LIB": "LIB", "LP": "LIB", "NAT": "NAT",
             "NATS": "NAT", "ALP": "ALP", "LNP": "LNP", "CLP": "CLP", "KAP": "KAP", "ON": "PHON", "PHON": "PHON"}


def _key(name: str) -> str:
    name = HONORIFIC.sub("", name.strip())
    name = re.sub(r"\(.*?\)", "", name)
    return re.sub(r"[^A-Z\- ]", "", name.upper().replace("’", "").replace("'", "")).strip()


def canonical_party(party: str | None) -> str | None:
    if not party:
        return None
    p = party.strip()
    return CANONICAL.get(p.upper(), p.upper())


class MemberIndex:
    def __init__(self, parliament: str):
        self.parliament = parliament
        self.by_chamber: dict[str, list[dict]] = {}
        path = MEMBERS_DIR / f"{parliament}.yaml"
        if path.exists():
            for chamber, data in (yaml.safe_load(path.read_text()) or {}).get("chambers", {}).items():
                self.by_chamber[chamber] = [dict(m, source_kind=data.get("source_kind")) for m in data["members"]]
        overrides = MEMBERS_DIR / "overrides.yaml"
        if overrides.exists():
            for chamber, entries in ((yaml.safe_load(overrides.read_text()) or {}).get(parliament) or {}).items():
                members = self.by_chamber.setdefault(chamber, [])
                for o in entries or []:
                    members[:] = [m for m in members if _key(m["name"]) != _key(o["name"])]
                    members.append(dict(o, source_kind="override"))

    def lookup(self, chamber: str, speaker_name: str | None, electorate: str | None = None) -> dict | None:
        """The member a Hansard speaker name refers to, or None if it can't be told."""
        if not speaker_name:
            return None
        members = self.by_chamber.get(chamber, [])
        key = _key(speaker_name)
        if not key:
            return None
        full = [m for m in members if _key(m["name"]) == key]
        if len(full) == 1:
            return full[0]
        tokens = key.split()
        surname = tokens[-1]
        same = [m for m in members if _key(m["name"]).split()[-1] == surname]
        if len(same) == 1:
            return same[0]
        if electorate:
            by_seat = [m for m in same if (m.get("electorate") or "").lower() == electorate.lower()]
            if len(by_seat) == 1:
                return by_seat[0]
        if len(tokens) > 1:   # "B JAMES", "G KELLY": initials, or a first name in title case
            first = tokens[0]
            by_first = [m for m in same if _key(m["name"]).split()[0].startswith(first[0])]
            if len(by_first) == 1:
                return by_first[0]
        return None


@lru_cache(maxsize=1)
def _governments() -> dict:
    return yaml.safe_load(GOVERNMENTS.read_text())["parliaments"]


def government_on(parliament: str, when: date) -> dict | None:
    p = _governments().get(parliament)
    if not p:
        return None
    for period in p["periods"]:
        start = period["from"] if isinstance(period["from"], date) else date.fromisoformat(str(period["from"]))
        end = period.get("to")
        end = end if isinstance(end, date) or end is None else date.fromisoformat(str(end))
        if start <= when and (end is None or when <= end):
            return period
    return None


def speaker_side(parliament: str, when: date, party: str | None, role: str | None) -> str:
    if role and role.startswith("presiding officer"):
        return "unknown"   # the chair speaks in a procedural role, whatever their party
    if role:
        if OPPOSITION_ROLE.search(role):
            return "opposition"
        if GOVERNMENT_ROLE.search(role):
            return "government"
    code = canonical_party(party)
    if not code:
        return "unknown"
    period = government_on(parliament, when)
    if not period:
        return "unknown"
    if code in {canonical_party(x) for x in period["government"]}:
        return "government"
    if code in {canonical_party(x) for x in period["opposition"]}:
        return "opposition"
    return "crossbench"


class Enricher:
    """Fills party (from the member list when Hansard doesn't print it) and speaker side."""

    def __init__(self, parliament: str):
        self.parliament = parliament
        self.index = MemberIndex(parliament)

    def party_for(self, chamber: str, speaker_name: str | None, role: str | None, electorate: str | None) -> str | None:
        name = speaker_name
        if role and role.startswith("presiding officer (") and role.endswith(")"):
            name = role[len("presiding officer ("):-1]   # who was in the chair
        member = self.index.lookup(chamber, name, electorate)
        return member["party"] if member else None

    def apply(self, chamber: str, when: date, speech) -> None:
        if not speech.party:
            speech.party = self.party_for(chamber, speech.speaker_name, speech.speaker_role, speech.electorate)
        speech.speaker_side = speaker_side(self.parliament, when, speech.party, speech.speaker_role) \
            if speech.speaker_name else None
