"""Interim login (spec §11): one shared username, a bcrypt hash in `.env`,
a signed httpOnly cookie, and throttling after repeated failures."""

import hmac
import time
from collections import defaultdict, deque

import bcrypt
from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from .config import get_settings

COOKIE = "hw_session"
GENERIC_ERROR = "Username or password is incorrect."

_failures: dict[str, deque[float]] = defaultdict(deque)


def _signer() -> TimestampSigner:
    secret = get_settings().session_secret
    if not secret:
        raise HTTPException(503, "Sign-in is not set up. Run `make secret` and `make set-password`.")
    return TimestampSigner(secret, salt="hw-session")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _throttled(ip: str) -> bool:
    s = get_settings()
    q = _failures[ip]
    cutoff = time.monotonic() - s.login_failure_window_seconds
    while q and q[0] < cutoff:
        q.popleft()
    return len(q) >= s.login_max_failures


def check_login(request: Request, username: str, password: str) -> None:
    s = get_settings()
    ip = _client_ip(request)
    if _throttled(ip):
        raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
    user_ok = hmac.compare_digest(username.strip().lower().encode(), s.app_username.lower().encode())
    try:
        pass_ok = bool(s.app_password_hash) and bcrypt.checkpw(password.encode(), s.app_password_hash.encode())
    except ValueError:
        pass_ok = False
    if not (user_ok and pass_ok):
        _failures[ip].append(time.monotonic())
        raise HTTPException(401, GENERIC_ERROR)
    _failures.pop(ip, None)


def set_session(request: Request, response: Response) -> None:
    s = get_settings()
    token = _signer().sign(s.app_username).decode()
    response.set_cookie(COOKIE, token, max_age=s.session_max_age_seconds, httponly=True,
                        secure=request.url.scheme == "https", samesite="lax", path="/")


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


def current_user(request: Request) -> str | None:
    token = request.cookies.get(COOKIE)
    if not token or not get_settings().session_secret:
        return None
    try:
        return _signer().unsign(token, max_age=get_settings().session_max_age_seconds).decode()
    except (BadSignature, SignatureExpired):
        return None


def require_session(request: Request) -> str:
    user = current_user(request)
    if not user:
        raise HTTPException(401, "Sign in to do this.")
    return user


def reset_throttle() -> None:
    _failures.clear()
