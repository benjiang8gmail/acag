"""Build config/members/{NSW,ACT,QLD}.yaml: who sits in each chamber, and their party.

Spec §9.4: speaker side is computed in code from party and ministerial role. NSW and ACT
Hansard don't print party, and QLD prints it only on full speaker headers, so each
parliament needs a member list.

Sources (fetched politely by `make members` into data/members-src/; see docs/sources.md):
- QLD: the Parliament's own Members Photo Sheet PDF (official).
- NSW, ACT, NT: the official member lists sit behind bot protection that blocks this build
  environment (parliament.nsw.gov.au, elections.act.gov.au), so the lists come from
  Wikipedia's "Members of the ..." articles (secondary, CC BY-SA). Every entry is
  cross-checked against names and electorates printed in Hansard by the tests, and
  config/members/overrides.yaml wins over any generated entry.

Usage: python -I scripts/build_members.py SRC_DIR
"""
from __future__ import annotations

import hashlib
import re
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "config" / "members"

SOURCES = {
    "NSW-LA": ("wp-nsw-la.html", "https://en.wikipedia.org/wiki/Members_of_the_New_South_Wales_Legislative_Assembly,_2023%E2%80%932027"),
    "NSW-LC": ("wp-nsw-lc.html", "https://en.wikipedia.org/wiki/Members_of_the_New_South_Wales_Legislative_Council,_2023%E2%80%932027"),
    "ACT-LA": ("wp-act.html", "https://en.wikipedia.org/wiki/Members_of_the_Australian_Capital_Territory_Legislative_Assembly,_2024%E2%80%932028"),
    "NT-LA": ("wp-nt.html", "https://en.wikipedia.org/wiki/Members_of_the_Northern_Territory_Legislative_Assembly,_2024%E2%80%932028"),
    "QLD-LA": ("qld-photosheet.pdf", "https://documents.parliament.qld.gov.au/members/photosheet/MembersPhotoSheet.pdf"),
}

# Party names as the sources write them → the codes used in config/governments.yaml.
PARTY_CODES = {
    "labor": "ALP", "alp": "ALP", "liberal": "LIB", "canberra liberals": "LIB", "national": "NAT",
    "nationals": "NAT", "greens": "GRN", "act greens": "GRN", "grn": "GRN", "independent": "IND", "ind": "IND",
    "shooters, fishers, farmers": "SFF", "shooters, fishers and farmers": "SFF", "animal justice": "AJP",
    "legalise cannabis": "LCP", "libertarian": "LBT", "one nation": "PHON", "family first": "FF",
    "lnp": "LNP", "liberal national": "LNP", "kap": "KAP", "katter's australian": "KAP",
    "country liberal": "CLP", "clp": "CLP",
}
TERM = re.compile(r"^(\d{4})\s*[–-]\s*(present|\d{4})")


def party_code(name: str) -> str:
    key = re.sub(r"\s+", " ", name).strip().lower()
    key = key.split(" / ")[-1]   # "One Nation / Independent": the current affiliation is last
    if key in PARTY_CODES:
        return PARTY_CODES[key]
    if "independent" in key:     # "Independent Liberal", "Fiona Carrick Independent", "Independents for Canberra"
        return "IND"
    return name.strip()


class _Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.t, self.row, self.cell, self.skip = [], None, None, None, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table" and "wikitable" in (a.get("class") or ""):
            self.t = []
            self.tables.append(self.t)
        elif self.t is not None and tag == "tr":
            self.row = []
            self.t.append(self.row)
        elif self.t is not None and tag in ("td", "th") and self.row is not None:
            self.cell = []
            self.row.append(self.cell)
        elif tag in ("sup", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag == "table":
            self.t = self.row = self.cell = None
        elif tag in ("sup", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if self.cell is not None and not self.skip:
            self.cell.append(data)


def wikipedia_members(html: str, has_electorate: bool) -> list[dict]:
    """Current members from a "Members of the ..." table. A member who changed party has
    continuation rows (party, term) under their main row; the row marked "present" wins."""
    p = _Tables()
    p.feed(html)
    table = max(p.tables, key=len)
    current: dict[str, dict] = {}
    last = None
    for row in table[1:]:
        cells = [re.sub(r"\s+", " ", "".join(c)).strip() for c in row]
        cells = [c for c in cells if c]
        if len(cells) >= 4 and TERM.match(cells[3]):
            last = {"name": cells[0], "party": party_code(cells[1])}
            if has_electorate:
                last["electorate"] = cells[2]
            else:
                last["term_ends"] = cells[2]
            if "present" in cells[3]:
                current[last["name"]] = dict(last)
        elif len(cells) == 2 and last and TERM.match(cells[1]):   # continuation: party changed
            if "present" in cells[1]:
                current[last["name"]] = {**last, "party": party_code(cells[0])}
    return list(current.values())


def qld_photosheet(raw: bytes) -> list[dict]:
    sys.path.insert(0, str(ROOT / "backend"))
    from parsers.pdf import pdf_pages

    lines = [l.strip() for p in pdf_pages(raw) for l in p.splitlines() if l.strip()]
    skip = {"Members of the", "Legislative Assembly", "58th Parliament"}
    furniture = re.compile(r"^(?:\d+|(?:LNP|ALP|KAP|GRN|IND|PHON) [A-Z].*|Parliament House.*|George Street.*"
                           r"|Brisbane Qld.*|ph:.*|www\..*|(?:As at|Updated|updated)\b.*)$")   # legend, footer
    lines = [l for l in lines if l not in skip and not furniture.match(l)]
    parties = r"(LNP|ALP|KAP|GRN|IND|PHON)"
    out, i = [], 0
    while i + 2 < len(lines):
        name, rest = lines[i], []
        j = i + 1
        while j < len(lines):
            m = re.match(rf"^(?:(?P<pre>.*?)\s+)?{parties}$", lines[j])
            if m:
                if m.group("pre"):
                    rest.append(m.group("pre"))
                out.append({"name": name, "electorate": " ".join(rest), "party": m.group(2)})
                break
            rest.append(lines[j])
            j += 1
        i = j + 1
    return out


def main(src: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    built: dict[str, dict] = {}
    for chamber, (fname, url) in SOURCES.items():
        raw = (src / fname).read_bytes()
        as_of = None
        if chamber == "QLD-LA":
            members, kind = qld_photosheet(raw), "official"
            sys.path.insert(0, str(ROOT / "backend"))
            from parsers.pdf import pdf_pages
            if m := re.search(r"updated (\d{1,2} \w+ \d{4})", " ".join(pdf_pages(raw))):
                as_of = m.group(1)
        else:
            members, kind = wikipedia_members(raw.decode("utf-8"), has_electorate=chamber != "NSW-LC"), "secondary"
        built[chamber] = {"source": url, "source_kind": kind, "retrieved": today, "source_as_of": as_of,
                          "source_sha256": hashlib.sha256(raw).hexdigest(), "members": members}
    for code, chambers in {"NSW": ["NSW-LA", "NSW-LC"], "ACT": ["ACT-LA"], "QLD": ["QLD-LA"], "NT": ["NT-LA"]}.items():
        doc = {"parliament": code,
               "note": "Generated by scripts/build_members.py; do not edit. Corrections go in overrides.yaml.",
               "chambers": {c: built[c] for c in chambers}}
        (OUT / f"{code}.yaml").write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
        print(code, {c: len(built[c]["members"]) for c in chambers})


if __name__ == "__main__":
    main(Path(sys.argv[1]))
