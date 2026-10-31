"""HTTP API (spec §6 "Minimum API").

Reading is open to everyone, as the product owner chose in the design
(PROGRESS.md, decision D2). Anything that costs money or changes data
(scans, imports, confirming program topics) needs the ACAG sign-in.
"""

import asyncio
import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app import auth, sample_data, scans

router = APIRouter(prefix="/api")


class Login(BaseModel):
    username: str
    password: str


# ---- Auth -----------------------------------------------------------------

@router.post("/auth/login")
def login(body: Login, request: Request, response: Response):
    auth.check_login(request, body.username, body.password)
    auth.set_session(request, response)
    return {"user": auth.get_settings().app_username}


@router.post("/auth/logout")
def logout(response: Response):
    auth.clear_session(response)
    return {"ok": True}


@router.get("/auth/me")
def me(request: Request):
    return {"user": auth.current_user(request)}


# ---- Health and status ----------------------------------------------------

@router.get("/health")
def health():
    return {"ok": True}


@router.get("/status")
def status():
    if auth.get_settings().scan_mode == "real":
        from app import live_status
        return live_status.status()
    ds, refreshed = sample_data.dataset(), sample_data.refreshed()
    sources = []
    for j in ds["jurisdictions"]:
        text = j["statusText"]
        if refreshed and j["status"] == "ok" and "new" in ds["scanResults"][j["code"]]:
            text = ds["scanResults"][j["code"]]
        sources.append({"code": j["code"], "parliament": j["parl"], "status": j["status"], "text": text})
    running = scans.running()
    return {
        "sampleData": True,
        "asOf": ds["asOf"],
        "lastChecked": ds["asOf"],
        "previousCheck": ds["previousCheck"],
        "hansardTo": "2026-10-30" if refreshed else "2026-10-29",
        "storedFrom": sample_data.period_start("2m"),
        "refreshed": refreshed,
        "sources": sources,
        "registers": ds["scanResults"]["REG"] if refreshed else "9 of 9 checked today",
        "upcomingSittings": ds["upcomingSittings"],
        "scanRunning": running.snapshot() if running else None,
    }


# ---- Scans ----------------------------------------------------------------

@router.post("/scans", dependencies=[Depends(auth.require_session)])
async def start_scan():
    return scans.start().snapshot()


def _scan(run_id: int) -> scans.Progress:
    p = scans.get(run_id)
    if p is None:
        raise HTTPException(404, "No such scan")
    return p


@router.get("/scans/{run_id}")
def get_scan(run_id: int):
    return _scan(run_id).snapshot()


@router.get("/scans/{run_id}/events")
async def scan_events(run_id: int):
    p = _scan(run_id)

    async def stream():
        while True:
            yield f"data: {json.dumps(p.snapshot())}\n\n"
            if p.done:
                return
            p.changed.clear()
            try:
                await asyncio.wait_for(p.changed.wait(), timeout=15)
            except TimeoutError:
                yield ": keep-alive\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})


# ---- Content (F1–F4) ------------------------------------------------------

@router.get("/offices")
def offices():
    return sample_data.dataset()["jurisdictions"]


@router.get("/sectors")
def sectors():
    return sample_data.dataset()["sectors"]


@router.get("/issues")
def issues():
    """Issues raised across parliaments (Compare)."""
    return sample_data.dataset()["issues"]


@router.get("/items")
def items(jur: str | None = None, period: str | None = None, sector: str | None = None):
    return sample_data.filter_items(sample_data.items(), jur, period, sector)


@router.get("/items/{item_id}")
def item(item_id: str):
    for i in sample_data.items():
        if i["id"] == item_id:
            return i
    raise HTTPException(404, "No such item")


def _mentions(jur=None, period=None, sector=None):
    return [i for i in sample_data.filter_items(sample_data.items(), jur, period, sector) if i["ofc"] and i["sent"]]


@router.get("/mentions")
def mentions(jur: str | None = None, period: str | None = None, sector: str | None = None):
    return _mentions(jur, period, sector)


@router.get("/developments")
def developments(jur: str | None = None, period: str | None = None, sector: str | None = None):
    return [i for i in sample_data.filter_items(sample_data.items(), jur, period, sector) if i["feat"] == "F3"]


@router.get("/reports")
def reports(office: str | None = None):
    rows = sample_data.dataset()["reports"]
    return [r for r in rows if not office or r["jur"] == office.upper()]


@router.get("/reports/{report_id}")
def report(report_id: str):
    for r in sample_data.dataset()["reports"]:
        if r["id"] == report_id:
            return r | {"mentions": [i for i in sample_data.items() if i["jur"] == r["jur"] and i["rep"] == r["title"] and i["sent"]]}
    raise HTTPException(404, "No such report")


@router.get("/gaps")
def gaps(jur: str | None = None, sector: str | None = None):
    rows = sample_data.dataset()["gaps"]
    return [g for g in rows if (not jur or jur.upper() == "ALL" or g["jur"] == jur.upper()) and (not sector or g["theme"] == sector)]


@router.get("/gaps/{gap_id}")
def gap(gap_id: str):
    for g in sample_data.dataset()["gaps"]:
        if g["id"] == gap_id:
            return g
    raise HTTPException(404, "No such gap")


@router.get("/search")
def search(q: str = "", jur: str | None = None, period: str | None = "2m"):
    """Stand-in for FTS5 search over stored speeches (Phase 2)."""
    return sample_data.filter_items(sample_data.items(), jur, period, q=q)


# ---- Exports --------------------------------------------------------------

def _csv(name: str, header: list[str], rows: list[list]) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return Response(buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


ITEM_COLS = ["date", "jur", "chamber", "headline", "speaker", "role", "side", "sent", "reason", "quote", "url"]


@router.get("/export/mentions.csv")
def export_mentions(jur: str | None = None, period: str | None = None, sector: str | None = None):
    rows = _mentions(jur, period, sector)
    return _csv("mentions.csv", ITEM_COLS + ["report"], [[i.get(c) or "" for c in ITEM_COLS] + [i["rep"] or ""] for i in rows])


@router.get("/export/items.csv")
def export_items(q: str = "", jur: str | None = None, period: str | None = None, sector: str | None = None):
    rows = sample_data.filter_items(sample_data.items(), jur, period, sector, q)
    return _csv("items.csv", ITEM_COLS, [[i.get(c) or "" for c in ITEM_COLS] for i in rows])


@router.get("/export/gaps.csv")
def export_gaps(jur: str | None = None, sector: str | None = None):
    rows = sorted(gaps(jur, sector), key=lambda g: -g["score"])
    by_id = {i["id"]: i for i in sample_data.items()}
    return _csv("gaps-longlist.csv", ["office", "issue", "sector", "coverage", "score", "breakdown", "closest", "reason", "evidence"],
                [[g["jur"], g["issue"], g["theme"], g["coverage"], g["score"],
                  "; ".join(f"{p['n']} {p['v']}/{p['w']}" for p in g["parts"]), g["closest"], g["why"],
                  " ".join(by_id[e]["url"] for e in g["ev"] if e in by_id)] for g in rows])


@router.get("/export/brief.docx")
@router.get("/export/brief.pdf")
@router.get("/export/gaps.docx")
def export_documents():
    raise HTTPException(501, "Word and PDF exports arrive in Phase 7.")
