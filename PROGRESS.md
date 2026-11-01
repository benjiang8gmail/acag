# Progress

## 1 Nov 2026: Tasmania — not an outage; downloads import under their own names

### Done

- **Corrected the record on Tasmania.** The product owner can use `search.parliament.tas.gov.au` in a browser right now (choose 2026, open a day, download the Word document), while every search path, including the `/search/search/` entry point, still gives this scanner HTTP 200 with 0 bytes (checked 01:06 UTC). So it is not an outage, as recorded last night; the site gives automated clients from here empty pages. The scanner is not disguised as a browser to get past that.
- **Made the working route easy: Word files downloaded by hand.** These are exactly what the Tasmanian reader was built and tested on.
  - `make import-folder` now takes files under the names the Parliament's search gives its downloads ("HA Tuesday 1 September 2026.docx", "LC …"), anywhere under the folder, so nothing needs renaming. The house and date come from the name, and a weekday that does not match its date is rejected.
  - A tracked drop folder, `imports/`, with a README covering how to add files without git (GitHub → Add file → Upload files).
  - `make import-folder` reads `imports/` by default (`DIR=` still works).
- **Dashboard:** Tasmania's status is now "empty pages" ("the site answers the scanner with empty pages although it works in a browser"), its Needs column reads "Word files downloaded by hand", and the "working route" count no longer counts it (6 → 5). Nothing else changed: the data files are byte-identical to what was published.

### Evidence

- `make test`: 163 backend tests pass. New: the **real** Tasmanian Word transcripts (House of Assembly and Council, 10 Sep 2026), saved under the site's own download names, one loose and one in a subfolder, import end to end through the existing reader (over 50 speeches each, draft flag read, party and side filled from the member list); a wrong weekday is rejected; downloading the same files again changes nothing.

### Next

- Tasmania's September sitting days (House of Assembly 1–3, 8–10; Council 1–3, 8–11), downloaded as Word files into `imports/`, then `make import-folder` and a dashboard refresh.

---

## 1 Nov 2026: Victorian readers via Cowork — stopped after the site cut that route off

### Done

- **Tried to read the ten Victorian sitting days with Cowork sessions**, the environment where WebFetch had been admitted, with a pilot first. Each reader was to read the whole day in parts, list every Auditor-General mention, then re-read to confirm each quote, keeping only confirmed ones.
- **Both pilots failed with `client_error`, nothing retrieved** — first with an older link, then with the link web search shows as current, so it is not a stale-link problem. The readers reported this plainly instead of inventing output.
- **The user's own Cowork audit session was refused at the same moment:** 13 consecutive failures from 00:50 to 00:53 UTC across nine documents, after reading the same PDFs successfully until 00:29. The Parliament's site stopped serving that route at about 00:50 UTC, most likely a rate limit after many large PDFs were paged through in parallel.
- **Stopped there:** the other nine readers were not started, and nothing was retried in a loop. The dashboard is unchanged.
- **Retried once, gently, at 00:56 UTC** (one reader, Council 9 Sep, no parallel calls): its search found the current link and WebFetch was still refused with `client_error`. Seven minutes on, the route was still closed, so readers 2–10 were not started.
- `tools/merge_vic.py` (scratchpad) is ready to turn readers' results into the dashboard's Victorian data — party and side from `config/members/VIC.yaml`, only re-checked quotes kept — if the route comes back.

### Next

- Victoria still needs its PDFs in hand: downloaded in a browser and imported, or read later at a gentle pace (one reader, one day at a time) if the Cowork route recovers.

---

## 1 Nov 2026: Victoria on the dashboard — what is exact without the transcripts

### Done

- **Added a separate Victoria card to the dashboard** with the only Victorian data that is exact without the transcripts:
  - **Ten confirmed sitting days** (Assembly 8, 9, 10, 23, 24 Sep; Council 9, 10, 22, 23, 24 Sep), each from its daily Hansard's own title in public web search, each linking to the official PDF. The Council on 9 Sep was newly confirmed (`974425065-36927`) and added to `config/vic_hansard.yaml`.
  - **The one Hansard item whose own title names the Victorian Auditor-General's Office** (Council, 9 Sep 2026, `HANSARD-974425065-36907`).
  - Both follow the date filter; nothing in the card is counted in the parsed totals, which stay 23,603 speeches across 5 parliaments.
- **Left out on purpose:** debates on VAGO reports under other titles ("Road maintenance", Council 23 Sep; "Suburban Rail Loop", Council 9 Sep). Only the search tool's model-written summaries connect them to the Auditor-General, and its summaries are not used as data. They appear once the transcripts can be read.
- **Not done, and why:** Victorian speeches. In this environment the site answers WebFetch with 403, and where WebFetch works it returns a model's reading, not the text (D20).

### Evidence

- The page was run against the real data before publishing: both Victorian tables align headers and cells (10 rows; 1 row), every row links to `www.parliament.vic.gov.au`, choosing October shows the "no Victorian sitting days" note, and the rest of the page is unchanged (72 / 23,603 / 128; 6 of 9 routed).

---

## 1 Nov 2026: Victoria via the Cowork session's method — search works here, fetch does not

### Done

- **Read the Cowork "Victorian Hansard audit scan" session's transcript to see its method exactly** (it is still running). Its subagents find daily-PDF URLs with WebSearch limited to `parliament.vic.gov.au`, then read each PDF with WebFetch, paging long ones with `offset` and asking for speakers, printed pages and short verbatim fragments.
  - **There, WebFetch reaches the site.** Its answer for the Assembly on 9 Sep 2026 names Katie Hall (Footscray), Tim McCurdy (Ovens Valley), Matt Fregon (Ashwood) and others with printed pages 3777–3783 — with page ranges marked "inferred" and the text "cut off mid-word".
  - **Here, WebFetch fails:** `www.parliament.vic.gov.au` is outside this environment's allowed network domains. The sessions run in different environments; that is the difference, not the site.
- **Ran the search half here.** It confirms, by result title, nine final-version Victorian sitting days in the window — Assembly 8, 9, 10, 23, 24 Sep; Council 10, 22, 23, 24 Sep — now listed in `config/vic_hansard.yaml` (was three). Assembly 22 Sep and Council 8–9 Sep were not surfaced and may still exist.
- **Found that the 60th Parliament rose on 24 September 2026** (valedictory statements; election 28 Nov). There are no October Victorian sittings to collect.

- **Then tested with the environment's network access set to Full.** This session kept its starting policy (WebFetch still "outside the allowed domains"), so a one-step test session was started: it reached the host, and **the site answered HTTP 403 Forbidden**. Here WebFetch fetches from the session's own cloud network, which the Cloudflare check refuses, exactly as it refuses the scanner. The Cowork session's WebFetch runs on infrastructure the site admits, so its method does not carry over to this environment.

### Decisions

- **D20. A fetch-and-summarise tool can verify Hansard but not supply it.** WebFetch answers questions about a PDF through a model with short quotes; it never yields the file. Its output can confirm sitting days, status and page ranges, or spot-check a mention, but the text stored behind a verbatim quote comes from the PDF bytes.

### Next

- If `www.parliament.vic.gov.au` is added to this environment's allowed domains, WebFetch can verify all nine days and fill the three gaps. Victorian speeches on the dashboard still need the PDFs themselves: downloaded by hand and imported, or fetched from a network the site serves.

---

## 1 Nov 2026: refresh scan — nothing new published, and a re-read bug it exposed

### Done

- **Ran a real scan (run 3, 00:05–00:10 UTC) with the current connectors against the live store**, then rebuilt the dashboard from it.
  - **32 transcripts rechecked** against the parliaments' own sites — every proof within the 28-day recheck window. All unchanged: 10 answered 304 Not Modified (ACT, QLD), 21 were downloaded and hashed the same (CTH, NSW ignore conditional requests).
  - **0 new or corrected speeches.** The ACT's 28–29 Oct are still unpublished (held pending). Tasmania's site still returns empty pages, so both chambers stay `error` with their watermark held.
  - **All four dashboard datasets came out byte-identical**, so the dashboard's figures were already current. To make the refresh visible rather than silent, the dashboard now shows a **"last checked" line** from a new `scan` dataset: when, transcripts rechecked, new speeches, days awaiting publication, chambers unreadable.
- **Fixed: NT re-read all 83 pages on every scan.** The refresh showed NT's day as "changed" with zero new speeches. Territory Stories embeds volatile fields in every record — six reshuffled "related records", relevance scores and the query time — so the raw hash changed on each request. Three real responses for the same unchanged day had three different hashes.
  - Connectors may now define `fingerprint(raw) -> bytes`; `_identity()` hashes that instead of the raw bytes, for the scanner and manual import alike. NT's fingerprint is the record's own fields (title, `modified`, page list, file) without `related` and `resume`.
  - All three real responses now share one fingerprint. A day re-checks in **1 request instead of 84**.
  - The stored NT document still carries its old raw hash, so the next scan re-reads it once under the new rule; after that it is stable.

### Evidence

- `make test`: 162 backend tests pass. New: two **real** Territory Stories responses for the unchanged 22 Oct record (31 Oct and 1 Nov, now both fixtures) share a fingerprint despite different raw hashes; the fingerprint moves when the title (draft → final), `modified` or the page list changes; and in sync, a response whose only change is volatile noise counts as unchanged and is not re-parsed, while a content change still makes a new version.

---

## 1 Nov 2026: the SA connector (listing complete) — and Tasmania was already built

### Done

- **`backend/connectors/sa.py`** — South Australia, both houses, on URL shapes **confirmed in the wild** by public search rather than inferred: the day table of contents `/daily/{lh|uh}/{YYYY-MM-DD}/download/toc` and each subject extract `/daily/{lh|uh}/{YYYY-MM-DD}/extract/{n}/download`. Confirming those first is what made SA buildable; yesterday only the per-subject URL (which carries an item id) was known.
  - **Sitting days** by HEAD-probing each weekday's day TOC per house, so neither the WAF-protected calendar nor the OpenAPI spec is needed to find days.
  - **Documents:** the day TOC as XML, keyed `toc:{source}:{date}`; its subjects are fetched as parts, as the NSW topic fragments are.
  - **Recent days stay open** (`settled_through`, 3 days): SA publishes "after 4pm on the day following the sitting", so a fresh 404 is not "no sitting".
  - **A refusal is never an empty calendar:** Azure WAF 403 → `Blocked`, anything else unexpected → `CouldNotCheck`.
  - **The reader is not written, and `citation_url` is deliberately left unset** rather than guessed: the TOC's element names and the reader-facing day URL are both still unknown (D6).
- **Tasmania was not rebuilt, because it already exists** and is the most complete of the nine in some ways: `backend/connectors/tas.py` (261 lines) is registered, both chambers are enabled, and 12 tests pass against **real .docx fixtures** — sections, topics, Question Time with supplementaries, Council headers, times, draft flag and speaker sides.
  - Tasmania's gap is not a missing connector but its site: the ISYS search application has been returning empty pages since 31 Oct. Nothing in the code would change that, and the empty-page fix already holds the watermark and retries.
  - The one new thing that *could* be built for Tasmania — a fallback to the Parliament's static daily PDFs — is blocked on exactly what Victoria and WA are blocked on: Cloudflare refuses the host here, and no real PDF exists to write the reader against. Building it on a guess would be the same mistake as writing a parser blind.

### Evidence

- `make test`: 157 backend tests pass, including 6 new for SA with no fixture and no network: URL derivation for both houses (asserted against the two search-confirmed examples), per-house weekday probing (10 HEAD probes over a Sat–Fri week, nothing downloaded), a house that did not sit, the settle window, WAF 403 → `Blocked` and 500 → `CouldNotCheck`, and the reader's refusal with `citation_url` unset.

### Where the nine stand

| | Connector | What it needs |
|---|---|---|
| CTH, NSW, QLD, ACT, NT | complete | nothing — scanning now |
| TAS | **complete, with real fixtures** | its own site to come back |
| WA | listing complete | one real daily PDF |
| SA | listing complete | one real day TOC |
| VIC | listing complete (staff-copied links) | one real daily PDF |

### Next

- Three parliaments now wait on exactly one real file each. Any of them can be finished in an afternoon once that file exists, by `make import` or by a scan from a network the site serves.

---

## 1 Nov 2026: the WA connector (listing complete; only the PDF reader is left)

### Done

- **`backend/connectors/wa.py`** — Western Australia, both houses, built on the date-predictable scheme confirmed yesterday. It needs no listing page, no staff-kept links and no search discovery, so unlike Victoria nothing about it depends on a human copying URLs.
  - **Sitting days** by HEAD-probing each weekday's dated PDF for each house (200 = sat, 404 = no sitting), exactly Queensland's pattern. Weekends are not probed.
  - **Documents:** `/hansard/daily/{lh|uh}/{YYYY-MM-DD}/pdf/download`, keyed `pdf:{source}:{date}`; `lh` is the Assembly, `uh` the Council.
  - **Recent days stay open** (`settled_through`, 3 days), so a day whose PDF is not out yet cannot be read as "no sitting" and cannot advance the watermark.
  - **A refusal is never an empty calendar:** the Azure WAF 403 reaches sync as `Blocked`, any other unexpected status as `CouldNotCheck`.
  - **The PDF reader is the only piece left.** It is written against the first real WA daily PDF (D6: no stand-in fixtures); until then `parse` says so, the connector stays out of `registry()`, and `make import` for WA reports the same.
- Recorded in `docs/sources.md` §WA.

### Evidence

- `make test`: 151 backend tests pass, including 6 new for WA, with no fixture and no network:
  - every URL derives from the date alone, for both houses;
  - weekday probing finds the right days per house (10 HEAD probes over a Sat–Fri week, no weekend, nothing downloaded);
  - a house that did not sit yields no document;
  - recent days stay open;
  - **a WAF 403 raises `Blocked` and a 500 raises `CouldNotCheck`** — neither is silently an empty calendar;
  - the reader refuses clearly and the connector is not registered.

### Next

- One real WA daily Hansard PDF (any 2026 sitting day, either house) finishes Western Australia: download it in a browser and `make import`, or run `make scan` from a network the site serves, where it will then list and fetch every day by itself.

---

## 1 Nov 2026: SA and WA checked the same way — both Azure WAF, but WA is the easiest to finish

### Done

- **Applied the same method (read the body, try every hostname, then search for other routes) to South Australia and Western Australia.** Both are genuinely gated, and the evidence is now exact rather than inferred.
- **South Australia — only the document subdomain is walled.**
  - `www.parliament.sa.gov.au` **is fully reachable from here**: HTTP 200, 51,250 bytes, Microsoft-IIS/10.0, `robots.txt` a 404 (so no rules). The bare host 301s to it via an Azure Application Gateway.
  - It holds no Hansard, though: of its 111 links, every Hansard one points at `hansardsearch.parliament.sa.gov.au`. The page carries only the description, the publishing time and the terms.
  - `hansardsearch.parliament.sa.gov.au` answers **403 with a page titled literally `Azure WAF`** — `robots.txt`, `/docs/api` and a real daily URL alike. The challenge carries no script, so there is nothing a polite client can satisfy.
  - Daily scheme confirmed in the wild: `/daily/{lh|uh}/{YYYY-MM-DD}/{n}`.
- **Western Australia — the whole site is walled, but its scheme is the cleanest of the three.**
  - `www.parliament.wa.gov.au` answers **403 titled `Azure WAF`** on every path: `robots.txt`, the old `hansard.nsf` search, and the full-day PDF endpoint for both houses. The bare host does not resolve.
  - The spec's `afd_azwaf_tok` hint is now **confirmed, not a guess**.
  - **The full-day PDF endpoint exists and is completely date-predictable:** `/hansard/daily/{lh|uh}/{YYYY-MM-DD}/pdf/download`, no opaque id anywhere, with public search returning those URLs and their sitting dates.
  - So WA needs **no listing page, no staff-kept links and no search discovery** — it is Queensland's pattern exactly. Once access exists, only the PDF reader remains.
- **Added a side-by-side table of the three blocked states** to `docs/sources.md`, and replaced the guessed `live_check` and `risk` lines in `config/sources.yaml` for all four SA/WA rows with the confirmed evidence.

### Evidence

- Probe set, response sizes and the two challenge-page titles in `docs/sources.md` §SA and §WA.
- `make test`: 145 backend tests pass (unchanged; this entry is findings and documentation, no code).

### Where the nine stand

- **Live (6):** CTH, NSW, QLD, ACT, NT, and TAS once its own search application is back.
- **Blocked (3):** VIC (Cloudflare), SA and WA (Azure WAF). All three are reachable by a person in a browser, so `make import` works today, and a scan from a network the sites serve would work for all three — for WA with no listing step at all.

### Next

- If one of the three is to be finished first, make it **WA**: its URL scheme needs no discovery, so the only work is the PDF reader, against the first real file (D6).

---

## 1 Nov 2026: Tasmania diagnosed — an outage, not a block — and a second document route found

### Done

- **Applied the Victoria method to Tasmania: inspect the response, then search for other routes.** The two states fail for opposite reasons.
- **`search.parliament.tas.gov.au` is suffering an outage of its search application.** With our own user-agent: `/qsl/searchlinks` (24,849 bytes) and the host root serve real HTML and `robots.txt` returns a 404 page, so the web server is up; but every `/search/quicksearch/{year}/…` path returns **HTTP 200 with 0 bytes**, for 2024, 2025 and 2026 and for every sibling collection. This morning's `isysquery` .docx link is empty too, so the document store is served by the query engine. A session cookie and a browser-style `Accept` header change nothing, and there is no public maintenance notice.
  - **No code change needed:** this morning's fix already treats an empty page as "could not check", holds the watermark and retries next scan. Tasmania resumes by itself when the site does.
- **Found a second, independent route to Tasmanian daily Hansard, by search alone:** the Parliament publishes each sitting day as a static PDF at `parliament.tas.gov.au/__data/assets/pdf_file/{nnnn}/{nnnnnn}/{HA|LC}-{Weekday}-{D}-{Month}-{YYYY}[-Draft].pdf`, the same naming as the .docx, with `-Draft` for a proof.
  - **Blocked here:** both `www.` and the bare host answer every path, that static PDF included, with 403 `cf-mitigated: challenge` — exactly like Victoria.
  - The two numeric segments are Squiz asset ids, not derivable from the date, so links must come from the index page or search.
- **Closed the gap that discovery exposed:** a hand-downloaded Tasmanian *PDF* would have crashed inside the .docx unzipper. `TASConnector.parse` now refuses any non-Word file with a message naming the PDF route and why its reader is still to be written.

### Evidence

- `make test`: 145 backend tests pass; Tasmania 12, including the new refusal test (a PDF, and a file named .docx that is not one, while the real .docx fixture still parses).
- Response sizes, headers and the probe set in `docs/sources.md` §TAS.

### Decisions

- **D19. Distinguish "blocked" from "broken" in the record.** Both leave a source empty, but only one is a policy question: a block is reported with its evidence and left alone, while an outage is retried on its own. Victoria is blocked; Tasmania is broken.

### Next

- Tasmania: re-run `make scan` when the search host serves again — nothing else is needed.
- (1 Nov, 01:01 UTC) Still down: the search host returns empty pages, the main site challenges this environment, and a Cowork reader was refused on its first request (the sitting calendar). No Tasmanian Hansard could be added to the dashboard. If the outage lasts, its daily PDFs can be imported by hand like Victoria's, once a real one exists to write the reader against.

---

## 1 Nov 2026: Victoria, every route tested to the point of evidence

### Done

- **Re-tested the suggestion that `www.parliament.vic.gov.au` is crawlable while only the search host is blocked.** It is not, from here. Inspecting the response rather than the status code settles it: every path answers HTTP 403 with `cf-mitigated: challenge`, `server: cloudflare` and the "Just a moment…" interstitial — `robots.txt`, the Browse Hansard listing, a per-speech `hansard-details` page, **and the static `globalassets` daily PDF**. `cf-ray` ends `-IAD`: this container egresses from a US datacentre.
- **`WebFetch` cannot resolve the host:** `parliament.vic.gov.au` is outside this session's allowed network domains. Adding it under the environment's Network access would let that route be tested.
- **Public web search is the one route that returned real Victorian data,** and it needs no request to the site. `site:parliament.vic.gov.au` queries give the daily PDF URLs with house, date and proof/final status.
  - `config/vic_hansard.yaml` now lists three verified sitting days: Council 23 Sep 2026 (`974425065-37180`), Assembly and Council 24 Sep 2026 (`2145855009-37599`, `974425065-37279`), all final.
  - The links are unverified (not fetched) and the first path segment is a rotating cache-buster that differs between proof and final, so one may 404 and need re-copying.
- **Recorded that search is for discovery only, never ingestion.** It returns snippets, and fetch-and-summarise tools restate figures (a report of "$138 billion" for a $136.8m item) and truncate long sittings. Verbatim quotes with page numbers must come from the PDF bytes.

### Evidence

- `make test`: 144 backend tests pass (Victoria's 6 unchanged; the committed day list is validated by one of them).
- Response headers and challenge body in `docs/sources.md` §VIC and `docs/recon/vic-recheck-2026-10-31.jsonl`.

### Decisions

- **D18. A challenge page is a closed door, whatever the path.** Static assets on a challenged host are not a side entrance; the PDF is served the same interstitial as the HTML, and solving it is the thing we do not do. Search indexes and official mirrors stay allowed because they serve us their own copy.

### Next

- Unchanged and unblocked by all of the above: one real daily PDF, by `make import` or a scan from a network the site serves. The reader is the only missing piece.

---

## 1 Nov 2026: Victoria, as far as it can go without a file; manual import for blocked sites

### Done

- **Victoria re-checked (31 Oct 2026, 22:15 UTC), politely, from the build network.** Log: `docs/recon/vic-recheck-2026-10-31.jsonl`.
  - `www.parliament.vic.gov.au` (listing and PDFs): still HTTP 403 from Cloudflare, even for robots.txt.
  - `hansard.parliament.vic.gov.au`: answers, but it is the Hansard search engine only; its robots.txt disallows the search and result paths. Its help page points readers to the PDFs on the main site.
  - Web archives, for a development copy only: the National Library's web archive runs its own bot check; the Internet Archive and Common Crawl are unreachable from here. Nothing was retried or worked around.
  - So there is no automated route from this network and no real Victorian PDF to build the reader on.
- **Manual import (spec §9.11), the fallback for blocked sites:** `make import SRC=VIC-LA DATE=2026-09-24 FILE=/full/path.pdf [URL=…]` and `make import-folder DIR=…` (files as `VIC-LA/2026-09-24.pdf`).
  - Imports run through the same pipeline as fetched documents (`_store_document`, shared with the scanner), are marked `origin=manual`, logged as a `manual` scan run, and de-duplicated by hash.
  - They work for disabled (blocked) sources.
  - **Hand-over:** when the scanner later reaches the site, the same file counts as unchanged and a corrected final supersedes the imported proof; nothing is duplicated.
  - A manual import never touches the network.
- **`backend/connectors/vic.py`:** sitting days from a staff-kept list, `config/vic_hansard.yaml` (one line per chamber and day with the PDF link copied from Browse Hansard; only `https` PDF links on the Parliament's own host are accepted), as for the NT. From a network the site accepts, `make scan` fetches those PDFs politely; from here the source stays blocked.
  - The PDF reader is written against the first real daily PDF (D6). Until then the connector is not registered, and `make import` for `VIC-LA`/`VIC-LC` says so.
- **`config/members/VIC.yaml`** (secondary, Wikipedia): Assembly 87 (one seat vacant), Council 40. `build_members.py` now rebuilds only the parliaments whose source files are present, strips "Hon" and birth years from names, and knows the Liberal Democrats → Libertarian rename and the DLP.
- README and `docs/sources.md` §VIC updated; `config/sources.yaml` VIC rows carry the re-check.

### Evidence

- `make test`: 144 backend tests pass. New:
  - **manual import:** new → unchanged (same bytes) → changed (corrected final, only the changed speech counted), raw copy kept under `DATA_DIR/raw`, no network calls;
  - **hand-over** from a manual import to the scanner for a source that was disabled at import time: same file unchanged, corrected final supersedes;
  - unknown source, no connector, wrong file type rejected before anything is recorded; folder layout parsed, undated files skipped;
  - **Victoria:** listed days become sitting days and PDF documents with version hints; links off the Parliament's host, non-https links and non-PDFs are rejected; the committed list is valid; the reader says it needs a real PDF; the connector is not registered.

### Decisions

- **D16. Archive copies are not a feed.** A copy of a blocked parliament's Hansard from a web archive could at most serve as a one-off development fixture, and only with the source named; the scanner itself reads the Parliament's own site or files a person downloaded. (Moot for now: no archive was reachable.)
- **D17. Staff lists for blocked parliaments.** Where a site blocks the scanner but a person on an accepted network can see the links, the days and links go in a config list (NT: `config/nt_hansard.yaml`; VIC: `config/vic_hansard.yaml`), and the fetch still goes through the polite fetcher.

### Next

- Victoria needs one real daily Hansard PDF (any 2026 sitting day, either house), downloaded in a browser, to write and test the reader. Then: import the September–October days, register the connector, enable the sources, refresh the dashboard.
- Or: a polite test of `www.parliament.vic.gov.au` from the pilot's Australian network (Remote Control). If it serves a plain client there, list the days in `config/vic_hansard.yaml` and run `make scan` from that network.
- Send access request B (permission and a lasting route) regardless.

---

## 1 Nov 2026: first real backfill, a live-data dashboard, and two fixes it found

### Done

- **First real two-month backfill** (`make backfill`, run from the cloud container into a scratch data folder, not committed):
  - 7 chambers in 5 parliaments, with no errors;
  - 72 sitting-day documents and 23,603 speeches;
  - by parliament: CTH 28 days / 7,762 speeches, NSW 24 / 9,789, QLD 9 / 3,234, ACT 10 / 2,550, NT 1 / 268;
  - ACT 28–29 Oct are pending (not yet published).
  - NSW fell back to topic-by-topic fragments on 3 days, where the day PDF matched fewer than 90% of headings: LA 20 Oct, LC 13 Oct and one more LC day.
  - QLD 17 Sep notes that 85 of 108 contents headings matched.
- **Fix: `#page=` links for ACT and Queensland** (71ad4a1). Both number Hansard pages through the year, so the links sent readers to page 3587 of a 107-page PDF.
  - The shared reader now takes a printed-to-file page map. Speeches keep the printed page for display.
  - The stored ACT and QLD speeches were re-anchored from their saved PDFs.
- **Fix: an empty answer from Tasmania is "could not check", not "no sittings".** At 15:45 UTC on 31 Oct, search.parliament.tas.gov.au answered the sitting calendar and the date search with HTTP 200 and no body, hours after serving the same pages.
  - The connector read that as a recess and moved the watermark to today, past real sitting days.
  - Now an empty page, or a calendar with no dates, raises `CouldNotCheck`; sync keeps the watermark and marks the source `error`.
  - Next year's calendar not being up yet (404) still counts as no sittings for that year.
  - The site was not retried or worked around. TAS is retried on the next scan.
- **Live-data dashboard** (private claude.ai page: https://claude.ai/artifact/P9EoKqpTwpDHxewhGHdccv), built from a snapshot of that store:
  - per-parliament status and route;
  - speeches per sitting day;
  - speaking turns by side;
  - 128 speeches mentioning an Auditor-General or audit office (a plain text match), each with excerpt and source link.

### Evidence

- `make test`: 134 backend tests pass. New tests:
  - ACT and QLD anchors point at the file page (printed 2751 is page 4);
  - Tasmania: an empty calendar or empty search raises `CouldNotCheck`, a calendar with no dates raises `CouldNotCheck`, and a 404 for next year's calendar is not an error.
- `scan_runs` row 1: status done, per-source counts as above, `llm_calls` 0.

### Open questions

- Tasmania: is the empty answer an outage or a block on this network? Check again from the pilot's Australian network before treating it as a blocker.

---

## 1 Nov 2026: Tasmania via the Parliament's own document search (6 parliaments live)

### Done

- **`backend/connectors/tas.py`:** House of Assembly and Legislative Council, from `search.parliament.tas.gov.au` (no robots.txt rules), because the main site blocks scripts.
  - **Listing:** the year's sitting calendar, then one search per sitting date, which gives that day's Word transcript for each chamber.
  - **Indexing lag:** dates not yet indexed are held as pending; after 30 days they count as no sitting.
  - **Text:** read straight from the .docx: Word heading styles; bold-name turns; Council headers with electorate, role and "(by leave)".
  - **Question Time:** questions to named ministers, answers and supplementaries; points of order kept separate.
  - **Other turns:** interjections, the presiding officer, procedural lines and times.
  - TAS-HA and TAS-LC are enabled.
- **`config/members/TAS.yaml`** (House of Assembly 35, Council 15; secondary) added to `make members`.
- **Side rules:** "Leader for the Government" (Tasmanian Council) counts as government.

### Evidence

- `make test`: 130 backend tests pass, including 7 for Tasmania:
  - the calendar, the date search, and pending (not-yet-indexed) days;
  - old unindexed days given up;
  - draft flag, sections, topics and times;
  - **Question Time: question, answer, point of order, answer, interjection, supplementary, answer**;
  - Council headers with electorate, role and "(by leave)";
  - no turn headers left in text;
  - sides for 99%+ of turns, with Treasurer government, Leader of the Opposition opposition, and Council government leader government.

### Where the six previously blocked parliaments stand

- **Live:** CTH (OpenAustralia mirror), NT (Territory Stories text; days listed by staff), TAS (the Parliament's search).
- **No legitimate route from this environment:** VIC, SA, WA. The options are:
  - run the scanner from an Australian network (Remote Control from the product owner's computer);
  - the access requests;
  - assisted manual import.

---

## 1 Nov 2026: NT Hansard via Territory Stories text pages (5 parliaments live)

### Done

- **`backend/connectors/nt.py`:** reads only the Territory Stories endpoints that its robots.txt allows (`/api/full_record`, `/api/content`), never the PDFs.
  - **Sitting days:** listed in `config/nt_hansard.yaml`; staff add each new day's handle.
  - **Pages:** text is read page by page, and the running header is stripped wherever it falls.
  - **Question Time:** question, then an answer by the office asked, with each topic as a heading.
  - **Speakers:** ministers by portfolio, members by electorate, "(Opposition Leader)" as a role; presiding officer and interjections as their own turns.
  - NT-LA is enabled.
- **`config/members/NT.yaml`** (25 members, secondary source) added to `make members`.
- **Side rules:** "Opposition Leader" means opposition and "Chief Minister" means government. "A point of order, …" in Question Time is a statement, not a question.

### Evidence

- `make test`: 123 backend tests pass, including 6 for NT:
  - the config list;
  - **the connector reads the record and all 83 pages through allowed endpoints and never requests a PDF**;
  - Question Time, with answers by office;
  - portfolios, the chair and interjections;
  - no page headers in the text;
  - sides: Chief Minister government, Leader of the Opposition opposition, 95%+ of turns known.

### Where the six previously blocked parliaments stand

| Parliament | Route | Status |
|---|---|---|
| CTH | OpenAustralia's public mirror of APH's XML | **live** |
| NT | Territory Stories' allowed text endpoint; days listed by staff | **live** (one line per sitting day) |
| TAS | `search.parliament.tas.gov.au` answers (no robots.txt rules); search form only | to explore |
| VIC | `hansard.parliament.vic.gov.au` disallows `/search/` and `/isysquery/` | no route from here |
| SA | hansardsearch is behind an Azure WAF; the legacy host doesn't resolve | no route from here |
| WA | Azure WAF; the bare domain doesn't resolve | no route from here |

For VIC, SA and WA the legitimate options are:
- run the scanner from an Australian network (the product owner's computer via Remote Control, or an ACAG or VAGO network);
- the access requests;
- assisted manual import.

### Next

- Tasmania via the search site, if its results can be listed by date politely.

---

## 1 Nov 2026: federal Hansard via the OpenAustralia mirror (4 parliaments live)

### Done

- **`backend/connectors/cth.py`:** Senate and House (including the Federation Chamber).
  - It reads **APH's own Hansard XML as republished by OpenAustralia** (`data.openaustralia.org.au/origxml`), because aph.gov.au blocks scripts.
  - **Listing:** the mirror's directory listings; 0-byte files mean no sitting.
  - **Speaker turns:**
    - questions, answers and speeches;
    - interjections and the chair, split out of the speech text by their name spans and given their speakers' details;
    - a speaker resuming after an interruption rejoins their own turn.
  - **Recorded per speech:** party, electorate, ministerial role, time and page, all printed in the XML. `<proof>` gives the version.
  - CTH-SEN and CTH-HOR are enabled, with the route recorded in `config/sources.yaml`.
- **Speaker side:** presiding officers' turns are now `unknown` in every parliament (the federal XML prints the Speaker's party).
  - APH party codes are mapped (LP→LIB, NATS→NAT, AG→GRN, ON→PHON).
- **Fetchers:** challenge detection now looks at what a challenge page shows (its title, or a short page with strong markers). Before, a passive Cloudflare script on a normal page (OpenAustralia's directory listing) was flagged as a challenge.
- **Other routes tested** (docs/sources.md):
  - **NT:** Territory Stories' allowed `/api/content` endpoint returns page text. Connector next.
  - **Tasmania:** `search.parliament.tas.gov.au` (no robots.txt rules) answers.
  - **Victoria:** `hansard.parliament.vic.gov.au` disallows `/search/` and `/isysquery/` in robots.txt, so it isn't usable.
  - **SA and WA:** the legacy and bare hosts didn't resolve.
  - **ParlInfo:** blocked.

### Evidence

- `make test`: 117 backend tests pass, including 6 for CTH:
  - the listing skips empty files;
  - the proof flag, pages and Federation Chamber;
  - House Question Time with interjections and the chair;
  - Senate questions, supplementaries and ministers;
  - no headers left in text;
  - party codes give sides.
- **Live run, CTH 12–31 Oct 2026:** 12 days, 3,311 speeches, 0 errors.

### Decisions

- **D16. Federal Hansard comes from OpenAustralia's public mirror of APH's XML**, until APH grants direct access. The product owner asked for "another way through".
  - It's a public republication of the official record, not a workaround of APH's firewall.
  - It's about a day behind APH, and speeches cite the mirrored file and printed page.

### Next

- NT connector (Territory Stories text pages), then Tasmania (search site).
- VIC, SA and WA: no legitimate route found from this environment. Run the scanner from an Australian network (the product owner's computer via Remote Control), send the access requests, or use assisted manual import.

---

## 1 Nov 2026: "Check for updates" runs the real scans

### Done

- **`backend/app/scans.py`** now has two modes, set by `SCAN_MODE`:
  - **`real`** (the default) runs the real sync for each parliament with an enabled connector (NSW, ACT, QLD).
    - Parliaments run one at a time, each in a worker thread, through the polite fetcher.
    - Each progress row updates live over the existing SSE stream, e.g. "1 new sitting day · 485 speeches stored", "2 awaiting publication" or "No new sitting days".
    - The six parliaments without a connector say why: "Not checked — the site blocks automated access; access requested".
    - The summary reports parliaments that sat, new sitting days and speeches stored, and notes that AI analysis comes next.
    - Each run is logged in `scan_runs` with per-chamber counts. One scan at a time.
  - **`sample`** replays the prototype's scan as before. The end-to-end journey that expects the sample "New" items runs with `SCAN_MODE=sample`.
- **`/api/status`** in real mode (`backend/app/live_status.py`) reads the real `sources`, `sitting_days` and `scan_runs` tables:
  - one row per parliament (9): "Last sat Thu 22 Oct", "Not sitting", or blocked with the reason;
  - `liveHansard`, `neverChecked`, `hansardTo` and `storedFrom` come from stored sitting days;
  - `lastScan` carries the last run's per-chamber counts.
- **Real scans no longer reveal the sample "new" items.** Only sample runs do.
- **Web app:**
  - the status panel says which parliaments have real Hansard ("Hansard is stored for real for NSW, ACT, Qld …");
  - it shows "Not checked yet" before the first scan;
  - the scan summary reads "1 parliament sat · 1 new sitting day · 485 speeches stored · …";
  - "Show me" appears only when there are new items.
- `.env.example` gains `SCAN_MODE`. The README documents both modes.

### Evidence

- `make test`: 110 backend tests pass. 3 new tests (`tests/test_real_scan.py`) drive the real mode through the API against the real NSW fixtures:
  - status before any scan names the blocked parliaments;
  - **POST /api/scans runs the real sync**: only one at a time; NSW reports "1 new sitting day · … speeches stored"; CTH says why it wasn't checked;
  - the summary counts are right, and status then shows "Last sat Thu 22 Oct";
  - the run is logged with `methods: {"pdf": 1}`;
  - **a second check straight away reports "No new sitting days" and stores 0 speeches**;
  - real scans don't reveal sample items.
- `make test-web`: typecheck and 6 unit tests pass. `npm run build` succeeds.

### Decisions

- **D15. No CORS proxies, relays, or automated browsers to get past bot checks.** The six blocked parliaments chose those checks. The legitimate routes are:
  - running the scanner from an Australian network the sites accept, such as the product owner's computer or an ACAG or VAGO network;
  - official alternative hosts or data;
  - access requests;
  - assisted manual import (a person downloads, the pipeline processes).

### Next

- The six parliaments: test legitimate routes, including running from the product owner's computer.

---

## 1 Nov 2026: member lists and speaker side

### Done

- **`config/members/{NSW,ACT,QLD}.yaml`**, generated by `scripts/build_members.py`:
  - every chamber is filled: NSW 93 + 42, ACT 25, QLD 93;
  - each list records its source URL, retrieval date and SHA-256, and whether the source is official or secondary;
  - `config/members/overrides.yaml` holds sourced corrections.
- **Sources:**
  - QLD is official: the Parliament's Members Photo Sheet.
  - NSW and ACT are secondary (Wikipedia), because the official lists are behind bot protection that blocks this environment. See `docs/sources.md` §6.
  - `make members` re-fetches the sources politely and rebuilds the lists.
- **`backend/pipeline/members.py`:**
  - `MemberIndex` matches Hansard speaker names to members: full name, then surname, then electorate or initials when two members share a surname. Presiding officers are matched through who was in the chair.
  - `speaker_side` is computed in code, per spec §9.4:
    - government office-holders (ministers, Leader of the House, Manager of Government Business and so on) are government whatever their party;
    - opposition office-holders are opposition;
    - otherwise the party is compared with the government of the day in `governments.yaml`;
    - anyone else is crossbench, and no party means unknown.
- **At ingest**, the sync fills party where Hansard doesn't print it, and sets `speaker_side` on every speech. **`make sides`** (`python -m app.cli sides`) recomputes stored speeches after a member list or government change.

### Evidence

- `make test`: 104 backend tests pass, including:
  - the lists fill every seat, and the QLD party counts match the official 53/36/2/1/1;
  - **cross-checks against Hansard:**
    - every NSW Assembly speaker in the 22 Oct contents is listed (Council: 1 known gap);
    - every ACT member voting on 17 Sep is listed;
    - QLD party and electorate agree with every full header on two days;
  - 16 side-rule cases;
  - **on real days, every member's turn gets a side**: NSW and ACT 100%, QLD 99.6%;
  - ingest sets Sloane to LIB and opposition, and a recompute repairs a stale value.

### Open items

- The NSW Council member "The Hon. Bernard Govind" isn't on the secondary list, so his party is unknown. Add him to `overrides.yaml` with a primary source.
- The ACT list says Leanne Castley left the Liberals in 2026. Confirm.
- Swap in the official NSW and ACT lists once access is arranged.

### Next

- Connect the web app's "Check for updates" and `/api/status` to the real scans.
- Find legitimate routes into the other six parliaments (CTH, VIC, SA, WA, TAS, NT).

---

## 1 Nov 2026: QLD connector, enabled (3 parliaments live: NSW, ACT, QLD)

### Done

- **`backend/connectors/qld.py`:**
  - **Sitting days:** found on the documents host with **HEAD requests** for each weekday's daily PDF (200 = sat, 404 = none), because the calendar on the main site is behind an Azure WAF.
  - **Document:** the day PDF (1 request).
  - **Outline:** the contents, which begin on the cover.
  - **Speaker headers** give electorate, **party**, role and time. Queensland is the first parliament whose Hansard prints party.
  - **Question Time:** by speaking order, with points of order kept separate.
  - **Dropped:** divisions and the attendance roll.
  - **Citations:** printed page numbers.
- **Sync: `settled_through`.** A connector that finds days by probing dated URLs can't tell "not sitting" from "not published yet" for recent days. Its watermark now stays at today − 3, so the last few days are probed again on each scan.
- **Fetcher: `head()`**, with the same robots.txt, spacing and blocking rules as `fetch()`.
- **Shared engine extensions** (`parsers/hansard_pdf.py`):
  - division starts are a pattern;
  - per-parliament header parsing (`header_fields`), so Queensland can return party, role and a 24-hour time;
  - party is remembered per member for the day;
  - in Question Time, points of order are statements, not questions.
- **QLD-LA enabled.**
- `config/governments.yaml`: the QLD Hansard spellings "Grn" and "Ind" are added.
- New fixture: the Record of Proceedings for 14 Oct 2026 (27 fixtures in total).

### Evidence

- `make test`: 85 backend tests pass, including 10 for QLD:
  - weekday probing makes no downloads;
  - recent days stay open;
  - the proof flag, contents and pages;
  - party, electorate, role and time from headers (including a ", by leave, without notice" tail);
  - **Question Time with points of order and interjections**;
  - no division lists, attendance roll or page furniture in the text;
  - the cover sign-off doesn't join the contents (14 Oct regression);
  - no speaker header left inside speech text on either day;
  - the sync keeps the last 3 days open, and a re-check costs 4 HEAD requests and one 304.
- **Live run, QLD 14–31 Oct 2026:** 5 sitting days, 1,750 speeches, 0 errors, 98–100% of contents headings matched each day, in 1 min 44 s.
  - The run found three bugs, all fixed with tests (a fourth, pdfminer printing a header's time before the name, turned up in the 13 Oct fixture and is fixed too):
    - the cover's sign-off joined the contents (one day matched only 27 of 55 headings);
    - names with bare initials ("Hon. G GRACE") were missed;
    - ministers' titles wrap over more than 3 lines.
  - 34 speeches mention the Auditor-General, including a committee debate on Auditor-General Report 12: 2022–23 (Growing ecotourism in Queensland).

### Known limits

- Party is printed only on full headers, so a member's turns earlier in the day than their first full header have no party. A member map will fill the gaps.
- Weekend sittings would be missed; the Assembly doesn't sit at weekends.

### Next

- Member-to-party maps for NSW and ACT, plus gap-filling for QLD, so every speech gets a speaker side.
- Wire the web app's "Check for updates" and `/api/status` to the real scans (NSW, ACT, QLD).
- Remaining parliaments (CTH, VIC, SA, WA, TAS, NT) wait on access: a re-test from an Australian network, or the access requests.

---

## 1 Nov 2026: ACT connector, enabled; shared PDF Hansard engine

### Done

- **`backend/parsers/hansard_pdf.py`:** the outline-guided PDF reader, moved out of the NSW connector so that NSW, ACT and later QLD share it.
  - Each parliament supplies its page lines, its outline of headings and its `Rules` (regular expressions for speakers, presiding officers, interjections, procedural lines and divisions).
  - A contents entry may carry a bracketed qualifier, e.g. "(Ministerial statement)", that the body prints on a separate line; the matcher accepts the title with or without it.
  - The NSW tests pass unchanged on the shared engine.
- **`backend/connectors/act.py`:**
  - **Listing:** the year index, with proof shown by a green row and "P" pages.
  - **Document:** the day PDF (1 request), keyed by date.
  - **Outline:** the PDF's own contents pages, where indentation shows groups.
  - **Speakers:**
    - Speaker headers can wrap over up to 4 lines (ministers' titles).
    - Question Time questions and answers follow speaking order.
    - Written answers are attributed to the minister.
    - Interjections and presiding officers (with who was in the chair) are separate turns.
  - **Dropped:** divisions.
  - **Citations:** each speech cites `PDF#page=N`, using printed page numbers.
- **Sync: unpublished sitting days.** A day the calendar lists with no document yet is now `pending`, not done. The watermark holds before it, so it's picked up when it appears; it's counted as `days_pending`, not an error. This applies to every connector.
- **ACT-LA enabled** in `config/sources.yaml`.
- **Config corrections from primary sources:**
  - `config/lexicon.yaml`: the ACT tabling wording is confirmed, "Auditor-General Act, pursuant to section 17—Auditor-General’s Report No {n}/{YYYY}—{title}" (ACT Hansard, 22 Oct 2026).
  - `config/governments.yaml`: **the ACT Leader of the Opposition is Mark Parton**, as printed in ACT Hansard on 17 Sep 2026. This replaces the low-confidence desk-research guess (Leanne Castley).

### Evidence

- `make test`: 75 backend tests pass, including:
  - 11 ACT connector tests on real fixtures:
    - the index lists proofs and unpublished days;
    - the stable document key;
    - recess, and a missing year index;
    - the proof flag, printed pages and citations;
    - a ministerial statement header wrapped over lines;
    - **Question Time: question, answer, supplementary, answer, a second questioner, answer**;
    - the Leader of the Opposition role, interjections, and written answers attributed to ministers;
    - no page furniture or division lists in the text;
    - a second day lines up with its contents;
    - the sync stores a day, a re-check costs 2 requests, and unpublished days hold the watermark.
  - A sync test that an unpublished day holds the watermark until it appears.
- **Live run, ACT 22–31 Oct 2026:**
  - 3 requests, 2 days stored (213 and 249 speeches), 28 and 29 Oct pending, 0 errors, 28 s.
  - It found Auditor-General's Report No 10/2026 (Management of community facilities) tabled on 22 Oct, and two Question Time answers citing the Auditor-General.

### Known limits

- When two contents titles share one statement, as on 17 Sep (NDIS, then Thriving Kids, then one "Ministerial statement"), the statement takes the second title.
- ACT Hansard prints no party, so speaker side needs a 25-member party map. That will be built from a verified members list, not from memory.
- The assembly segment in the URL (`11th-assembly`) is a constant until the Oct 2028 election.

### Next

- QLD connector: daily PDF from the documents host, found by date. It can reuse the engine; the outline comes from the PDF's own index.
- Member-to-party maps for NSW and ACT.
- Wire the web app's "Check for updates" and `/api/status` to the real scans now that two parliaments are live.

---

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
