"""Hansard sync: the "no rescanning" rules of spec §8 (SC1, SC2).

For each enabled source:
1. Window: from the day after its watermark (or the same date BACKFILL_MONTHS
   ago) to today, plus any day still not final within PROOF_RECHECK_DAYS.
2. List sitting days. "No sittings" and "could not check" are different results.
3. Fetch each document conditionally; same hash means unchanged, and we stop there.
4. Parse only changed documents. A changed document becomes a new version, and
   the old one is marked superseded. Speeches whose text hash is new are counted
   as needing analysis; unchanged speeches never are.
5. Advance the watermark only up to the day before the first failure.
6. Log per-source counts in `scan_runs`.
"""

from __future__ import annotations

import calendar
import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml
from sqlalchemy import select

from app.config import REPO_ROOT, get_settings
from app.db import Document, ScanRun, SittingDay, Source, Speech, session, utcnow
from connectors.base import CouldNotCheck, registry, DocumentRef, HansardConnector, SittingDayRef

from .fetch import Blocked, Fetcher

SOURCES_YAML = REPO_ROOT / "config" / "sources.yaml"
STALE_LOCK = timedelta(hours=6)


class ScanInProgress(Exception):
    pass


@dataclass
class SourceCounts:
    days_checked: int = 0
    new_days: int = 0
    days_pending: int = 0          # sat, but the transcript isn't published yet
    new_documents: int = 0
    changed_documents: int = 0
    unchanged_documents: int = 0
    not_modified: int = 0          # 304 answers: nothing downloaded
    unchanged_downloads: int = 0   # server ignored conditional headers; body hashed and discarded
    parts_fetched: int = 0         # sub-resources fetched for changed documents (e.g. NSW day PDF)
    methods: dict = field(default_factory=dict)  # how documents were read, e.g. {"pdf": 3}
    speeches_to_analyse: int = 0   # new or changed text; Phase 4 analyses only these
    llm_calls: int = 0             # no LLM stage yet (Phase 4)
    errors: int = 0
    status: str = "ok"
    note: str | None = None


def months_ago(d: date, months: int) -> date:
    """The same date `months` earlier (31 Oct → 31 Aug; 31 Dec → 31 Oct; 31 Mar → 28/29 Feb)."""
    y, m = divmod(d.year * 12 + d.month - 1 - months, 12)
    return date(y, m + 1, min(d.day, calendar.monthrange(y, m + 1)[1]))


def text_hash(text: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode()).hexdigest()


def seed_sources(db) -> None:
    """Upsert the 15 chambers from config/sources.yaml without touching status or watermark."""
    for row in yaml.safe_load(SOURCES_YAML.read_text())["sources"]:
        src = db.get(Source, row["id"]) or Source(id=row["id"], status=row.get("status", "unverified"))
        src.parliament, src.chamber, src.connector = row["parliament"], row["chamber"], row["connector"]
        src.enabled = bool(row.get("enabled"))
        db.merge(src)
    db.commit()


def _version(*hints: str) -> str:
    return "final" if "final" in hints else "proof" if "proof" in hints else "unknown"


def sync_parliament(db, connector: HansardConnector, fetcher: Fetcher, today: date,
                    data_dir: Path) -> dict[str, SourceCounts]:
    settings = get_settings()
    sources = {s.id: s for s in db.scalars(select(Source).where(
        Source.id.in_(connector.source_ids), Source.enabled.is_(True)))}
    counts = {sid: SourceCounts() for sid in sources}
    if not sources:
        return counts
    backfill_start = months_ago(today, settings.backfill_months)
    starts = {sid: (s.watermark_date + timedelta(days=1)) if s.watermark_date else backfill_start
              for sid, s in sources.items()}
    recheck_from = today - timedelta(days=settings.proof_recheck_days)
    recheck = {(d.source_id, d.sitting_date): d.version for d in db.scalars(select(SittingDay).where(
        SittingDay.source_id.in_(sources), SittingDay.version != "final",
        SittingDay.sitting_date >= max(recheck_from, backfill_start)))}

    now = datetime.now(timezone.utc)
    try:
        start = min(starts.values())
        listed = connector.list_sitting_days(start, today) if start <= today else []
    except (CouldNotCheck, Blocked) as e:
        status = "blocked" if isinstance(e, Blocked) else "error"
        for sid, src in sources.items():
            src.status, src.last_checked_at, src.notes = status, now, str(e)
            counts[sid].status, counts[sid].note = status, str(e)
            counts[sid].errors += status == "error"
        db.commit()
        return counts

    days: dict[str, dict[date, SittingDayRef]] = {sid: {} for sid in sources}
    for d in listed:
        if d.source_id in sources and starts[d.source_id] <= d.sitting_date <= today:
            days[d.source_id][d.sitting_date] = d
    for (sid, day), version in recheck.items():
        days[sid].setdefault(day, SittingDayRef(sid, day, version))

    blocked: str | None = None
    for sid, src in sources.items():
        c = counts[sid]
        first_failure: date | None = None
        for day in sorted(days[sid]):
            if blocked:
                break
            c.days_checked += 1
            try:
                if not _sync_day(db, connector, fetcher, days[sid][day], c, data_dir):
                    # Listed as a sitting day but not published yet: hold the watermark before it
                    # so it is picked up when it appears. Not an error.
                    c.days_pending += 1
                    first_failure = first_failure or day
            except Blocked as e:
                db.rollback()  # drop the half-synced day; it is retried next run
                blocked = str(e)
                first_failure = first_failure or day
            except Exception as e:  # noqa: BLE001 — one bad day must not stop the others
                db.rollback()
                c.errors += 1
                c.note = f"{day}: {e.__class__.__name__}: {e}"
                first_failure = first_failure or day
                sd = db.scalar(select(SittingDay).where(SittingDay.source_id == sid, SittingDay.sitting_date == day))
                if sd:
                    sd.status = "error"
                db.commit()
        src.last_checked_at = now
        if blocked:
            src.status, src.notes, c.status, c.note = "blocked", blocked, "blocked", blocked
        elif c.errors:
            src.status, src.notes, c.status = "error", c.note, "error"
        else:
            src.status = c.status = "ok" if days[sid] else "no_sittings"
            src.notes, src.last_success_at = None, now
        new_mark = (first_failure - timedelta(days=1)) if first_failure else today
        if settled := getattr(connector, "settled_through", None):
            # Sources found by probing dated URLs can't tell "not sitting" from "not published
            # yet" for recent days, so they keep re-checking the last few days.
            new_mark = min(new_mark, settled(today))
        if new_mark >= starts[sid] - timedelta(days=1):
            src.watermark_date = max(src.watermark_date or new_mark, new_mark)
        db.commit()
    return counts


def _sync_day(db, connector, fetcher: Fetcher, day: SittingDayRef, c: SourceCounts, data_dir: Path) -> bool:
    """Returns False when the day has no published document yet."""
    sd = db.scalar(select(SittingDay).where(SittingDay.source_id == day.source_id,
                                            SittingDay.sitting_date == day.sitting_date))
    if sd is None:
        sd = SittingDay(source_id=day.source_id, sitting_date=day.sitting_date, version=day.version_hint)
        db.add(sd)
        db.flush()
        c.new_days += 1
    refs = connector.list_documents(day)
    if not refs:
        sd.status = "pending"
        db.commit()
        return False
    versions = [day.version_hint]
    for ref in refs:
        versions.append(_sync_document(db, connector, fetcher, sd, ref, c, data_dir))
    sd.version, sd.status = _version(*versions), "done"
    db.commit()
    return True


def _sync_document(db, connector, fetcher: Fetcher, sd: SittingDay, ref: DocumentRef,
                   c: SourceCounts, data_dir: Path) -> str:
    key = ref.key or ref.url
    prev = db.scalar(select(Document).where(Document.sitting_day_id == sd.id, Document.doc_key == key,
                                            Document.superseded_by.is_(None)))
    res = fetcher.fetch(ref.url, etag=prev.etag if prev else None,
                        last_modified=prev.last_modified if prev else None,
                        previous_sha256=prev.sha256 if prev else None)
    if res.status == "unchanged":
        c.unchanged_documents += 1
        c.not_modified += not res.downloaded
        c.unchanged_downloads += res.downloaded
        if prev and res.downloaded:
            prev.etag, prev.last_modified = res.etag or prev.etag, res.last_modified or prev.last_modified
        return prev.version if prev else "unknown"

    day_dir = data_dir / "raw" / ref.source_id / ref.sitting_date.isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    raw = day_dir / f"{res.sha256}.{ref.format}"
    raw.write_bytes(res.body)

    def fetch_part(url: str) -> bytes:
        part = fetcher.fetch(url)
        (day_dir / f"{part.sha256}.part").write_bytes(part.body)
        c.parts_fetched += 1
        return part.body

    parsed = connector.parse(res.body, ref, fetch_part)
    if parsed.method:
        c.methods[parsed.method] = c.methods.get(parsed.method, 0) + 1
    if parsed.note:
        c.note = f"{ref.sitting_date}: {parsed.note}"
    doc = Document(sitting_day_id=sd.id, url=ref.url, doc_key=key, format=ref.format,
                   version=_version(parsed.version, ref.version_hint), etag=res.etag,
                   last_modified=res.last_modified, sha256=res.sha256, raw_path=str(raw))
    db.add(doc)
    db.flush()
    old_hashes: set[str] = set()
    if prev:
        prev.superseded_by = doc.id
        old_hashes = set(db.scalars(select(Speech.text_sha256).where(Speech.document_id == prev.id)))
        c.changed_documents += 1
    else:
        c.new_documents += 1
    for s in parsed.speeches:
        h = text_hash(s.text)
        db.add(Speech(document_id=doc.id, text_sha256=h, **asdict(s)))
        c.speeches_to_analyse += h not in old_hashes
    return doc.version


def run_scan(trigger: str = "cli", today: date | None = None,
             connectors: list[HansardConnector] | None = None, fetcher: Fetcher | None = None) -> ScanRun:
    """One update across every enabled source. Only one scan runs at a time (§8.8)."""
    settings = get_settings()
    today = today or datetime.now(timezone.utc).astimezone().date()
    own_fetcher = fetcher is None
    fetcher = fetcher or Fetcher(settings.fetch_user_agent, settings.fetch_min_interval_seconds)
    with session() as db:
        busy = db.scalar(select(ScanRun).where(ScanRun.status == "running",
                                               ScanRun.started_at > utcnow() - STALE_LOCK))
        if busy:
            raise ScanInProgress(f"scan {busy.id} is still running")
        seed_sources(db)
        run = ScanRun(trigger=trigger)
        db.add(run)
        db.commit()
        if connectors is None:
            wanted = {s.connector for s in db.scalars(select(Source).where(Source.enabled.is_(True)))}
            known = registry()
            connectors = [known[name](fetcher) for name in sorted(wanted) if name in known]
        per_source: dict[str, dict] = {}
        try:
            for conn in connectors:
                for sid, cnt in sync_parliament(db, conn, fetcher, today, settings.data_dir).items():
                    per_source[sid] = asdict(cnt)
            run.status = "done"
        except Exception as e:
            run.status, run.error_summary = "failed", f"{e.__class__.__name__}: {e}"
            raise
        finally:
            run.finished_at, run.per_source_json = utcnow(), per_source
            db.commit()
            if own_fetcher:
                fetcher.close()
        return run
