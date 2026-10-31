"""Fixtures are real files from the live sites: each one is listed in the
manifest with its hash, and none is a saved bot-challenge page."""
import hashlib
import re
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
MARKERS = ("client challenge", "just a moment...", "azure waf", "captcha", "page blocked by waf")


def manifest():
    rows = re.findall(r"^\| `([^`]+)` \| (\S+) \| [\d-]+ \| [\d,]+ \| `([0-9a-f]{16})` \|$",
                      (FIXTURES / "MANIFEST.md").read_text(), re.M)
    return {path: (url, sha) for path, url, sha in rows}


def test_every_fixture_is_in_the_manifest_with_a_matching_hash():
    m = manifest()
    on_disk = {str(p.relative_to(FIXTURES)) for p in FIXTURES.rglob("*") if p.is_file() and p.name != "MANIFEST.md"}
    assert on_disk == set(m)
    for path, (url, sha) in m.items():
        assert url.startswith("https://"), path
        assert hashlib.sha256((FIXTURES / path).read_bytes()).hexdigest().startswith(sha), path


def test_no_fixture_is_a_bot_challenge_page():
    for p in FIXTURES.rglob("*"):
        if p.suffix in (".html", ".xml", ".json", ".pdf"):
            head = p.read_bytes()[:30_000].decode("utf-8", "replace").lower()
            assert not any(m in head for m in MARKERS), p
            if p.suffix == ".pdf":
                assert p.read_bytes()[:5] == b"%PDF-", p
