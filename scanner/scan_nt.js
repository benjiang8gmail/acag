// Northern Territory: Territory Stories holds each sitting day as a PDF; every document in the window is scanned in full.
const path = require('path');
const { WINDOW, CACHE, get, pool, save, download, pdfPages, clean, countMentions } = require('./common');
const { parseSpeaker, extract, nicerHeading } = require('./pdfscan');

const TS = 'https://territorystories.nt.gov.au';
const S3 = 'https://ntdl-territorystories.s3.amazonaws.com/';
const COLLECTION = 'debates and questions for 15th assembly 2024 -';

async function listDocs() {
  const body = JSON.stringify({ search: { collection: [COLLECTION], ntdl_type: ['debate'], source: ['parliament nt'] }, sort: 'date_new' });
  const j = JSON.parse(await get(`${TS}/api/search`, { method: 'POST', body, headers: { 'Content-Type': 'application/json' } }));
  return j.results
    .map((r) => ({ date: r.start_date.slice(0, 10), title: r.title, handle: r.handle.replace('https://hdl.handle.net/', ''), id: r.id }))
    .filter((r) => r.date >= WINDOW.from && r.date <= WINDOW.to);
}

// NT headings run together on one line, e.g. "MINISTERIAL REPORT Child Protection in the Northern Territory".
const HEADING = /^[A-Z][A-Z'’\-–,&()\/ 0-9]{4,}(?:\s|$)/;
const SERIAL = /^\(?Serial \d+\)?$/i;
const STAGE = /^(consideration in detail|in committee|second reading|first reading|third reading|introduction|continued from|resumed)/i;
function headingOf(line, nextLine) {
  const t = line.trim();
  if (!t || t.length > 200 || parseSpeaker(t) || SERIAL.test(t)) return null;
  if (/[.;:?!,…]$/.test(t) || /:\s/.test(t)) return null;
  const caps = t.match(HEADING);
  if (caps && (caps[0].match(/[A-Z]{3,}/g) || []).length >= 1 && !/^(Mr|Ms|Mrs|Dr|Madam)\b/.test(t)) {
    const main = caps[0].trim().replace(/\s*\(?SERIAL \d+\)?$/i, '');
    const rest = t.slice(caps[0].length).trim().replace(/\(?Serial \d+\)?/i, '').trim();
    return { main: nicerHeading(main), sub: rest || null };
  }
  // Short title-case line right before a speaker opens is a sub-heading.
  if (t.length < 130 && /^[A-Z]/.test(t) && nextLine && parseSpeaker(nextLine.trim())) return { main: null, sub: t };
  return null;
}

function scanDay(pages) {
  const lines = [];
  const linePage = [];
  pages.forEach((p, n) => {
    for (const l of p.split('\n')) {
      // A heading and a speaker can share a line: "ADJOURNMENT Mr EDGINGTON (Leader of Government Business): ...".
      const both = l.trim().match(/^([A-Z][A-Z ,'\u2019\-\u2013&()\/0-9]{3,}?)\s+((?:Mr|Ms|Mrs|Dr|Madam|Hon)\s.*|[A-Z]\s[A-Z]{2,}\s*\(.*)$/);
      if (both && parseSpeaker(both[2])) {
        lines.push(both[1], both[2]);
        linePage.push(n + 1, n + 1);
        continue;
      }
      lines.push(l);
      linePage.push(n + 1);
    }
  });
  // The cover and contents pages come before "took the Chair"; they aren't part of the debate.
  const bodyStart = Math.max(0, lines.findIndex((l) => /took the Chair/i.test(l)));
  const skipText = (l) => {
    const t = l.trim();
    return /^\d{1,4}$/.test(t) || /^(Daily Hansard|Debates and Questions)\s*[–-]/.test(t) || /^(Draft Daily Hansard|Legislative Assembly|of the Northern Territory)$/.test(t) || /uncorrected proof/i.test(t) || /\.{4,}\s*\d*\s*$/.test(t);
  };
  const skip = (l, i) => (i != null && i < bodyStart) || skipText(l);
  const tops = [];
  const headingLines = new Set();
  let main = null;
  let sub = null;
  for (let i = bodyStart; i < lines.length; i++) {
    if (skip(lines[i], i)) continue;
    let j = i + 1;
    while (j < lines.length && (!lines[j].trim() || skip(lines[j], j))) j++;
    const h = headingOf(lines[i], lines[j]);
    if (h) {
      headingLines.add(i);
      if (h.main) {
        main = h.main;
        sub = h.sub;
      } else {
        sub = h.sub;
      }
    }
    tops[i] = { main, sub };
  }
  const topicAt = (i) => {
    const t = tops[i] || { main, sub };
    if (t.sub && STAGE.test(t.sub)) return { title: t.main || t.sub, proceeding: t.sub };
    if (t.sub) return { title: t.sub, proceeding: t.main };
    return { title: t.main || 'Proceedings', proceeding: null };
  };
  const printedAt = (i) => {
    const pg = pages[linePage[i] - 1] || '';
    const ls = pg.split('\n').map((x) => x.trim()).filter(Boolean);
    const last = ls[ls.length - 1];
    return /^\d{1,4}$/.test(last || '') ? Number(last) : null;
  };
  const recs = extract(lines, linePage, { skipLine: skip, topicAt, printedAt, headingLines });
  return { recs, total: countMentions(clean(lines.filter((l, i) => !skip(l, i)).join(' '))) };
}

(async () => {
  const docs = await listDocs();
  console.log(`${docs.length} NT sitting-day documents in window`);
  const all = [];
  const tally = [];
  const missing = [];
  await pool(docs, 3, async (d) => {
    const full = JSON.parse(await get(`${TS}/api/full_record?content=true&handle=${encodeURIComponent(d.handle)}`));
    const rec = full.results[0];
    const url = S3 + rec.pdfpath.split('/').map(encodeURIComponent).join('/');
    const file = await download(url, path.join(CACHE, 'nt', `${d.date}.pdf`));
    if (!file) { missing.push(d.date); return; }
    const { recs, total } = scanDay(pdfPages(file));
    tally.push({ date: d.date, title: d.title, handle: d.handle, total, records: recs.reduce((n, r) => n + r.mentions, 0), pages: (rec.pages || []).length });
    const base = (rec.link || '').replace(/\/\d+\.pdf$/, '');
    for (const r of recs) {
      all.push({
        jur: 'NT',
        date: d.date,
        chamber: 'Legislative Assembly',
        ...r,
        url: `${TS}/${d.handle}/0/${r.page - 1}`,
        pdf: base ? `${base}/${r.page - 1}.pdf` : url,
        sourceLabel: `${/draft/i.test(d.title) ? 'Draft Daily Hansard' : 'Debates and Questions'}${r.printed ? `, p ${r.printed}` : `, PDF page ${r.page}`}`,
        status: /draft/i.test(d.title) ? 'proof' : 'final',
      });
    }
  });
  all.sort((a, b) => (a.date < b.date ? 1 : -1));
  save('nt.json', all);
  save('nt_tally.json', { missing, tally: tally.sort((a, b) => (a.date < b.date ? -1 : 1)) });
  console.log(`NT: ${all.length} contributions, ${all.reduce((n, r) => n + r.mentions, 0)} mentions; missing: ${missing.join(',') || 'none'}`);
})().catch((e) => { console.error('NT FAILED', e); process.exit(1); });
