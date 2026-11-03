// Victoria: every daily Hansard PDF is read in full, because the Parliament's search misses some mentions.
// The search API and debate pages are still used to upgrade links to the exact speech and to add party and electorate.
const fs = require('fs');
const path = require('path');
const { WINDOW, CACHE, get, pool, save, download, pdfPages, stripTags, clean, excerpt, countMentions, hasMention, sleep, decodeEntities } = require('./common');
const { parseContents, alignContents, extract, nicerHeading, norm } = require('./pdfscan');

const BASE = 'https://www.parliament.vic.gov.au';
const MONTHS = { January: '01', February: '02', March: '03', April: '04', May: '05', June: '06', July: '07', August: '08', September: '09', October: '10', November: '11', December: '12' };

function isoFromLong(s) {
  const m = String(s).match(/(\d{1,2}) (\w+) (\d{4})/);
  return m ? `${m[3]}-${MONTHS[m[2]]}-${m[1].padStart(2, '0')}` : null;
}

async function listDays() {
  const days = [];
  for (let page = 1; page < 60; page++) {
    const j = JSON.parse(await get(`${BASE}/api/search/debate?page=${page}&pageSize=50`, { headers: { Accept: 'application/json' } }));
    const rows = j.result.hits || [];
    if (!rows.length) break;
    let older = 0;
    for (const h of rows) {
      const date = isoFromLong(h.title);
      if (!date || date < WINDOW.from) { older++; continue; }
      if (date > WINDOW.to || !h.downloadButton) continue;
      days.push({ date, chamber: h.category, status: /final/i.test(h.status || '') ? 'final' : 'proof', pdf: BASE + h.downloadButton.href, online: h.onlineButton ? BASE + h.onlineButton.href : null });
    }
    if (older === rows.length) break;
    await sleep(200);
  }
  return days;
}

// --- Search phase: finds speech anchors, party and electorate. ---
async function searchAll(term) {
  const hits = [];
  for (let page = 1; page < 200; page++) {
    const url = `${BASE}/api/search/hansard?page=${page}&pageSize=100&sortType=15&term=${encodeURIComponent(term)}`;
    const j = JSON.parse(await get(url, { headers: { Accept: 'application/json' } }));
    const rows = j.result.hits || [];
    if (!rows.length) break;
    let older = 0;
    for (const h of rows) {
      const date = isoFromLong(h.content.context);
      if (!date || date < WINDOW.from) { older++; continue; }
      if (date > WINDOW.to) continue;
      hits.push({ ...h.content, date, theme: h.theme });
    }
    if (older === rows.length) break;
    await sleep(200);
  }
  return hits;
}

function parseDebate(html) {
  const out = [];
  for (const part of html.split(/<div data-js-hook="speech-wrapper" id="/).slice(1)) {
    const id = part.slice(0, part.indexOf('"'));
    const end = part.search(/<div data-js-hook="|<\/main>|<footer/);
    const body = end > 0 ? part.slice(0, end) : part;
    out.push({ id, text: stripTags(body.slice(body.indexOf('>') + 1)) });
  }
  return out;
}

async function speechIndex() {
  const hits = [...(await searchAll('"Auditor-General"')), ...(await searchAll('"Auditor General"'))];
  const pages = new Map();
  const members = {};
  for (const h of hits) {
    const m = h.url.match(/hansard-details\/(HANSARD-[\d-]+)/);
    if (!m) continue;
    if (!pages.has(m[1])) pages.set(m[1], { docId: m[1], hit: h, members: {} });
    const anchor = (h.url.split('#')[1] || '').split('X')[0];
    if (anchor) pages.get(m[1]).members[anchor] = { name: h.memberName, electorate: h.memberElectorate, party: h.memberParty };
    if (h.memberName) members[surnameKey(h.memberName)] = { name: h.memberName, electorate: h.memberElectorate, party: h.memberParty };
  }
  const index = [];
  await pool([...pages.values()], 4, async (p) => {
    const html = await get(`${BASE}/parliamentary-activity/hansard/hansard-details/${p.docId}`);
    if (!html) return;
    const h = p.hit;
    for (const s of parseDebate(html)) {
      if (!hasMention(s.text)) continue;
      const member = p.members[s.id.split('X')[0]] || {};
      index.push({
        date: h.date,
        chamber: h.theme === 'lc' ? 'Legislative Council' : 'Legislative Assembly',
        title: stripTags(h.title),
        proceeding: stripTags([h.proceeding, h.subProceeding].filter(Boolean).join(' – ')),
        speaker: member.name || null,
        url: `${BASE}/parliamentary-activity/hansard/hansard-details/${p.docId}#${s.id}`,
        text: s.text,
      });
    }
  });
  console.log(`search found ${pages.size} debate pages, ${index.length} speeches`);
  return { index, members };
}

// --- PDF phase ---
const STAGE = /^(second reading|third reading|introduction and first reading|first reading|introduction|statement of compatibility|committee\b|council[\u2019']s (amendments?|suggestions?)|assembly[\u2019']s (amendments?|suggestions?)|amendments?\b|consideration in detail|referral\b|royal assent|appropriation message|message from)/i;
// "Bev McARTHUR (Western Victoria) (10:48):", "Sarah MANSFIELD:", "The PRESIDENT (09:33):", "The DEPUTY SPEAKER:".
const SPEAKER = /^((?:[A-Z][\w'’\-]*\s+){1,4}[A-Z][a-zA-Z'’\-]*[A-Z]{2,}[A-Z'’\-]*|The\s+[A-Z][A-Z ]+?)\s*((?:\([^()]*(?:\([^()]*\)[^()]*)*\)\s*)*):(?=\s|$)/;
function parseSpeaker(line) {
  const m = line.match(SPEAKER);
  if (!m) return null;
  const paren = (m[2] || '').match(/\(([^()]*)\)/);
  const inner = paren ? clean(paren[1]) : '';
  return { name: clean(m[1]), electorate: inner && !/^\d/.test(inner) ? clean(inner.split(/\s[–—-]\s/)[0]) : null, party: null };
}
function surnameKey(name) {
  const words = clean(name).split(' ');
  return norm(words[words.length - 1]);
}
const properName = (name) => clean(name).split(' ').map((w, i, a) => {
  if (i === a.length - 1 || /^[A-Z]{3,}$/.test(w)) {
    return w.toLowerCase().replace(/(^|[-'’])([a-z])/g, (_, x, y) => x + y.toUpperCase()).replace(/^Mc([a-z])/, (_, c) => 'Mc' + c.toUpperCase());
  }
  return w;
}).join(' ');

function scanDay(pages) {
  const lines = [];
  const linePage = [];
  const printedOf = [];
  pages.forEach((p, n) => {
    const ls = p.split('\n');
    const printed = ls.slice(0, 10).map((x) => x.trim()).find((x) => /^\d{1,5}$/.test(x));
    printedOf[n] = printed ? Number(printed) : null;
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
  const bodyStart = Math.max(0, lines.findIndex((l) => /took the chair/i.test(l)));
  const entries = [];
  let main = null;
  let parent = null;
  let firstDots = -1;
  let lastDots = -1;
  for (let i = 0; i < bodyStart; i++) {
    if (!/\.{3,}\s*\d{1,5}\s*$/.test(lines[i])) continue;
    if (firstDots < 0) firstDots = i;
    lastDots = i;
  }
  const block = firstDots < 0 ? '' : lines.slice(firstDots, lastDots + 1).filter((l) => {
    const t = l.trim();
    return t && t !== 'CONTENTS' && !/^\d{1,5}$/.test(t);
  }).join(' ');
  {
    for (const e of parseContents(block)) {
      const split = e.title.match(/^([A-Z][A-Z ,'’&()\/\-]{2,}?)\s+(?=[A-Z][a-z0-9(])(.+)$/);
      let sub = e.title;
      if (split) { main = split[1]; sub = split[2]; } else if (!/[a-z]/.test(e.title)) { main = e.title; }
      const stage = STAGE.test(sub);
      if (!stage) parent = sub;
      entries.push({ title: stage ? parent || sub : sub, stage: stage ? sub : null, match: sub, main, page: e.page });
    }
  }
  const marks = alignContents(lines, entries, (p) => firstLineOf[p], bodyStart);
  const topicAt = (i) => {
    let m = null;
    for (const k of marks) {
      if (k.line <= i) m = k;
      else break;
    }
    if (!m) return { title: 'Proceedings', proceeding: null };
    const heading = m.entry.main ? nicerHeading(m.entry.main) : null;
    return { title: nicerHeading(m.entry.title), proceeding: m.entry.stage ? [heading, m.entry.stage].filter(Boolean).join(' \u2013 ') : heading };
  };
  const skip = (l, i) => {
    const t = l.trim();
    if (i != null && i < bodyStart) return true;
    return /^\d{1,5}$/.test(t) || /^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) \d{1,2} \w+ \d{4}$/.test(t) || /^Legislative (Assembly|Council)$/.test(t) || (t.length < 90 && t.length > 3 && !/[a-z]/.test(t));
  };
  const recs = extract(lines, linePage, { skipLine: skip, topicAt, headingLines: new Set(marks.filter((m) => m.exact).map((m) => m.line)), printedAt: (i) => printedOf[linePage[i] - 1], parseSpeaker, speakerName: properName });
  return { recs, total: countMentions(clean(lines.filter((l, i) => !skip(l, i)).join(' '))), marks: marks.length, entries: entries.length };
}

(async () => {
  const days = await listDays();
  console.log(`${days.length} Victorian chamber-days in window`);
  // The speech index is slow to build and rarely changes; delete this file to rebuild it.
  const indexFile = path.join(CACHE, 'vic_speech_index.json');
  let built;
  if (fs.existsSync(indexFile)) built = JSON.parse(fs.readFileSync(indexFile, 'utf8'));
  else {
    built = await speechIndex();
    fs.writeFileSync(indexFile, JSON.stringify(built));
  }
  const { index, members } = built;

  const all = [];
  const tally = [];
  const missing = [];
  await pool(days, 3, async (d) => {
    const file = await download(d.pdf, path.join(CACHE, 'vic', `${`${d.date}|${d.chamber}`.replace(/[^\w-]/g, '_')}.pdf`));
    if (!file) { missing.push(`${d.date} ${d.chamber}`); return; }
    const { recs, total, marks, entries } = scanDay(pdfPages(file));
    tally.push({ date: d.date, chamber: d.chamber, pdf: d.pdf, total, records: recs.reduce((n, r) => n + r.mentions, 0), marks, entries });
    for (const r of recs) {
      // Lists of tabled documents are the Clerk's record, not something the last speaker said.
      if (/^(papers|documents)$/i.test(r.title)) { r.speaker = null; r.electorate = null; }
      const key = r.speaker ? surnameKey(r.speaker) : null;
      const same = index.filter((s) => s.date === d.date && s.chamber === d.chamber && (!key || (s.speaker && surnameKey(s.speaker) === key)));
      const anchorText = (r.passage.match(/.{0,30}auditors?[\s-]*generals?.{0,30}/i) || [''])[0].replace(/…/g, '').trim();
      const hit = same.find((s) => norm(s.title) === norm(r.title) && anchorText && norm(s.text).includes(norm(anchorText))) || same.find((s) => anchorText && norm(s.text).includes(norm(anchorText))) || same.find((s) => norm(s.title) === norm(r.title));
      const m = key ? members[key] : null;
      all.push({
        jur: 'VIC',
        date: d.date,
        chamber: d.chamber,
        ...r,
        title: hit ? hit.title : r.title,
        proceeding: hit ? hit.proceeding : r.proceeding,
        speaker: (m && m.name) || r.speaker,
        electorate: (m && m.electorate) || r.electorate,
        party: (m && m.party) || null,
        url: hit ? hit.url : `${d.pdf}#page=${r.page}`,
        pdf: d.pdf,
        sourceLabel: hit ? `Hansard debate page${r.printed ? `, p ${r.printed}` : ''}` : `Daily Hansard PDF${r.printed ? `, p ${r.printed}` : `, PDF page ${r.page}`}`,
        status: d.status,
      });
    }
  });
  all.sort((a, b) => (a.date < b.date ? 1 : -1));
  save('vic.json', all);
  save('vic_tally.json', { missing, tally: tally.sort((a, b) => (a.date < b.date ? -1 : 1)) });
  const linked = all.filter((r) => /hansard-details/.test(r.url)).length;
  console.log(`VIC: ${all.length} contributions, ${all.reduce((n, r) => n + r.mentions, 0)} mentions (PDF text total ${tally.reduce((n, t) => n + t.total, 0)}); ${linked} linked to the speech; missing PDFs: ${missing.length}`);
})().catch((e) => { console.error('VIC FAILED', e); process.exit(1); });
