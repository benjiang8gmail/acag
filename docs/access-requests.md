# Access requests (drafts)

Spec §5.1: when a source blocks automated access, ACAG asks that Parliament's Hansard team for an allowlist or a data feed. Meanwhile, the source is covered by manual import (§9.11).

**Status, 31 Oct 2026: drafts only. Nothing has been sent.**

The live check (`docs/sources.md` §0a) confirmed bot protection on the sites below. It ran from a US cloud network, so first **re-run `make recon` from the pilot's Australian network**, and send only the requests that are still needed.

Before sending, fill in these placeholders:

| Placeholder | What to put there |
|---|---|
| `{CONTACT_NAME}`, `{CONTACT_EMAIL}` | The crawler contact (spec §15 Q3; also goes in `FETCH_USER_AGENT`) |
| `{EGRESS_IPS}` | The pilot host's outbound IP addresses, once hosting is decided (§15 Q5) |

### Hansard

| Source | What answered on 31 Oct | Send to | Draft |
|---|---|---|---|
| CTH-SEN, CTH-HOR | Azure WAF "Page Blocked by WAF", even for robots.txt | Parliamentary Library / Hansard, Department of Parliamentary Services (via aph.gov.au "Contact us"; quote the block reference shown on the page) | A |
| VIC-LA, VIC-LC | Cloudflare challenge, even for robots.txt. Reuse beyond the listed purposes also needs the Presiding Officers' permission. | info@parliament.vic.gov.au | B |
| SA-HA, SA-LC | Azure WAF JavaScript challenge, even for robots.txt and the published API | Hansard, Parliament of South Australia | C |
| WA-LA, WA-LC | Azure WAF challenge, even for robots.txt | Hansard, Parliament of Western Australia | C (adapted) |
| TAS-HA, TAS-LC | Cloudflare challenge, even for robots.txt | Hansard, Parliament of Tasmania | C (adapted) |
| NT-LA | The parliament site shows a Cloudflare challenge. Territory Stories works, but its robots.txt disallows the PDF files. | Library & Archives NT (Territory Stories), copying Hansard, Legislative Assembly of the NT | D |

**Not needed:**

| Source | Why |
|---|---|
| NSW | Use the public Hansard API, which answered normally. Only the website is behind Cloudflare. |
| QLD | Use `documents.parliament.qld.gov.au`, which answered normally. Only the main site is behind Azure WAF. |
| ACT | Answered normally. |

### Audit offices

| Office | What answered on 31 Oct | Draft |
|---|---|---|
| ANAO | No response (timeouts) | E |
| QAO | "Client Challenge" page, even for robots.txt | E |
| Audit Office of SA | "Client Challenge" page, even for robots.txt | E |
| OAG WA | nginx 403 | E |
| ACT Audit Office | Cloudflare challenge | E |
| NT Auditor-General's Office | Cloudflare challenge | E |

AONSW, VAGO and Audit Tasmania answered normally. VAGO's robots.txt disallows `/search/`, so its register will be read from its sitemap.

---

## A. Parliament of Australia (APH)

> **Subject:** Request for automated access to Hansard XML for the Australasian Council of Auditors-General
>
> Dear Hansard team,
>
> The Australasian Council of Auditors-General (ACAG) is piloting **Hansard Watch**. It is an internal tool that helps Australia's nine audit offices see what Parliament says about their Auditors-General, their tabled reports and their forward audit programs. It reads each sitting day's Hansard once, stores it, and produces short sourced briefs for audit office staff. Every quote links back to the official record on aph.gov.au.
>
> Our client is blocked by the website's firewall, including for robots.txt. We'd be grateful for either:
>
> 1. **an allowlist** for our client on `www.aph.gov.au` and `parlinfo.aph.gov.au`
>    - User-Agent: `ACAG-HansardWatch/0.1 (+mailto:{CONTACT_EMAIL})`
>    - source IPs: `{EGRESS_IPS}`
>
>    **or**
>
> 2. **a data feed** (or a recommended endpoint) for the daily Senate and House Hansard XML, including the Federation Chamber.
>
> What our client does:
> - It requests only new or changed sitting days. That is about 2–4 files per sitting day, and it uses conditional requests (`If-None-Match` / `If-Modified-Since`).
> - It waits at least 2 seconds between requests and obeys robots.txt.
> - It runs once a day at most, or when a user asks.
> - It does not republish transcripts. It is used non-commercially, in line with the CC BY-NC-ND 3.0 AU licence: verbatim quotes with attribution and a link to the official record.
>
> Contact: {CONTACT_NAME}, {CONTACT_EMAIL}, on behalf of ACAG.
>
> Kind regards,

## B. Parliament of Victoria

> **Subject:** Permission and automated access to Hansard for the Australasian Council of Auditors-General
>
> Dear Presiding Officers and Hansard team,
>
> The Australasian Council of Auditors-General (ACAG), with the Victorian Auditor-General's Office as product owner, is piloting **Hansard Watch**. It is an internal tool that helps audit offices see what Parliament says about their Auditors-General, tabled audit reports and forward audit programs. It reads each sitting day's Hansard once and gives audit office staff short briefs with verbatim quotes, each linking to the official record on parliament.vic.gov.au.
>
> We ask for:
>
> 1. **permission** under the Parliament's copyright conditions to store Hansard transcripts and quote short verbatim extracts, with attribution and links, in an internal tool used by audit offices;
> 2. **automated access** to the daily Hansard (proof and final PDFs, or a data feed or API if one exists). Our client was refused by the website's bot protection. An allowlist for User-Agent `ACAG-HansardWatch/0.1 (+mailto:{CONTACT_EMAIL})` and source IPs `{EGRESS_IPS}` would be enough.
>
> What our client does:
> - It requests only new or changed sitting days, and uses conditional requests.
> - It waits at least 2 seconds between requests and obeys robots.txt.
> - It runs once a day at most.
> - It does not try to get around the site's protection.
>
> Contact: {CONTACT_NAME}, {CONTACT_EMAIL}.
>
> Kind regards,

## C. Parliament of South Australia (adapt for Western Australia)

> **Subject:** Automated access to Hansard for the Australasian Council of Auditors-General
>
> Dear Hansard team,
>
> The Australasian Council of Auditors-General (ACAG) is piloting **Hansard Watch**. It is an internal tool that helps Australia's audit offices follow what Parliament says about their Auditors-General, tabled audit reports and forward audit programs. It reads each sitting day's Hansard once and gives audit office staff short briefs with verbatim quotes. Each quote is attributed and links to the official record, in line with the Parliament's conditions for using extracts.
>
> [SA:] We'd like to use the published Hansard API (`hansardsearch.parliament.sa.gov.au/docs/api`) responsibly, but our client is refused by the site's protection.
> [WA:] Our client is challenged by the website's firewall when it reads the Daily Hansard.
>
> Could you allowlist User-Agent `ACAG-HansardWatch/0.1 (+mailto:{CONTACT_EMAIL})` and source IPs `{EGRESS_IPS}`, or tell us the preferred way to receive the daily Hansard XML or PDF?
>
> What our client does:
> - It requests only new or changed sitting days, and uses conditional requests.
> - It waits at least 2 seconds between requests and obeys robots.txt.
> - It runs once a day at most.
>
> Contact: {CONTACT_NAME}, {CONTACT_EMAIL}.
>
> Kind regards,

---

## D. Territory Stories (Library & Archives NT)

> **Subject:** Automated access to Draft Daily Hansard PDFs in Territory Stories for the Australasian Council of Auditors-General
>
> Dear Territory Stories team,
>
> The Australasian Council of Auditors-General (ACAG) is piloting **Hansard Watch**. It is an internal tool that helps audit offices, including the NT Auditor-General's Office, follow what Parliament says about their work.
>
> The Legislative Assembly's Draft Daily Hansard and Debates and Questions are published in Territory Stories under CC BY 4.0. We read their metadata through `/api/full_record`, as your robots.txt allows. The robots.txt also disallows `*.pdf`, so we have not downloaded the documents themselves.
>
> Could you confirm whether we may download one Hansard PDF per sitting day (about 2–4 per sitting week)? Or tell us the preferred way to receive the text: the PDF link in `full_record`, an OAI-PMH feed, or a text endpoint.
>
> What our client does:
> - It uses User-Agent `ACAG-HansardWatch/0.1 (+mailto:{CONTACT_EMAIL})`.
> - It waits at least 2 seconds between requests and uses conditional requests.
> - It attributes every quote to the Legislative Assembly of the Northern Territory and links to the Territory Stories record.
>
> Contact: {CONTACT_NAME}, {CONTACT_EMAIL}.
>
> Kind regards,

## E. Audit offices (adapt per office)

> **Subject:** Automated access to your published reports and audit program for the Australasian Council of Auditors-General
>
> Dear {office} web team,
>
> As part of ACAG's **Hansard Watch** pilot, an internal tool for Australia's nine audit offices, we read each office's published list of tabled reports and its forward audit program about once a week. We use them to link parliamentary debate to the right report.
>
> Our client is refused by your website's bot protection, even for robots.txt. Could you allowlist User-Agent `ACAG-HansardWatch/0.1 (+mailto:{CONTACT_EMAIL})` and source IPs `{EGRESS_IPS}`, or point us to a feed (RSS, sitemap or API) for new reports and program updates?
>
> We obey robots.txt, wait at least 2 seconds between requests, and use conditional requests, so an unchanged page costs almost nothing.
>
> Contact: {CONTACT_NAME}, {CONTACT_EMAIL}.
>
> Kind regards,

## Other sources: terms to confirm

These sources are not blocked, but their reuse terms could not be confirmed. Raise them only if the terms pages, checked with `make recon`, are unclear:

- **QLD:** the Clerk has previously declined "authorised publisher" status to third parties (Parliament of Queensland Act 2001 s51(4)(g)). Our use is internal monitoring with short quotes and links. Check the copyright page; if unclear, write to the Clerk.
- **ACT:** the reuse policy is at `parliament.act.gov.au/function/footer/reuse-policy`. It was unreachable on 31 Oct (connection reset); read it before the ACT connector goes live.
- **TAS:** no terms page found yet.
