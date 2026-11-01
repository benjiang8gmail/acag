# Hansard Watch: standalone page

`hansard-watch.html` is the Claude Design prototype rebuilt as one self-contained file (page, styles, script and data, no network requests) running on **real data**. Open it in any browser, or host it anywhere. Every view has its own link (`#view=…&jur=…`), so shared links open the same view.

## What's in it (snapshot of 1 Nov 2026)

| Source | What it gives |
|---|---|
| `data/scan/` | The Hansard Watch store after the Phase 0/2 scans: 128 speeches naming an Auditor-General in the federal Parliament, NSW, Queensland and the ACT (7 Sep – 29 Oct 2026), speeches read per sitting day, speaking turns by side, each parliament's status, and the last scan run. |
| `data/cowork/vago-scan.json` | The Cowork task "Victorian Hansard audit scan": 39 checked VAGO mentions (3 Feb – 24 Sep 2026), 27 tabled reports, the 20-topic gap longlist, 28 themes with coverage, blind spots, limitations and corrections. |
| `config/*.yaml` | Offices, Auditors-General, programs, governments and sector terms from the Phase 0 recon. |

Rules the page applies, all visible on it: side comes from party and the government of the day; sectors are a keyword match on the debate title and text; Queensland report names are found by the report number in the text. Victorian notes and assessments were written with AI assistance and are labelled. Nothing is invented: where data doesn't exist yet (sentiment outside Victoria, gaps for other offices, SA/WA/Tasmania Hansard), the page says so.

## Rebuild

```sh
python3 standalone/build.py   # needs PyYAML; writes standalone/hansard-watch.html
```

Edit the page in `app.html` (`__HW_DATA__` is where the data goes) and the data merge in `build.py`.
