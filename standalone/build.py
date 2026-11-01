"""Build the self-contained Hansard Watch page from real data.

Inputs (all in this repo):
  standalone/data/scan/*.json        Hansard Watch store snapshot, 1 Nov 2026 (Phase 0/2 scans)
  standalone/data/cowork/vago-scan.json  Victorian Hansard scan for VAGO (Cowork task), 3 Feb – 24 Sep 2026
  config/offices.yaml, governments.yaml, sources.yaml, themes.yaml

Output:
  standalone/hansard-watch.html      one file: page, styles, script and data

Run:  python3 standalone/build.py
"""

import json
import re
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "standalone"
AS_OF = "2026-11-01"
REPO_DOCS = "https://github.com/benjiang8gmail/acag/blob/claude/hansard-watch-app/docs/sources.md"


def load_json(p):
    return json.loads((HERE / "data" / p).read_text())


def load_yaml(p):
    return yaml.safe_load((ROOT / "config" / p).read_text())


scan = {k: load_json(f"scan/{k}.json") for k in ["mentions", "days", "sides", "parliaments", "scan", "vic_days", "vic_items"]}
vic = load_json("cowork/vago-scan.json")
offices = {o["jurisdiction"]: o for o in load_yaml("offices.yaml")["offices"]}
governments = load_yaml("governments.yaml")["parliaments"]
sources = load_yaml("sources.yaml")["sources"]
themes = load_yaml("themes.yaml")["themes"]

# ---- Jurisdictions ---------------------------------------------------------
# Display names, colours and tile-map positions are the design's (prototype).
DISPLAY = {
    "CTH": ("Cth", "Commonwealth", "Parliament of Australia", "ANAO", "#4f52b2", [1, 1]),
    "NSW": ("NSW", "New South Wales", "Parliament of NSW", "Audit Office NSW", "#0f6cbd", [2, 3]),
    "VIC": ("Vic", "Victoria", "Parliament of Victoria", "VAGO", "#5c2e91", [3, 3]),
    "QLD": ("Qld", "Queensland", "Queensland Parliament", "QAO", "#a4262c", [1, 3]),
    "SA": ("SA", "South Australia", "Parliament of South Australia", "Audit Office SA", "#c239b3", [2, 2]),
    "WA": ("WA", "Western Australia", "Parliament of Western Australia", "OAG WA", "#ca5010", [2, 1]),
    "TAS": ("Tas", "Tasmania", "Parliament of Tasmania", "Audit Tasmania", "#107c10", [4, 3]),
    "ACT": ("ACT", "Australian Capital Territory", "ACT Legislative Assembly", "ACT Audit Office", "#0099bc", [2, 4]),
    "NT": ("NT", "Northern Territory", "Legislative Assembly of the NT", "NT Auditor-General", "#8e562e", [1, 2]),
}
CHAMBER = {s["id"]: s["chamber"] for s in sources}
CHAMBER.update({"VIC-PAEC": "Public Accounts and Estimates Committee"})
STATUS = {p["code"]: p for p in scan["parliaments"]}

days_by = {}
for d in scan["days"]:
    days_by.setdefault(d["code"], []).append(d)


def gov_info(code):
    g = governments[code]
    cur = g["periods"][-1]
    head = cur.get("head_of_government") or {}
    lead = cur.get("leader_of_opposition") or {}
    return {
        "head": head.get("name"), "title": head.get("title"), "party": head.get("party"),
        "type": cur.get("government_type"), "government": cur.get("government", []), "opposition": cur.get("opposition", []),
        "leader": lead.get("name"), "nextElection": str(g.get("next_election")) if g.get("next_election") else None,
    }


jurisdictions = []
for code, (short, name, parl, office_short, color, pos) in DISPLAY.items():
    o, st = offices[code], STATUS[code]
    rows = days_by.get(code, [])
    read = None
    if rows:
        ds = sorted({r["date"] for r in rows})
        read = {"from": ds[0], "to": ds[-1], "days": len(ds), "speeches": sum(r["speeches"] for r in rows), "by": "scan"}
    if code == "VIC":
        cov = vic["meta"]["coverage"]
        read = {"from": "2026-02-03", "to": "2026-09-24", "by": "cowork",
                "days": cov["lc_days_checked"] + cov["la_days_checked"], "daysTotal": cov["lc_days_total"] + cov["la_days_total"],
                "paec": cov["paec_checked"], "paecTotal": cov["paec_total"], "speeches": None}
    prog = o.get("program") or {}
    jurisdictions.append({
        "code": code, "short": short, "name": name, "parl": parl, "office": office_short, "officeName": o["name"],
        "officeCode": o["code"], "ag": o["auditor_general"], "color": color, "tilePos": pos,
        "chambers": [{"id": s, "name": CHAMBER.get(s, s)} for s in o["sources"]],
        "status": {"live": "live", "blocked": "blocked", "empty pages": "empty"}.get(st["status"], st["status"]),
        "route": st["route"], "needs": None if st["needs"] in ("—", "-", "") else st["needs"],
        "read": read,
        "program": {"name": prog.get("name"), "published": prog.get("published"), "url": prog.get("url") or prog.get("document")},
        "website": o["website"], "reportsUrl": o.get("reports_url"),
        "gov": gov_info(code),
    })

# ---- Sectors (keyword rule) ---------------------------------------------------
# A transparent stand-in until AI theming (Phase 4): a mention belongs to a sector
# when its debate title or text contains one of that sector's pre-filter terms.
SECTOR_RES = []
for t in themes:
    terms = [re.escape(x) for x in t["terms"]]
    rx = re.compile(r"\b(" + "|".join(terms) + r")s?\b", re.I)
    SECTOR_RES.append((t["id"], rx))
CHAMBER_WORDS = re.compile(r"legislative council|council chamber|federation chamber|legislative assembly", re.I)


def sectors_for(*texts):
    blob = CHAMBER_WORDS.sub(" ", " ".join(x for x in texts if x))
    return [sid for sid, rx in SECTOR_RES if rx.search(blob)]


# ---- Mentions ------------------------------------------------------------------
QLD_REPORT = re.compile(r"Auditor-General(?:['’]s)?\s+Report\s+(\d+)\s*:\s*(\d{4}[-–]\d{2})\s*[—–-]\s*([^,.;:]+)", re.I)


def tidy_debate(s):
    s = (s or "").strip()
    if s.isupper() and len(s) > 6:
        s = s.capitalize()
    return s


mentions = []
for r in scan["mentions"]:
    m = QLD_REPORT.search(r["excerpt"])
    rep = f"{m.group(3).strip()} (Report {m.group(1)}: {m.group(2)})" if m else None
    mentions.append({
        "id": f"s{r['id']}", "src": "scan", "jur": r["parliament"], "date": r["date"], "chamber": r["chamber"],
        "house": CHAMBER.get(r["chamber"], r["chamber"]), "speaker": r["speaker"], "party": r["party"] or None,
        "side": r["side"] or None, "debate": tidy_debate(r["debate"]), "kind": r["kind"], "page": r["page"],
        "text": r["excerpt"], "url": r["source"], "report": rep, "reportHow": "pattern" if rep else None,
        "sectors": sectors_for(r["debate"], r["excerpt"]),
    })

VIC_SIDE = {"Labor": "government", "Liberal": "opposition", "Nationals": "opposition", "Greens": "crossbench", "Legalise Cannabis": "crossbench"}
HOUSE = {"Council": "VIC-LC", "Assembly": "VIC-LA", "PAEC": "VIC-PAEC"}
# Cowork's `report` field names what the member referred to. Only some name a VAGO report.
NOT_A_REPORT = ("VAGO public rebuttal", "Integrity agency", "Joint integrity", "A-G ", "Engagement with", "VAGO's own",
                "Committee recommendation", "PAEC oversight", "'The auditor'", "Public lottery licence extension")
for r in vic["mentions"]:
    first_party = r["party"].split(" / ")[0]
    side = VIC_SIDE.get(first_party, "witness")
    is_report = not r["report"].startswith(NOT_A_REPORT)
    mentions.append({
        "id": f"v{r['n']}", "src": "cowork", "jur": "VIC", "date": r["date"], "chamber": HOUSE[r["house"]],
        "house": CHAMBER[HOUSE[r["house"]]], "speaker": r["speaker"], "party": r["party"], "side": side, "seat": r.get("seat"),
        "debate": r["debate"], "kind": "committee" if r["house"] == "PAEC" else "speech", "page": None,
        "text": r["quote"], "note": r["note"], "url": r["url"], "report": r["report"] if is_report else None,
        "reportHow": "scan" if is_report else None, "topic": None if is_report else r["report"],
        "stance": r["stance"], "verified": r["verified"], "vsector": r["sector"],
        "sectors": sectors_for(r["debate"], r["quote"], r["report"]),
    })
# One name per report: Hansard text varies in case and wording, the number doesn't.
names = {}
for m in mentions:
    if m["reportHow"] == "pattern":
        key = re.search(r"\(Report .*\)$", m["report"]).group(0)
        names.setdefault(key, []).append(m["report"])
best = {k: max(set(v), key=lambda t: (v.count(t), sum(c.isupper() for c in t))) for k, v in names.items()}
for m in mentions:
    if m["reportHow"] == "pattern":
        m["report"] = best[re.search(r"\(Report .*\)$", m["report"]).group(0)]
mentions.sort(key=lambda m: (m["date"], m["id"]), reverse=True)

# ---- Developments --------------------------------------------------------------
ctx = vic["meta"]["context"]
dev = []


def add_dev(jur, d, typ, source, headline, body, url, why=None):
    dev.append({"id": f"d{len(dev) + 1}", "jur": jur, "date": d, "type": typ, "source": source,
                "headline": headline, "body": body, "why": why, "url": url})


topic1 = next(t for t in vic["topics"] if t["rank"] == 1)
add_dev("VIC", "2026-07-28", "Governance", "Public record", "Ben Carroll sworn in as Premier after Jacinta Allan resigns", ctx[2],
        None, topic1["why"])
add_dev("VIC", "2026-08-20", "Governance", "Public record", "Royal Commission into major project integrity established", ctx[3],
        None, topic1["changed"])
waste = next(m for m in vic["mentions"] if m["stance"] == "call for audit")
add_dev("VIC", waste["date"], "Audit requests", "Hansard", "Committee recommends an Auditor-General review of the waste-to-energy framework",
        waste["note"], waste["url"], "The only request for new VAGO work in eight months, and it comes from a standing committee of the Parliament.")
add_dev("VIC", "2026-08-26", "Responses", "Hansard", "Government cuts Suburban Rail Loop estimate after VAGO audit", ctx[5],
        "https://www.audit.vic.gov.au/report/delivering-suburban-rail-loop",
        "The Authority had accepted none of the five recommendations directed to it; the government acted within two days.")
add_dev("VIC", "2026-09-24", "Governance", "Hansard", "Final sitting day of the 60th Parliament", ctx[0] + " " + ctx[1],
        scan["vic_days"][-1]["link"], "Reports tabled after the House rose cannot be debated by this Parliament.")
add_dev("VIC", "2026-10-01", "Mandate", "Public record", "IBAC gains 'follow the money' powers over subcontractors", ctx[4],
        None, "Changes the integrity landscape around the bodies VAGO audits; no equivalent change applies to VAGO.")
add_dev("VIC", "2026-06-24", "Program", "Office website", "VAGO Annual Plan 2026–27 tabled",
        f"{sum(1 for p in vic['plan'] if p['status'] == 'Outstanding')} of {len(vic['plan'])} planned audits are still outstanding at 30 Oct 2026.",
        offices["VIC"]["program"]["url"])
for t in vic["tabled"]:
    add_dev("VIC", t["date"], "New reports", "Office website", t["title"], t["finding"], t["url"],
            {"No": "Not raised in Parliament.", "Yes": f"Raised in Parliament: {t['debated']}.",
             "Post-rising": "Tabled after Parliament rose, so this Parliament cannot debate it."}[t["raised"]])
# Other offices, from the Phase 0 recon (docs/sources.md).
add_dev("ACT", "2026-02-08", "Governance", "Public record", "Ajay Sharma PSM becomes ACT Auditor-General",
        "Appointed to 7 Feb 2033 (DI2025-305), replacing Michael Harris.", REPO_DOCS)
add_dev("NT", "2026-06-01", "Governance", "Public record", "NT ICAC and Ombudsman merge into the Integrity and Ethics Commissioner",
        "Since 1 Jun 2026 the two bodies are one office, the Office of the Integrity and Ethics Commissioner.", REPO_DOCS)
add_dev("ACT", "2026-06-09", "Program", "Office website", "ACT Audit Office releases its Performance Audit Program 2026–27",
        "Covers 2026–27 and 2027–28.", offices["ACT"]["program"]["document"])
add_dev("TAS", "2026-06-22", "Program", "Office website", "Auditor-General's Annual Plan 2026–27 signed", "Published under s11 of the Audit Act 2008.",
        offices["TAS"]["program"]["url"])
add_dev("QLD", "2026-06-30", "Program", "Office website", "QAO publishes its Forward work plan 2026–29",
        "Published with an acquittal of the office's prior work plans (June 2026).", offices["QLD"]["program"]["document"])
add_dev("NSW", "2026-07-31", "Program", "Office website", "Audit Office NSW publishes its Audit Work Plan 2026–2029",
        "Web page and PDF, \"As at July 2026\".", offices["NSW"]["program"]["url"])
add_dev("CTH", "2026-07-31", "Program", "Office website", "ANAO Annual Audit Work Program 2026–27 finalised",
        "The draft was open for comment from 17 Mar to 10 Apr 2026; the final was published about July 2026.", offices["CTH"]["program"]["url"])
dev.sort(key=lambda x: x["date"], reverse=True)

# ---- Coming up ------------------------------------------------------------------
events = [
    {"date": "2026-11-03", "jur": "VIC", "text": "Parliament expires; caretaker period starts at 6 pm"},
    {"date": "2026-11-09", "jur": "VIC", "text": "Royal Commission public hearings begin (to 20 Nov)"},
    {"date": "2026-11-28", "jur": "VIC", "text": "Victorian state election"},
    {"date": "2027-03-13", "jur": "NSW", "text": "NSW state election"},
]

data = {
    "asOf": AS_OF,
    "built": date.today().isoformat(),
    "provenance": {
        "scan": "Hansard Watch store snapshot (Phase 0 session, scan run 3 at 00:09 UTC 1 Nov 2026): speeches whose text names an Auditor-General or audit office.",
        "cowork": vic["source"],
        "config": "config/offices.yaml, governments.yaml, sources.yaml, themes.yaml (Phase 0 recon, 31 Oct 2026)",
    },
    "scan": scan["scan"][0],
    "jurisdictions": jurisdictions,
    "mentions": mentions,
    "days": scan["days"],
    "sides": scan["sides"],
    "sectors": [{"id": t["id"], "label": t["label"]} for t in themes],
    "developments": dev,
    "events": events,
    "vic": {
        "meta": vic["meta"], "tabled": vic["tabled"], "topics": vic["topics"], "plan": vic["plan"],
        "limitations": vic["limitations"], "themes": [dict(name=k, **v) for k, v in vic["themes"].items()],
        "signals": vic["signals"], "blindSpots": vic["blind_spots"], "coverage": vic["coverage"],
        "corrections": vic["corrections"], "days": scan["vic_days"], "items": scan["vic_items"],
    },
}

blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
page = (HERE / "app.html").read_text().replace("__HW_DATA__", blob)
(HERE / "hansard-watch.html").write_text(page)

# The claude.ai page: the host supplies the doctype, charset, viewport and the
# :root safe-area padding, so the page keeps only its title, styles and body.
art = page.replace("const ARTIFACT = false;", "const ARTIFACT = true;")
head = art.split("<head>", 1)[1].split("</head>", 1)[0]
head = "\n".join(l for l in head.splitlines() if not l.startswith(('<meta charset', '<meta name="viewport"', '<meta name="description"')))
body = art.split("<body>", 1)[1].rsplit("</body>", 1)[0]
ART_CSS = "<style>.hdr { padding-top: 0; } .bnav { padding-bottom: 0; } .ob-foot { padding-bottom: 12px; }</style>"
(HERE / "hansard-watch.artifact.html").write_text(head.strip() + "\n" + ART_CSS + "\n" + body.strip() + "\n")
print(f"hansard-watch.html: {len(page):,} bytes · {len(mentions)} mentions "
      f"({sum(m['src'] == 'scan' for m in mentions)} scan, {sum(m['src'] == 'cowork' for m in mentions)} Victorian) · "
      f"{len(dev)} developments · {sum(1 for m in mentions if m['report'])} report mentions · "
      f"{sum(1 for m in mentions if m['sectors'])} with a sector")
