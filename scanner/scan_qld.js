// Queensland: downloads the Record of Proceedings PDF for every sitting date and scans the full text.
const path = require('path');
const { WINDOW, CACHE, get, pool, save, download, pdfPages, clean, countMentions } = require('./common');
const { parseContents, alignContents, extract, nicerHeading, norm } = require('./pdfscan');

const SITE = 'https://www.parliament.qld.gov.au';
const CAL = `${SITE}/qpsapi/Calendar/GetCalendarEvents?settingId=da0be5ea-cc4e-4256-ba8c-408e9c047a6f`;
const STAGES = /^(introduction|first reading|second reading|third reading|consideration in detail|cognate debate|message from governor|resumed from|referral to|declared urgent|report|long title|statement of compatibility|explanatory notes|tabled paper|motion|amendment|division|question put|withdrawal)/i;

async function sittingDates() {
  const out = new Set();
  for (const y of [2025, 2026]) {
    const j = JSON.parse(await get(`${CAL}&year=${y}`, { headers: { Accept: 'application/json' } }));
    for (const item of j.Items || []) for (const e of item.Events || []) {
      if (e.EventType === 'House Sitting Date') {
        const d = e.StartDate.slice(0, 10);
        if (d >= WINDOW.from && d <= WINDOW.to) out.add(d);
      }
    }
  }
  return [...out].sort();
}

async function pdfUrlFor(date) {
  const html = await get(`${SITE}/Work-of-the-Assembly/Sitting-Dates/Dates/Sitting-Date?date=${date}`).catch(() => null);
  const stamp = date.replace(/-/g, '_');
  const found = html && (html.match(new RegExp(`https?://documents\\.parliament\\.qld\\.gov\\.au/events/han/\\d{4}/${stamp}[^"'\\s<]*\\.pdf`, 'i')) || [])[0];
  if (found) return found;
  for (const kind of ['WEEKLY', 'DAILY']) {
    for (const ext of ['pdf', 'PDF']) {
      const u = `https://documents.parliament.qld.gov.au/events/han/${date.slice(0, 4)}/${stamp}_${kind}.${ext}`;
      const r = await fetch(u, { method: 'HEAD' }).catch(() => null);
      if (r && r.ok) return u;
    }
  }
  return null;
}

function scanDay(pages, date) {
  const lines = [];
  const linePage = [];
  const printedOf = [];
  const headLines = new Set(); // Running heads aren't debate text, so they're neither read nor counted.
  const pageHeads = []; // The debate named in each page's running head.
  pages.forEach((p, n) => {
    const ls = p.split('\n');
    const base = lines.length;
    // Running head: date, debate name and page number, in either order, at the top of the page.
    const top = ls.map((t, i) => ({ t: t.trim(), i })).filter((x) => x.t).slice(0, 6);
    const dateLine = top.find((x) => /^\d{1,2} \w{3} \d{4}$/.test(x.t));
    const numLine = top.find((x) => /^\d{1,5}$/.test(x.t));
    printedOf[n] = numLine ? Number(numLine.t) : null;
    if (dateLine && numLine) {
      const end = Math.max(dateLine.i, numLine.i);
      const inHead = top.filter((x) => x.i <= end);
      inHead.forEach((x) => headLines.add(base + x.i));
      const title = inHead.filter((x) => x !== dateLine && x !== numLine).map((x) => x.t).join(' ');
      if (title) pageHeads.push({ line: base, title });
    }
    for (const l of ls) {
      lines.push(l);
      linePage.push(n + 1);
    }
  });
  const firstLineOf = {};
  linePage.forEach((pg, i) => {
    const printed = printedOf[pg - 1];
    if (printed != null && firstLineOf[printed] == null) firstLineOf[printed] = i;
  });

  // The contents run from the first "Table of Contents" page; the transcript starts where dot leaders stop.
  let firstDots = -1;
  let lastDots = 0;
  lines.forEach((l, i) => {
    if (i < 700 && /\.{4,}\s*\d{1,5}\s*$/.test(l)) {
      if (firstDots < 0) firstDots = i;
      lastDots = i;
    }
  });
  const entries = [];
  let main = null;
  const block = firstDots < 0 ? '' : lines.slice(firstDots, lastDots + 1).filter((l) => {
    const t = l.trim();
    return t && !/^Table of Contents/.test(t) && t !== 'Subject' && t !== 'Page' && !/\b(SPEAKER|CLERK OF THE PARLIAMENT|CHIEF REPORTER)$/.test(t);
  }).join(' ');
  for (const e of parseContents(block)) {
    if (/^Tabled paper:/.test(e.title)) continue;
    const shouting = !/[a-z]/.test(e.title);
    if (shouting) main = e.title;
    entries.push({ ...e, main: shouting ? e.title : main, shouting });
  }
  const skip = (l) => {
    const t = l.trim();
    return /^\d{1,5}$/.test(t) || /^\d{1,2} \w{3} \d{4}$/.test(t) || /^Table of Contents/.test(t) || /\.{4,}\s*\d{1,5}\s*$/.test(t);
  };
  const aligned = alignContents(lines, entries, (p) => firstLineOf[p], lastDots + 1);
  // A page's running head corrects the topic when a heading was missing from the contents.
  const lastAlignedBefore = (line) => {
    let m = null;
    for (const k of aligned) {
      if (k.line <= line) m = k;
      else break;
    }
    return m;
  };
  const marks = [...aligned];
  for (const h of pageHeads) {
    if (h.line <= lastDots) continue;
    const cur = lastAlignedBefore(h.line);
    const same = cur && [cur.entry.title, cur.entry.main].some((t) => t && norm(t) === norm(h.title));
    if (!same) marks.push({ line: h.line, entry: { title: h.title, shouting: true, fromHead: true } });
  }
  marks.sort((a, b) => a.line - b.line);
  const topicAt = (i) => {
    let m = null;
    for (const k of marks) {
      if (k.line <= i) m = k;
      else break;
    }
    if (!m) return { title: 'Proceedings', proceeding: null };
    const e = m.entry;
    if (e.shouting) return { title: nicerHeading(e.title), proceeding: null };
    if (STAGES.test(e.title)) return { title: nicerHeading(e.main || e.title), proceeding: e.title };
    return { title: e.title, proceeding: e.main ? nicerHeading(e.main) : null };
  };
  const recs = extract(lines, linePage, { skipLine: (l, i) => i <= lastDots || headLines.has(i) || skip(l), topicAt, headingLines: new Set(aligned.filter((m) => m.exact).map((m) => m.line)), printedAt: (i) => printedOf[linePage[i] - 1] });
  return { recs, total: countMentions(clean(lines.filter((l, i) => i > lastDots && !headLines.has(i) && !skip(l)).join(' '))), marks: marks.length, entries: entries.length };
}

(async () => {
  const dates = await sittingDates();
  console.log(`${dates.length} Queensland sitting dates in window`);
  const missing = [];
  const all = [];
  const tally = [];
  await pool(dates, 3, async (date) => {
    const url = await pdfUrlFor(date);
    if (!url) { missing.push(date); return; }
    const file = await download(url, path.join(CACHE, 'qld', `${date}.pdf`));
    if (!file) { missing.push(date); return; }
    const { recs, total, marks, entries } = scanDay(pdfPages(file), date);
    tally.push({ date, url, total, records: recs.reduce((n, r) => n + r.mentions, 0), marks, entries });
    for (const r of recs) {
      all.push({
        jur: 'QLD',
        date,
        chamber: 'Legislative Assembly',
        ...r,
        // The tabled papers list is the Clerk's record, not something the last speaker said.
        ...(/^Tabled Papers$/i.test(r.title) ? { speaker: null, electorate: null, party: null } : {}),
        url: `${url}#page=${r.page}`,
        pdf: url,
        sourceLabel: `Record of Proceedings${r.printed ? `, p ${r.printed}` : `, PDF page ${r.page}`}`,
        status: /DAILY/i.test(url) ? 'proof' : 'final',
      });
    }
  });
  all.sort((a, b) => (a.date < b.date ? 1 : -1));
  save('qld.json', all);
  save('qld_tally.json', { missing, tally: tally.sort((a, b) => (a.date < b.date ? -1 : 1)) });
  console.log(`QLD: ${all.length} contributions, ${all.reduce((n, r) => n + r.mentions, 0)} mentions; missing PDFs: ${missing.length ? missing.join(',') : 'none'}`);
})().catch((e) => { console.error('QLD FAILED', e); process.exit(1); });
