"""Database models and session (spec §7).

Phase 1 added `scan_runs`; Phase 2 adds the Hansard store (`sources`,
`sitting_days`, `documents`, `speeches`). Later phases add the rest of §7
through Alembic migrations.
"""

from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger: Mapped[str] = mapped_column(String(16))  # manual / scheduled / cli
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running / done / failed
    per_source_json: Mapped[dict] = mapped_column(JSON, default=dict)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    error_summary: Mapped[str | None] = mapped_column(String, nullable=True)


class Source(Base):
    """One row per chamber (15), seeded from config/sources.yaml."""
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # e.g. VIC-LA
    parliament: Mapped[str] = mapped_column(String(8))
    chamber: Mapped[str] = mapped_column(String(64))
    connector: Mapped[str] = mapped_column(String(32))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="unverified")  # ok / no_sittings / blocked / error / unverified
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    watermark_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SittingDay(Base):
    __tablename__ = "sitting_days"
    __table_args__ = (UniqueConstraint("source_id", "sitting_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    sitting_date: Mapped[date] = mapped_column(Date)  # local date in the parliament's own time zone
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    version: Mapped[str] = mapped_column(String(8), default="unknown")  # proof / final / unknown
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending / done / error


class Document(Base):
    """A fetched file. A new row is written only when its sha256 changes (§7)."""
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sitting_day_id: Mapped[int] = mapped_column(ForeignKey("sitting_days.id"))
    url: Mapped[str] = mapped_column(Text)
    doc_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)  # stable identity; NSW TOC ids change
    format: Mapped[str] = mapped_column(String(8))  # xml / html / pdf / docx / json
    version: Mapped[str] = mapped_column(String(8), default="unknown")
    etag: Mapped[str | None] = mapped_column(String(256), nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64))
    raw_path: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    superseded_by: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    origin: Mapped[str] = mapped_column(String(8), default="auto")  # auto / manual


class Speech(Base):
    """One speaker turn under a debate heading. FTS5 indexes text, title and speaker."""
    __tablename__ = "speeches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    seq: Mapped[int] = mapped_column(Integer)
    debate_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    proceeding_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    speaker_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    speaker_id: Mapped[str | None] = mapped_column(String(32), nullable=True)  # parliament's member id
    speaker_role: Mapped[str | None] = mapped_column(String(128), nullable=True)
    party: Mapped[str | None] = mapped_column(String(32), nullable=True)
    speaker_side: Mapped[str | None] = mapped_column(String(16), nullable=True)  # set in code from config/governments.yaml
    electorate: Mapped[str | None] = mapped_column(String(64), nullable=True)
    start_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    page: Mapped[str | None] = mapped_column(String(16), nullable=True)
    anchor_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    text_sha256: Mapped[str] = mapped_column(String(64), index=True)


_engine = None
_Session = None


def engine():
    global _engine, _Session
    if _engine is None:
        settings = get_settings()
        if settings.db_url.startswith("sqlite:///"):
            settings.data_dir.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(settings.db_url, connect_args={"check_same_thread": False} if settings.db_url.startswith("sqlite") else {})
        _Session = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def session():
    engine()
    return _Session()


def reset_engine() -> None:
    """Drop the cached engine (used by tests after changing settings)."""
    global _engine, _Session
    if _engine is not None:
        _engine.dispose()
    _engine = _Session = None
