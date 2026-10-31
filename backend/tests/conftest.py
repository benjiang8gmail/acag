import pytest
from fastapi.testclient import TestClient

from app import auth, config, db, scans
from app.auth import hash_password

TEST_PASSWORD = "correct horse battery staple"  # test-only value, not the product owner's password


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.setenv("APP_PASSWORD_HASH", hash_password(TEST_PASSWORD))
    monkeypatch.setenv("SAMPLE_SCAN_STEP_SECONDS", "0.01")
    monkeypatch.setenv("SCAN_MODE", "sample")   # the sample flow; test_real_scan.py covers real scans
    config.get_settings.cache_clear()
    db.reset_engine()
    auth.reset_throttle()
    scans.reset()
    from app.main import app
    with TestClient(app) as c:
        yield c
    db.reset_engine()
    config.get_settings.cache_clear()


@pytest.fixture
def signed_in(client):
    r = client.post("/api/auth/login", json={"username": "acag", "password": TEST_PASSWORD})
    assert r.status_code == 200
    return client
