// ACT: downloads every daily Hansard PDF listed for the window and scans the full text.
const path = require('path');
const { WINDOW, CACHE, get, pool, save, download, pdfPages, clean, countMentions } = require('./common');
const { parseContents, alignContents, extract, nicerHeading } = require('./pdfscan');

const BASE = 'https://www.hansard.act.gov.au/hansard/11th-assembly';

async function listPdfs() {
  const out = [];
  for (const y of ['2025', '2026']) {
    const html = await get(`${BASE}/${y}/debates(PDF).htm`);
    for (const m of html.matchAll(/href="([^"]+\/PDF\/(t?)P(\d{2})(\d{2})(\d{2})[^"\/]*\.pdf)"/gi)) {
      const date = `20${m[3]}-${m[4]}-${m[5]}`;
      if (date >= WINDOW.from && date <= WINDOW.to) out.push({ date, url: m[1].startsWith('http') ? m[1] : `${BASE}/${y}/${m[1].replace(/^\.?\//, '')}`, proof: !!m[2] });
    }
  }
  const seen = new Set();
  return out.filter((x) => !seen.has(x.date) && seen.add(x.date)).sort((a, b) => (a.date < b.date ? -1 : 1));
}

const STANDALONE = /^(Papers|Petitions|Adjournment|Questions without notice|Motion to take note of petitions)$/;
const skipLineText = (l) => {
  const t = l.trim();
  return !t || /^P?\d{3,5}$/.test(t) || t === 'PROOF' || /^(Monday|Tuesday|Wednesday|Thursday|Friday),? \d{1,2} \w+ \d{4}$/.test(t) || /^\d{1,2} \w+ \d{4}$/.test(t) || t === 'Legislative Assembly for the ACT' || /^Contents$/i.test(t);
};

function scanDay(pages) {
  const lines = [];
  const linePage = [];
  const printedOf = [];
  pages.forEach((p, n) => {
    const ls = p.split('\n');
    const printed = ls.map((x) => x.trim()).find((x) => /^P?\d{3,5}$/.test(x));
    printedOf[n] = printed ? Number(printed.replace(/^P/, '')) : null;
    for (const l of ls) {
      lines.push(l);
      linePage.push(n + 1);
    }
  });
  const firstLineOf = {};
  linePage.forEach((pg, i) => {
    const pr = printedOf[pg - 1];
    if (pr != null && firstLineOf[pr] == null) firstLineOf[pr] = i;
  });

  // Contents sit on the first pages, with entries running together on long lines.
  let firstDots = -1;
  let lastDots = 0;
  lines.forEach((l, i) => {
    if (i > 400 || !/\.{3,}\s*P?\d{3,5}/.test(l)) return;
    if (firstDots < 0) firstDots = i;
    lastDots = i;
  });
  const entries = [];
  const block = firstDots < 0 ? '' : lines.slice(firstDots, lastDots + 1).filter((l) => !skipLineText(l)).join(' ');
  let group = null;
  for (const e of parseContents(block)) {
    const colon = e.title.match(/^([A-Z][^:]{2,60}):\s+(.+)$/);
    if (colon) group = colon[1];
    const title = colon ? colon[2] : e.title;
    const kind = (title.match(/\(([^)]+)\)\s*$/) || [])[1] || null;
    entries.push({
      title,
      proceeding: colon ? colon[1] : kind,
      match: title.replace(/\s*\([^)]*\)\s*$/, ''),
      page: e.page,
    });
  }
  const skip = (l) => {
    const t = l.trim();
    return /^P?\d{3,5}$/.test(t) || t === 'PROOF' || /^\d{1,2} \w+ \d{4}$/.test(t) || t === 'Legislative Assembly for the ACT' || /\.{3,}\s*P?\d{3,5}/.test(t);
  };
  const marks = alignContents(lines, entries, (p) => firstLineOf[p], lastDots + 1);
  // Some recurring headings are missing from the contents pages, so a line that is only "Papers" also starts a topic.
  lines.forEach((l, i) => {
    if (i > lastDots && STANDALONE.test(l.trim())) marks.push({ line: i, exact: true, entry: { match: l.trim(), proceeding: null } });
  });
  marks.sort((a, b) => a.line - b.line);
  const topicAt = (i) => {
    let m = null;
    for (const k of marks) {
      if (k.line <= i) m = k;
      else break;
    }
    if (!m) return { title: 'Proceedings', proceeding: null };
    return { title: nicerHeading(m.entry.match), proceeding: m.entry.proceeding };
  };
  const recs = extract(lines, linePage, { skipLine: (l, i) => i <= lastDots || skip(l), topicAt, headingLines: new Set(marks.filter((m) => m.exact).map((m) => m.line)), printedAt: (i) => printedOf[linePage[i] - 1] });
  return { recs, total: countMentions(clean(lines.slice(lastDots + 1).filter((l) => !skip(l)).join(' '))), marks: marks.length, entries: entries.length };
}

(async () => {
  const days = await listPdfs();
  console.log(`${days.length} ACT daily PDFs in window`);
  const all = [];
  const tally = [];
  const missing = [];
  await pool(days, 3, async (d) => {
    const file = await download(d.url, path.join(CACHE, 'act', `${d.date}.pdf`));
    if (!file) { missing.push(d.date); return; }
    const { recs, total, marks, entries } = scanDay(pdfPages(file));
    tally.push({ date: d.date, url: d.url, total, records: recs.reduce((n, r) => n + r.mentions, 0), marks, entries });
    for (const r of recs) {
      all.push({
        jur: 'ACT',
        date: d.date,
        chamber: 'Legislative Assembly',
        ...r,
        url: `${d.url}#page=${r.page}`,
        pdf: d.url,
        sourceLabel: `Daily Hansard${r.printed ? `, p ${r.printed}` : `, PDF page ${r.page}`}`,
        status: d.proof ? 'proof' : 'final',
      });
    }
  });
  all.sort((a, b) => (a.date < b.date ? 1 : -1));
  save('act.json', all);
  save('act_tally.json', { missing, tally: tally.sort((a, b) => (a.date < b.date ? -1 : 1)) });
  console.log(`ACT: ${all.length} contributions, ${all.reduce((n, r) => n + r.mentions, 0)} mentions; missing: ${missing.join(',') || 'none'}`);
})().catch((e) => { console.error('ACT FAILED', e); process.exit(1); });
