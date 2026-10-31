"""Update scans (spec §8, §10.4).

Until the Phase 2 connectors exist, a scan walks the 9 parliaments and the
office registers on a timer and reports the sample results, so the update
flow and its live progress (SSE) can be built end to end.
"""

import asyncio
from dataclasses import dataclass, field

from .config import get_settings
from .db import ScanRun, session, utcnow
from .sample_data import dataset

REGISTERS = "REG"


@dataclass
class Progress:
    run_id: int
    step: int = 0  # 0–8 = parliaments in order, 9 = office registers, 10 = finished
    changed: asyncio.Event = field(default_factory=asyncio.Event)

    @property
    def total(self) -> int:
        return len(dataset()["jurisdictions"]) + 1

    @property
    def done(self) -> bool:
        return self.step >= self.total

    def snapshot(self) -> dict:
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


async def _walk(p: Progress) -> None:
    global _current
    delay = get_settings().sample_scan_step_seconds
    while not p.done:
        await asyncio.sleep(delay)
        p.step += 1
        p.changed.set()
    with session() as db:
        run = db.get(ScanRun, p.run_id)
        run.status, run.finished_at, run.per_source_json = "done", utcnow(), p.snapshot()
        db.commit()


def start(trigger: str = "manual") -> Progress:
    """Start a scan, or return the one already running (one scan at a time, §8.8)."""
    global _current
    if (p := running()) is not None:
        return p
    with session() as db:
        run = ScanRun(trigger=trigger)
        db.add(run)
        db.commit()
        run_id = run.id
    _current = _runs[run_id] = Progress(run_id)
    asyncio.get_running_loop().create_task(_walk(_current))
    return _current


def reset() -> None:
    global _current
    _current = None
    _runs.clear()
