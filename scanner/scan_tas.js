// Tasmania: the Parliament's search lists every sitting day; each day's transcript is a DOCX with real headings.
const fs = require('fs');
const path = require('path');
const { WINDOW, CACHE, UA, get, pool, save, clean, excerpt, countMentions, hasMention, decodeEntities } = require('./common');
const { paragraphs } = require('./docx');

const BASE = 'https://search.parliament.tas.gov.au';
const MONTHS = { January: '01', February: '02', March: '03', April: '04', May: '05', June: '06', July: '07', August: '08', September: '09', October: '10', November: '11', December: '12' };
const STAGE = /^(first reading|second reading|third reading|in committee|committee stage|recommittal|bill agreed|report$|resumed\b|motion$)/i;
// Headings that interrupt a debate without starting a new topic.
const INTERRUPTION = /^(supplementary question|recognition of visitors|visitors|in attendance|continued|time extended|suspension of sitting|sitting suspended|statement by speaker|statement by the speaker|statement by president|statement by the president)/i;
const MONTH_NAMES = Object.keys(MONTHS);

const isoFrom = (s) => {
  const m = String(s).match(/(\d{1,2}) (\w+) (\d{4})/);
  return m && MONTHS[m[2]] ? `${m[3]}-${MONTHS[m[2]]}-${m[1].padStart(2, '0')}` : null;
};

// The Parliament's "sitting days" list has stale dates, so transcripts are listed by searching each month's name.
// Every transcript carries its date on the title page, so its month search always finds it.
function monthsInWindow() {
  const out = [];
  let [y, m] = WINDOW.from.split('-').map(Number);
  const [ey, em] = WINDOW.to.split('-').map(Number);
  while (y < ey || (y === ey && m <= em)) {
    out.push(`${MONTH_NAMES[m - 1]} ${y}`);
    if (++m > 12) { m = 1; y++; }
  }
  return out;
}

async function listDocs() {
  const docs = new Map();
  for (const month of monthsInWindow()) {
    const res = await fetch(`${BASE}/Search/search/search?IW_FIELD_ADVANCE_PHRASE=${encodeURIComponent(month)}&IW_DATABASE=Hansard&IW_SORT=-9`, { headers: { 'User-Agent': UA }, signal: AbortSignal.timeout(170000) });
    const cookie = res.headers.getSetCookie().map((c) => c.split(';')[0]).join('; ');
    const html = await res.text();
    const collect = (h) => {
      for (const m of h.matchAll(/href="([^"]*\/isysquery\/[^"]*\/doc\/[^"]+\.docx?)"/gi)) {
        const href = decodeEntities(m[1]);
        const name = decodeURIComponent(href.split('/').pop());
        const date = isoFrom(name);
        if (date && date >= WINDOW.from && date <= WINDOW.to && !docs.has(name)) docs.set(name, { href, name, cookie, date });
      }
    };
    collect(html);
    const pages = [...new Set([...html.matchAll(/href="([^"]*\/isysquery\/[^"]*\/\d+-\d+\/list\/)"/g)].map((m) => m[1]))];
    for (const p of pages) {
      const r = await fetch(BASE + p, { headers: { 'User-Agent': UA, Cookie: cookie }, signal: AbortSignal.timeout(170000) });
      collect(await r.text());
    }
    console.log(`  ${month}: ${pages.length + 1} result pages, ${docs.size} transcripts so far`);
  }
  return pickBest(docs.values());
}

// The same sitting can be held under several names ("HA ...", "House of Assembly ...", "... Draft - Full Text").
// Keep one per date, house and committee: final before draft, then the short HA/LC name.
function pickBest(docs) {
  const all = [...docs];
  const best = new Map();
  const score = (d) => (/draft/i.test(d.name) ? 0 : 4) + (/^(HA|LC)\b/i.test(d.name) ? 2 : 0) + (/Tuessday/.test(d.name) ? -1 : 0);
  for (const d of all) {
    const house = /^(LC|Legislative Council)\b/i.test(d.name) ? 'LC' : 'HA';
    const committee = (d.name.match(/Estimates Committee [A-Z]/i) || [''])[0].toUpperCase();
    const key = `${d.date}|${house}|${committee}`;
    if (!best.has(key) || score(d) > score(best.get(key))) best.set(key, d);
  }
  console.log(`${all.length} transcript files, ${best.size} after removing duplicates and drafts`);
  return [...best.values()].sort((a, b) => (a.date < b.date ? -1 : 1));
}

// --cached scans what's already downloaded, without touching the slow search.
function cachedDocs() {
  const dir = path.join(CACHE, 'tas');
  const out = [];
  for (const name of fs.readdirSync(dir)) {
    const date = isoFrom(name);
    if (date && date >= WINDOW.from && date <= WINDOW.to) out.push({ name, date });
  }
  return pickBest(out);
}

const dayLink = (phrase) => `${BASE}/Search/search/search?IW_FIELD_ADVANCE_PHRASE=${encodeURIComponent(phrase)}&IW_DATABASE=Hansard&IW_SORT=-9`;

async function fetchDoc(doc) {
  const file = path.join(CACHE, 'tas', doc.name.replace(/[^\w. -]/g, '_'));
  if (fs.existsSync(file) && fs.statSync(file).size > 0) return fs.readFileSync(file);
  const res = await fetch(BASE + doc.href.replace(/ /g, '%20'), { headers: { 'User-Agent': UA, Cookie: doc.cookie }, signal: AbortSignal.timeout(180000) });
  if (!res.ok) throw new Error(`HTTP ${res.status} ${doc.name}`);
  const buf = Buffer.from(await res.arrayBuffer());
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, buf);
  return buf;
}

function scanDoc(buf) {
  const ps = paragraphs(buf);
  const groups = new Map();
  let main = null;
  let sub = null;
  let speaker = null;
  let skipSub = false;
  let total = 0;
  ps.forEach((p, i) => {
    if (/^TOC/i.test(p.style)) return;
    // A Speaker's statement or visitors' welcome interrupts a debate, which then carries on with no new heading.
    if (/^Heading1/i.test(p.style) && INTERRUPTION.test(p.text)) { skipSub = true; }
    else if (/^Heading1/i.test(p.style)) { main = p.text; sub = null; speaker = null; skipSub = false; }
    else if (/^Heading2/i.test(p.style)) {
      if (skipSub) skipSub = false;
      else if (!isoFrom(p.text) && !INTERRUPTION.test(p.text)) sub = p.text;
    }
    // Question headings lose the space between bold runs ("Mr WILLIEquestion to PREMIER"), so compare without spaces.
    else if (p.bold && /^(Mr|Ms|Mrs|Miss|Dr|Hon|Madam|The|CHAIR|DEPUTY|Sir)\b/i.test(p.bold) && p.text.replace(/\s+/g, '').startsWith(p.bold.replace(/\s+/g, ''))) speaker = clean(p.bold).replace(/[:\-\s]+$/, '').replace(/\s*question to\b.*$/i, '');
    if (!hasMention(p.text)) return;
    const n = countMentions(p.text);
    total += n;
    const isHeading = /^Heading/i.test(p.style);
    const key = `${main}|${sub}|${speaker}`;
    if (!groups.has(key)) {
      const opener = ps.slice(Math.max(0, i - 60), i + 1).reverse().find((q) => speaker && q.text.startsWith(speaker) && /\(/.test(q.text.slice(speaker.length, speaker.length + 3)));
      const paren = opener ? (opener.text.slice(speaker.length).match(/\(([^)]*)\)/) || [])[1] : null;
      groups.set(key, { main, sub, speaker, electorate: paren ? clean(paren.split(/\s[-–—]\s/)[0]) : null, mentions: 0, parts: [] });
    }
    const g = groups.get(key);
    g.mentions += n;
    if (!isHeading && ps[i - 1] && !/^Heading|^TOC/i.test(ps[i - 1].style)) g.parts.push(ps[i - 1].text);
    g.parts.push(p.text);
    if (ps[i + 1] && !/^Heading/i.test(ps[i + 1].style)) g.parts.push(ps[i + 1].text);
  });
  const shouting = (s) => { const l = String(s).replace(/[^A-Za-z]/g, ''); return l.length > 0 && l.replace(/[^A-Z]/g, '').length / l.length > 0.7; };
  const nice = (s) => (s && shouting(s) ? s.toLowerCase().replace(/(^|[\s(\-])([a-z])/g, (_, a, b) => a + b.toUpperCase()).replace(/\b(And|Of|The|In|On|For|To)\b/g, (w, _o, idx) => (idx === 0 ? w : w.toLowerCase())) : s);
  const recs = [...groups.values()].map((g) => {
    const stage = g.sub && STAGE.test(g.sub);
    const title = g.sub && !stage ? g.sub : nice(g.main) || 'Proceedings';
    const proceeding = g.sub ? (stage ? g.sub : nice(g.main)) : null;
    const seen = new Set();
    const text = clean(g.parts.filter((x) => !seen.has(x) && seen.add(x)).join(' '));
    return { title, proceeding, speaker: g.speaker, electorate: g.electorate, mentions: g.mentions, passage: excerpt(text) };
  });
  return { recs, total, paragraphs: ps.length };
}

(async () => {
  const docs = process.argv.includes('--cached') ? cachedDocs() : await listDocs();
  console.log(`${docs.length} Tasmanian transcripts in window`);
  const all = [];
  const tally = [];
  const failed = [];
  await pool(docs, 2, async (doc) => {
    try {
      const buf = await fetchDoc(doc);
      // Parliament's search can hold a transcript under another day's file name, which would count that debate twice.
      const titleDate = paragraphs(buf).slice(0, 12).map((p) => isoFrom(p.text)).find(Boolean);
      // A title date outside the window is a typo on the title page (one reads 2626), not another sitting.
      if (titleDate && titleDate !== doc.date && titleDate >= WINDOW.from && titleDate <= WINDOW.to) {
        failed.push(`${doc.name}: title page says ${titleDate}, so it was skipped`);
        return;
      }
      const { recs, total, paragraphs: count } = scanDoc(buf);
      const base = doc.name.replace(/\.docx?$/i, '');
      const house = /^(LC|Legislative Council)\b/i.test(base) ? 'Legislative Council' : 'House of Assembly';
      const committee = (base.match(/Estimates Committee [A-Z]/i) || [])[0];
      const chamber = committee ? `${house} ${committee}` : house;
      const phrase = (base.match(/(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*\d{1,2} \w+ \d{4}/) || [base])[0].trim();
      tally.push({ date: doc.date, name: doc.name, chamber, total, records: recs.reduce((n, r) => n + r.mentions, 0), paragraphs: count });
      for (const r of recs) {
        all.push({
          jur: 'TAS',
          date: doc.date,
          chamber,
          ...r,
          title: r.title === 'Proceedings' && committee ? `${committee} hearing` : r.title,
          url: dayLink(phrase),
          sourceLabel: `${base} (search result, then Download Document)`,
          docName: doc.name,
        });
      }
    } catch (e) {
      failed.push(`${doc.name}: ${e.message}`);
    }
  });
  all.sort((a, b) => (a.date < b.date ? 1 : -1));
  save('tas.json', all);
  save('tas_tally.json', { failed, tally: tally.sort((a, b) => (a.date < b.date ? -1 : 1)) });
  console.log(`TAS: ${tally.length} transcripts, ${all.length} contributions, ${all.reduce((n, r) => n + r.mentions, 0)} mentions; failed: ${failed.length}`);
})().catch((e) => { console.error('TAS FAILED', e); process.exit(1); });
