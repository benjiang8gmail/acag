"""Database models and session (spec §7).

Phase 1 holds only the tables the app shell uses. Later phases add the rest of
§7 through Alembic migrations.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, create_engine
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
