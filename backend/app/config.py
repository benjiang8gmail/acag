"""Settings from the environment and `.env` (spec §14)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    app_username: str = "acag"
    app_password_hash: str = ""
    session_secret: str = ""
    session_max_age_seconds: int = 8 * 60 * 60
    login_max_failures: int = 5
    login_failure_window_seconds: int = 15 * 60
    data_dir: Path = REPO_ROOT / "data"
    database_url: str = ""
    display_timezone: str = "Australia/Melbourne"
    # "real" syncs the enabled connectors; "sample" replays the prototype's sample scan (app/scans.py)
    scan_mode: str = "real"
    # Phase 2 scan settings (§8, §14)
    backfill_months: int = 2
    proof_recheck_days: int = 28
    fetch_min_interval_seconds: float = 2.0
    fetch_user_agent: str = "ACAG-HansardWatch/0.1 (+mailto:CONTACT_EMAIL)"
    # Seconds between simulated scan steps; the sample scan stands in for Phase 2 connectors.
    sample_scan_step_seconds: float = 0.42

    @property
    def db_url(self) -> str:
        return self.database_url or f"sqlite:///{self.data_dir / 'hansard_watch.db'}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
