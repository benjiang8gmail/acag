# Progress

## 31 Oct 2026: app shell and dashboard on sample data

**Scope agreed with the product owner before starting:** build the frontend and a backend skeleton now, using the prototype's sample data, rather than starting at Phase 0. This covers Phase 1 (skeleton and login) and the dashboard part of Phase 6. Phases 0 and 2–5 are still to do.

### Done

- **Backend (Phase 1):**
  - FastAPI app with the minimum API from §6. Endpoints read from `backend/app/fixtures/sample_data.json`, which was generated from the prototype's data.
  - Interim sign-in per §11:
    - `APP_USERNAME` and a bcrypt `APP_PASSWORD_HASH` in `.env`, set with `make set-password`.
    - Signed httpOnly session cookie: SameSite=Lax, 8-hour expiry, Secure over HTTPS.
    - Constant-time username check and a generic error message.
    - Throttling after 5 failures in 15 minutes per IP.
    - CSP, frame-ancestors and Referrer-Policy headers.
  - Alembic baseline with `scan_runs`. Migrations run automatically on start.
  - `POST /api/scans` (signed in only) runs a **simulated** scan across the 9 parliaments and the office registers. It streams progress over SSE (`/api/scans/{id}/events`), allows one scan at a time, and logs each run in `scan_runs`. After a scan, the 5 "new" sample items appear and `hansardTo` moves forward.
  - CSV exports work for mentions, Explore results and the gaps longlist. Word and PDF return 501 until Phase 7.
- **Web app (Phase 6 dashboard):** React 18 + Fluent UI 9, built to match `Hansard Watch Prototype.dc.html`, including:
  - First run.
  - Brief, Compare, Mentions (Auditors-General and Reports), Developments, Potential gaps and Explore.
  - Item, gap, report and cross-parliament panels.
  - Pickers for jurisdiction, period and sector.
  - Status and refresh panel with live progress.
  - Sign in only to refresh.
  - Share dialog (copy, email, Teams) and a single Export menu.
  - Toasts, "New" badges and the "Added to your brief" list.
  - Below 768 px it switches to the phone layout: one-row header, chips under the title, bottom tab bar, and bottom sheets in place of drop-downs.
- **URL state:** the address bar always holds the shareable link. Back and forward work between pages and panels. A link from someone else shows the "Opened from a shared link" bar and never overwrites your saved jurisdiction.

### Evidence

- `make test-backend`: 15 tests. They cover auth (generic error, cookie flags, tampered cookie, throttling, logout), security headers, open reads, 401 for scans without a session, filters, CSV, scan → new items, one scan at a time, and the SSE stream.
- `make test-web`: TypeScript strict build, plus unit tests for URL round-trips and date formats.
- `make e2e`: 17 Playwright journeys pass at 1280 px and 375 px. They cover the spec's journeys (a) and (c)–(g) as written, and (b) adapted to sign-in-to-refresh. Plus shared links and the sector filter.
- `make e2e` also runs axe on every page and on first run: no serious or critical findings (WCAG 2.2 AA tags).
- Screenshots at 1280 px and 375 px are in `docs/screens/`.

### Decisions

- **D1. Fixture, not a port.** The sample data was extracted from the prototype by running its own generator, so the numbers match the design exactly. It's clearly labelled as sample data in the status panel and README.
- **D2. Open browsing, sign-in to refresh.** This follows the design the product owner settled on, rather than SC4's "every page requires a session". Only scans need a session. Imports and confirming program topics will need one too once they exist. **SC4 needs revisiting before any shared deployment.**
- **D3. Calculations happen in the browser for now.** Figures such as ranks, medians and attention-map colours are calculated in `web/src/model.ts` from the raw lists the API returns, as the prototype did. When the pipeline exists, the heavier ones (brief, gaps) should move to `/api/brief` and `/api/gaps`.
- **D4. Compare tab, "Following" and "Coming up"** are kept. The design added them and the product owner kept them through several rounds, though the spec doesn't mention them.
- **D5. Light theme only for now.** §10.1 asks for light and dark themes; dark is not built yet.

### Open questions

1. The spec refers to a `CLAUDE.md` of standing rules. It wasn't in the handoff bundle, so please add it.
2. D2: confirm open browsing is acceptable for the pilot, or whether every page should need sign-in (SC4 as written).
3. All the §15 questions remain open.

### Next

- **Phase 0:** source recon for the 15 chambers and 9 offices, written up in `docs/sources.md` with fixtures. The spec says to stop there for product-owner review.
- **Phase 7 items already visible in the UI:** Word and PDF exports, and dark theme.
