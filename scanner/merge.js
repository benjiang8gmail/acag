// Combines the eight jurisdiction scans into one schema: one record per speaker per debate.
const fs = require('fs');
const path = require('path');
const { ROOT, RAW, WINDOW, clean, excerpt, countMentions } = require('./common');

const load = (name) => JSON.parse(fs.readFileSync(path.join(RAW, name), 'utf8'));

// Merged excerpts can overlap and repeat a long block of a speech. Genuine repeats in Hansard are far shorter.
function dropRepeats(text, min = 200) {
  let s = text;
  for (;;) {
    let at = null;
    for (let i = 0; i + min <= s.length && !at; i += 20) {
      const j = s.indexOf(s.slice(i, i + min), i + min);
      if (j >= 0) at = [i, j];
    }
    if (!at) return s.replace(/…(\s*…)+/g, '…');
    let [i, j] = at;
    while (i > 0 && s[i - 1] === s[j - 1]) { i--; j--; }
    let len = 0;
    while (j + len < s.length && i + len < j && s[i + len] === s[j + len]) len++;
    // Cut on word boundaries, so a word the two copies happen to share survives whole.
    while (len > 0 && /\S/.test(s[j - 1])) { j++; len--; }
    while (len > 0 && j + len < s.length && /\S/.test(s[j + len]) && /\S/.test(s[j + len - 1])) len--;
    s = (s.slice(0, j) + s.slice(j + len)).replace(/\s+/g, ' ').trim();
  }
}

function displayName(raw) {
  if (!raw) return null;
  const s = clean(String(raw)).replace(/[:\s]+$/, '').replace(/\s*\(.*$/, '').replace(/\s+(replied|interjected|interjecting)$/i, '');
  const cap = (w) => w.toLowerCase().replace(/(^|[-'\u2019])([a-z])/g, (_, a, b) => a + b.toUpperCase()).replace(/^Mc([a-z])/, (_, c) => 'Mc' + c.toUpperCase()).replace(/^Mac([a-z])(?=[a-z]{3})/, (_, c) => 'Mac' + c.toUpperCase());
  return s
    .split(' ')
    .map((w, i, all) => {
      if (/^(Mc|Mac)[A-Z]{2,}$/.test(w)) return cap(w); // "McGIRR" becomes "McGirr".
      if (/[a-z]/.test(w)) return w; // Already mixed case: "Ron", "de".
      if (/^(DI|DE|DEL|VAN|VON|LE|LA)$/.test(w) && i < all.length - 1) return cap(w); // "DI PASQUA" becomes "Di Pasqua".
      // Initials, but never the last word, which is the surname: "Mr Jason LI" becomes "Mr Jason Li".
      if (/^([A-Z]\.)+[A-Z]?\.?$/.test(w) || (/^[A-Z]{1,2}$/.test(w) && i < all.length - 1 && !/^(MR|MS|DR)$/.test(w))) return w;
      return cap(w);
    })
    .join(' ');
}

function fromBrowser(rows, jur, origin) {
  return rows.map((r) => {
    const heading = String(r.heading || '');
    const parsed = heading.match(/^(.*?)\s*\(([^()]+)\)\s*-\s*\d{1,2}\/\d{1,2}\/\d{4}\s*$/);
    const title = clean(r.subject) || (parsed ? parsed[1] : heading);
    const type = r.type || (parsed ? parsed[2] : null);
    const chamber = r.chamber || (r.tags || []).find((t) => /Assembly|Council|Estimates/.test(t)) || (r.house === 'uh' ? 'Legislative Council' : r.house === 'lh' ? (jur === 'SA' ? 'House of Assembly' : 'Legislative Assembly') : '');
    const raw = r.speakerRaw || '';
    const paren = raw.match(/\(([^()]*)\)/);
    const electorate = paren && !/^\d/.test(paren[1]) ? clean(paren[1]) : null;
    return {
      jur,
      date: r.date,
      chamber,
      title,
      proceeding: [type, r.sub].filter(Boolean).filter((x, i, a) => a.indexOf(x) === i).join(' – '),
      speaker: raw || null,
      electorate,
      mentions: r.mentions,
      passage: excerpt((r.parts || []).join(' ')),
      url: `${origin}${r.path}${r.anchor ? '#' + r.anchor : ''}`,
      sourceLabel: 'Hansard debate page',
    };
  });
}

const sources = [
  ...load('nsw.json'),
  ...load('vic.json'),
  ...load('qld.json'),
  ...fromBrowser(load('wa.json'), 'WA', 'https://www.parliament.wa.gov.au'),
  ...fromBrowser(load('sa.json'), 'SA', 'https://hansardsearch.parliament.sa.gov.au'),
  ...load('tas.json'),
  ...load('act.json'),
  ...load('nt.json'),
];

// Tasmania holds some sittings under several file names; count each sitting once.
const tasBest = new Map();
const tasScore = (n) => (/draft/i.test(n) ? 0 : 4) + (/^(HA|LC)\b/i.test(n) ? 2 : 0);
for (const r of sources) {
  if (r.jur !== 'TAS' || !r.docName) continue;
  const key = `${r.date}|${r.chamber}`;
  if (!tasBest.has(key) || tasScore(r.docName) > tasScore(tasBest.get(key))) tasBest.set(key, r.docName);
}

// WA question records carry the asker in the text: "372. Mr Basil Zempilas to the Minister for Mental Health".
function askerOf(r) {
  if (r.jur !== 'WA' || r.speaker) return r.speaker;
  const m = String(r.passage).match(/\b\d+\.\s+((?:Hon|Mr|Ms|Mrs|Miss|Dr)\s+[^.:;]{2,50}?)\s+to the\s+(?:Minister|Parliamentary Secretary|Premier|Treasurer|Attorney|Deputy Premier|Leader)/);
  return m ? m[1] : null;
}

const merged = new Map();
for (const r of sources) {
  if (r.date < WINDOW.from || r.date > WINDOW.to) continue;
  if (r.jur === 'TAS' && r.docName && tasBest.get(`${r.date}|${r.chamber}`) !== r.docName) continue;
  r.speaker = askerOf(r);
  const speaker = displayName(r.speaker);
  const key = [r.jur, r.date, r.chamber, r.title, speaker || r.url].join('|');
  if (!merged.has(key)) merged.set(key, { ...r, speaker, parts: [r.passage] });
  else {
    const m = merged.get(key);
    m.mentions += r.mentions;
    if (!m.parts.includes(r.passage)) m.parts.push(r.passage);
    if (!m.electorate && r.electorate) m.electorate = r.electorate;
    if (!m.party && r.party) m.party = r.party;
  }
}

// A mention in a heading only counts when nothing under that heading mentions the Auditor-General.
// So a short speakerless record is dropped when the same debate has a speaker's record.
const debateHasSpeaker = new Set();
const debateOf = (r) => [r.jur, r.date, r.chamber, r.title].join('|');
for (const r of merged.values()) if (r.speaker) debateHasSpeaker.add(debateOf(r));
const dropped = [];
for (const [k, r] of merged) {
  if (!r.speaker && r.parts.join(' ').length < 220 && debateHasSpeaker.has(debateOf(r))) {
    dropped.push({ jur: r.jur, date: r.date, title: r.title, mentions: r.mentions, text: r.parts.join(' ') });
    merged.delete(k);
  }
}
fs.writeFileSync(path.join(RAW, 'dropped_headings.json'), JSON.stringify(dropped, null, 1));

const order = ['NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT'];
const counters = {};
const rows = [...merged.values()]
  .sort((a, b) => order.indexOf(a.jur) - order.indexOf(b.jur) || (a.date < b.date ? 1 : a.date > b.date ? -1 : 0) || a.title.localeCompare(b.title))
  .map((r) => {
    counters[r.jur] = (counters[r.jur] || 0) + 1;
    const { parts, passage, docId, anchor, docName, page, printed, ...rest } = r;
    return {
      id: `${r.jur}-${String(counters[r.jur]).padStart(4, '0')}`,
      ...rest,
      title: clean(r.title).replace(/\bAuditor(s?)General/g, 'Auditor$1-General'),
      proceeding: r.proceeding ? clean(r.proceeding) : null,
      // PDF text extraction drops non-breaking hyphens: "AuditorGeneral" is "Auditor-General" in the printed Hansard.
      passage: dropRepeats(clean(parts.join(' ')).replace(/\bAuditor(s?)General/g, 'Auditor$1-General')).slice(0, 2600),
      page: page || null,
      printed: printed || null,
    };
  });

fs.writeFileSync(path.join(ROOT, 'data', 'mentions.json'), JSON.stringify(rows, null, 1));

const dir = path.join(ROOT, 'data', 'to_summarise');
fs.mkdirSync(dir, { recursive: true });
fs.mkdirSync(path.join(ROOT, 'data', 'summaries'), { recursive: true });
for (const j of order) {
  const items = rows
    .filter((r) => r.jur === j)
    .map((r) => ({ id: r.id, date: r.date, chamber: r.chamber, debate: r.title, proceeding: r.proceeding, speaker: r.speaker, mentions: r.mentions, passage: r.passage.slice(0, 1900) }));
  fs.writeFileSync(path.join(dir, `${j}.json`), JSON.stringify(items, null, 1));
  // Debates with three or more speakers also get a one-line gist.
  const groups = new Map();
  for (const it of items) {
    const k = `${it.date}|${it.chamber}|${it.debate}`;
    if (!groups.has(k)) groups.set(k, { date: it.date, chamber: it.chamber, debate: it.debate, ids: [] });
    groups.get(k).ids.push(it.id);
  }
  fs.writeFileSync(path.join(dir, `${j}.debates.json`), JSON.stringify([...groups.values()].filter((g) => g.ids.length >= 3), null, 1));
}

const stat = order.map((j) => {
  const rs = rows.filter((r) => r.jur === j);
  return {
    jur: j,
    contributions: rs.length,
    mentions: rs.reduce((n, r) => n + r.mentions, 0),
    debates: new Set(rs.map((r) => `${r.date}|${r.chamber}|${r.title}`)).size,
    days: new Set(rs.map((r) => r.date)).size,
    noSpeaker: rs.filter((r) => !r.speaker).length,
    passageChars: rs.reduce((n, r) => n + r.passage.length, 0),
  };
});
console.table(stat);
console.log('total', rows.length, 'contributions;', rows.reduce((n, r) => n + r.mentions, 0), 'mentions');
