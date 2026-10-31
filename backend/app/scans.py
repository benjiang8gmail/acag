"""Update scans (spec §8, §10.4).

Two modes, chosen by SCAN_MODE:

- `real` (default): each parliament with an enabled connector (config/sources.yaml) is
  synced in a worker thread with the polite fetcher, one parliament at a time, and its
  progress row updates live over SSE. Parliaments without a connector report why they
  weren't checked. Office registers come in Phase 3.
- `sample`: walks the 9 parliaments on a timer and reports the prototype's sample
  results, so the update flow can be demonstrated and the Playwright journeys that
  expect the sample "new" items keep working until AI analysis exists (Phase 4).

Either way: one scan at a time (§8.8), and every run is logged in `scan_runs`.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from .config import get_settings
from .db import ScanRun, Source, session, utcnow
from .sample_data import dataset

REGISTERS = "REG"
CODES = ["CTH", "NSW", "VIC", "QLD", "SA", "WA", "TAS", "ACT", "NT"]
NOT_CHECKED = {
    "blocked": "Not checked — the site blocks automated access; access requested",
    "unverified": "Not connected yet",
}

# Test hooks: how the real scan gets its fetcher and today's date.
FETCHER_FACTORY = None


def today() -> date:
    return datetime.now(ZoneInfo(get_settings().display_timezone)).date()


@dataclass
class Progress:
    run_id: int
    real: bool = False
    step: int = 0  # 0–8 = parliaments in order, 9 = office registers, 10 = finished
    changed: asyncio.Event = field(default_factory=asyncio.Event)
    texts: dict[str, str] = field(default_factory=dict)
    summary: dict | None = None

    @property
    def total(self) -> int:
        return len(CODES) + 1

    @property
    def done(self) -> bool:
        return self.step >= self.total

    def snapshot(self) -> dict:
        if not self.real:
            return self._sample_snapshot()
        rows = []
        for k, code in enumerate(CODES + [REGISTERS]):
            state = "done" if k < self.step else "checking" if k == self.step else "waiting"
            rows.append({"code": code, "state": state, "text": self.texts.get(code) if state == "done" else None})
        return {"id": self.run_id, "step": self.step, "total": self.total, "done": self.done, "sources": rows,
                "summary": self.summary if self.done else None}

    def _sample_snapshot(self) -> dict:
        ds = dataset()
        rows = []
        for k, code in enumerate([j["code"] for j in ds["jurisdictions"]] + [REGISTERS]):
            state = "done" if k < self.step else "checking" if k == self.step else "waiting"
            rows.append({"code": code, "state": state, "text": ds["scanResults"][code] if state == "done" else None})
        new_items = [i for i in ds["items"] if i["pending"]]
        return {
            "id": self.run_id, "step": self.step, "total": self.total, "done": self.done, "sources": rows,
            "summary": {
                "parliamentsSat": 4, "newSittingDays": 4, "newItems": len(new_items),
                "newItemsMentioningOffice": {c: sum(1 for i in new_items if i["jur"] == c and i["ofc"]) for c in {i["jur"] for i in new_items}},
                "registers": "1 new ACT Audit Office report",
            } if self.done else None,
        }


_current: Progress | None = None
_runs: dict[int, Progress] = {}


def running() -> Progress | None:
    return _current if _current and not _current.done else None


def get(run_id: int) -> Progress | None:
    return _runs.get(run_id)


# ---- sample mode ---------------------------------------------------------------

async def _walk_sample(p: Progress) -> None:
    delay = get_settings().sample_scan_step_seconds
    while not p.done:
        await asyncio.sleep(delay)
        p.step += 1
        p.changed.set()
    with session() as db:
        run = db.get(ScanRun, p.run_id)
        run.status, run.finished_at, run.per_source_json = "done", utcnow(), {"sample": True, **p.snapshot()}
        db.commit()


# ---- real mode -----------------------------------------------------------------

def describe(counts: dict) -> str:
    """One line per parliament for the progress panel, from the sync's per-chamber counts."""
    statuses = {c["status"] for c in counts.values()}
    if "blocked" in statuses:
        return "Blocked — the site refused this check; access requested"
    if "error" in statuses:
        note = next((c["note"] for c in counts.values() if c.get("note")), "")
        return f"Couldn't check — will retry next time{': ' + note if note else ''}"
    new_days = sum(c["new_days"] for c in counts.values())
    finals = sum(c["changed_documents"] for c in counts.values())
    speeches = sum(c["speeches_to_analyse"] for c in counts.values())
    pending = sum(c.get("days_pending", 0) for c in counts.values())
    parts = []
    if new_days:
        parts.append(f"{new_days} new sitting day{'s' if new_days != 1 else ''}")
    if finals:
        parts.append(f"{finals} proof{'s' if finals != 1 else ''} replaced by final")
    if speeches:
        parts.append(f"{speeches} speeches stored")
    if pending:
        parts.append(f"{pending} awaiting publication")
    if parts:
        return " · ".join(parts)
    return "Not sitting" if statuses == {"no_sittings"} else "No new sitting days"


def _sync_parliament(code: str, when: date, fetcher, totals: dict) -> str:
    from connectors.base import registry
    from pipeline.sync import sync_parliament

    with session() as db:
        sources = db.scalars(select(Source).where(Source.parliament == code)).all()
        enabled = [s for s in sources if s.enabled]
        if not enabled:
            status = sources[0].status if sources else "unverified"
            return NOT_CHECKED.get(status, NOT_CHECKED["unverified"])
        connector = registry().get(enabled[0].connector)
        if connector is None:
            return NOT_CHECKED["unverified"]
        counts = sync_parliament(db, connector(fetcher), fetcher, when, get_settings().data_dir)
    from dataclasses import asdict
    per = {sid: asdict(c) for sid, c in counts.items()}
    totals.update(per)
    return describe(per)


async def _walk_real(p: Progress) -> None:
    from pipeline.fetch import Fetcher
    from pipeline.sync import seed_sources

    settings = get_settings()
    fetcher = FETCHER_FACTORY() if FETCHER_FACTORY else Fetcher(settings.fetch_user_agent, settings.fetch_min_interval_seconds)
    when, totals, status, error = today(), {}, "done", None
    try:
        with session() as db:
            seed_sources(db)
        for k, code in enumerate(CODES):
            p.step = k
            p.changed.set()
            try:
                p.texts[code] = await asyncio.to_thread(_sync_parliament, code, when, fetcher, totals)
            except Exception as e:  # noqa: BLE001 — one parliament must not stop the others
                p.texts[code] = f"Couldn't check — will retry next time: {e.__class__.__name__}"
                status, error = "failed", f"{code}: {e.__class__.__name__}: {e}"
        p.step = len(CODES)
        p.changed.set()
        p.texts[REGISTERS] = "Office registers are not connected yet (next phase)"
    finally:
        fetcher.close()
        sat = {sid.split("-")[0] for sid, c in totals.items() if c["new_days"]}
        p.summary = {
            "parliamentsSat": len(sat), "newSittingDays": sum(c["new_days"] for c in totals.values()),
            "newItems": 0, "newItemsMentioningOffice": {},
            "speechesStored": sum(c["speeches_to_analyse"] for c in totals.values()),
            "registers": "office registers not connected yet",
            "note": "Hansard is stored; AI analysis of new speeches comes in the next phase.",
        }
        p.step = p.total
        p.changed.set()
        with session() as db:
            run = db.get(ScanRun, p.run_id)
            run.status, run.finished_at, run.per_source_json, run.error_summary = status, utcnow(), totals, error
            db.commit()


def start(trigger: str = "manual") -> Progress:
    """Start a scan, or return the one already running (one scan at a time, §8.8)."""
    global _current
    if (p := running()) is not None:
        return p
    real = get_settings().scan_mode == "real"
    with session() as db:
        run = ScanRun(trigger=trigger)
        db.add(run)
        db.commit()
        run_id = run.id
    _current = _runs[run_id] = Progress(run_id, real=real)
    asyncio.get_running_loop().create_task(_walk_real(_current) if real else _walk_sample(_current))
    return _current


def reset() -> None:
    global _current
    _current = None
    _runs.clear()
