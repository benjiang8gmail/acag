# Refreshing the Auditor-General Hansard data

The dashboard (`../index.html`) is a single file with its data built in, and `../hansards.html` is a separate version that marks each contribution as attack (red), praise (blue) or neutral (grey). To refresh them, run these from this folder. You need Node 20 or later and `pdftotext` (Poppler).

1. Set the window in `common.js` (`WINDOW`) and, for WA and SA, in `browser_wa_sa.js`.
2. Run the scans that work from a script. Set `HANSARD_CACHE` to a folder for downloaded PDFs.

   ```bash
   node scan_nsw.js
   ```
   ```bash
   node scan_vic.js
   ```
   ```bash
   node scan_qld.js
   ```
   ```bash
   node scan_tas.js
   ```
   ```bash
   node scan_act.js
   ```
   ```bash
   node scan_nt.js
   ```

   If the NSW API answers HTTP 429, stop and wait: it can ask for up to an hour. `rebuild_nsw.js` rebuilds NSW from what's already downloaded, and `scan_tas.js --cached` does the same for Tasmania, whose search can take minutes per page.

3. Run WA and SA in a browser, because those sites refuse scripted requests. Start the receiver, then paste `browser_wa_sa.js` into the browser console on each site's Hansard search page.

   ```bash
   node receiver.js 8767
   ```

4. Combine the results. This writes `../data/mentions.json` and one file per jurisdiction in `../data/to_summarise/`.

   ```bash
   node merge.js
   ```

5. Summarise. For each jurisdiction, write `../data/summaries/<CODE>.json` from its `to_summarise` file, in the format `check_summaries.js` validates. Also write `../data/summaries/national.json` as `{ "national": ["paragraph", ...] }`. These were AI-written. If a re-scan renumbers records, `remap_summaries.js` carries existing summaries across. Afterwards, `check_faithfulness.js` flags summaries that don't match their passage and `verify_links.js` re-checks PDF page references.

   ```bash
   node check_summaries.js VIC
   ```

6. Label sentiment for `hansards.html`, following `SENTIMENT.md`. `sentiment_batch.js` prints the records, labels go in `../data/sentiment/parts/`, and `join_sentiment.js` validates them and writes `../data/sentiment/<CODE>.json`. `../data/sentiment/national.json` gathers jurisdiction themes into the national list, by theme label. These were AI-written too. To measure reliability, have a second reader label the sample from `sentiment_agreement.js print` without seeing the first labels, then run `sentiment_agreement.js compare`.

   ```bash
   node join_sentiment.js VIC
   ```

7. Check `../data/speaker_fixes.json`. It corrects eleven Tasmanian records by record id, for both pages, so remove any entry a re-scan renumbers or makes unnecessary.

8. Build the pages. This writes `../index.html` and, once every jurisdiction has sentiment labels, `../hansards.html`.

   ```bash
   node build.js
   ```

The NT collection name in `scan_nt.js` and the ACT assembly path in `scan_act.js` change when a new Assembly starts.

A review on 1 November 2026 corrected records, summaries and labels directly in `../data/` (see `../index_review.md`). `merge.js` rebuilds `mentions.json` from `../data/raw/`, so a re-scan loses the speaker and debate-title corrections, brings back the heading records it removed, and renumbers records. Re-check those afterwards, and carry labels across with `remap_summaries.js`.
