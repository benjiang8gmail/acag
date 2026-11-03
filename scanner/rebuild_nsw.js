// NSW: rebuilds data/raw/nsw.json from already-downloaded fragments and daily PDFs, with no API calls.
// Use it when the Parliament's API has asked you to slow down (HTTP 429). scan_nsw.js must have run once to fill the cache.
const fs = require('fs');
const path = require('path');
const { RAW, CACHE, WINDOW, pdfPages, stripTags, clean, excerpt, countMentions, hasMention, decodeEntities } = require('./common');

const SITE = 'https://www.parliament.nsw.gov.au/parliamentary-business/hansard/hansard-full-details';

// Joins adjacent speaker spans, because a name can be split across them: <span>Mr JASO</span><span>N LI</span>.
function speakerSpans(raw) {
  const spans = [...raw.matchAll(/<span class="(?:Member|Office)[^"]*"[^>]*>([\s\S]*?)<\/span>/g)];
  if (!spans.length) return null;
  let text = '';
  let end = spans[0].index;
  for (const m of spans) {
    if (raw.slice(end, m.index).replace(/\s+/g, '') !== '') break;
    text += decodeEntities(m[1].replace(/<[^>]+>/g, ''));
    end = m.index + m[0].length;
  }
  return clean(text);
}

function parseFragment(xml) {
  const electorates = {};
  for (const m of xml.matchAll(/<talker>[\s\S]*?<name>([^<]*)<\/name>\s*<electorate>([^<]*)<\/electorate>/g)) {
    electorates[clean(decodeEntities(m[1]))] = clean(decodeEntities(m[2]));
  }
  const sub = [...xml.matchAll(/<subproceedinginfo>\s*<text>([^<]*)<\/text>/g)].map((m) => clean(decodeEntities(m[1])));
  const proceeding = (xml.match(/<proceedinginfo>\s*<text>([^<]*)<\/text>/) || [])[1];
  const topic = (xml.match(/<topicinfo>\s*<text[^>]*>([^<]*)<\/text>/) || [])[1];
  const date = (xml.match(/<date>(\d{4}-\d{2}-\d{2})/) || [])[1];
  const chamber = (xml.match(/<chamber>([^<]*)<\/chamber>/) || [])[1];
  const speeches = [];
  const headings = [];
  let current = null;
  for (const m of xml.matchAll(/<p\b([^>]*)>([\s\S]*?)<\/p>/g)) {
    const raw = m[2];
    if (/class="[^"]*Debate-H/.test(m[1])) {
      headings.push(stripTags(raw));
      continue;
    }
    const by = speakerSpans(raw);
    if (by) {
      const name = by.replace(/[:\s]+$/, '').replace(/\s*\(.*$/, '');
      if (!current || current.name !== name) {
        current = { name, parts: [] };
        speeches.push(current);
      }
    }
    if (!current) {
      current = { name: null, parts: [] };
      speeches.push(current);
    }
    const text = stripTags(raw);
    if (text) current.parts.push(text);
  }
  return { date, chamber, electorates, sub, headings, topic: topic ? clean(decodeEntities(topic)) : null, proceeding: proceeding ? clean(decodeEntities(proceeding)) : null, speeches, draft: /<draft>true<\/draft>/.test(xml) };
}

const old = JSON.parse(fs.readFileSync(path.join(RAW, 'nsw_scan_backup.json'), 'utf8'));
const dayInfo = {};
for (const r of old) {
  const toc = (r.url.match(/[?&]id=([^&]+)/) || [])[1];
  dayInfo[`${r.date}|${r.chamber}`] = { toc, pdf: r.pdf };
}

const dir = path.join(CACHE, 'nsw_frag');
const records = [];
const seenFragments = new Set();
const headingExtra = {};
for (const f of fs.readdirSync(dir)) {
  const id = f.replace(/\.xml$/, '');
  const xml = fs.readFileSync(path.join(dir, f), 'utf8');
  if (!hasMention(xml)) continue;
  const p = parseFragment(xml);
  if (!p.date || p.date < WINDOW.from || p.date > WINDOW.to) continue;
  const k = `${p.date}|${p.chamber}`;
  const info = dayInfo[k] || {};
  const headingMentions = countMentions(p.headings.join(' '));
  const speechHasMention = p.speeches.some((s) => hasMention(s.parts.join(' ')));
  let added = false;
  p.speeches.forEach((s, i) => {
    let text = s.parts.join(' ');
    if (headingMentions && !speechHasMention && i === 0) text = `${p.headings.join(': ')}: ${text}`;
    if (!hasMention(text)) return;
    added = true;
    records.push({
      jur: 'NSW',
      date: p.date,
      chamber: p.chamber,
      title: p.topic || 'Untitled section',
      proceeding: [p.proceeding, ...p.sub.slice(0, 1)].filter(Boolean).join(' – '),
      speaker: s.name || null,
      electorate: p.electorates[s.name] || null,
      mentions: countMentions(text),
      passage: excerpt(text),
      url: info.toc ? `${SITE}?id=${info.toc}&section=${id}` : null,
      pdf: info.pdf || null,
      sourceLabel: p.draft ? 'Hansard section (proof)' : 'Hansard section',
      status: p.draft ? 'proof' : 'final',
      docId: id,
    });
  });
  if (added) seenFragments.add(id);
  if (headingMentions && speechHasMention) headingExtra[k] = (headingExtra[k] || 0) + headingMentions;
}

// Any section the earlier full scan found but the cache lacks is kept from that scan.
let kept = 0;
for (const r of old) {
  if (seenFragments.has(r.docId) || !hasMention(r.passage)) continue;
  records.push({ ...r });
  kept++;
}
// Records kept from the earlier scan may have cut-off names. Repair them from the passage, or from the full member list.
const fullNames = new Set();
for (const f of fs.readdirSync(dir)) {
  for (const m of fs.readFileSync(path.join(dir, f), 'utf8').matchAll(/<talker>[\s\S]*?<name>([^<]*)<\/name>/g)) fullNames.add(clean(decodeEntities(m[1])));
}
const fullList = [...fullNames].filter((n) => n.length > 5);
for (const r of records) {
  if (!r.speaker || fullList.includes(r.speaker)) continue;
  const stem = r.speaker.replace(/[:\s]+$/, '').toUpperCase();
  const fromPassage = fullList.find((n) => n.toUpperCase().startsWith(stem) && r.passage.toUpperCase().includes(n.toUpperCase()));
  const candidates = fullList.filter((n) => n.toUpperCase().startsWith(stem));
  if (fromPassage) r.speaker = fromPassage;
  else if (candidates.length === 1) r.speaker = candidates[0];
}
// The XML spaces out its inline tags: "( Strathfield ) ( 13:20 :09 ):" becomes "(Strathfield) (13:20:09):".
for (const r of records) r.passage = clean(r.passage.replace(/\(\s+/g, '(').replace(/\s+\)/g, ')').replace(/\s+([,.:;])/g, '$1'));

// Reconcile against the daily PDFs, leaving out their contents pages.
const pdfDir = path.join(CACHE, 'nsw');
const pdfTotals = {};
for (const f of fs.readdirSync(pdfDir)) {
  const pages = pdfPages(path.join(pdfDir, f));
  const first = clean(pages[0]).slice(0, 200);
  const date = (first.match(/(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})/) || []);
  const months = { January: '01', February: '02', March: '03', April: '04', May: '05', June: '06', July: '07', August: '08', September: '09', October: '10', November: '11', December: '12' };
  if (!date[0]) continue;
  const iso = `${date[3]}-${months[date[2]]}-${date[1].padStart(2, '0')}`;
  const chamber = /Legislative Council/i.test(first) ? 'Legislative Council' : 'Legislative Assembly';
  const text = pages.join('\n').split('\n').filter((l) => !/\.{4,}/.test(l)).join(' ');
  pdfTotals[`${iso}|${chamber}`] = countMentions(clean(text));
}
const xmlTotals = {};
for (const r of records) xmlTotals[`${r.date}|${r.chamber}`] = (xmlTotals[`${r.date}|${r.chamber}`] || 0) + r.mentions;
const gaps = Object.keys({ ...pdfTotals, ...xmlTotals })
  .map((k) => ({ k, pdf: pdfTotals[k] || 0, xml: (xmlTotals[k] || 0) + (headingExtra[k] || 0) }))
  .filter((g) => g.pdf !== g.xml);

records.sort((a, b) => (a.date < b.date ? 1 : -1));
fs.writeFileSync(path.join(RAW, 'nsw.json'), JSON.stringify(records, null, 1));
fs.writeFileSync(path.join(RAW, 'nsw_recall.json'), JSON.stringify({ chamberDays: Object.keys(pdfTotals).length, pdfTotal: Object.values(pdfTotals).reduce((a, b) => a + b, 0), xmlTotal: records.reduce((n, r) => n + r.mentions, 0), headingMentions: Object.values(headingExtra).reduce((a, b) => a + b, 0), keptFromEarlierScan: kept, gaps }, null, 1));
console.log(`NSW: ${records.length} contributions, ${records.reduce((n, r) => n + r.mentions, 0)} mentions (+${Object.values(headingExtra).reduce((a, b) => a + b, 0)} in headings); PDFs ${Object.values(pdfTotals).reduce((a, b) => a + b, 0)} over ${Object.keys(pdfTotals).length} chamber-days; kept from earlier scan ${kept}; chamber-days that differ ${gaps.length}`);
console.log(gaps.map((g) => `${g.k} pdf ${g.pdf} xml ${g.xml}`).join('\n'));
const noUrl = records.filter((r) => !r.url).length;
console.log('records with no section link:', noUrl);
