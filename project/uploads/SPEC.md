# Hansard Watch — build specification

| | |
|---|---|
| Client | Australasian Council of Auditors-General (ACAG) |
| Product owner | Ben Jiang, Victorian Auditor-General's Office |
| Spec date | 31 Oct 2026 |
| Status | v1 for build |

> **Claude Code:** read this whole file before planning. `CLAUDE.md` holds the standing rules. Wherever this spec says *verify*, probe the real site and record the answer in `docs/sources.md` rather than guessing.

---

## 1. Purpose

Senior people in Australia's audit offices need to know, quickly, what Parliament is saying that affects them: mentions of their office and its reports, debate about their mandate, and emerging issues that could become audit topics. Today that means reading Hansard from 7 parliaments and 13 chambers.

Hansard Watch scans every sitting day once, stores what it has read, and turns it into a short, sourced brief that a Senior Executive can absorb in 30 seconds and a Manager can drill into and cite.

## 2. Users

| User | What they need, in one line | Default view |
|---|---|---|
| Senior Executive (Auditor-General, Deputy, SES) | "What do I need to know this fortnight, and is anyone talking about us?" | Brief |
| Director | "What's happening in my sectors across parliaments, and are there audit topic signals?" | Themes |
| Manager | "Find everything said about X, with exact quotes and links I can cite." | Explore |

There is one shared login for now, so personal settings (office, default view, last visit) live in the browser.

## 3. Success criteria and acceptance tests

| # | Criterion (from ACAG) | Acceptance test — must pass, with evidence shown |
|---|---|---|
| SC1 | Scan and store the last two months of Hansard so material is not rescanned each time | The first run ingests every sitting day from the same date two months ago to today for every non-blocked chamber, storing raw files, parsed speeches and AI results. Running the update again straight away makes **0 downloads of unchanged documents and 0 LLM calls**, proven by a test and by the scan log. |
| SC2 | Offer the user an update covering anything since the last scan | On opening the app, a banner shows when Hansard was last checked and offers "Check for updates". The update processes only new sitting days and documents that changed (for example proof → final), shows live progress per parliament, and ends with a plain-English summary. |
| SC3 | Engaging, simple, intuitive dashboard for Managers, Directors and Senior Executives | A first-time executive finds the top item for their office and opens its Hansard source in 30 seconds or less and 3 clicks or fewer (scripted Playwright journey, plus a 3-person hallway test recorded in PROGRESS.md). WCAG 2.2 AA with no serious or critical axe findings. Usable at 375 px wide. |
| SC4 | Small login page needing only a username and password | `/login` accepts username `acag` and the password the product owner supplies at setup (stored only as a hash in `.env`). Every other page and API route requires a session. Wrong credentials get a generic error and repeated failures are throttled. |

## 4. Scope

**In v1:** chamber Hansard (proof and final) for the 7 parliaments and 13 chambers in §5; a two-month backfill then incremental updates; AI triage, summaries and briefs; the dashboard; Word/PDF/CSV exports; a manual-import fallback for blocked sources.

**Not in v1 — design so each is easy to add later:**
- ACT and NT Legislative Assemblies (both ACAG members) and New Zealand — confirm with the sponsor (§15)
- Committee Hansard, including Senate Estimates and PAC/PAEC/JCPAA hearings — high value, likely v2
- Questions-on-notice papers, tabled papers, media monitoring
- "Ask Hansard" natural-language Q&A with citations
- Entra ID single sign-on, Teams/Adaptive Card posting

## 5. Sources

Researched on 31 Oct 2026. These are **leads to verify in Phase 0**, not guarantees.

| Code | Parliament and chambers | Start page from sponsor | Leads found | Publishing pattern | Terms noted |
|---|---|---|---|---|---|
| CTH | Parliament of Australia — Senate; House of Representatives (Federation Chamber proceedings should appear with House Hansard — verify) | `https://www.aph.gov.au/Parliamentary_Business/Hansard/Hanssen261110` (Senate), `https://www.aph.gov.au/Parliamentary_Business/Hansard/Hansreps_2011` (House) | The main page `https://www.aph.gov.au/Parliamentary_Business/Hansard` lists each sitting day with **PDF, XML and ParlInfo** links and "Previous sitting week" paging. ParlInfo serves one XML file per sitting day, e.g. `https://parlinfo.aph.gov.au/parlInfo/download/chamber/hansardr/2005-03-16/toc_unixml/3766-5.xml;fileType=text%2Fxml` (`hansardr` = House; the Senate dataset is probably `hansards` — verify). The Senate year page listed dates only up to 2025 when checked — confirm it is maintained before relying on it. | Proof first, Official later | CC BY-NC-ND 3.0 AU |
| NSW | Parliament of NSW — Legislative Assembly, Legislative Council | `https://www.parliament.nsw.gov.au/parliamentary-business/hansard/hansard-and-house-papers` (`filter-year`, `filter-month` query parameters) | **Public Hansard API** covering sitting dates, members, bills, daily transcripts in XML and PDF, a table of contents per day, and fragments, from Sept 1991. Docs: `https://www.parliament.nsw.gov.au/parliamentary-business/hansard/hansard-api` — the endpoint list was not in the page text we could read; inspect it. | Proof text about 3 hours after words are spoken, progressively; daily PDF about 3 hours after the last House rises; later replaced by a corrected copy | Parliament copyright and conditions of use; Data.NSW lists the API as CC BY |
| VIC | Parliament of Victoria — Legislative Assembly, Legislative Council | `https://www.parliament.vic.gov.au/parliamentary-activity/hansard/hansard-debate?page=1&pageSize=10` | Day pages at `/parliamentary-activity/hansard/hansard-details/HANSARD-974425065-{id}`; progressive HTML publishing (Dec 2018 on) and PDF records; listings are tagged Proof or Final. **Our automated test fetch was refused by bot detection.** The listing probably calls a JSON endpoint — inspect what the page requests, but do not bypass protection. | A member's speech within about 3 hours; full-day proof about 4 hours after the sitting ends; final about 5 working days later | Check |
| QLD | Queensland Parliament — Legislative Assembly (unicameral) | `https://www.parliament.qld.gov.au/Work-of-the-Assembly/Record-of-Proceedings` | Daily proof PDF: `https://documents.parliament.qld.gov.au/events/han/{YYYY}/{YYYY_MM_DD}_DAILY.pdf` (weekly `_WEEKLY.pdf` also exists). A preview of QLD's newer platform used `/Work-of-the-Assembly/Record-of-Proceedings/daily/lh/{YYYY-MM-DD}/pdf/download` — the same shape as SA's site, so check the live site for XML or extract endpoints. | Daily PDF stamped "(PROOF)"; find the final signal | Check |
| SA | Parliament of South Australia — House of Assembly (`lh`), Legislative Council (`uh`) | `https://hansardsearch.parliament.sa.gov.au/search/calendar` | **Structured XML.** Day table of contents: `https://hansardsearch.parliament.sa.gov.au/daily/{lh\|uh}/{YYYY-MM-DD}/download/toc`. Extracts: `/daily/{lh\|uh}/{YYYY-MM-DD}/extract/{n}/download`. XML carries `reviewStage`, `dateModified`, `proceeding`, `subject`, `talker` (name, house, electorate) and `startTime`. **The calendar page refused our automated test fetch.** | Use `reviewStage` and `dateModified` to detect proof → final | Copyright held by the Attorney-General of SA; extracts must be fair and accurate and must not be used for satire, ridicule or to misrepresent members |
| WA | Parliament of Western Australia — Legislative Assembly, Legislative Council | `https://www.parliament.wa.gov.au/hansard/hansard.nsf/NewAdvancedSearch` — **drop the `afd_azwaf_tok` parameter from the sponsor's original link; it is a one-off firewall session token** | Lotus Domino site. The search page has a "Daily Hansard" calendar (Council sits / Assembly sits / both) with a PDF per house per day. The token name suggests an Azure Front Door firewall that may challenge automated clients. | Draft published progressively during the day; complete draft daily about 3 hours after the house rises | Check |
| TAS | Parliament of Tasmania — House of Assembly, Legislative Council | `https://search.parliament.tas.gov.au/adv/hahansard` — **House of Assembly only.** The Legislative Council is a separate collection; start from `https://search.parliament.tas.gov.au/adv/advanced` | ISYS search engine with full-text query filtered by year. Result documents download as Original (.docx), Text, HTML5 or PDF. Coverage 1992 on. | Find the proof/final signal | Check |

**Phase 0 output for every chamber:** how to list sitting days; document URL pattern; format; how speakers are marked up; proof/final signal; robots.txt result; terms of use; rate limits; blockers; recommended connector approach; one saved real sitting-day fixture.

**If a source blocks automated access:** mark it `blocked`, keep going with the others, list it in PROGRESS.md open questions, and rely on manual import (§9.7) until access is arranged. Draft a short request ACAG can send to that Parliament's Hansard team asking for an allowlist or data feed, in `docs/access-requests.md`.

## 6. Architecture

```
 "Check for updates" button · CLI · optional schedule
                     │
                     ▼
            Scan orchestrator ──► Connectors (one per parliament) ──► Raw store data/raw/…
                     │                         │
                     │                         ▼
                     │          Parsers → normaliser → speeches (SQLite + FTS5)
                     │                         │
                     │          Pre-filter (lexicon + rules)
                     │                         │
                     │          LLM triage → LLM summary → items
                     │                         │
                     └─► scan_runs log         Period brief synthesis (cached)
                                               │
          FastAPI: auth · status · scans (SSE) · items · search · briefs · exports · imports
                                               │
          React + Fluent 2 SPA: Login · Brief · Themes · Explore · Coverage
```

**Repo layout:** `backend/` (`app/`, `connectors/`, `parsers/`, `pipeline/`, `api/`, `tests/`), `web/`, `config/`, `eval/`, `docs/`, `data/` (gitignored).

**Connector interface** (Python `Protocol`, one file per parliament in `backend/connectors/{code}.py`):

| Method | Returns | Rule |
|---|---|---|
| `list_sitting_days(start, end)` | sitting days with chamber and version hint | Must distinguish "no sitting" from "could not check" |
| `list_documents(day)` | document refs: URL, format, version hint, ETag/Last-Modified if known | |
| `fetch(ref)` | body or `unchanged` | Conditional GET; SHA-256 of body |
| `parse(raw)` | normalised speeches | Keep page numbers or anchors for citations |

Adding ACT or NT later should mean one new connector file plus one row in `config/sources.yaml`.

**Minimum API:**

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` |
| Status and scans | `GET /api/status`, `POST /api/scans`, `GET /api/scans/{id}`, `GET /api/scans/{id}/events` (SSE) |
| Content | `GET /api/items`, `GET /api/items/{id}`, `GET /api/search`, `GET /api/brief`, `GET /api/themes/matrix` |
| Exports and imports | `GET /api/export/brief.docx`, `GET /api/export/brief.pdf`, `GET /api/export/items.csv`, `POST /api/imports` |
| Health | `GET /api/health` (no auth) |

## 7. Data model

SQLite via SQLAlchemy and Alembic, written so a later move to Postgres is a config change.

| Table | Key columns | Notes |
|---|---|---|
| `sources` | `id` (e.g. `VIC-LA`), parliament, chamber, connector, enabled, status (`ok`/`no_sittings`/`blocked`/`error`), `last_checked_at`, `last_success_at`, `watermark_date`, notes | One row per chamber (13) |
| `sitting_days` | `source_id`, `sitting_date` (local date), `discovered_at`, version (`proof`/`final`/`unknown`), status | Unique on (`source_id`, `sitting_date`) |
| `documents` | id, `sitting_day_id`, url, format, version, etag, `last_modified`, `sha256`, `raw_path`, `fetched_at`, `superseded_by`, origin (`auto`/`manual`) | New row only when `sha256` changes |
| `speeches` | id, `document_id`, seq, `debate_title`, `proceeding_type`, `speaker_name`, `speaker_role`, party, electorate, `start_time`, page, `anchor_url`, text, `text_sha256` | FTS5 index on text, debate title and speaker |
| `analyses` | `speech_id`, `text_sha256`, stage (`triage`/`summary`), model, `prompt_version`, `output_json`, `input_tokens`, `output_tokens`, `cost_usd`, `created_at` | Unique on (`text_sha256`, stage, model, `prompt_version`) — the "never re-analyse" key |
| `items` | id, `speech_id`, category, significance, offices, themes, agencies, tone, headline, summary, `why_it_matters`, quote, `quote_verified`, confidence, `first_seen_run_id` | What the dashboard shows |
| `briefs` | office, `period_start`, `period_end`, `data_version`, `output_json`, `created_at` | Cached synthesis |
| `scan_runs` | id, trigger (`manual`/`scheduled`/`cli`), `started_at`, `finished_at`, status, `per_source_json`, tokens, `cost_usd`, `error_summary` | Audit trail; drives "last checked" |

Raw files live at `data/raw/{source_id}/{YYYY-MM-DD}/{sha256}.{ext}` and are never deleted by a scan.

## 8. Scan logic — how "no rescanning" works (SC1, SC2)

1. **Window.** Backfill runs from the same date two months ago to today (31 Aug to 31 Oct 2026 for a run on 31 Oct). Set by `BACKFILL_MONTHS`.
2. **Discover.** For each enabled source, list sitting days from `watermark_date + 1` to today, plus any day still marked `proof` within `PROOF_RECHECK_DAYS` (default 28).
3. **Fetch conditionally.** Send `If-None-Match` / `If-Modified-Since` where known. Hash the body. Same hash means `unchanged`; stop there.
4. **Parse only changed documents.** A final that replaces a proof becomes a new document version. Speeches are re-derived, and only speeches whose `text_sha256` changed go forward. Items keep their ids where the text is unchanged.
5. **Analyse only what is new.** Skip any speech whose (`text_sha256`, stage, model, `prompt_version`) already has an analysis. Bumping `PROMPT_VERSION` is the only deliberate way to re-analyse, and the UI shows the estimated cost and asks first.
6. **Advance the watermark** only after a day has been fetched, parsed and analysed without error.
7. **Log** every run in `scan_runs` with per-source counts: days checked, new, changed, unchanged, speeches analysed, items created, errors, tokens and cost.
8. **One scan at a time** (database lock). If a scan is running, anyone who opens the app sees its progress instead of a second button.
9. **Recess is not failure.** If the calendar shows no sittings, the status is `no_sittings` (shown grey, e.g. "Not sitting since Thu 1 Oct"), not an error.
10. **Retention.** Keep everything by default. The widest dashboard period is the stored window. `RETENTION_DAYS` is optional.

## 9. AI analysis

### 9.1 Pipeline

| Stage | What happens | Engine |
|---|---|---|
| A. Normalise | Split each day into speeches (one speaker turn under a debate heading). In Question Time, analyse the question and answer together. Chunk speeches over ~6k tokens with overlap. | Code |
| B. Pre-filter | Send a speech to the LLM if it hits the audit lexicon (always) or theme and risk terms above a threshold. Record why. Aim for 10% or fewer of speeches reaching the LLM. | Code with `config/lexicon.yaml` and `config/themes.yaml` |
| C. Triage | Relevant or not, category, significance, offices, themes, agencies, tone, confidence | `LLM_TRIAGE_MODEL` (default `claude-haiku-5-5`) |
| D. Summarise | Headline, summary, why it matters, verbatim quote — for relevant speeches with significance 2 or more | `LLM_SUMMARY_MODEL` (default `claude-sonnet-5-5`) |
| E. Brief | Per office and for "ACAG — all", per period: top 5 items, issues raised in several parliaments, mention counts and tone, coverage note | `LLM_SUMMARY_MODEL`, cached in `briefs` |

### 9.2 Lexicon and themes (seed — Phase 0 completes and verifies)

| List | Seed entries |
|---|---|
| Audit offices | Australian National Audit Office (ANAO); Audit Office of New South Wales; Victorian Auditor-General's Office (VAGO); Queensland Audit Office (QAO); Auditor-General's Department (SA); Office of the Auditor General Western Australia (OAG WA); Tasmanian Audit Office (TAO) |
| Generic audit terms | Auditor-General, Auditor General, audit report, performance audit, financial audit, Audit Act, audit recommendations |
| Committees | JCPAA (Cth), Public Accounts Committee (NSW), Public Accounts and Estimates Committee (Vic), Public Accounts Committee (WA), Public Accounts Committee (Tas) — add each parliament's equivalent (verify QLD and SA) |
| Integrity bodies | NACC (Cth), ICAC (NSW, SA), IBAC (Vic), CCC (QLD, WA), Integrity Commission (Tas), state Ombudsman offices |
| Risk terms | cost overrun, blowout, delay, procurement, tender, grant, probity, conflict of interest, consultants, contract variation, value for money, cyber, data breach, fraud, overspend, waste, service failure, workforce shortage |
| Themes | Health; Education and training; Transport and infrastructure; Housing and homelessness; Justice, police and corrections; Child protection and social services; Disability and NDIS; Local government; Environment, water and energy; Digital, data and cyber; Public finance and budget; Procurement and grants; Integrity and governance; Public sector workforce; Emergency management; First Nations outcomes |

### 9.3 Categories, significance and tone

| Category | Meaning |
|---|---|
| `AG_MENTION` | An Auditor-General, audit office or audit report is mentioned |
| `AUDIT_DEBATE` | An audit report is tabled, debated or used as evidence |
| `COMMITTEE` | Accountability committee activity tied to audit work |
| `MANDATE` | Bills or motions on an audit office's mandate, independence, powers or funding |
| `FOLLOW_UP` | Government response to, or progress on, audit recommendations |
| `RISK_SIGNAL` | A specific issue that could become an audit topic |
| `INTEGRITY` | Integrity-body findings or misconduct involving public money |

| Significance | Rule |
|---|---|
| 5 | Changes an office's mandate, powers, funding or independence; or a Premier, Prime Minister, Treasurer or Minister disputes or endorses an audit finding |
| 4 | An audit report is debated or cited in Question Time or a ministerial statement; a committee acts on an audit |
| 3 | A specific risk signal (named program or agency plus dollars, dates or numbers) in a sector audit offices cover |
| 2 | A passing reference to an audit office or a general accountability point |
| 1 | Background only — stored, hidden by default |

Tone toward the audit office: `supportive`, `critical`, `neutral` or `n/a`. Always show it as an icon plus a word, never colour alone.

### 9.4 Output contract

Use structured output (JSON schema or tool use). Merged view of triage and summary:

```json
{
  "relevant": true,
  "category": "AUDIT_DEBATE",
  "significance": 4,
  "offices": ["VAGO"],
  "themes": ["Health"],
  "agencies": ["Department of Health"],
  "tone": "critical",
  "headline": "12 words or fewer, e.g. 'Minister rejects audit finding on hospital wait times'",
  "summary": "60 words or fewer, plain English",
  "why_it_matters": "30 words or fewer, written for an audit office executive",
  "quote": "40 words or fewer, copied exactly from the speech",
  "confidence": 0.82
}
```

### 9.5 Guardrails

- Hansard text is untrusted input. Wrap it in delimiters and instruct the model to ignore any instructions inside it.
- **Quote check:** after normalising whitespace and quote marks, the quote must be an exact substring of the speech. Otherwise drop it and set `quote_verified = false`.
- **Number check:** every number in the headline and summary must appear in the speech. Otherwise regenerate once, then flag.
- Invalid JSON gets one retry, then the analysis is marked `failed` — shown on the Coverage page, never on the dashboard.
- Store model, prompt version, tokens and cost for every call.

### 9.6 Cost and data controls

- Pre-filter before any LLM call. Use the Message Batches API for the backfill. Prompt-cache the static system prompt and taxonomy.
- `LLM_MAX_SPEND_USD_PER_RUN` is a hard cap: stop cleanly and carry on next run.
- Only public Hansard text and the generic taxonomy go to the model. User settings and saved items never leave the server.
- Keep LLM access behind `LLMClient` (default: Anthropic API) so ACAG can switch to Claude on Amazon Bedrock, Google Cloud or Microsoft Foundry if it wants in-region processing.

### 9.7 Manual import (fallback for blocked sources)

Coverage page → "Import a sitting day": choose parliament, chamber and date, upload PDF, XML, DOCX or HTML. It runs through the same parse and analyse pipeline, is marked `manual`, and is de-duplicated by hash.

### 9.8 Evaluation

Build `eval/gold.jsonl` with about 60 speeches across all 7 parliaments, including about 25 negatives. Claude Code proposes labels; the product owner confirms them. `make eval` reports relevance precision and recall and category agreement. Targets: `AG_MENTION` recall 0.95 or higher; overall relevance precision 0.8 or higher. Write results to `docs/eval.md` and rerun whenever prompts change.

## 10. Dashboard

### 10.1 Principles

- **30-second rule:** the top story for your office is visible without scrolling or clicking.
- **Brief → item → source:** three levels, never more.
- Plain English and Australian spelling. No acronym without a tooltip.
- Every number is clickable and leads to the items behind it.
- Every AI summary is labelled "AI summary — check the source" and links to the Hansard page or anchor it came from.
- Show gaps honestly ("WA not checked — access blocked"). Never pad.
- Calm visual design: Fluent 2, generous whitespace, one consistent accent colour per parliament, light and dark themes.

### 10.2 First run

Two questions, stored in the browser and changeable from the header:
1. "Which office are you from?" — the 7 offices in §9.2 plus "ACAG — all offices".
2. "What do you want to see first?" — Brief, Themes or Explore.

### 10.3 Screens

| Screen | For | Contents |
|---|---|---|
| Login | Everyone | App name, username, password, Sign in. Nothing else. |
| Brief (home) | Executives | Update banner · "This fortnight in 30 seconds": 3–5 headline cards (headline, why it matters, parliament chip, date, tone, "Read in Hansard ↗") · 4 KPI tiles: mentions of your office, mentions of any Auditor-General, new risk signals, mandate items — each with change against the previous period · Australia tile map (7 tiles, shade = item count, ring where your office was mentioned) · "Same issue, several parliaments" · Download brief (Word or PDF) · Copy for email or Teams |
| Themes | Directors | Heatmap of themes × parliaments (click a cell for the filtered list) · theme cards with a trend sparkline and top items · risk signals ranked by significance |
| Explore | Managers | Full-text search over all stored Hansard (FTS5, not only AI items) plus filters: parliament, chamber, dates, category, theme, significance, tone, speaker, party · results with highlighted snippets · item drawer: summary, why it matters, verified quote, debate title, speaker and role, source link to the page or anchor, related items in other parliaments, "Add to brief", "Copy citation" · CSV export |
| Coverage | Everyone; admin actions | Per chamber: status, last checked, latest sitting day stored, proof/final counts, last error · scan history with tokens and cost · manual import · retry failed analyses |

Header on every page: office switcher, view tabs (Brief · Themes · Explore), period picker (default last 2 weeks, up to the full stored window), and a "New since your last visit" count.

### 10.4 Update flow (SC2)

1. On load, `GET /api/status` returns the last check time, status per source, and `update_recommended` (true if more than 24 hours since the last check, or a known sitting day is newer than a watermark).
2. Banner: "Hansard last checked Mon 26 Oct 2026 (5 days ago). Check for anything new since then?" with [Check now] and [Not now].
3. Progress panel: one row per parliament with live state over SSE — checking → n new days → analysing → done, or no sittings, or blocked.
4. Finish: "3 parliaments sat · 6 new sitting days · 11 new items · 2 mention your office" with [Show me]. New items carry a "New" badge.

### 10.5 Exports

- Brief to Word (.docx) and PDF, one page: period, coverage note, top items with source citations, mentions summary.
- "Copy for email or Teams": plain-text/markdown version of the brief.
- Explore results to CSV.

### 10.6 Quality bar

WCAG 2.2 AA (axe: no serious or critical findings); fully keyboard-usable with visible focus; screen-reader labels; respects reduced motion; works at 375 px; the Brief loads in 2 seconds or less with two months of data on a laptop.

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
| 0 · Source recon | Know exactly how to get each chamber | `docs/sources.md` complete for all 13 chambers (§5 output list) · one real sitting-day fixture per chamber in `tests/fixtures/`, or a documented blocker · lexicon verified · `docs/access-requests.md` drafted for any blocked source · **stop for product-owner review** |
| 1 · Skeleton and login | Running app shell | `backend/`, `web/`, Makefile, `.env.example`, Alembic baseline · login, logout and session per §11 · protected API returns 401 without a session · `make test` green |
| 2 · Connectors and store | Two-month backfill and incremental updates | Connectors for all non-blocked sources pass fixture tests · `make backfill` completes and logs a scan run · an immediate `make scan` shows 0 changed downloads and 0 LLM calls · proof → final test passes · `/api/status` correct |
| 3 · AI analysis | Items and briefs | Pre-filter, triage, summary and brief working · guardrails enforced by tests · `make eval` report in `docs/eval.md` · backfill and update costs reported |
| 4 · Dashboard | Brief, Themes, Explore, Coverage, update flow | Playwright journeys pass: (a) login → brief → open source; (b) check for updates → progress → summary → "New" badges; (c) search → filter → CSV export · axe clean · 375 px screenshots in `docs/screens/` |
| 5 · Hardening and handover | Ready for a pilot | Word/PDF export · manual import · README (setup, run, add a parliament) · RUNBOOK (failed scans, blocked sources, costs) · an independent review subagent checks the code against this spec, and every finding is fixed or logged |

## 13. Testing

- Unit tests never touch the network: connectors run against recorded fixtures.
- Parser golden files: fixture in, expected speeches JSON out.
- Sync tests: unchanged → no-op; a new day → only that day processed; proof → final with edits → only the changed speeches re-analysed.
- LLM tests use a fake `LLMClient`. One opt-in live smoke test (`make smoke-llm`).
- End-to-end: the Playwright journeys in Phase 4.

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
FETCH_MIN_INTERVAL_SECONDS=2
FETCH_USER_AGENT=ACAG-HansardWatch/0.1 (+mailto:CONTACT_EMAIL)
SCAN_SCHEDULE_CRON=             # blank = manual updates only
DISPLAY_TIMEZONE=Australia/Melbourne
DATA_DIR=./data
```

Config files: `config/sources.yaml` (13 chambers, enable/disable), `config/lexicon.yaml`, `config/themes.yaml`, `config/offices.yaml` (office → jurisdiction, display name, colour).

## 15. Open questions for the product owner

1. Add the ACT and NT Legislative Assemblies (both ACAG members)? New Zealand?
2. Add committee Hansard (Senate Estimates, PAC/PAEC/JCPAA hearings) in v2?
3. Contact email for the crawler's User-Agent and for access requests to parliaments.
4. Which LLM route will ACAG approve: Anthropic API direct, or Claude through a cloud provider?
5. Hosting and identity for the pilot: whose tenant, and the Entra ID plan across offices.
6. Who confirms the evaluation labels?
