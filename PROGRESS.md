# Progress

## 1 Nov 2026: NSW switched to contents + day PDF (2 requests per chamber-day)

The product owner approved the change from one request per topic to the day's PDF.

### Done

- **`connectors/nsw.py`:**
  - When a day's table of contents is new or changed, the connector fetches **the day PDF (1 request)** and reads it in step with the contents.
  - **Headings:** contents headings are matched in order. Topic titles may be found further ahead, while generic labels only match close by.
  - **Speakers:**
    - The speaker line gives name, electorate, ministerial title and time; member ids come from the contents.
    - Question and answer labels come from the contents.
    - Interjections, presiding officers (with who was in the chair) and statements by members with the call follow the same rules as the XML parser.
  - **Dropped:** page furniture and division lists ("Tesch, L", "Ruddick").
  - **Citations:** each speech links to `PDF#page=N`.
  - **Fallback:** if fewer than 90% of topic headings line up, the connector fetches each topic's fragment, as before. The scan log shows `methods` (`pdf` or `fragments`) and a note.
- **`parsers/pdf.py`:** shared PDF text extraction for NSW, and later QLD and ACT.
  - It uses pdfminer.six (MIT) with `boxes_flow=None`. pypdf split words ("t ransport"), which would break the exact-quote check, and pdfminer's default layout reordered headings.
  - The last 4 PDFs read are cached in-process.
- New fixture: the Council day PDF for 22 Oct 2026 (26 fixtures in total).

### Evidence

- `make test`: 63 backend tests pass. The NSW connector tests now include:
  - the PDF path costs 1 request and every speech cites its page;
  - Question Time from the PDF, with question and answer labels, the minister's resumption rejoining her answer, and page 7;
  - no division names or page headers in the text, and no split words;
  - **the PDF and the XML agree on turns, speakers and words for 5 Assembly topics** (Question Time, a tabled document, a private member's statement, a written statement, a bill);
  - **all 312 turns of a Council committee stage appear in the PDF in the same order**;
  - the fallback: a PDF that doesn't line up is read topic by topic (1 + 244 requests);
  - the sync stores the day with `parts_fetched: 1` and `methods: {"pdf": 1}`, and a re-check is 1 request.
- **Live run, 21 Oct 2026, both chambers:** 4 requests, both read from the PDF, 506 + 293 speeches, 0 errors, every turn with a page. It took **46 s including parsing**; the old route would have taken about 16 minutes.
  - It surfaced a real F3 item: the Public Accounts Committee chair took note of a report on appropriation for the services of the Auditor-General (Assembly, page 30).
- **New volume estimate:** the two-month NSW backfill is about 48 requests plus about 10 minutes of PDF parsing, down from about 3.3 hours. This settles **D14**.

### Known limits

- The PDF doesn't carry the presiding officer's member id; the role records who was in the chair.
- When pdfminer meets a numbered list, it can print the "(1) (2) (3)" markers as one block ahead of the items. No words are lost.
- A procedural line printed just before its stage heading keeps the topic title without the stage name.

### Next

- ACT connector (year index → proof PDF, reusing `parsers/pdf.py`), then QLD.
- NSW member-to-party map, for speaker side.

---

## 31 Oct 2026 (night): Phase 2, NSW connector, enabled

### Done

- **`backend/connectors/nsw.py`**, built on the public NSW Hansard API and its real fixtures:
  - **Listing:** the year list. Its `Uncorrected` flag gives proof or final per chamber.
  - **Stored document:** the day's table of contents, keyed `toc:{source}:{date}` because its id can change.
  - **Topic fragments** are fetched only when the table of contents has changed. Re-checking a proof day costs **one request**.
  - **Speaker turns:**
    - Each speech, question or answer is one turn.
    - A member with the call is a contribution (`MemberUpper-H`), not an interjection.
    - Title-case names are interjections (`MemberLower-H`).
    - Presiding officers are their own turns, with the member in the chair, e.g. "presiding officer (The Hon. Rod Roberts)".
    - A speaker resuming after an interruption rejoins their own turn.
    - A mover's "In reply" is a separate speech.
    - Division lists are skipped.
  - **Recorded per speech:** member id, electorate, ministerial title and time.
  - **Citations** go to the day's PDF.
  - Party is not in NSW Hansard; speaker side comes from members data later.
- **Sync changes:**
  - Connectors now receive the polite fetcher.
  - `fetch_part` fetches sub-resources and keeps their raw files.
  - Documents are matched on `doc_key`.
  - Scans count `parts_fetched`.
  - A migration adds `documents.doc_key` and `speeches.speaker_id`.
- **NSW-LA and NSW-LC are enabled** in `config/sources.yaml`.

### Evidence

- `make test`: 54 backend tests pass, 11 of them for the NSW connector, all against real saved files:
  - the listing, with proof and final days and recess;
  - a second-reading speech, Question Time (question, answer, Speaker, interjection, the minister resuming), a tabled document, a written statement, and a motion debate with an "in reply";
  - a Council committee stage whose names are split across spans;
  - a whole day walking all 244 topics in order;
  - **a sync of 22 Oct, then a re-check that makes 2 requests (year list, then a 304 on the table of contents), fetches 0 fragments and finds 0 speeches to analyse.**
- **Live check, NSW-LC 22 Oct 2026**, through the real polite fetcher into a throwaway database: 72 topics, 581 speeches, 0 errors, status `ok`.
  - It found two Council markup issues: names split across spans, and members with the call being labelled interjections. Both are fixed, and the fragment that showed them is now a fixture.
- Fixtures: 25, with the manifest rebuilt by `scripts/fixture_manifest.py`.

### Decision needed

- **D14. Request volume.** NSW serves text one topic at a time: about 245 requests for each chamber-day.
  - At `FETCH_MIN_INTERVAL_SECONDS=2`, the two-month backfill (24 chamber-days) is about **3.3 hours**, and a typical sitting week about **50 minutes**.
  - About 60% of Assembly topics are **written** community recognition statements, which are very unlikely to mention an audit office.
  - Options:
    - (a) accept the time;
    - (b) skip written community recognition statements;
    - (c) a shorter interval for this API, which is built for programmatic use and publishes no limit;
    - (d) a combination.
  - I've kept everything, at 2 s, until you decide.

### Next

- ACT connector (year index → proof PDF, or the HTML edition; party from a 25-member map), then QLD.
- NSW member-to-party map, used for speaker side (Phase 4 needs it).
- Wire the web app's "Check for updates" and `/api/status` to the real scan.

---

## 31 Oct 2026 (evening): Phase 0 live check, with real fixtures for the reachable sources

Network access was opened for this session, so `make recon` and some follow-up requests ran against every host. All requests were polite and obeyed robots.txt. Results are in `docs/sources.md` §0a, and the log is `docs/recon/recon-2026-10-31.jsonl`.

### What happened

- **The requests came from a US cloud network** (Cloudflare's IAD data centre). Most refusals were **bot-protection pages in front of the whole site, robots.txt included**. Those may be aimed at cloud or overseas addresses, so re-test from the pilot's Australian network.
- **Hansard reachable:**
  - **NSW**, through its API. The year list has an `Uncorrected` proof flag, and the XML marks `<draft>`.
  - **QLD**, through the documents host: the daily proof PDF, with `Name (Electorate—PARTY)` speaker lines.
  - **ACT**: a year index and proof PDFs. The "P" page prefix marks a proof; every 2026 day is still a proof.
- **Hansard blocked:**
  - CTH (Azure WAF block page)
  - VIC (Cloudflare)
  - SA (Azure WAF JavaScript challenge, including the published API)
  - WA (Azure WAF)
  - TAS (Cloudflare)
- **NT:** the listing works through the Territory Stories API. Its robots.txt disallows the PDFs, so **we didn't download them**; that needs permission.
- **Offices reachable:** AONSW, VAGO and Audit Tasmania (bare domain).
  - VAGO's robots.txt disallows `/search/`, where its report listings live, so its register will come from the sitemap.
- **Offices blocked:**
  - QAO and the Audit Office of SA ("Client Challenge")
  - OAG WA (nginx 403)
  - ACT Audit Office and NT Auditor-General's Office (Cloudflare)
  - ANAO did not respond.
- **19 real fixtures** are saved in `backend/tests/fixtures/`, each recorded in `MANIFEST.md` with its URL and SHA-256.
  - Three QAO and SA files turned out to be challenge pages that a 200 response had disguised. They were deleted. Both fetchers now recognise those pages, including when one is served in place of robots.txt.
- **Corrections to the desk research:**
  - ACT file names: `tP` and `P` are both proofs; the file-name prefix doesn't mark the final version.
  - NSW and ACT Hansard carry no party, so speaker side needs member-to-party maps.
  - QLD party codes LNP and ALP are confirmed.

### Updated

- `config/sources.yaml`: statuses set from the live check. NSW, QLD and ACT are `ok`; CTH, VIC, SA, WA, TAS and NT are `blocked`. Each source has a `live_check` note. All stay disabled until their connectors pass.
- `config/offices.yaml`: a `live_check` note per office, plus corrected listing URLs for VAGO, Audit Tasmania and AONSW.
- `config/governments.yaml`: notes on NSW and ACT party mapping.
- `docs/access-requests.md`: rebuilt around the confirmed blocks. It adds draft D (Territory Stories PDFs) and draft E (audit offices). Still unsent.
- `scripts/recon_batch.tsv`: corrected URLs, so the run can be repeated from the pilot network.

### Evidence

- `make test`: 43 backend tests pass. New ones:
  - every fixture is in the manifest with a matching hash, no fixture is a challenge page, and every PDF starts with `%PDF-`;
  - robots.txt served as a challenge page blocks the host, tested in both fetchers.

### Decisions

- **D12. A robots.txt that is refused (403) or is itself a challenge page means "do not fetch".** Python's own robots parser treats a 403 the same way. We never fall back to fetching the page anyway.
- **D13. No PDFs from Territory Stories without permission.** The files sit on a separate S3 host, but Territory Stories' robots.txt clearly disallows `*.pdf`. Draft D asks for permission.

### Open questions (update)

- **4 (network):** answered for this session. Re-test the blocked sites from the pilot network before sending any access request.
- **8 (new):** NT Hansard text: ask Library & Archives NT for permission (draft D), or rely on manual import for the NT?

### Next

- Phase 2 connectors on real fixtures, in this order:
  1. NSW (API)
  2. ACT (index → PDF, or the HTML edition)
  3. QLD (date URL → PDF)
- Member-to-party maps for NSW and ACT.

---

## 31 Oct 2026: Phase 2, part 1 — Hansard store and no-rescan sync (source-independent)

**Scope.** The product owner said "continue" after the Phase 0 review page. The parliament and office sites are still unreachable from the build environment, so this covers only the Phase 2 work that doesn't need real fixtures. Connectors for real chambers wait for real fixtures (decision D6).

### Done

- **Store (spec §7):** an Alembic migration adds `sources`, `sitting_days`, `documents` and `speeches`.
  - `speeches` has an FTS5 index on text, debate title and speaker, kept in sync by triggers. SQLite only; on Postgres the step is skipped.
  - Raw files are saved to `data/raw/{source}/{date}/{sha256}.{ext}` and never deleted.
- **Connector interface (§6):** `backend/connectors/base.py`.
  - `list_sitting_days` must raise `CouldNotCheck` rather than return "no sittings" when the calendar can't be read.
  - Connectors never make HTTP requests themselves.
  - The registry is empty until a real connector passes its real-fixture tests.
- **Polite fetcher:** `backend/pipeline/fetch.py`, used by every connector.
  - Obeys robots.txt and its crawl-delay; skips a host whose robots.txt can't be read.
  - Waits at least `FETCH_MIN_INTERVAL_SECONDS` per host and makes conditional GETs.
  - Hashes each body with SHA-256.
  - Treats 401, 403, 429 and challenge pages as `blocked` for the rest of the run, with no retries and no workarounds.
- **Sync (§8):** `backend/pipeline/sync.py`.
  - Window: from the watermark, or a backfill of the same date `BACKFILL_MONTHS` ago, plus non-final days within `PROOF_RECHECK_DAYS`.
  - "No sittings" and "could not check" are kept separate.
  - A new document row is written only on a changed hash; the old version is marked `superseded_by`.
  - Speeches are re-derived, and only new speech-text hashes count as `speeches_to_analyse`.
  - The watermark stops at the day before the first failure.
  - One scan at a time, using a lock row in `scan_runs` (stale after 6 h).
  - Per-source counts go into `scan_runs`.
- **Commands:** `make backfill` and `make scan` run the same sync, which backfills sources that have no watermark. With no enabled sources they log a run and say why nothing was scanned.
- **Sources** are seeded from `config/sources.yaml` on every scan. This never overwrites a source's status or watermark.

### Evidence

- `make test`: 39 backend tests pass, 15 of them new in `tests/test_sync.py`. They run against a fake two-chamber parliament served over a mock HTTP transport. It is a test double, not a stand-in for any real source. The tests cover:
  - the first run backfills from 31 Aug to 31 Oct and stores raw files;
  - **an immediate re-run makes 0 downloads and finds 0 speeches to analyse**: the only request is one 304 for the day still in proof, and final days are not fetched again;
  - a server that ignores conditional headers still creates no new rows;
  - a new day processes only that day;
  - **proof → final with one edited speech** creates a new document version, marks the old one superseded, finds exactly 1 speech to analyse, and then stops rechecking that day;
  - recess gives `no_sittings`; an unreadable calendar gives `error` and keeps the watermark;
  - a failed day holds the watermark at the day before it;
  - a 403 marks the source `blocked` after a single request; robots.txt `Disallow` is obeyed;
  - disabled sources are skipped; only one scan runs at a time;
  - FTS5 search works; the 15 real sources are seeded and start disabled.
- `make scan` against an empty database: migrations run, scan 1 is `done`, and it prints "No enabled sources".

### Decisions

- **D9. One fetcher for everyone.** Connectors only describe a site; all politeness rules live in `pipeline/fetch.py`, so a new connector can't skip them.
- **D10. LLM calls are counted but zero.** `llm_calls` is in each scan's per-source counts so that SC1's "0 LLM calls" is visible in the scan log from Phase 4.
- **D11. "Check for updates" in the web app still runs the simulated scan** while no real source is enabled. It switches to `run_scan` when the first connector is enabled, at which point `/api/status` also reads the `sources` table.

### Next

- Real connectors, in the order in `docs/sources.md` §5, each built on a real fixture from `make recon` or manual import. This still needs the network access in open question 4.
- Wire `/api/status` and the scan button to the real store when the first source is enabled.

---

## 31 Oct 2026: Phase 0 source recon (desk research done; fixtures blocked by the build environment)

**Status: stopped for product-owner review (spec §12).** Phase 0 is **not complete**. The written recon and config are done, but no real fixtures were saved. The cloud container's network policy refused every parliament and audit office host, including the web fetch tool.

### Done

- **`docs/sources.md`:** all 15 chambers and 9 offices, with the spec's Phase 0 fields:
  - Chambers: listing, URL pattern, format, speaker markup, proof/final signal, robots.txt, terms, rate limits, blockers, recommended connector, fixture.
  - Offices: program, topic statuses, reports listing, audit requests, current Auditor-General, robots/terms, blockers.
  - Every fact carries an H/M/L confidence. These came from web searches of official pages, published sample files and open-source clients, not from direct fetches.
- **`config/lexicon.yaml`:** office names and aliases, current and former Auditors-General with the forms used in Hansard, generic terms (including WA's unhyphenated "Auditor General"), tabling and request phrases, committees, integrity bodies, risk terms and public-body change terms.
- **`config/governments.yaml`:** all 9 parliaments, as of 31 Oct 2026. Each has head of government, governing parties, majority or minority status, opposition, crossbench notes, party codes per parliament, and the side-classification rules.
- **`config/sources.yaml`** (15 chambers) and **`config/offices.yaml`** (9 offices, spec §14). Every source has status `unverified` and is disabled until a real fixture exists.
- **`config/themes.yaml`:** the 16 sector themes from §9.2, with pre-filter hints.
- **`docs/access-requests.md`:** drafts for CTH (APH), VIC, SA and WA, the sources with evidence of bot protection. **Not sent.** Send each only after the block is confirmed from the pilot network. TAS, QLD and ACT terms still to confirm.
- **Polite fetcher:** `scripts/recon_fetch.py`, run as `make recon`.
  - It obeys robots.txt and does not fetch at all if robots.txt can't be checked.
  - It waits at least 2 s per host, uses the project User-Agent, and logs every request.
  - It stops at the first 401, 403 or 429, or at a bot-challenge page, and never saves a challenge page as a fixture.
- **`scripts/recon_batch.tsv`:** 38 real URLs seen in search results. These are listings, one sitting day per chamber where a dated URL was found, and each office's program and report pages.

### Evidence

- `docs/recon/2026-10-31-attempt-1.jsonl`: the first run against 18 hosts. Every robots.txt request got a proxy 403 ("Tunnel connection failed"), and nothing was fetched.
- `make test`: 24 backend tests pass.
  - 5 new tests for the fetcher's politeness rules: obeys disallow, skips when robots.txt is unreachable, stops at the first block, never saves challenge pages.
  - 4 new tests check that the config files cover all 15 chambers, 9 offices and 9 parliaments, and agree with each other.
- Web typecheck and unit tests pass.

### What the recon found (highlights)

- **Auditors-General:**
  - ACT: **Ajay Sharma** since 8 Feb 2026 (replacing Michael Harris).
  - NT: **Jara K. Dean** since 13 Sep 2024 (replacing Julie Crisp).
  - Tas: **Martin Thompson**.
  - Cth: Dr Caralee McLiesh since 4 Nov 2024.
  - The others are unchanged.
- **SA's office is now the "Audit Office of South Australia"** (since 1 Jul 2024). The code `SAAGD` is kept.
- **WA Hansard has moved off Lotus Domino** onto the same `/daily/{house}/{date}` platform as SA. SA publishes an official OpenAPI spec.
- **CTH is the biggest risk.** A third-party project reports that APH's Azure WAF answers 403 to scripts, even for robots.txt. OpenAustralia mirrors the original XML (decision needed, below).
- **Forward programs:** SA and NT publish none. WA has only "audits in progress", with topics selected twice a year.
- **NT mandate:** NT sources say the NT Auditor-General has no general power to do performance audits. The NT gaps page should say so.
- **Committees:**
  - Qld: the Auditor-General is overseen by the Governance, Energy and Finance Committee.
  - SA: has no PAC.
  - ACT: the committee is now Public Accounts and Administration.
- **Integrity bodies:** NT merged its ICAC and Ombudsman into the Integrity and Ethics Commissioner on 1 Jun 2026.
- **Within the 2-month backfill window:**
  - ACT Greens ended confidence-and-supply talks (16 Sep).
  - One Nation won WA's Secret Harbour by-election (29 Aug).
  - Victoria enters caretaker on 3 Nov for the 28 Nov election.
  - None of these changes who is government.

### Decisions

- **D6. No stand-in fixtures.** Nothing in `backend/tests/fixtures/` was invented or rebuilt from search snippets. Phase 2 fixture tests must use real files from `make recon` or manual import.
- **D7. "Blocked" stays unproven until tested.** No source is marked `blocked`. Our environment was blocked, not their sites. Sources with evidence of bot protection (CTH, VIC, SA calendar, WA) are flagged as risks.
- **D8. Search-only facts are marked.** Anything not confirmed by an official 2025–26 snippet is marked M or L in `docs/sources.md`, or `verified: false` in config. Party codes for NSW, SA, WA, TAS, ACT and NT are left empty until fixtures show the real codes.

### Open questions (numbering continues from the entry below)

4. **Network access to finish Phase 0.** Either:
   - allow these hosts in this cloud environment's network settings: aph.gov.au, parlinfo.aph.gov.au, parliament.nsw.gov.au, api.parliament.nsw.gov.au, parliament.vic.gov.au, parliament.qld.gov.au, documents.parliament.qld.gov.au, hansardsearch.parliament.sa.gov.au, parliament.wa.gov.au, parliament.tas.gov.au, search.parliament.tas.gov.au, hansard.act.gov.au, parliament.nt.gov.au, territorystories.nt.gov.au, anao.gov.au, audit.nsw.gov.au, audit.vic.gov.au, qao.qld.gov.au, audit.sa.gov.au, audit.wa.gov.au, audit.tas.gov.au, audit.act.gov.au, ago.nt.gov.au;
   - or run `make recon` from a machine on the pilot network.

   Either way, I'll then finish the fixtures, robots.txt results, terms checks and party codes.
5. **CTH fallback:** if APH's WAF blocks us, may we use OpenAustralia's mirror of the original Hansard XML (`data.openaustralia.org.au`) while the access request is pending, or only manual import?
6. **Access-request sender and contact email** (§15 Q3): needed for the User-Agent and for `docs/access-requests.md`.
7. **SA, NT and WA programs** (§15 Q7): confirmed that none is published (WA: in-progress only). Is "recent reports only" acceptable, or will those offices share their program?

### Next

- After the review and network access: `make recon`, then save fixtures, record robots.txt and terms per host in `docs/sources.md`, fill in the remaining party codes and tabling phrases, and change each source's status from `unverified`.
- Then Phase 2: Hansard connectors, in the order given in `docs/sources.md` §5.

---

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
