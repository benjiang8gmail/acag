# Hansard Watch — build specification

| | |
|---|---|
| Client | Australasian Council of Auditors-General (ACAG) |
| Product owner | Ben Jiang, Victorian Auditor-General's Office |
| Version | v1.2, 31 Oct 2026 — adds the four minimum features (F1–F4) and the ACT and NT |
| Status | For build |

> **Claude Code:** read this whole file before planning. `CLAUDE.md` holds the standing rules. Wherever this spec says *verify*, check the real site and record the answer in `docs/sources.md` rather than guessing.

---

## 1. Purpose

Senior people in Australia's audit offices need to know, quickly, what Parliament is saying that affects them. Today that means reading Hansard from 9 parliaments and 15 chambers, then checking it by hand against each office's reports and forward audit program.

Hansard Watch scans every sitting day once, stores what it has read, and turns it into a short, sourced brief that a Senior Executive can absorb in 30 seconds and a Manager can drill into and cite. It covers the Commonwealth, all 6 states and both territories (ACT and NT), and their 9 audit offices.

**Minimum features — the app is not done without all four:**

| # | Feature | Acceptance |
|---|---|---|
| F1 | Mentions of each jurisdiction's Auditor-General, with sentiment | SC5 |
| F2 | Mentions of reports tabled by each Auditor-General, with sentiment | SC6 |
| F3 | Latest developments that affect audit offices: the office itself, its mandate and resources, its future audit program, the bodies it audits | SC7 |
| F4 | Potential gaps in each office's forward performance audit program (e.g. VAGO's Annual Plan, QAO's Forward work plan) | SC8 |

## 2. Users

| User | What they need, in one line | Default view |
|---|---|---|
| Senior Executive (Auditor-General, Deputy, SES) | "What's being said about us and our reports, and what's changing for the office?" | Brief |
| Director | "Is Parliament raising issues in my sectors that our program doesn't cover?" | Gaps |
| Manager | "Find everything said about X, with exact quotes and links I can cite." | Explore |

There is one shared login for now, so personal settings (office, default view, last visit) live in the browser.

## 3. Success criteria and acceptance tests

| # | Criterion | Acceptance test — must pass, with evidence shown |
|---|---|---|
| SC1 | Scan and store the last two months of Hansard so material is not rescanned each time | The first run ingests every sitting day from the same date two months ago to today for every non-blocked chamber, storing raw files, parsed speeches and AI results. Running the update again straight away makes **0 downloads of unchanged documents and 0 LLM calls**, proven by a test and by the scan log. |
| SC2 | Offer the user an update covering anything since the last scan | On opening the app, a banner shows when Hansard was last checked and offers "Check for updates". The update processes only new sitting days, changed documents (for example proof → final) and changed audit office registers, shows live progress, and ends with a plain-English summary. |
| SC3 | Engaging, simple, intuitive dashboard for Managers, Directors and Senior Executives | A first-time executive finds the top item for their office and opens its source in 30 seconds or less and 3 clicks or fewer (scripted Playwright journey, plus a 3-person hallway test recorded in PROGRESS.md). All 9 jurisdictions appear on the dashboard. WCAG 2.2 AA with no serious or critical axe findings. Usable at 375 px wide. |
| SC4 | Small login page needing only a username and password | `/login` accepts username `acag` and the password the product owner supplies at setup (stored only as a hash in `.env`). Every other page and API route requires a session. Wrong credentials get a generic error and repeated failures are throttled. |
| SC5 | **F1** — Auditor-General mentions with sentiment | For each of the 9 offices, for the chosen period: mentions in its own parliament and in others; the sentiment split (positive / neutral / negative / mixed) and change against the previous period; and a split by speaker side (government / opposition / crossbench). Every mention shows the speaker, a one-line reason for the sentiment, a verified quote and a source link. Gold set: mention recall ≥ 0.95; sentiment agreement ≥ 0.75, with positive ↔ negative flips ≤ 5%. |
| SC6 | **F2** — Tabled-report mentions with sentiment | Each office's register of tabled reports is loaded: titles, numbers and dates for every year its website lists, plus details for the last 3 years. Hansard references are linked to the specific report where it can be identified, otherwise kept as "report not identified". Each report shows its mentions, sentiment split, speakers, first and last mention, and a "not yet mentioned in Parliament" flag. Gold set: report-link precision ≥ 0.9. |
| SC7 | **F3** — Developments affecting audit offices | A Developments feed per office, newest first, covering mandate and legislation, resourcing, governance (appointments, oversight), calls and requests for audits, debate on the office's program, public bodies created, merged or abolished, and government responses to recommendations. Sources: Hansard, plus changes found on the office's website (new or changed program, new reports, published audit requests). Each item has "why it matters" and a source link. Gold set: type agreement ≥ 0.8. |
| SC8 | **F4** — Gaps in forward performance audit programs | Each office's current program is loaded, and its topics are extracted and confirmed by a person. Issues raised in that office's parliament are compared with planned topics, audits in progress and reports from the last 3 years. Potential gaps are ranked by a transparent attention score; each shows its evidence, the closest program topic and why that topic doesn't cover the issue. Exports as a longlist (CSV and Word). An office with no published program is compared with recent reports only, and the page says so. Gold set: coverage judgement agrees with the product owner ≥ 0.8. |

## 4. Scope

**In v1:**
- Chamber Hansard (proof and final) for the 9 parliaments and 15 chambers in §5.1, including the ACT and NT Legislative Assemblies
- Audit office registers for the 9 offices in §5.2: tabled reports, forward programs, published audit requests
- Two-month Hansard backfill, then incremental updates
- AI triage, sentiment, report linking, developments, gap analysis and briefs
- The dashboard; Word, PDF and CSV exports; manual import for blocked sources

**Not in v1 — design so each is easy to add later:**
- New Zealand (ACAG member) — confirm with the sponsor (§15)
- Committee Hansard, including Senate Estimates and PAC/PAEC/JCPAA hearings — high value, likely v2
- Questions-on-notice papers, tabled papers, media monitoring
- Scoring gaps against each office's own topic-prioritisation rubric (v1 exports a longlist that feeds it)
- "Ask Hansard" natural-language Q&A with citations
- Entra ID single sign-on, Teams/Adaptive Card posting

## 5. Sources

Researched on 31 Oct 2026. These are **leads to verify in Phase 0**, not guarantees.

### 5.1 Hansard (9 parliaments, 15 chambers)

| Code | Parliament and chambers | Start page | Leads found | Publishing pattern | Terms noted |
|---|---|---|---|---|---|
| CTH | Parliament of Australia — Senate; House of Representatives (Federation Chamber proceedings should appear with House Hansard — verify) | `https://www.aph.gov.au/Parliamentary_Business/Hansard/Hanssen261110` (Senate), `https://www.aph.gov.au/Parliamentary_Business/Hansard/Hansreps_2011` (House) | The main page `https://www.aph.gov.au/Parliamentary_Business/Hansard` lists each sitting day with **PDF, XML and ParlInfo** links and "Previous sitting week" paging. ParlInfo serves one XML file per sitting day, e.g. `https://parlinfo.aph.gov.au/parlInfo/download/chamber/hansardr/2005-03-16/toc_unixml/3766-5.xml;fileType=text%2Fxml` (`hansardr` = House; the Senate dataset is probably `hansards` — verify). The Senate year page listed dates only up to 2025 when checked — confirm it is maintained before relying on it. | Proof first, Official later | CC BY-NC-ND 3.0 AU |
| NSW | Parliament of NSW — Legislative Assembly, Legislative Council | `https://www.parliament.nsw.gov.au/parliamentary-business/hansard/hansard-and-house-papers` (`filter-year`, `filter-month` query parameters) | **Public Hansard API** covering sitting dates, members, bills, daily transcripts in XML and PDF, a table of contents per day, and fragments, from Sept 1991. Docs: `https://www.parliament.nsw.gov.au/parliamentary-business/hansard/hansard-api` — the endpoint list was not in the page text we could read; inspect it. | Proof text about 3 hours after words are spoken, progressively; daily PDF about 3 hours after the last House rises; later replaced by a corrected copy | Parliament copyright and conditions of use; Data.NSW lists the API as CC BY |
| VIC | Parliament of Victoria — Legislative Assembly, Legislative Council | `https://www.parliament.vic.gov.au/parliamentary-activity/hansard/hansard-debate?page=1&pageSize=10` | Day pages at `/parliamentary-activity/hansard/hansard-details/HANSARD-974425065-{id}`; progressive HTML publishing (Dec 2018 on) and PDF records; listings are tagged Proof or Final. **Our automated test fetch was refused by bot detection.** The listing probably calls a JSON endpoint — inspect what the page requests, but do not bypass protection. | A member's speech within about 3 hours; full-day proof about 4 hours after the sitting ends; final about 5 working days later | Check |
| QLD | Queensland Parliament — Legislative Assembly (unicameral) | `https://www.parliament.qld.gov.au/Work-of-the-Assembly/Record-of-Proceedings` | Daily proof PDF: `https://documents.parliament.qld.gov.au/events/han/{YYYY}/{YYYY_MM_DD}_DAILY.pdf` (weekly `_WEEKLY.pdf` also exists). A preview of QLD's newer platform used `/Work-of-the-Assembly/Record-of-Proceedings/daily/lh/{YYYY-MM-DD}/pdf/download` — the same shape as SA's site, so check the live site for XML or extract endpoints. | Daily PDF stamped "(PROOF)"; find the final signal | Check |
| SA | Parliament of South Australia — House of Assembly (`lh`), Legislative Council (`uh`) | `https://hansardsearch.parliament.sa.gov.au/search/calendar` | **Structured XML.** Day table of contents: `https://hansardsearch.parliament.sa.gov.au/daily/{lh\|uh}/{YYYY-MM-DD}/download/toc`. Extracts: `/daily/{lh\|uh}/{YYYY-MM-DD}/extract/{n}/download`. XML carries `reviewStage`, `dateModified`, `proceeding`, `subject`, `talker` (name, house, electorate) and `startTime`. **The calendar page refused our automated test fetch.** | Use `reviewStage` and `dateModified` to detect proof → final | Copyright held by the Attorney-General of SA; extracts must be fair and accurate and must not be used for satire, ridicule or to misrepresent members |
| WA | Parliament of Western Australia — Legislative Assembly, Legislative Council | `https://www.parliament.wa.gov.au/hansard/hansard.nsf/NewAdvancedSearch` — **drop the `afd_azwaf_tok` parameter from the sponsor's original link; it is a one-off firewall session token** | Lotus Domino site. The search page has a "Daily Hansard" calendar (Council sits / Assembly sits / both) with a PDF per house per day. The token name suggests an Azure Front Door firewall that may challenge automated clients. | Draft published progressively during the day; complete draft daily about 3 hours after the house rises | Check |
| TAS | Parliament of Tasmania — House of Assembly, Legislative Council | `https://search.parliament.tas.gov.au/adv/hahansard` — **House of Assembly only.** The Legislative Council is a separate collection; start from `https://search.parliament.tas.gov.au/adv/advanced` | ISYS search engine with full-text query filtered by year. Result documents download as Original (.docx), Text, HTML5 or PDF. Coverage 1992 on. | Find the proof/final signal | Check |
| ACT | ACT Legislative Assembly (unicameral) | `https://hansard.act.gov.au/` | Debates published as PDF; the site also links unfinalised question time transcripts. | Proof daily Hansard the day after a sitting; official weekly Hansard about 3 weeks after each sitting week; final transcripts may differ slightly from proofs | Check |
| NT | Legislative Assembly of the Northern Territory (unicameral) | `https://parliament.nt.gov.au/business/parliamentary-records/draft` | Draft daily Hansard PDFs are stored in Territory Stories, the NT Library's digital repository (e.g. a file named "draft daily hansard - tuesday 10 march 2026.pdf"); records at `https://territorystories.nt.gov.au/10070/{id}`. Find how sitting days are listed and how the final version replaces the draft. | Draft first, final later — verify timing | Check |

**Phase 0 output for every chamber:** how to list sitting days; document URL pattern; format; how speakers are marked up; proof/final signal; robots.txt result; terms of use; rate limits; blockers; recommended connector approach; one saved real sitting-day fixture.

**If a source blocks automated access:** mark it `blocked`, keep going with the others, list it in PROGRESS.md open questions, and rely on manual import (§9.11) until access is arranged. Draft a short request ACAG can send to that Parliament's Hansard team asking for an allowlist or data feed, in `docs/access-requests.md`.

### 5.2 Audit offices (9)

| Code | Office | Forward performance audit program (latest found) | Other pages to use | Notes |
|---|---|---|---|---|
| ANAO | Australian National Audit Office | Annual Audit Work Program 2026–27. The draft was open for comment 17 Mar–10 Apr 2026 (`https://www.anao.gov.au/work-program/draft`); find the final version. The site also has a searchable work program (`/work-program/search`). | Audit requests appear as pages under `/work/request/` | Structured web pages — probably the easiest office source |
| AONSW | Audit Office of New South Wales | Audit Work Plan 2026–2029 (`https://www.audit.nsw.gov.au/audit-work-plan-2026-2029`, plus PDF). Earlier editions: Annual Work Program / Audit Work Program. | `/our-work/audit-program`, `/our-work/requests-for-audit` | |
| VAGO | Victorian Auditor-General's Office | Annual Plan 2026–27 (PDF dated 24 Jun 2026, with appendices) | Reports can be filtered by completed, in progress and in planning | |
| QAO | Queensland Audit Office | Forward work plan 2026–29 (PDF, Jun 2026). Older editions were called the strategic audit plan. | "Acquittal of Queensland Audit Office prior published work plans – June 2026" gives the status of previously planned audits | |
| SAAGD | Auditor-General's Department, South Australia (sa.gov.au lists it as the Audit Office of South Australia — verify the current name) | **None found** — verify whether a forward program is published | Reports at `https://www.audit.sa.gov.au/reports` | If none, F4 compares against recent reports only and says so |
| OAGWA | Office of the Auditor General Western Australia | **None found** — verify | Reports at `https://audit.wa.gov.au/reports-and-publications/reports/` | Same fallback as SA |
| AUDTAS | Audit Tasmania (Tasmanian Audit Office) | Auditor-General's Annual Plan 2026–27 (signed 22 Jun 2026; `https://audit.tas.gov.au/publication/auditor-generals-annual-plan-2026-27/`). Editions up to 2023–24 were the Annual Plan of Work. | | Public brand is now "Audit Tasmania" |
| ACTAO | ACT Audit Office | Performance Audit Program 2026–27 (PDF at `https://www.audit.act.gov.au`, with a media release) | Reports at `https://www.audit.act.gov.au` | |
| NTAGO | Northern Territory Auditor-General's Office | **None found** — verify | Reports to the Legislative Assembly are issued as dated volumes (e.g. `https://ago.nt.gov.au/reports/2024_May.pdf`); performance management system audits at `https://ago.nt.gov.au/audits/performance-management-system-audits` | Reports are bundles — split them into individual audits when building the register. Same fallback as SA if no program |

**Phase 0 output for every office:** program name, URL and format; how topics are listed (fields and statuses); report listing URL, format and paging; audit-request pages; current Auditor-General's name; robots.txt result and terms; blockers. The same polite-fetching rules apply, and manual upload (§9.11) covers any blocked site.

## 6. Architecture

```
 "Check for updates" button · CLI · optional schedule
                     │
                     ▼
              Scan orchestrator
          ┌──────────┴───────────┐
          ▼                      ▼
 Hansard connectors (9)   Office register connectors (9)
          │                      │
          ▼                      ▼
 Raw store data/raw/…     Reports · programs · topics · audit requests
          │                      │
 Parsers → speeches (FTS5)       │
          │                      │
 Pre-filter (lexicon + rules)    │
          │                      │
 LLM triage → sentiment → report linking → summaries
          │                      │
          └──────► Developments feed ◄──────┘
          │
 Gap engine: issues → coverage vs programs and reports → attention score
          │
 Brief synthesis (cached) · scan_runs log
          │
 FastAPI: auth · status · scans (SSE) · offices · mentions · reports · developments · gaps · search · exports · imports
          │
 React + Fluent 2 SPA: Login · Brief · Mentions · Developments · Gaps · Explore · Coverage
```

**Repo layout:** `backend/` (`app/`, `connectors/`, `registers/`, `parsers/`, `pipeline/`, `gaps/`, `api/`, `tests/`), `web/`, `config/`, `eval/`, `docs/`, `data/` (gitignored).

**Hansard connector interface** (Python `Protocol`, one file per parliament in `backend/connectors/{code}.py`):

| Method | Returns | Rule |
|---|---|---|
| `list_sitting_days(start, end)` | sitting days with chamber and version hint | Must distinguish "no sitting" from "could not check" |
| `list_documents(day)` | document refs: URL, format, version hint, ETag/Last-Modified if known | |
| `fetch(ref)` | body or `unchanged` | Conditional GET; SHA-256 of body |
| `parse(raw)` | normalised speeches | Keep page numbers or anchors for citations |

**Register connector interface** (one file per office in `backend/registers/{code}.py`):

| Method | Returns | Rule |
|---|---|---|
| `list_reports()` | report refs: number, title, tabled date, URL | Every year the site lists; page through politely |
| `fetch_report(ref)` | summary page or PDF | Only within `REPORT_LOOKBACK_YEARS` |
| `list_programs()` | current and previous program documents | |
| `list_audit_requests()` | published audit requests | Only where the office publishes them |

Adding a parliament later (e.g. New Zealand) should mean one Hansard connector, one register connector, and a row in each of `config/sources.yaml` and `config/offices.yaml`.

**Minimum API:**

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` |
| Status and scans | `GET /api/status`, `POST /api/scans`, `GET /api/scans/{id}`, `GET /api/scans/{id}/events` (SSE) |
| Offices and mentions (F1) | `GET /api/offices`, `GET /api/mentions` |
| Reports (F2) | `GET /api/reports`, `GET /api/reports/{id}` |
| Developments (F3) | `GET /api/developments` |
| Programs and gaps (F4) | `GET /api/programs`, `PATCH /api/program-topics/{id}` (confirm or edit), `GET /api/gaps`, `GET /api/gaps/{id}`, `GET /api/gaps/matrix` |
| Content | `GET /api/items`, `GET /api/items/{id}`, `GET /api/search`, `GET /api/brief` |
| Exports and imports | `GET /api/export/brief.docx`, `GET /api/export/brief.pdf`, `GET /api/export/items.csv`, `GET /api/export/mentions.csv`, `GET /api/export/gaps.csv`, `GET /api/export/gaps.docx`, `POST /api/imports` |
| Health | `GET /api/health` (no auth) |

## 7. Data model

SQLite via SQLAlchemy and Alembic, written so a later move to Postgres is a config change.

| Table | Key columns | Notes |
|---|---|---|
| `sources` | `id` (e.g. `VIC-LA`, `ACT-LA`, `NT-LA`), parliament, chamber, connector, enabled, status (`ok`/`no_sittings`/`blocked`/`error`), `last_checked_at`, `last_success_at`, `watermark_date`, notes | One row per chamber (15) |
| `sitting_days` | `source_id`, `sitting_date` (local date), `discovered_at`, version (`proof`/`final`/`unknown`), status | Unique on (`source_id`, `sitting_date`) |
| `documents` | id, `sitting_day_id`, url, format, version, etag, `last_modified`, `sha256`, `raw_path`, `fetched_at`, `superseded_by`, origin (`auto`/`manual`) | New row only when `sha256` changes |
| `speeches` | id, `document_id`, seq, `debate_title`, `proceeding_type`, `speaker_name`, `speaker_role`, party, `speaker_side`, electorate, `start_time`, page, `anchor_url`, text, `text_sha256` | FTS5 index on text, debate title and speaker |
| `analyses` | `speech_id`, `text_sha256`, stage, model, `prompt_version`, `output_json`, `input_tokens`, `output_tokens`, `cost_usd`, `created_at` | Unique on (`text_sha256`, stage, model, `prompt_version`) — the "never re-analyse" key |
| `items` | id, `speech_id`, categories, significance, themes, agencies, headline, summary, `why_it_matters`, quote, `quote_verified`, confidence, `first_seen_run_id` | One per relevant speech |
| `offices` | code (`ANAO`, `AONSW`, `VAGO`, `QAO`, `SAAGD`, `OAGWA`, `AUDTAS`, `ACTAO`, `NTAGO`), name, other names, jurisdiction, parliament source ids, website, program name | Seeded from `config/offices.yaml` (9 rows) |
| `office_mentions` | `speech_id`, office, sentiment, reason, quote, `quote_verified`, `speaker_side` | One row per office mentioned in a speech (F1) |
| `audit_reports` | id, office, number, title, `tabled_date`, `report_type`, themes, agencies, url, `sha256`, `fetched_at` | The report register (F2, F4) |
| `report_mentions` | `speech_id`, `report_id` (null = not identified), `as_said`, `match_method`, confidence, sentiment, reason, quote, `quote_verified` | F2 |
| `audit_programs` | id, office, title, period, `published_date`, url, `sha256`, version, `confirmed_by`, `confirmed_at` | One row per program version |
| `program_topics` | id, `program_id`, title, objective, themes, agencies, `planned_timing`, status (`planned`/`in_progress`/`tabled`/`deferred`/`removed`), `page_ref`, `linked_report_id`, confirmed | F4 |
| `audit_requests` | id, office, title, requester, date, status, url | Where offices publish them (F3, F4) |
| `developments` | id, office, type, `source_type` (`hansard`/`office_site`), date, headline, `why_it_matters`, significance, links to speech / report / program / request | Unified feed (F3) |
| `issues` | id, jurisdiction, label, themes, agencies, `first_raised`, `last_raised`, `item_ids`, `attention_score`, `score_breakdown`, `evidence_hash` | Clusters of Hansard items (F4) |
| `coverage_assessments` | `issue_id`, office, coverage (`planned`/`in_progress`/`recent_report`/`partly`/`not_covered`), `matched_topic_ids`, `matched_report_ids`, reason, `input_hash`, model, `prompt_version` | Cached; recomputed only when `input_hash` changes |
| `briefs` | office, `period_start`, `period_end`, `data_version`, `output_json`, `created_at` | Cached synthesis |
| `scan_runs` | id, trigger (`manual`/`scheduled`/`cli`), `started_at`, `finished_at`, status, `per_source_json`, tokens, `cost_usd`, `error_summary` | Audit trail; drives "last checked" |

Raw files live at `data/raw/{source_id}/{YYYY-MM-DD}/{sha256}.{ext}` (Hansard) and `data/raw/offices/{office}/{sha256}.{ext}` (registers), and are never deleted by a scan.

## 8. Scan logic — how "no rescanning" works (SC1, SC2)

1. **Window.** Backfill runs from the same date two months ago to today (31 Aug to 31 Oct 2026 for a run on 31 Oct). Set by `BACKFILL_MONTHS`.
2. **Discover.** For each enabled source, list sitting days from `watermark_date + 1` to today, plus any day still marked `proof` within `PROOF_RECHECK_DAYS` (default 28).
3. **Fetch conditionally.** Send `If-None-Match` / `If-Modified-Since` where known. Hash the body. Same hash means `unchanged`; stop there.
4. **Parse only changed documents.** A final that replaces a proof becomes a new document version. Speeches are re-derived, and only speeches whose `text_sha256` changed go forward. Items keep their ids where the text is unchanged.
5. **Analyse only what is new.** Skip any speech whose (`text_sha256`, stage, model, `prompt_version`) already has an analysis. Bumping `PROMPT_VERSION` is the only deliberate way to re-analyse, and the UI shows the estimated cost and asks first.
6. **Advance the watermark** only after a day has been fetched, parsed and analysed without error.
7. **Log** every run in `scan_runs` with per-source counts: days checked, new, changed, unchanged, speeches analysed, items created, errors, tokens and cost.
8. **One scan at a time** (database lock). If a scan is running, anyone who opens the app sees its progress instead of a second button.
9. **Recess is not failure.** If the calendar shows no sittings, the status is `no_sittings` (shown grey, e.g. "Not sitting since Thu 1 Oct"), not an error. The territories sit far less often than the larger parliaments; that is expected.
10. **Retention.** Keep everything by default. The widest dashboard period is the stored window. `RETENTION_DAYS` is optional.
11. **Registers.** Each update also refreshes office registers older than `REGISTER_REFRESH_DAYS` (default 7), with the same conditional-fetch and hash rules. A changed program document becomes a new program version: its topics are re-extracted (marked unconfirmed) and the differences from the previous version (added, removed, deferred topics) are recorded as developments. A newly listed report triggers report linking again, but only for references still "not identified".
12. **Gap analysis** recomputes only issues whose evidence changed and offices whose program or report register changed, using the `input_hash` stored on each coverage assessment.

## 9. AI analysis

### 9.1 Pipeline

| Stage | What happens | Engine |
|---|---|---|
| A. Normalise | Split each day into speeches (one speaker turn under a debate heading). In Question Time, analyse the question and answer together. Chunk speeches over ~6k tokens with overlap. Compute `speaker_side` (§9.4). | Code |
| B. Pre-filter | Send a speech to the LLM if it hits the audit lexicon (always — including office names, Auditor-General names and report titles from the registers) or theme and risk terms above a threshold. Record why. Aim for 10% or fewer of speeches reaching the LLM. | Code with `config/lexicon.yaml` and `config/themes.yaml` |
| C. Triage | Relevant or not; categories (multi-label, §9.3); significance; offices mentioned, each with sentiment; report references as said, each with sentiment; development type; themes; agencies | `LLM_TRIAGE_MODEL` (default `claude-haiku-5-5`) |
| D. Report linking | Match each report reference to a register entry, or "not identified" (§9.5) | Code + `LLM_TRIAGE_MODEL` |
| E. Summarise | Headline, summary, why it matters, verbatim quote — for relevant speeches with significance 2 or more | `LLM_SUMMARY_MODEL` (default `claude-sonnet-5-5`) |
| F. Registers | Extract program topics (with page references) from program documents; normalise report metadata; split bundled reports (e.g. NT) into individual audits | `LLM_SUMMARY_MODEL`; a person confirms program topics |
| G. Developments | Merge Hansard developments and register changes into one feed per office (§9.6) | Code |
| H. Gap analysis | Issues → coverage → attention score (§9.7) | Local embeddings + `LLM_SUMMARY_MODEL` + code |
| I. Brief | Per office and for "ACAG — all", per period: top items across F1–F4, coverage note | `LLM_SUMMARY_MODEL`, cached in `briefs` |

### 9.2 Lexicon and themes (seed — Phase 0 completes and verifies)

| List | Seed entries |
|---|---|
| Audit offices | The 9 offices in §5.2 with short and alternative names (e.g. Tasmanian Audit Office / Audit Tasmania; Auditor-General's Department / Audit Office of South Australia) |
| Auditors-General | Each current Auditor-General's name (verify in Phase 0). Count a name only near audit context. |
| Attribution rule | An unqualified "the Auditor-General" refers to the Auditor-General of that parliament's own jurisdiction |
| Generic audit terms | Auditor-General, Auditor General, audit report, performance audit, financial audit, Audit Act, audit recommendations |
| Report titles | Every title and number in the report registers (§5.2) |
| Tabling phrases | "tabled the report of the Auditor-General", "Auditor-General—Report …" (verify each parliament's wording) |
| Request phrases | "call on the Auditor-General", "refer … to the Auditor-General", "ask the Auditor-General to investigate" |
| Committees | JCPAA (Cth), Public Accounts Committee (NSW), Public Accounts and Estimates Committee (Vic), Public Accounts Committee (WA), Public Accounts Committee (Tas), Standing Committee on Public Accounts (ACT), Public Accounts Committee (NT) — verify ACT, NT, QLD and SA equivalents |
| Integrity bodies | NACC (Cth), ICAC (NSW, SA), IBAC (Vic), CCC (QLD, WA), Integrity Commission (Tas), ACT Integrity Commission, NT Independent Commissioner Against Corruption, Ombudsman offices |
| Risk terms | cost overrun, blowout, delay, procurement, tender, grant, probity, conflict of interest, consultants, contract variation, value for money, cyber, data breach, fraud, overspend, waste, service failure, workforce shortage |
| Public-body changes | establish, abolish, merge, dissolve, new authority, new agency, machinery of government |
| Themes | Health; Education and training; Transport and infrastructure; Housing and homelessness; Justice, police and corrections; Child protection and social services; Disability and NDIS; Local government; Environment, water and energy; Digital, data and cyber; Public finance and budget; Procurement and grants; Integrity and governance; Public sector workforce; Emergency management; First Nations outcomes |

### 9.3 Categories and significance

| Family | Category | Meaning | Feeds |
|---|---|---|---|
| Office and reports | `AG_MENTION` | An Auditor-General or audit office is mentioned | F1 |
| | `REPORT_MENTION` | A tabled audit report is referred to | F2 |
| | `REPORT_TABLED` | The tabling of an audit report is recorded | F2, F3 |
| | `COMMITTEE` | Accountability committee activity tied to audit work | F3 |
| Developments | `MANDATE` | Bills or motions on an office's mandate, independence or powers | F3 |
| | `RESOURCING` | Funding, budget, appropriation or staffing of an audit office | F3 |
| | `GOVERNANCE` | Appointment, term or conduct of an Auditor-General; oversight of the office | F3 |
| | `AUDIT_REQUEST` | A call, request or referral for an audit | F3, F4 |
| | `PROGRAM` | Debate about an office's forward program | F3, F4 |
| | `ENTITY_CHANGE` | A public body created, merged or abolished (changes what offices audit) | F3 |
| | `FOLLOW_UP` | Government response to, or progress on, audit recommendations | F3, F4 |
| Signals | `RISK_SIGNAL` | A specific issue that could become an audit topic | F4 |
| | `INTEGRITY` | Integrity-body findings or misconduct involving public money | F3, F4 |

| Significance | Rule |
|---|---|
| 5 | Changes an office's mandate, powers, funding or independence; an Auditor-General's appointment, removal or conduct; or a Premier, Chief Minister, Prime Minister, Treasurer or Minister disputes or endorses an audit finding |
| 4 | An audit report is debated or cited in Question Time or a ministerial statement; a committee acts on an audit or on the office's program or budget; a formal call or referral for an audit |
| 3 | A specific risk signal (named program or agency plus dollars, dates or numbers); a public body created, merged or abolished; a government response to recommendations |
| 2 | A passing reference to an audit office or report, or a general accountability point |
| 1 | Background only — stored, hidden by default |

### 9.4 Sentiment (F1, F2)

- **Meaning:** the speaker's stance toward the audit office, or toward the specific report and its findings. Not their view of the government, and not the tone of the report itself.
- **Values:** `positive` (relies on, endorses or praises), `neutral` (factual reference, tabling, procedure), `negative` (disputes, dismisses, or attacks credibility or independence), `mixed` (both).
- **Example:** an opposition member saying "the Auditor-General's damning report shows the project is failing" is **positive** toward the report. A minister saying "the report relies on old data and is wrong" is **negative**.
- Every sentiment has a reason (20 words or fewer) and a verified quote. Mentions without a verified quote are left out of sentiment totals.
- **Speaker side** (government / opposition / crossbench / unknown) is computed in code from party and ministerial role using `config/governments.yaml` (verify the current governing parties of all 9 parliaments in Phase 0). The model never decides it.
- **Aggregates** per office and period: count by sentiment; net sentiment = (positive − negative) ÷ total × 100; change against the previous period; split by side. With small counts (common in the ACT and NT), show the counts rather than a net score.

### 9.5 Report linking (F2)

1. **Candidates:** the register of the office the reference points to (by the attribution rule), ranked by report-number match, fuzzy title match (rapidfuzz) and local embedding similarity, with a recency boost.
2. The model picks one of up to 5 candidates or "not identified", with a confidence.
3. Link only when confidence ≥ `REPORT_LINK_MIN_CONFIDENCE` (0.7); otherwise keep "report not identified" with the words as said.
4. Reconcile `REPORT_TABLED` events with register dates; log mismatches.
5. When a new report enters the register, re-run linking only for references still "not identified".

### 9.6 Developments (F3)

- **From Hansard:** items in the development categories (§9.3).
- **From office websites:** a new or changed program version (topics added, removed or deferred, diffed against the previous version); newly listed reports; newly published audit requests (ANAO and NSW publish these — verify the others).
- One feed per office, newest first. When the same event appears in Hansard and on the website, merge it and show both sources.

### 9.7 Program gaps (F4)

1. **Program register.** Extract each program's topics: title, objective, themes, agencies, planned timing, status, page reference. A person confirms topics on the Program register screen. Until then, gap results are labelled "Draft — program not yet confirmed".
2. **Status** (planned / in progress / tabled / deferred / removed) comes from the program and the office's website — e.g. VAGO's in-progress filter, QAO's acquittal document, ANAO's work program pages.
3. **Issues.** Group Hansard items flagged `RISK_SIGNAL`, `AUDIT_REQUEST`, `FOLLOW_UP` or `INTEGRITY` into issues per jurisdiction using local embeddings (fastembed), with a label written by the model. A new item joins an existing issue above a similarity threshold, otherwise it starts a new one. Issue ids stay stable.
4. **Coverage.** Compare each issue with that office's planned and in-progress topics and its reports from the last `REPORT_LOOKBACK_YEARS` (top 5 by similarity). The model judges `planned`, `in_progress`, `recent_report`, `partly` or `not_covered`, giving a reason and the matched ids. If only an older report covered the issue, show "Last audited: {year}".
5. **Attention score (0–100)**, computed in code with weights in `config/gap_scoring.yaml`:

| Factor | Measures |
|---|---|
| Volume | Distinct items (log-scaled) |
| Breadth | Distinct speakers; bonus when both government and non-government members raise it |
| Intensity | Highest significance |
| Forum | Question Time, committee and ministerial statements weigh more than adjournment or members' statements |
| Recency | 30-day half-life |
| Materiality | Largest dollar amount mentioned |
| Audit requests | Explicit calls for an audit |
| Echo | Raised in other parliaments (small weight, shown separately) |

6. **Potential gap** = coverage `partly` or `not_covered`, and score ≥ `GAP_SCORE_THRESHOLD` (default 40). Each shows: the issue, sectors, agencies, score with a "why this score" breakdown, evidence items with links, the closest program topic and why it doesn't cover the issue, and first and last raised. Thresholds may need tuning per office: the ACT and NT parliaments are smaller and sit less often.
7. **"Program topics in the spotlight":** planned topics Parliament is actively discussing (helps with scoping and timing).
8. **Independence note**, always visible: "Prepared from public sources. Each Auditor-General sets their own program; parliamentary attention is one input among many."
9. Results are only as deep as the Hansard window — two months at first, growing as data accumulates. Show the window on the page.

### 9.8 Output contract

Use structured output (JSON schema or tool use). Merged view of triage and summary for one speech:

```json
{
  "relevant": true,
  "categories": ["REPORT_MENTION", "AUDIT_REQUEST"],
  "significance": 4,
  "office_mentions": [
    {"office": "ACTAO", "sentiment": "negative", "reason": "20 words or fewer", "quote": "verbatim, 40 words or fewer"}
  ],
  "report_refs": [
    {"as_said": "the Auditor-General's report on hospital wait times", "sentiment": "positive", "reason": "20 words or fewer", "quote": "verbatim, 40 words or fewer"}
  ],
  "development_type": "AUDIT_REQUEST",
  "themes": ["Health"],
  "agencies": ["Canberra Health Services"],
  "headline": "12 words or fewer",
  "summary": "60 words or fewer, plain English",
  "why_it_matters": "30 words or fewer, written for an audit office executive",
  "confidence": 0.82
}
```

`report_id` is added by stage D, and `speaker_side` by code — never by this call.

### 9.9 Guardrails

- Hansard text is untrusted input. Wrap it in delimiters and instruct the model to ignore any instructions inside it.
- **Quote check:** after normalising whitespace and quote marks, every quote must be an exact substring of the speech. Otherwise drop it and set `quote_verified = false`.
- **Number check:** every number in a headline or summary must appear in the speech. Otherwise regenerate once, then flag.
- Sentiment totals include only mentions with a verified quote.
- Report links below `REPORT_LINK_MIN_CONFIDENCE` are never shown as linked.
- A coverage judgement must name the matched topic or report ids; one with no ids can only be `not_covered`.
- Invalid JSON gets one retry, then the analysis is marked `failed` — shown on the Coverage page, never on the dashboard.
- Store model, prompt version, tokens and cost for every call.

### 9.10 Cost and data controls

- Pre-filter before any LLM call. Use the Message Batches API for the backfill. Prompt-cache the static system prompt and taxonomy.
- `LLM_MAX_SPEND_USD_PER_RUN` is a hard cap: stop cleanly and carry on next run.
- Embeddings run locally with fastembed — no extra service, and nothing leaves the machine.
- Only public text goes to the model: Hansard, program documents and report metadata. User settings, confirmations and saved items never leave the server.
- Keep LLM access behind `LLMClient` (default: Anthropic API) so ACAG can switch to Claude on Amazon Bedrock, Google Cloud or Microsoft Foundry if it wants in-region processing.

### 9.11 Manual import (fallback for blocked sources)

Coverage page → "Import": upload a Hansard sitting day (choose parliament, chamber and date; PDF, XML, DOCX or HTML), or an office's program document or report list. Imports run through the same pipeline, are marked `manual`, and are de-duplicated by hash.

### 9.12 Evaluation

Claude Code proposes labels and the product owner (or each office's nominee) confirms them. `make eval` writes results to `docs/eval.md`; rerun whenever prompts change. Every gold set includes items from all 9 parliaments.

| Gold set | Size | Target |
|---|---|---|
| Relevance and categories | ~70 speeches, ~25 of them negatives | Office and report mention recall ≥ 0.95; relevance precision ≥ 0.8 |
| Sentiment | ~90 office and report mentions | Agreement ≥ 0.75; positive ↔ negative flips ≤ 5% |
| Report links | ~45 references | Precision ≥ 0.9 |
| Developments | ~30 items | Type agreement ≥ 0.8 |
| Coverage | ~35 issue–program pairs | Agreement ≥ 0.8 |

## 10. Dashboard

### 10.1 Principles

- **30-second rule:** the top story for your office is visible without scrolling or clicking.
- **Brief → item → source:** three levels, never more.
- Plain English and Australian spelling. No acronym without a tooltip.
- Every number is clickable and leads to the items behind it.
- Every AI summary is labelled "AI summary — check the source" and links to the page or anchor it came from.
- Sentiment always shows its reason and quote. Gap results show evidence, not instructions, and always carry the independence note.
- Show gaps in coverage honestly ("WA not checked — access blocked"; "NT has no published program — compared with recent reports only"). Never pad.
- **All 9 jurisdictions are always visible**, including the ACT and NT. A jurisdiction with no sittings in the period shows "Not sitting", not an empty space.
- Calm visual design: Fluent 2, generous whitespace, one consistent accent colour per jurisdiction (9), light and dark themes.

### 10.2 First run

Two questions, stored in the browser and changeable from the header:
1. "Which office are you from?" — the 9 offices in §5.2, plus "ACAG — all offices".
2. "What do you want to see first?" — Brief, Mentions, Developments, Gaps or Explore.

### 10.3 Screens

| Screen | For | Contents |
|---|---|---|
| Login | Everyone | App name, username, password, Sign in. Nothing else. |
| Brief (home) | Executives | Update banner · "This fortnight in 30 seconds": 3–5 headline cards ranked by significance, with at least one from each of F1–F4 when they have items · 4 tiles, one per minimum feature: Auditor-General mentions (count and sentiment bar), report mentions (count and sentiment bar), new developments, potential program gaps — each with change against the previous period · Australia tile map with **9 tiles** (Cth, NSW, Vic, Qld, SA, WA, Tas, ACT, NT; toggle: mentions, net sentiment, gaps) · Download brief (Word or PDF) · Copy for email or Teams. With "ACAG — all offices" selected, a 9-row table replaces the tiles: one row per office across F1–F4. |
| Mentions (F1, F2) | All | **Auditors-General tab:** one row per office (9) — mentions (own parliament / elsewhere), sentiment bar, net sentiment, trend sparkline, split by side; click for the mention list (speaker, side, sentiment and reason, verified quote, source link). **Reports tab:** register table — office, number, title, tabled date, mentions, sentiment bar, last mentioned; a "not yet mentioned" filter; click for a report page with every mention and a timeline since tabling. |
| Developments (F3) | All | Feed per office, newest first, grouped by type: mandate, resourcing, governance, audit requests, program, public bodies, responses to recommendations · source badge (Hansard or office website) · why it matters · filters by office, type and date |
| Gaps (F4) | Directors | Per office: program summary (name, version, confirmed or draft, topics by status) · ranked potential gaps (issue, sectors, attention score with "why this score", evidence count, closest program topic and why it doesn't cover the issue, "Last audited" where relevant) · sector × coverage heatmap (themes × covered / partly / not covered) · "Program topics in the spotlight" · export longlist (CSV, Word) · independence note |
| Explore | Managers | Full-text search over all stored Hansard (FTS5, not only AI items), plus filters: jurisdiction, chamber, dates, category, theme, significance, sentiment, speaker, party, side · results with highlighted snippets · item drawer: summary, why it matters, verified quote, debate title, speaker and role, source link, related items in other parliaments, "Add to brief", "Copy citation" · CSV export |
| Coverage and registers (menu) | Everyone; admin actions | Status of all 15 Hansard chambers and 9 office registers: last checked, latest item stored, last error · Program register: review, edit and confirm extracted topics · scan history with tokens and cost · import · retry failed analyses |

Header on every page: office switcher, view tabs (Brief · Mentions · Developments · Gaps · Explore), period picker (default last 2 weeks, up to the full stored window), and a "New since your last visit" count. Coverage and registers sit in the menu.

### 10.4 Update flow (SC2)

1. On load, `GET /api/status` returns the last check time, status per source, and `update_recommended` (true if more than 24 hours since the last check, or a known sitting day is newer than a watermark).
2. Banner: "Hansard last checked Mon 26 Oct 2026 (5 days ago). Check for anything new since then?" with [Check now] and [Not now].
3. Progress panel: one row per parliament (9) and one for the office registers, with live state over SSE — checking → n new days → analysing → done, or not sitting, or blocked.
4. Finish: "4 parliaments sat · 7 new sitting days · 12 new items · 2 mention your office · 1 new ACT Audit Office report · QAO program unchanged" with [Show me]. New items carry a "New" badge.

### 10.5 Exports

- Brief to Word (.docx) and PDF, one page: period, coverage note, top items across F1–F4 with source citations, mentions and sentiment summary.
- "Copy for email or Teams": plain-text/markdown version of the brief.
- Mentions (F1, F2) to CSV.
- Gaps longlist to CSV and Word: issue, sectors, agencies, score and breakdown, evidence links, closest program topic and reason, first and last raised.
- Explore results to CSV.

### 10.6 Quality bar

WCAG 2.2 AA (axe: no serious or critical findings); fully keyboard-usable with visible focus; screen-reader labels; respects reduced motion; works at 375 px (the 9-tile map stays legible); the Brief loads in 2 seconds or less with two months of data on a laptop.

## 11. Login and security (SC4 — interim)

- `/login` takes a username and password only. Username: `acag`. Password: supplied by the product owner at setup.
- Store `APP_USERNAME` and `APP_PASSWORD_HASH` (argon2 or bcrypt) in `.env`, which is gitignored. **Never write the plaintext password into any committed file, log or test.** Provide `make set-password`.
- Session: signed cookie, httpOnly, Secure when served over HTTPS, SameSite=Lax, 8-hour expiry; logout clears it.
- Every `/api/*` route except `/api/auth/login` and `/api/health` needs a session. SPA routes redirect to `/login`.
- Constant-time comparison, a generic error message, and throttling after 5 failures in 15 minutes per IP.
- Security headers: CSP, frame-ancestors, Referrer-Policy. Pin dependency versions.
- Before any shared deployment, replace this with Entra ID (multiple offices means a multi-tenant app or B2B guests) and HTTPS only. Not part of this build.

## 12. Build phases

One phase at a time. At the end of each: `make test` green, PROGRESS.md updated (done · evidence · decisions · next), one commit.

| Phase | Outcome | Definition of done — evidence shown in the session |
|---|---|---|
| 0 · Source recon | Know exactly how to get every chamber and every office register | `docs/sources.md` complete for 15 chambers (§5.1) and 9 offices (§5.2) · one real fixture per chamber and per office source, or a documented blocker · lexicon verified, including current Auditor-General names · current governing parties of all 9 parliaments in `config/governments.yaml` · `docs/access-requests.md` drafted for blocked sources · **stop for product-owner review** |
| 1 · Skeleton and login | Running app shell | `backend/`, `web/`, Makefile, `.env.example`, Alembic baseline · login, logout and session per §11 · protected API returns 401 without a session · `make test` green |
| 2 · Hansard connectors and store | Two-month backfill and incremental updates | Connectors for all non-blocked chambers (including ACT and NT) pass fixture tests · `make backfill` completes and logs a scan run · an immediate `make scan` shows 0 changed downloads and 0 LLM calls · proof → final test passes · `/api/status` correct |
| 3 · Audit office registers | Reports, programs and audit requests for all 9 offices | Report registers loaded for every office (NT bundles split into individual audits) · current programs loaded where published, "not published" recorded otherwise · topics extracted with page references and shown on the Program register screen for confirmation · an immediate re-run makes 0 changed downloads |
| 4 · AI analysis (F1–F3) | Items, sentiment, report links, developments, briefs | Pre-filter, triage, sentiment, report linking, developments, summaries and brief working · guardrails enforced by tests · `make eval` meets the SC5–SC7 targets · backfill and update costs reported |
| 5 · Gap analysis (F4) | Issues, coverage, attention score, longlist export | Coverage gold set meets the SC8 target · every gap shows evidence, closest topic and reason · a re-run with no new evidence and no program change makes 0 LLM calls · CSV and Word longlist exports work |
| 6 · Dashboard | Brief, Mentions, Developments, Gaps, Explore, Coverage, update flow | Playwright journeys pass: (a) login → brief → open source; (b) check for updates → progress → summary → "New" badges; (c) Auditors-General → filter by side → open a mention; (d) report → its mentions → source; (e) gaps → evidence → export longlist; (f) search → filter → CSV; (g) all 9 jurisdictions visible on the Brief map and in the office switcher · axe clean · 375 px screenshots in `docs/screens/` |
| 7 · Hardening and handover | Ready for a pilot | Word/PDF brief export · manual import (Hansard and office documents) · README (setup, run, add a parliament or office) · RUNBOOK (failed scans, blocked sources, program confirmation, costs) · an independent review subagent checks the code against this spec, and every finding is fixed or logged |

## 13. Testing

- Unit tests never touch the network: Hansard and register connectors run against recorded fixtures.
- Parser golden files: fixture in, expected speeches (or program topics) JSON out.
- Sync tests: unchanged → no-op; a new day → only that day processed; proof → final with edits → only the changed speeches re-analysed; unchanged register → no-op; changed program → new version with the topic differences recorded as developments.
- Gap tests: recompute only when inputs change; coverage cache keyed by `input_hash`.
- LLM tests use a fake `LLMClient`. One opt-in live smoke test (`make smoke-llm`).
- End-to-end: the Playwright journeys in Phase 6.

## 14. Configuration

`.env.example` (real values only in `.env`):

```
APP_USERNAME=acag
APP_PASSWORD_HASH=              # make set-password
SESSION_SECRET=                 # make secret
ANTHROPIC_API_KEY=
LLM_TRIAGE_MODEL=claude-haiku-5-5
LLM_SUMMARY_MODEL=claude-sonnet-5-5
PROMPT_VERSION=1
LLM_MAX_SPEND_USD_PER_RUN=30
BACKFILL_MONTHS=2
PROOF_RECHECK_DAYS=28
REGISTER_REFRESH_DAYS=7
REPORT_LOOKBACK_YEARS=3
REPORT_LINK_MIN_CONFIDENCE=0.7
GAP_SCORE_THRESHOLD=40
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5   # fastembed, runs locally
FETCH_MIN_INTERVAL_SECONDS=2
FETCH_USER_AGENT=ACAG-HansardWatch/0.1 (+mailto:CONTACT_EMAIL)
SCAN_SCHEDULE_CRON=             # blank = manual updates only
DISPLAY_TIMEZONE=Australia/Melbourne
DATA_DIR=./data
```

Config files:
- `config/sources.yaml` — 15 chambers, enable/disable
- `config/offices.yaml` — 9 offices: names and other names, jurisdiction, current Auditor-General, program name and URL, reports URL, audit-requests URL, colour
- `config/governments.yaml` — governing parties per parliament, with dates
- `config/lexicon.yaml`, `config/themes.yaml`
- `config/gap_scoring.yaml` — attention-score weights, with optional per-office thresholds

Sitting dates are stored as local dates per parliament (WA, QLD and NT do not use daylight saving).

## 15. Open questions for the product owner

1. Add New Zealand (an ACAG member)?
2. Add committee Hansard (Senate Estimates, PAC/PAEC/JCPAA hearings) in v2?
3. Contact email for the crawler's User-Agent and for access requests to parliaments and offices.
4. Which LLM route will ACAG approve: Anthropic API direct, or Claude through a cloud provider?
5. Hosting and identity for the pilot: whose tenant, and the Entra ID plan across offices.
6. Who confirms the evaluation labels?
7. SA, WA and NT: if no forward program is published, is comparing against recent reports only acceptable — or can those offices share their program?
8. Who confirms each office's extracted program topics — the office's planning team?
9. Are the gap threshold (score 40) and 3-year report lookback right for ACAG, and should the ACT and NT have lower thresholds?
10. Should offices see each other's gap results, or only their own? All inputs are public, but the presentation may be sensitive.
