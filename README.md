# Hansard Watch

What Australia's 9 parliaments are saying about their Auditors-General, their reports and their forward programs, in a brief a Senior Executive can read in 30 seconds. Built for the Australasian Council of Auditors-General (ACAG). The full brief is in [`project/uploads/SPEC (2).md`](project/uploads/SPEC%20(2).md).

> **Status: app shell with sample data.** The dashboard is built from the Claude Design prototype (`project/Hansard Watch Prototype.dc.html`) and runs against **invented sample data**. Nothing in the app is real Hansard yet. The Hansard connectors, office registers and AI pipeline come in later phases; see [PROGRESS.md](PROGRESS.md).

## Run it

You need Python 3.13 with [uv](https://docs.astral.sh/uv/), and Node 22.

```sh
make setup          # install dependencies; creates .env from .env.example
make secret         # paste the output into .env as SESSION_SECRET
make set-password   # paste the output into .env as APP_PASSWORD_HASH
make dev            # API on :8000, web app on http://localhost:5173
```

Or run a single process that serves the built web app and the API on http://localhost:8000:

```sh
make serve
```

Browsing is open to everyone. Signing in (username `acag`, plus the password you set) is only needed to **refresh**, because a refresh will run paid AI analysis once the pipeline exists.

**Check for updates** runs the real Hansard sync (`SCAN_MODE=real`, the default) for every parliament with a working connector: NSW, ACT and Queensland so far. The other six show why they weren't checked. Briefs and items are still sample data until AI analysis is built. `SCAN_MODE=sample` replays the prototype's sample scan instead.

## Test

```sh
make test                          # backend pytest, web typecheck and unit tests
make serve &                       # then, in another shell:
SCAN_MODE=sample E2E_PASSWORD=yourpassword make e2e  # Playwright journeys (desktop and 375 px) and axe checks; journey (b) expects the sample scan
```

## Layout

| Path | What's there |
|---|---|
| `backend/app/` | FastAPI app, settings, sign-in, database, sample data, simulated scans |
| `backend/api/` | HTTP routes (`/api/...`; interactive docs at `/api/docs`) |
| `backend/migrations/` | Alembic migrations |
| `backend/connectors/` | Hansard connectors: interface (`base.py`), NSW (`nsw.py`), ACT (`act.py`), QLD (`qld.py`) |
| `backend/pipeline/` | Polite fetcher (`fetch.py`) and the no-rescan sync (`sync.py`); `make backfill`, `make scan` |
| `backend/parsers/` | PDF text (`pdf.py`) and the outline-guided Hansard PDF reader (`hansard_pdf.py`) |
| `backend/registers/`, `gaps/` | Placeholders for Phases 3–5 |
| `web/` | React + Fluent UI 9 single-page app |
| `web/e2e/` | Playwright journeys and accessibility checks |
| `config/` | Sources (15 chambers), offices (9), lexicon, governments, themes |
| `docs/sources.md` | Phase 0 source recon; `docs/access-requests.md` drafts |
| `scripts/recon_fetch.py` | Polite fetcher for `make recon` (robots.txt, rate limits, stops at blocks) |
| `docs/screens/` | Desktop and 375 px screenshots |
| `project/` | The Claude Design handoff: prototype, chat transcript and spec |

## Shareable links

Every view has its own URL, so a link opens exactly what the sender saw. For example:

`/?view=mentions&jur=NSW&period=4w&tab=reports&office=NSW&unmentioned=1&sector=health`

Opening someone else's link never overwrites your own saved jurisdiction. A bar at the top offers to switch back.
