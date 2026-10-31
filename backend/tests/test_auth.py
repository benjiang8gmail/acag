from app.auth import GENERIC_ERROR


def test_health_needs_no_session(client):
    assert client.get("/api/health").json() == {"ok": True}


def test_wrong_credentials_get_a_generic_error(client):
    for body in ({"username": "acag", "password": "nope"}, {"username": "someone", "password": "nope"}):
        r = client.post("/api/auth/login", json=body)
        assert r.status_code == 401
        assert r.json()["detail"] == GENERIC_ERROR


def test_login_sets_a_secure_session_cookie(signed_in):
    assert signed_in.get("/api/auth/me").json() == {"user": "acag"}
    cookie = signed_in.cookies.jar
    assert any(c.name == "hw_session" and c.has_nonstandard_attr("HttpOnly") for c in cookie)


def test_logout_clears_the_session(signed_in):
    signed_in.post("/api/auth/logout")
    assert signed_in.get("/api/auth/me").json() == {"user": None}


def test_tampered_cookie_is_rejected(client):
    client.cookies.set("hw_session", "acag.forged.signature")
    assert client.get("/api/auth/me").json() == {"user": None}
    assert client.post("/api/scans").status_code == 401


def test_repeated_failures_are_throttled(client):
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "acag", "password": "wrong"})
    r = client.post("/api/auth/login", json={"username": "acag", "password": "wrong"})
    assert r.status_code == 429


def test_security_headers(client):
    h = client.get("/api/health").headers
    assert "frame-ancestors 'none'" in h["content-security-policy"]
    assert h["referrer-policy"] == "strict-origin-when-cross-origin"
