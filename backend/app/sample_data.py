"""Invented sample data that stands in for the real pipeline until Phases 2–5.

The fixture was generated from the Claude Design prototype so the dashboard
can be built and tested against realistic shapes. Nothing in it is real
Hansard: names, quotes and counts are made up. Links point to the real
parliament and office home pages.
"""

import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select

from .db import ScanRun, session

FIXTURE = Path(__file__).parent / "fixtures" / "sample_data.json"
PERIOD_DAYS = {"2w": 14, "4w": 28, "2m": 61}


@lru_cache
def dataset() -> dict:
    return json.loads(FIXTURE.read_text())


def refreshed() -> bool:
    """True once a sample scan has finished; the sample items it 'found' then become visible.
    Real scans don't reveal sample items."""
    with session() as db:
        runs = db.scalars(select(ScanRun.per_source_json).where(ScanRun.status == "done")).all()
        return any(isinstance(r, dict) and r.get("sample") for r in runs)


def items(include_pending: bool | None = None) -> list[dict]:
    show_pending = refreshed() if include_pending is None else include_pending
    return [i for i in dataset()["items"] if show_pending or not i["pending"]]


def period_start(period: str) -> str:
    as_of = date.fromisoformat(dataset()["asOf"])
    return (as_of - timedelta(days=PERIOD_DAYS.get(period, 14))).isoformat()


def filter_items(rows: list[dict], jur: str | None = None, period: str | None = None,
                 sector: str | None = None, q: str | None = None) -> list[dict]:
    if jur and jur.upper() != "ALL":
        rows = [i for i in rows if i["jur"] == jur.upper()]
    if period:
        start = period_start(period)
        rows = [i for i in rows if i["date"] >= start]
    if sector:
        rows = [i for i in rows if i["theme"] == sector]
    if q:
        needle = q.lower()
        rows = [i for i in rows if needle in " ".join(str(i.get(k) or "") for k in ("headline", "summary", "quote", "speaker", "debate")).lower()]
    return rows
