""""Check for updates" in real mode (SCAN_MODE=real): the web app's scan runs the real
sync for each parliament with a connector, streams progress, and /api/status reads the
real store. NSW is served from its real fixtures; nothing touches the network."""
from datetime import date

import httpx
import pytest

from app import scans
from app.db import ScanRun, Source, session
from pipeline.fetch import Fetcher
from tests.test_connector_nsw import FixtureSite

D = date(2026, 10, 22)


def wait_for_scan(client, run_id, timeout=120):
    """Real scans parse PDFs (seconds each), so allow longer than the sample-scan helper."""
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snap = client.get(f"/api/scans/{run_id}").json()
        if snap["done"]:
            return snap
        time.sleep(0.1)
    raise AssertionError("scan did not finish")


@pytest.fixture
def live(signed_in, tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN_MODE", "real")
    from app import config
    config.get_settings.cache_clear()
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(
        "sources:\n"
        "  - {id: NSW-LA, parliament: NSW, chamber: Legislative Assembly, connector: nsw, enabled: true, status: ok}\n"
        "  - {id: CTH-SEN, parliament: CTH, chamber: Senate, connector: cth, enabled: false, status: blocked}\n"
        "  - {id: WA-LA, parliament: WA, chamber: Legislative Assembly, connector: wa, enabled: false, status: blocked}\n")
    monkeypatch.setattr("pipeline.sync.SOURCES_YAML", yaml_path)
    with session() as s:
        s.add(Source(id="NSW-LA", parliament="NSW", chamber="Legislative Assembly", connector="nsw",
                     enabled=True, status="ok", watermark_date=date(2026, 10, 21)))
        s.commit()
    site = FixtureSite()
    monkeypatch.setattr(scans, "FETCHER_FACTORY",
                        lambda: Fetcher("test", min_interval=0, transport=httpx.MockTransport(site.handler)))
    monkeypatch.setattr(scans, "today", lambda: D)
    yield signed_in
    config.get_settings.cache_clear()


def test_status_before_any_scan_names_the_blocked_parliaments(live):
    st = live.get("/api/status").json()
    rows = {r["code"]: r for r in st["sources"]}
    assert len(rows) == 9 and st["liveHansard"] == ["NSW"] and st["neverChecked"]
    assert rows["NSW"]["text"] == "Not checked yet — refresh to load Hansard"
    assert rows["WA"]["status"] == "blocked" and "blocks automated access" in rows["WA"]["text"]
    assert rows["VIC"]["text"] == "Not connected yet"


def test_check_for_updates_runs_the_real_sync_and_streams_progress(live):
    run = live.post("/api/scans").json()
    assert live.post("/api/scans").json()["id"] == run["id"], "only one scan at a time"
    snap = wait_for_scan(live, run["id"])
    rows = {r["code"]: r["text"] for r in snap["sources"]}
    assert rows["NSW"].startswith("1 new sitting day · ") and rows["NSW"].endswith(" speeches stored")
    assert "blocks automated access" in rows["CTH"]
    s = snap["summary"]
    assert s["parliamentsSat"] == 1 and s["newSittingDays"] == 1 and s["speechesStored"] > 400
    assert s["newItems"] == 0 and "AI analysis" in s["note"]

    st = live.get("/api/status").json()
    nsw = next(r for r in st["sources"] if r["code"] == "NSW")
    assert nsw == {"code": "NSW", "parliament": "Parliament of NSW", "status": "ok", "text": "Last sat Thu 22 Oct"}
    assert st["hansardTo"] == "2026-10-22" and not st["neverChecked"]
    assert st["lastScan"]["NSW-LA"]["methods"] == {"pdf": 1}
    with session() as s:
        logged = s.get(ScanRun, run["id"])
        assert logged.status == "done" and logged.per_source_json["NSW-LA"]["new_documents"] == 1

    # A second check straight away finds nothing new (SC1).
    snap = wait_for_scan(live, live.post("/api/scans").json()["id"])
    assert {r["code"]: r["text"] for r in snap["sources"]}["NSW"] == "No new sitting days"
    assert snap["summary"]["speechesStored"] == 0


def test_real_scans_do_not_reveal_sample_items(live):
    before = len(live.get("/api/items").json())
    wait_for_scan(live, live.post("/api/scans").json()["id"])
    assert len(live.get("/api/items").json()) == before
