# Sources — Phase 0 recon

Recon date: **31 Oct 2026**. Covers the 15 Hansard chambers (spec §5.1) and 9 audit offices (spec §5.2).

Related files:

| File | What's in it |
|---|---|
| `config/sources.yaml` | The 15 chambers |
| `config/offices.yaml` | The 9 offices |
| `config/lexicon.yaml` | The audit lexicon, including current Auditors-General |
| `config/governments.yaml` | Governing parties |
| `docs/access-requests.md` | Draft requests for blocked sources |
| `scripts/recon_batch.tsv` | The fixture capture list (`make recon`) |

## 0. How this was done, and what is still open

**Direct access was not possible from the build environment.** The cloud container's egress policy refused every parliament and audit office host with a proxy `403` before any request reached those sites.

- That includes `robots.txt`. See `docs/recon/2026-10-31-attempt-1.jsonl`, which records 18 hosts and 0 bytes received.
- The web fetch tool was refused in the same way.
- **These refusals are about our environment. They say nothing about the parliaments' own sites.** No source has yet been shown to block us.

What was done instead: web searches of official pages, published sample files, and open-source projects that use these sources (OpenAustralia, GLAM Workbench, community API docs, R and MCP clients). Each fact below carries a confidence level:

| Mark | Meaning |
|---|---|
| **H** | Seen in an official page, file or code snippet dated 2025–26 |
| **M** | Consistent secondary sources, or an official source seen only in part |
| **L** | Inference, a single source, or old information |

**Still to do for Phase 0 to be complete.** Run these from a network allowed to reach the hosts:

1. `make recon` captures `robots.txt` for every host and one real fixture per chamber and per office into `backend/tests/fixtures/`.
   - The fetcher is `scripts/recon_fetch.py`. It obeys `robots.txt`, waits at least 2 s per host, and stops at the first `401`, `403` or `429`, or at the first bot challenge.
2. Confirm the terms-of-use pages that are marked *unverified* below.
3. Confirm the speaker markup and proof/final flags against those fixtures.

Until this is done, every source has status `unverified` in `config/sources.yaml`. **No fixture is in the repo yet, so for every source the blocker is the build environment's network policy.**

## 1. Hansard: summary

| Source | Format and recommended approach | Listing sitting days | Proof → final signal | Risk of automated-access block | Conf. |
|---|---|---|---|---|---|
| CTH-SEN, CTH-HOR | ParlInfo XML, one file per chamber per day | aph.gov.au Hansard page (also an XML link per day) | `<session.header><proof>`; the label "Proof" on the listing | **High.** Third-party reports of an Azure WAF answering 403 even for `robots.txt` | H/M |
| NSW-LA, NSW-LC | Official JSON/XML API with no key | `/api/sittingdate`, `/api/hansard/search/year/{yyyy}` | "– PROOF" in the title; becomes "corrected copy" | Low | M-H |
| VIC-LA, VIC-LC | Daily PDF; HTML per speech | Browse Hansard listing (no API found) | Title "PROOF Hansard …" → no "PROOF" about 5 working days later | **Medium-high.** The spec's own test fetch was refused by bot detection | H |
| QLD-LA | Daily PDF at a predictable URL | Latest Sitting Week page; date-based URL | "Record of Proceedings (Proof)" | Low | H |
| SA-HA, SA-LC | XML from the official OpenAPI | `/search/calendar` and the API | `reviewStage` / `dateModified` per the spec (element names unconfirmed) | **Medium.** The spec's test fetch of the calendar was refused | H (API) / L (elements) |
| WA-LA, WA-LC | Per-extract and per-day downloads (same platform as SA since late 2024) | `/hansard/search` calendar | "uncorrected draft" notice | **Medium.** Azure Front Door token in the original link | H |
| TAS-HA, TAS-LC | Draft full-text PDF linked from each day's proceedings page; final later | Chamber proceedings calendar pages | File name `…-Draft-Full-Text.pdf` → final in chamber proceedings | Low | H |
| ACT-LA | Proof daily PDF at a predictable URL; official weekly PDF later | Predictable URL `tP{YYMMDD}.pdf` | `tP` proof prefix → `{YYYYMMDD}.pdf` weekly official | Low | H |
| NT-LA | Draft daily PDF in Territory Stories; final later | Parliament "draft" page and Territory Stories titles | "Draft Daily Hansard" → "Debates and Questions" | Low | H |

## 2. Hansard: per chamber

### CTH: Senate (`CTH-SEN`) and House of Representatives (`CTH-HOR`)

- **List sitting days:**
  - `https://www.aph.gov.au/Parliamentary_Business/Hansard` lists each sitting day with a Proof PDF, an XML file and a ParlInfo link, with "Previous sitting week" paging. **H**
  - The spec found that the Senate year page `Hanssen261110` listed dates only to 2025. Use the main Hansard page, not the year pages.
- **Document URL:**
  - `https://parlinfo.aph.gov.au/parlInfo/download/chamber/{dataset}/{YYYY-MM-DD}/toc_unixml/{id}.xml;fileType=text%2Fxml`
  - `{dataset}` is `hansardr` for the House **(H)** and `hansards` for the Senate **(M)**. The Senate value is seen in an OpenAustralia issue that links a ParlInfo search on that dataset (12 Oct 2026).
  - `{id}` is not predictable. Take it from the XML link on the listing page.
- **Format:** XML (also PDF).
  - **The Federation Chamber is in the House file** as `<fedchamb.xscript>`, next to `<chamber.xscript>` and `<answers.to.questions>`. Before 14 Aug 2012 the element was `<maincomm.xscript>`. **H** (Nature *Scientific Data* paper on the corpus).
- **Speaker markup:**
  - `debate/speech/talk.start/talker` holds `name` (e.g. "Abbott, Tony, MP"), `name.id` (APH id; 10000 is the generic Speaker), `electorate`, `party`, `in.gov`, `first.speech`, `page.no` and `time.stamp`.
  - `party` and `electorate` are sometimes missing.
  - Interjections and continuations are nested elements.
  - **H**
- **Proof/final:**
  - `<session.header>` has `<proof>`. Sample official files show `0`, so `1` probably means proof **(M)**.
  - The listing labels new transcripts "Proof". The Official Hansard replaces them about 2 weeks after the sitting week (Parliamentary Education Office).
  - Re-check days up to `PROOF_RECHECK_DAYS`.
- **robots.txt:** not checked (environment egress denied). A third-party project (parl-monitor, Oct 2026) reports that `robots.txt` itself returns 403 from the WAF.
- **Terms:** CC BY-NC-ND 3.0 AU, according to GLAM Workbench and the hansard-xml README **(M)**. The current aph.gov.au copyright page has not been seen. Our use is non-commercial and quotes verbatim with a link. Derived summaries need a check against ND: we store and quote; we don't republish modified transcripts.
- **Rate limits:** none published. There is no official Hansard API.
- **Blockers:** likely WAF block on `aph.gov.au` and `parlinfo.aph.gov.au` **(M; to confirm with `make recon`)**.
- **Recommended connector:**
  - ParlInfo XML via the listing page's XML links, with conditional GET.
  - If the WAF blocks us: send the access request in `docs/access-requests.md` and use manual import (§9.11) meanwhile.
  - OpenAustralia mirrors the same original XML at `https://data.openaustralia.org.au/origxml/representatives_debates/{YYYY-MM-DD}.xml` (a 2026-03-05 file was seen; `senate_debates` is presumed). It is a possible interim source, **but only with product-owner approval**: it's a third party, it lags, and its parser had Senate issues in Oct 2026.
- **Fixture:** none yet (environment). Batch: listing page, then the XML link for one recent day per chamber.

### NSW: Legislative Assembly (`NSW-LA`) and Legislative Council (`NSW-LC`)

- **List sitting days:** the API base is `https://api.parliament.nsw.gov.au/api`. **M-H** (community docs at parliament-api-docs.readthedocs.io and the nsw-hansard-mcp client, changelog Jul 2026).
  - `/sittingdate`, `/sittingdatetype`
  - `/hansard/search/year/{yyyy}`
  - `/hansard/search/bydate?date={date}` returns the document ids per house.
- **Document URL:**
  - `/hansard/search/daily/tableofcontents/{documentId}` (XML)
  - `/hansard/search/daily/fragment/{documentId}` (XML or JSON; sources disagree)
  - `/hansard/search/daily/pdf/{documentId}`
  - The website also links daily PDFs such as `/__data/assets/pdf_file/0017/25253/hansard-la-15-september-2026.pdf`. Those asset ids are not predictable, so use the API.
- **Format:** XML or JSON via the API; PDF. Coverage from Sep 1991. No key needed; provided "as is" with no developer support.
- **Speaker markup:** not yet seen. Read from the TOC and fragment fixture.
- **Proof/final:**
  - Proof text is published progressively, within about 3 h of being spoken.
  - The daily proof PDF follows within about 3 h of the last House rising.
  - Members have 2 weeks to submit corrections, then the "corrected copy" replaces the proof.
  - Titles carry "– PROOF".
  - **H** (official Hansard page)
- **robots.txt:** not checked (environment).
- **Terms:** Data.NSW lists the API as CC BY. The Parliament's copyright page asks for attribution, says we accept the defamation risk, and forbids advertising use. **M**; take the stricter reading.
- **Rate limits:** none published. Use the default 2 s spacing.
- **Blockers:** none known.
- **Recommended connector:** NSW Hansard API: `bydate` → TOC → fragments, plus the PDF for page citations.
- **Fixture:** none yet (environment). Batch: `year/2026` JSON plus the 15 Sep 2026 LA and LC proof PDFs; then the TOC and a fragment for one document id.

### VIC: Legislative Assembly (`VIC-LA`) and Legislative Council (`VIC-LC`)

- **List sitting days:**
  - `https://www.parliament.vic.gov.au/parliamentary-activity/hansard/hansard-debate?page=1&pageSize=10` (Browse Hansard).
  - No calendar API was found. The page probably loads a JSON endpoint; inspect it with `make recon`, but do not bypass protection.
- **Document URL:**
  - Day PDF: `/{cache}/globalassets/hansard-daily-pdfs/hansard-{house}-{docid}/hansard-{house}-{docid}.pdf`, e.g. LA 24 Sep 2026 is `hansard-2145855009-37599`.
  - Per-speech HTML: `/parliamentary-activity/hansard/hansard-details/HANSARD-{house}-{docid}`.
  - House codes: Assembly `2145855009`, Council `974425065`. **H**
  - `{cache}` is a 6-hex segment that changes between crawls, probably a cache-buster **(L)**. Take links from the listing; don't build them.
- **Format:** PDF per day; HTML per speech since Dec 2018.
- **Speaker markup:** in the PDFs, a bold name followed by the electorate and party code, e.g. "(Name, ALP)". Party codes are in `config/governments.yaml`; **note that `LP` means Libertarian in Victoria**. To confirm from the fixture.
- **Proof/final:**
  - A speech is online within about 3 h.
  - The full-day proof is out about 4 h after the sitting ends.
  - The final follows about 5 working days later.
  - The PDF title starts "PROOF Hansard"; the final drops "PROOF".
  - **H**
- **robots.txt:** not checked (environment).
- **Terms:** reuse beyond the listed purposes needs the Presiding Officers' permission (info@parliament.vic.gov.au). No Creative Commons licence found. **M**. Include Victoria in the access request so ACAG gets written permission.
- **Rate limits:** none published.
- **Blockers:** the spec's test fetch was refused by bot detection **(H, from spec research)**. Treat as **likely blocked** until `make recon` shows otherwise.
- **Recommended connector:** daily PDF found from the listing page. If blocked, use manual import and the access request.
- **Fixture:** none yet (environment). Batch: the listing page, the LA PDF for 24 Sep 2026, and one LC PDF.

### QLD: Legislative Assembly (`QLD-LA`)

- **List sitting days:**
  - `https://www.parliament.qld.gov.au/Work-of-the-Assembly/Sitting-Dates/Latest-Sitting-Week` labels each transcript "Full transcript – Proof". **M**
  - Simplest: test the predictable date URL for each calendar sitting date.
- **Document URL:**
  - Daily: `https://documents.parliament.qld.gov.au/events/han/{YYYY}/{YYYY_MM_DD}_DAILY.pdf`, e.g. `2026_10_13_DAILY.pdf`.
  - Weekly: `{YYYY_MM_DD}_WEEKLY.pdf`, dated by the first sitting day of the week.
  - **H**
  - A preview site on the same platform as SA and WA (`previewqld.public.parliament.io/.../daily/lh/{date}/pdf/download`) exists. XML there is unconfirmed **(L)**.
- **Format:** PDF.
- **Speaker markup:** PDF text with the speaker in capitals and the electorate in brackets. To confirm from the fixture. Party codes: LNP, ALP, KAP, GRN, IND **(H)**.
- **Proof/final:**
  - "Record of Proceedings (Proof)" plus "PROOFS MUST BE RETURNED BY 12 noon …". Usually published within a day. **H**
  - The final signal is the "(Proof)" marker disappearing, or the weekly volume. Confirm with a later fetch of the same URL; the hash changes.
- **robots.txt:** not checked (environment).
- **Terms:** the copyright page is at `parliament.qld.gov.au/Global/Copyright` (not seen). Historically restrictive: the Clerk refused OpenAustralia "authorised publisher" status under s51(4)(g) of the Parliament of Queensland Act 2001. **M**. Our use is internal monitoring with short quotes and links, not republication. Confirm with the access letter.
- **Rate limits:** none published.
- **Blockers:** none known.
- **Recommended connector:** daily PDF by date; re-check weekly for the final.
- **Fixture:** none yet (environment). Batch: `2026_10_13_DAILY.pdf`.

### SA: House of Assembly (`SA-HA`, `lh`) and Legislative Council (`SA-LC`, `uh`)

- **List sitting days:**
  - `https://hansardsearch.parliament.sa.gov.au/search/calendar` lists all events for a year.
  - **Official OpenAPI 3 spec** at `/docs/api/index.html` (raw: `/docs/api/v1/swagger.json`), grouped into Hansard, Parliament and Chambers, with a request to "use these APIs responsibly". **H**. The endpoint paths were not visible in search; read them from the swagger fixture.
- **Document URL:**
  - Day TOC: `/daily/{lh|uh}/{YYYY-MM-DD}/download/toc`
  - Extract: `/daily/{lh|uh}/{YYYY-MM-DD}/extract/{n}/download`
  - Page: `/daily/{lh|uh}/{YYYY-MM-DD}/{n}`
  - **H**
  - The legacy `hansardpublic…/HansardData.svc` is probably obsolete **(L)**.
- **Format:** XML. Since Oct 2007, per subject; before that, single-file PDFs.
- **Speaker markup:** the TOC carries speaker names, electorates, ministerial titles, subjects, page numbers and timestamps. The spec names the elements `talker`, `proceeding`, `subject` and `startTime`, but search could not confirm them **(L)**. Confirm from the fixture.
- **Proof/final:**
  - Published "after 4 pm on the day following the sitting" **(H)**.
  - The spec reports `reviewStage` and `dateModified` as the signal **(L until the fixture is seen)**.
- **robots.txt:** not checked (environment).
- **Terms:** copyright is held by the Attorney-General of SA. Excerpts must be attributed, fair and accurate, not used for advertising, satire or ridicule, and must not misrepresent members. Republication is not covered by privilege. **H**. Quote verbatim and link back.
- **Rate limits:** none published, beyond "use responsibly". Use the 2 s spacing or more.
- **Blockers:** the spec's test fetch of the calendar was refused **(H, from spec research)**. The API may behave differently. To confirm with `make recon`.
- **Recommended connector:** the official API for the sitting list, then TOC and extract XML per day.
- **Fixture:** none yet (environment). Batch: swagger.json, the calendar, and the `lh` TOC for 6 May 2026.

### WA: Legislative Assembly (`WA-LA`, `lh`) and Legislative Council (`WA-LC`, `uh`)

- **The system has changed since the spec's lead.** Hansard from late 2024 is no longer in the Lotus Domino `hansard.nsf`. It uses the same `/daily/...` scheme as SA. **H**
- **List sitting days:** `https://www.parliament.wa.gov.au/hansard/search` (Daily Hansard calendar).
- **Document URL:**
  - Page: `/hansard/daily/{lh|uh}/{YYYY-MM-DD}/{n}`
  - Extract: `/hansard/daily/{house}/{date}/extract/{n}/download`
  - Full day: `/hansard/daily/{house}/{date}/pdf/download`
  - Estimates committees use `esta` and `estb`.
  - Aug 2000 – Nov 2024 is still one PDF per date in the old system.
  - Whether `/download/toc` exists as on SA is unconfirmed **(L)**.
- **Format:** HTML, per-extract downloads, PDF.
- **Speaker markup:** to confirm from the fixture. It probably matches SA's XML if the TOC exists.
- **Proof/final:**
  - Published progressively; the full day within about 3 h of the house rising.
  - Pages carry "uncorrected draft — not to be quoted or distributed".
  - The Daily PDF "may still be corrected".
  - **H**
- **robots.txt:** not checked (environment).
- **Terms:** © Parliament of WA, reuse allowed with the notice. No advertising, satire or misrepresentation; the Parliament prefers links to republication. **M-H**
- **Rate limits:** none published.
- **Blockers:** the sponsor's link carried `afd_azwaf_tok`, an Azure Front Door WAF token, so the site may challenge scripts. Search found no other evidence **(L)**. Never reuse the token.
- **Recommended connector:** calendar → day TOC or extracts (SA-style if available), else the full-day PDF.
- **Fixture:** none yet (environment). Batch: `uh` 18 Jun 2026 full-day PDF; an `lh` day to pick from the calendar.

### TAS: House of Assembly (`TAS-HA`) and Legislative Council (`TAS-LC`)

- **List sitting days:**
  - Chamber proceedings calendar pages:
    - `/house-of-assembly/chamber-proceedings/proceedings/{YYYY}/{month}/house-of-assembly-{D}-{month}`
    - `/legislative-council/chamber-proceedings/calendars/{YYYY}/{month}/legislative-council-{D}-{month}-{YYYY}`
  - Each links to that day's Hansard. **H**
  - The ISYS search (`search.parliament.tas.gov.au/adv/hahansard`, `/adv/lchansard`) is useful for backfill checks but not as the primary list.
- **Document URL:** `/__data/assets/pdf_file/{nnnn}/{assetid}/{HA|LC}-{Weekday}-{D}-{Month}-{YYYY}-Draft-Full-Text.pdf`. The asset id is not predictable, so take the link from the day page. **H**
- **Format:** PDF draft. Search also offers .docx, text and HTML5 versions.
- **Speaker markup:** PDF text. To confirm from the fixture.
- **Proof/final:**
  - The draft carries "issued in advance of the final Hansard", is not covered by privilege, and has "Draft-Full-Text" in the file name.
  - The final appears in chamber proceedings "after several days" (about 3 days, per a 2020 annual report).
  - **H**
- **robots.txt:** not checked (environment).
- **Terms:** not found. *Unverified.*
- **Rate limits:** none published.
- **Blockers:** none known.
- **Recommended connector:** calendar page → draft PDF; re-check for the final.
- **Fixture:** none yet (environment). Batch: HA 18 Aug 2026 and LC 11 Aug 2026 drafts.

### ACT: Legislative Assembly (`ACT-LA`)

- **List sitting days:** the predictable proof URL per calendar date. The `hansard.act.gov.au` index also lists them.
- **Document URL:**
  - Proof daily: `https://www.hansard.act.gov.au/hansard/11th-assembly/{YYYY}/PDF/tP{YYMMDD}.pdf`
  - Official weekly, per day: `…/PDF/{YYYYMMDD}.pdf`
  - Question Time proof: `/hansard/question-time/Q{MMDD}{Ddd}.pdf`
  - **H**
  - The `11th-assembly` segment changes after the Oct 2028 election.
- **Format:** PDF.
- **Speaker markup:** PDF text. To confirm from the fixture.
- **Proof/final:**
  - The proof is out the day after the sitting, headed "EDITED PROOF TRANSCRIPT … subject to further checking".
  - The official Weekly Hansard follows about 3 weeks after the sitting week.
  - Different file names make proof → final an easy new document version.
  - **H**
- **robots.txt:** not checked (environment).
- **Terms:** not found. *Unverified.*
- **Rate limits:** none published.
- **Blockers:** none known.
- **Recommended connector:** date-based proof PDF, then the official PDF. Small volumes: the ACT sits far less often than the larger parliaments.
- **Fixture:** none yet (environment). Batch: `tP260917.pdf`.

### NT: Legislative Assembly (`NT-LA`)

- **List sitting days:**
  - `https://parliament.nt.gov.au/business/parliamentary-record/draft` ("Draft Daily Hansard, Questions and Minutes").
  - `/business/meeting-documents` lists the Notice Paper by meeting.
  - **H**
- **Document URL:**
  - Territory Stories: `https://territorystories.nt.gov.au/10070/{itemId}/0/{n}`, also reachable as `hdl.handle.net/10070/{id}`. `n` is probably a file index **(L)**.
  - Draft title: "Draft Daily Hansard - Day N - D Month YYYY"
  - Final title: "Debates and Questions - Day N - D Month YYYY"
- **Format:** PDF.
- **Speaker markup:** PDF text. To confirm from the fixture.
- **Proof/final:** the title prefix ("Draft Daily Hansard" → "Debates and Questions"). Finals were indexed for sittings up to Jul 2026, so the lag looks like roughly 2–3 months **(L)**.
- **robots.txt:** not checked (environment).
- **Terms:** Territory Stories item metadata says CC BY 4.0, with the Legislative Assembly of the NT as copyright owner. **H**
- **Rate limits:** none published. No OAI-PMH endpoint found.
- **Blockers:** none known.
- **Recommended connector:** parliament draft page → Territory Stories PDF; match the final by day number and date.
- **Fixture:** none yet (environment). Batch: the draft page and one Territory Stories item.

## 3. Audit offices

### Summary

| Office | Current Auditor-General | Forward program | Reports listing | Published audit requests | Conf. |
|---|---|---|---|---|---|
| ANAO | Dr Caralee McLiesh PSM (from 4 Nov 2024) | Annual Audit Work Program 2026–27 (web pages, multi-year) | `/pubs/performance-audit` (paged) | Yes: `/work-program/requests`, items at `/work/request/{slug}` | H |
| AONSW | Bola Oyetunji (from 4 Apr 2024) | Audit Work Plan 2026–2029 (web + PDF, "As at July 2026") | Listing URL unconfirmed | Yes: `/our-work/requests-for-audit` (since Jul 2019, with requester, date and status) | H |
| VAGO | Andrew Greaves (2nd term to 18 Sep 2030) | Annual Plan 2026–27 (PDF + HTML, tabled 24 Jun 2026) | `/reports` unconfirmed; items at `/report/{slug}` | No list ("Suggest an audit" form only) | H |
| QAO | Rachel Vagg (12 Aug 2024 – 11 Aug 2031) | Forward work plan 2026–29 (PDF, Jun 2026) + acquittal of prior plans | `/reports-resources/reports-parliament` (M) | Yes: `/audit-program/requests-audits` | H |
| SAAGD | Andrew Blaskett (from 8 Jan 2024) | **None published** | `/reports` (paged) | Not found | H / M (absence) |
| OAGWA | Caroline Spencer (May 2018 – May 2028) | **No dated program.** "Audits in progress" pages; topics selected twice a year | `/reports-and-publications/reports/` | Not found | H / M |
| AUDTAS | Martin Thompson (from 1 May 2024) | Auditor-General's Annual Plan 2026–27 (dated 22 Jun 2026) | `/publication-category/performance-audit/` (paged) | No list (referral guidance only) | H |
| ACTAO | Ajay Sharma PSM (8 Feb 2026 – 7 Feb 2033) | Performance Audit Program 2026–27 (PDF, 9 Jun 2026) | Listing URL unconfirmed | No list | H |
| NTAGO | Jara K. Dean (from 13 Sep 2024) | **None published** ("Plan of Work" in the annual report) | `/publications/ag-reports-parliament` | Not found | H / M |

**Corrections to the spec's leads:**

- **SA:** the office's name has been **Audit Office of South Australia** since 1 Jul 2024. The office code `SAAGD` is kept for continuity.
- **WA:** writes "Auditor General" with no hyphen. The lexicon handles this.
- **ACT:** Michael Harris has been replaced by Ajay Sharma.
- **NT:** Julie Crisp has been replaced by Jara K. Dean.
- **Tasmania:** the Auditor-General is Martin **Thompson**.

For all 9 offices, **`robots.txt` and the terms pages are not checked** (environment egress denied). Government sites usually publish under CC BY 4.0, but that is to be confirmed per site with `make recon`.

### ANAO: Australian National Audit Office

- **Program:**
  - Annual Audit Work Program 2026–27, overview at `https://www.anao.gov.au/work-program/overview`, with portfolio pages (e.g. `/work-program/portfolio/{name}`).
  - From 2026–27 it is multi-year: topics that may start in 2026–27, plus a 2027–29 forward pool.
  - The draft was open for comment from 17 Mar to 10 Apr 2026. The final was published about July 2026 (exact date unconfirmed).
  - Web pages; no single PDF found.
- **Topic fields:** per potential audit, the portfolio, title and rationale (to confirm from the fixture).
- **Statuses:** the work program search (`/work-program/search`) covers potential audits and those in progress.
- **Reports:** `/pubs/performance-audit`, paged, about 1,450 items. Titled "Auditor-General Report No. N YYYY–YY".
- **Audit requests:** `/work-program/requests` (paged, about 150 items); each at `/work/request/{slug}`, e.g. `cheaper-home-batteries-program-february-2026`.
- **Blockers:** none known beyond the environment.

### AONSW: Audit Office of New South Wales

- **Program:** Audit Work Plan 2026–2029 (`/audit-work-plan-2026-2029` plus PDF). It covers the 2026–27 financial and performance audit plan and a forward plan for 2027–28 to 2028–29, and replaces the Audit Work Program 2025–2028.
- **Statuses:** the "Published reports" and "Upcoming reports" sections under Our work.
- **Reports:** listing URL not confirmed (guess: `/our-work/reports`).
- **Audit requests:** all requests and suggestions from MPs since 1 Jul 2019, with requester, date and status (`/our-work/requests-for-audit`).

### VAGO: Victorian Auditor-General's Office

- **Program:**
  - Annual Plan 2026–27, tabled 24 Jun 2026 under s73 of the Audit Act 1994.
  - Covers 22 performance engagements and 2 financial results reports in 2026–27, within a 3-year forward program.
  - PDF: `/sites/default/files/2026-06/20260624_Annual-Plan-2026-27.pdf`; HTML at `/node/35573`.
- **Statuses:** reports can be filtered as completed, in progress and in planning (spec lead; to confirm).
- **Reports:** items at `/report/{slug}`; listing URL to confirm.
- **Audit requests:** "Suggest an audit" form; no published list.

### QAO: Queensland Audit Office

- **Program:**
  - Forward work plan 2026–29 (PDF, Jun 2026), hub at `/audit-program`.
  - **Status source:** "Acquittal of Queensland Audit Office prior published work plans – June 2026" (PDF). It says no topics were removed from the 2025–28 plan.
  - Fact sheet added Aug 2026.
- **Reports:** `/reports-resources/reports-parliament` (paged). Seen on a staging host; the live path is inferred **(M)**.
- **Audit requests:** published list at `/audit-program/requests-audits`.

### SAAGD: Audit Office of South Australia

- **Program:** **none published** (two searches; absence likely but not proven). Reporting is after the event:
  - the annual report (Sept);
  - numbered reports, "Report N of YYYY" (e.g. Report 6 of 2026, Status of performance audit recommendations, 1 Sep 2026);
  - an operations report.
- **F4 fallback:** compare with recent reports only, and say so (spec §9.7). The same question applies to WA and NT (spec §15 Q7).
- **Reports:** `https://www.audit.sa.gov.au/reports` (paged).
- **Audit requests:** none published.
- **Context for F3:** Report 6 of 2026 says SA has "no formal arrangement" for Parliament to review audit findings, and there is no PAC.

### OAGWA: Office of the Auditor General Western Australia

- **Program:**
  - **No dated forward program.** Topics are selected twice a year (Strategic Plan 2025–30), and an audit's objective and timing are published once it starts.
  - Use `/audit-program/audits-in-progress/` as the "in progress" list.
  - An older page, "Work in Progress and Forward Audit Program", exists; its current status is unclear.
  - Partial F4: compare with in-progress audits plus recent reports, and say so.
- **Reports:** `/reports-and-publications/reports/`, numbered "Report N: YYYY-YY".
- **Audit requests:** none published.

### AUDTAS: Audit Tasmania

- **Program:**
  - Auditor-General's Annual Plan 2026–27, dated 22 Jun 2026, under s11 of the Audit Act 2008 (publication page; PDF link to take from the page).
  - Past plans showed audits cut for lack of funding greyed out. Record these as `deferred`.
- **Reports:** `/publication-category/performance-audit/` (WordPress, paged).
- **Audit requests:** none published. The referrals page explains that requests from the Treasurer, PAC, Ombudsman and Integrity Commission are provided for in the Act.

### ACTAO: ACT Audit Office

- **Program:**
  - Performance Audit Program 2026–27, released 9 Jun 2026, with a media release.
  - Covers 18 potential audits over 2026–27 and 2027–28.
  - PDF at `/__data/assets/pdf_file/0003/3080730/ACT-Audit-Office-Performance-Audit-Program-2026-27.pdf`.
- **Reports:** "Report No. N/YYYY"; items under `/reports-and-publications/audit-reports/{YYYY}/...`. Listing URL to confirm.
- **Audit requests:** none published; the annual report describes how to lodge one.

### NTAGO: Northern Territory Auditor-General's Office

- **Program:** **none published.** The annual report has a "Plan of Work" section, and older reports to the Assembly had a "Proposed Audit Activity" appendix for the next six months. Fallback as for SA.
- **Mandate caveat for F4:** NT sources say the NT Auditor-General has no general statutory power to conduct performance audits; it does performance management system audits, and ministers can request audits. The gaps page should say so.
- **Reports:**
  - `/publications/ag-reports-parliament`. Reports are titled "Report to the Legislative Assembly N: YYYY-YY" (No 1, Jul 2026; No 2, Aug 2026), and older ones are dated volumes (`/reports/2024_May.pdf`).
  - **These are bundles: split them into individual audits** (Phase 3).
- **Audit requests:** none published.

## 4. Lexicon, committees and governments

- **`config/lexicon.yaml`:**
  - Office names and aliases, including the SA rename and Audit Tasmania / Tasmanian Audit Office.
  - Current and former Auditors-General, with the forms expected in Hansard.
  - Generic terms, tabling phrases (verified for Vic; partly for NSW; the rest to confirm from fixtures), request phrases, committees, integrity bodies, risk terms and public-body change terms.
- **Committees, verified Oct 2026 (H):**
  - **Qld:** the Auditor-General is overseen by the **Governance, Energy and Finance Committee** (since 28 Nov 2024).
  - **SA:** has **no PAC**. The Economic and Finance Committee and the Budget and Finance Committee hear the Auditor-General.
  - **ACT:** the **Standing Committee on Public Accounts and Administration** (since 3 Dec 2024).
  - **NT:** still has a Public Accounts Committee.
- **Integrity bodies, NT change (H):** since 1 Jun 2026 the ICAC and Ombudsman NT are merged into the **Office of the Integrity and Ethics Commissioner**.
- **`config/governments.yaml`:** all 9 parliaments, with head of government, governing parties, majority or minority status, opposition, and party codes. Changes relevant to the backfill window (31 Aug – 31 Oct 2026):
  - **ACT:** the Greens ended confidence-and-supply talks on 16 Sep 2026. No change to who is government or crossbench.
  - **WA:** One Nation won the Secret Harbour by-election on 29 Aug 2026. Crossbench.
  - **Vic:** Premier Ben Carroll took office on 28 Jul 2026, and the state election is on 28 Nov 2026 (caretaker from 3 Nov). Update after the election.
  - **SA:** the 21 Mar 2026 election returned Labor; One Nation (4) is crossbench, not opposition.

## 5. Recommended Phase 2 connector order

From easiest and most structured first:

1. **SA:** official API and XML.
2. **NSW:** API.
3. **QLD:** date-based PDF.
4. **ACT:** date-based PDF.
5. **WA:** SA-style platform.
6. **TAS:** calendar page → PDF.
7. **NT:** draft page → Territory Stories.
8. **VIC:** PDF; likely bot protection.
9. **CTH:** XML, but WAF risk.

CTH and VIC are the most likely to need the access requests in `docs/access-requests.md` and manual import in the meantime.
