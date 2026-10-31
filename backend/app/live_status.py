"""`/api/status` from the real store (SCAN_MODE=real): one row per parliament (9).

Content pages still show sample data until AI analysis exists (Phase 4), so the
other fields the dashboard reads (as-of date, upcoming sittings) stay sample.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select

from . import sample_data, scans
from .db import ScanRun, SittingDay, Source, session

NAMES = {j["code"]: j["parl"] for j in sample_data.dataset()["jurisdictions"]}


def _day(d: date) -> str:
    return f"{d:%a} {d.day} {d:%b}"


def status() -> dict:
    from pipeline.sync import seed_sources

    ds = sample_data.dataset()
    with session() as db:
        seed_sources(db)
        sources = db.scalars(select(Source)).all()
        last_sat = dict(db.execute(select(SittingDay.source_id, func.max(SittingDay.sitting_date))
                                   .where(SittingDay.status == "done").group_by(SittingDay.source_id)).all())
        span = db.execute(select(func.min(SittingDay.sitting_date), func.max(SittingDay.sitting_date))
                          .where(SittingDay.status == "done")).one()
        last_run = db.scalar(select(ScanRun).where(ScanRun.status.in_(["done", "failed"]),
                                                   ScanRun.per_source_json.is_not(None))
                             .order_by(ScanRun.finished_at.desc()).limit(1))
        previous = db.scalars(select(ScanRun.finished_at).where(ScanRun.status.in_(["done", "failed"]))
                              .order_by(ScanRun.finished_at.desc()).limit(2)).all()

    rows, live = [], []
    for code in scans.CODES:
        mine = [s for s in sources if s.parliament == code]
        enabled = [s for s in mine if s.enabled]
        if not enabled:
            status = "blocked"
            text = scans.NOT_CHECKED.get(mine[0].status if mine else "unverified", scans.NOT_CHECKED["unverified"])
        else:
            live.append(code)
            statuses = {s.status for s in enabled}
            sat = [last_sat[s.id] for s in enabled if s.id in last_sat]
            if "blocked" in statuses:
                status, text = "blocked", "Blocked at the last check; access requested"
            elif "error" in statuses:
                status, text = "ok", "Last check failed; will retry"
            elif sat:
                status, text = "ok", f"Last sat {_day(max(sat))}"
            elif statuses <= {"no_sittings"}:
                status, text = "nosit", "Not sitting"
            else:
                status, text = "ok", "Not checked yet — refresh to load Hansard"
        rows.append({"code": code, "parliament": NAMES.get(code, code), "status": status, "text": text})

    today = scans.today()
    checked = previous[0].date() if previous else None
    running = scans.running()
    return {
        "sampleData": True,          # briefs and items are still sample until AI analysis (Phase 4)
        "liveHansard": live,         # parliaments whose Hansard is being stored for real
        "asOf": ds["asOf"],
        "lastChecked": (checked or today).isoformat(),
        "neverChecked": checked is None,
        "previousCheck": (previous[1].date() if len(previous) > 1 else checked or today).isoformat(),
        "hansardTo": (span[1] or today).isoformat(),
        "storedFrom": (span[0] or today - timedelta(days=61)).isoformat(),
        "refreshed": False,
        "sources": rows,
        "registers": "Office registers are not connected yet (next phase)",
        "upcomingSittings": ds["upcomingSittings"],
        "scanRunning": running.snapshot() if running else None,
        "lastScan": last_run.per_source_json if last_run else None,
    }
