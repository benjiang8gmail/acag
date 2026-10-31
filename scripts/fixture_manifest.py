"""Rebuild backend/tests/fixtures/MANIFEST.md from the files on disk and the recon logs.

Usage: python -I scripts/fixture_manifest.py
"""
import glob
import hashlib
import json
import os

F = "backend/tests/fixtures"
HEADER = ("# Fixtures\n\nReal files saved by `scripts/recon_fetch.py` (robots.txt obeyed, ≥2 s per host) "
          "during Phase 0, 31 Oct 2026. Never edit them: parser golden files are derived from them. "
          "Sources and licences are in `docs/sources.md`; the request log is in `docs/recon/`.\n\n"
          "| File | Fetched from | Date | Bytes | SHA-256 (first 16) |\n|---|---|---|---|---|\n")
RENAMED = {"2026-02-24-official.pdf": "2026-02-24-proof-P.pdf", "territorystories-1052298.pdf": "territorystories-1052298.html"}
EXTRA = {"sources/NT-LA/full_record-10070-1052298.json":
         ("https://territorystories.nt.gov.au/api/full_record?handle=10070/1052298", "2026-10-31"),
         # 83 page texts from /api/content (page=0..82), combined into one file; each request is in the recon log.
         "sources/TAS/sittingdays-2026.html":
         ("https://search.parliament.tas.gov.au/search/quicksearch/2026/sittingdays.html", "2026-10-31"),
         "sources/TAS/search-2026-09-10.html":
         ("https://search.parliament.tas.gov.au/Search/search/search?IW_FIELD_ADVANCE_PHRASE=Thursday+10+September+2026&IW_DATABASE=Hansard&IW_SORT=-9", "2026-10-31"),
         "sources/TAS/search-2026-10-30-not-indexed.html":
         ("https://search.parliament.tas.gov.au/Search/search/search?IW_FIELD_ADVANCE_PHRASE=Friday+30+October+2026&IW_DATABASE=Hansard&IW_SORT=-9", "2026-10-31"),
         "sources/NT-LA/2026-10-22-pages.json":
         ("https://territorystories.nt.gov.au/api/content?handle=https%3A%2F%2Fhdl.handle.net%2F10070%2F1052298&group=0&page=0..82", "2026-10-31")}

origin = {}
for log in sorted(glob.glob("docs/recon/*.jsonl")):
    for line in open(log):
        e = json.loads(line)
        out = e.get("out", "")
        if e.get("result") == "ok" and out.startswith(F + "/"):
            rel = out[len(F) + 1:]
            for old, new in RENAMED.items():
                rel = rel.replace(old, new)
            origin[rel] = (e["url"], e["ts"][:10])
origin.update(EXTRA)

rows = []
for root, _, files in os.walk(F):
    for name in files:
        if name == "MANIFEST.md":
            continue
        path = os.path.join(root, name)
        rel = path[len(F) + 1:]
        url, day = origin.get(rel, ("?", ""))
        data = open(path, "rb").read()
        rows.append(f"| `{rel}` | {url} | {day} | {len(data):,} | `{hashlib.sha256(data).hexdigest()[:16]}` |")
with open(os.path.join(F, "MANIFEST.md"), "w") as out:
    out.write(HEADER + "\n".join(sorted(rows)) + "\n")
print(f"{len(rows)} fixtures")
