// NSW: uses only the Parliament's documented public Hansard API.
// Every daily PDF is scanned for mentions, each mention is placed under its topic heading, and the topic's
// XML fragment then supplies the speaker and exact text. PDF and XML counts are reconciled at the end.
const fs = require('fs');
const path = require('path');
const { WINDOW, CACHE, get, pool, save, download, pdfPages, stripTags, clean, excerpt, countMentions, hasMention, MENTION, decodeEntities, sleep } = require('./common');

const API = 'https://api.parliament.nsw.gov.au/api/hansard/search';
const SITE = 'https://www.parliament.nsw.gov.au/parliamentary-business/hansard/hansard-full-details';
let lastCall = 0;
async function polite(url) {
  const at = Math.max(Date.now(), lastCall + 600);
  lastCall = at;
  await sleep(at - Date.now());
  return get(url, { tries: 5 });
}
async function byDate(date) {
  const dir = path.join(CACHE, 'nsw_bydate');
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, date + '.json');
  if (fs.existsSync(file)) return JSON.parse(fs.readFileSync(file, 'utf8'));
  const text = await polite(API + '/bydate?date=' + date);
  fs.writeFileSync(file, text);
  return JSON.parse(text);
}
const norm = (s) => clean(decodeEntities(s)).toUpperCase().replace(/[^A-Z0-9]/g, '');

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
  const speeches = [];
  let current = null;
  const headings = [];
  for (const m of xml.matchAll(/<p\b([^>]*)>([\s\S]*?)<\/p>/g)) {
    const raw = m[2];
    // Section headings aren't speech, but "Auditor-General" tabling items carry the mention only in the heading.
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
  return { electorates, sub, headings, topic: topic ? clean(decodeEntities(topic)) : null, proceeding: proceeding ? clean(decodeEntities(proceeding)) : null, speeches };
}

// Finds where each topic heading starts in the day's PDF text, in order.
function alignTopics(lines, details) {
  const normLines = lines.map(norm);
  const marks = [];
  let at = 0;
  for (const d of details) {
    const h = norm(d.Text);
    if (!h) continue;
    for (let i = at; i < lines.length; i++) {
      const l = normLines[i];
      if (!l) continue;
      const joined = l + (normLines[i + 1] || '');
      if (l === h || joined === h || (h.length > 40 && l.length >= 30 && h.startsWith(l))) {
        marks.push({ line: i, id: d.DocumentId, text: d.Text });
        at = i + 1;
        break;
      }
    }
  }
  return marks;
}

(async () => {
  const days = [];
  for (const y of ['2025', '2026']) {
    const list = JSON.parse(await get(`${API}/year/${y}`));
    for (const d of list) {
      if (d.date < WINDOW.from || d.date > WINDOW.to) continue;
      for (const e of d.Events || []) if (e.PdfDocId) days.push({ date: d.date, chamber: e.Chamber, pdf: e.PdfDocId, toc: e.TocDocId, proof: !!e.Uncorrected });
    }
  }
  console.log(`${days.length} chamber-days in window`);

  const dayFragments = new Map(); // fragmentId -> { day, details, index }
  const pdfCounts = {};
  const scanned = await pool(days, 3, async (d) => {
    const file = await download(`${API}/daily/pdf/${d.pdf}`, path.join(CACHE, 'nsw', `${d.pdf}.pdf`));
    if (!file) return { ...d, missing: true };
    const pages = pdfPages(file);
    const lines = [];
    const linePage = [];
    pages.forEach((p, n) => {
      for (const l of p.split('\n')) {
        lines.push(l);
        linePage.push(n + 1);
      }
    });
    // Dot-leader lines are the contents page, not the debate.
    const whole = clean(lines.filter((l) => !/\.{4,}/.test(l)).join(' '));
    const pdfMentions = countMentions(whole);
    pdfCounts[`${d.date}|${d.chamber}`] = pdfMentions;
    if (!pdfMentions) return { ...d, pdfMentions, details: [] };

    const by = await byDate(d.date);
    const house = (by.data || []).find((h) => h.PdfDocumentId === d.pdf) || (by.data || []).find((h) => h.HouseName === d.chamber);
    const details = (house && house.Details) || [];
    const marks = alignTopics(lines, details);
    const hits = new Set();
    lines.forEach((l, i) => {
      // Two-line window catches "Auditor-" at a line end.
      const w = clean(l + ' ' + (lines[i + 1] || ''));
      if (!hasMention(w)) return;
      let idx = -1;
      for (let k = 0; k < marks.length; k++) {
        if (marks[k].line <= i) idx = k;
        else break;
      }
      if (idx >= 0) hits.add(marks[idx].id);
    });
    const order = details.map((x) => x.DocumentId);
    for (const id of hits) dayFragments.set(id, { d, order, details, pages });
    return { ...d, pdfMentions, details: details.length, aligned: marks.length, hits: hits.size };
  });
  console.log(`mentions found in daily PDFs: ${Object.values(pdfCounts).reduce((a, b) => a + b, 0)} across ${dayFragments.size} topic sections`);

  const records = new Map();
  const fetched = new Map();
  const headingExtra = {};
  const headingCounted = new Set();
  const fragDir = path.join(CACHE, 'nsw_frag');
  fs.mkdirSync(fragDir, { recursive: true });
  const fragment = async (id) => {
    if (!fetched.has(id)) {
      const file = path.join(fragDir, `${id}.xml`);
      fetched.set(id, fs.existsSync(file) ? Promise.resolve(fs.readFileSync(file, 'utf8')) : polite(`${API}/daily/fragment/${id}`).then((x) => {
        if (x) fs.writeFileSync(file, x);
        return x;
      }).catch(() => null));
    }
    return fetched.get(id);
  };
  const addFromFragment = (id, xml, ctx) => {
    if (!xml) return 0;
    const f = parseFragment(xml);
    let n = 0;
    const isDraft = /<draft>true<\/draft>/.test(xml);
    const headingMentions = countMentions(f.headings.join(' '));
    const speechHasMention = f.speeches.some((s) => hasMention(s.parts.join(' ')));
    // The PDF prints section headings too; keep that count so the two totals can be compared fairly.
    if (headingMentions && speechHasMention && !headingCounted.has(id)) {
      headingCounted.add(id);
      const k = `${ctx.d.date}|${ctx.d.chamber}`;
      headingExtra[k] = (headingExtra[k] || 0) + headingMentions;
    }
    f.speeches.forEach((s, sIdx) => {
      let text = s.parts.join(' ');
      // A heading-only mention (e.g. "Auditor-General: Reports") is carried by the section's first speaker.
      const carriesHeading = headingMentions && !speechHasMention && sIdx === 0;
      if (carriesHeading) text = `${f.headings.join(': ')}: ${text}`;
      if (!hasMention(text)) return;
      const key = `${id}#${sIdx}`;
      if (records.has(key)) return;
      n += countMentions(text);
      const name = s.name || '';
      records.set(key, {
        jur: 'NSW',
        date: ctx.d.date,
        chamber: ctx.d.chamber,
        title: f.topic || (ctx.details.find((x) => x.DocumentId === id) || {}).Text || 'Untitled section',
        proceeding: [f.proceeding, ...f.sub.slice(0, 1)].filter(Boolean).join(' – '),
        speaker: name,
        electorate: f.electorates[name] || null,
        mentions: countMentions(text),
        passage: clean(excerpt(text).replace(/\(\s+/g, '(').replace(/\s+\)/g, ')').replace(/\s+([,.:;])/g, '$1')),
        url: `${SITE}?id=${ctx.d.toc}&section=${id}`,
        pdf: `${API}/daily/pdf/${ctx.d.pdf}`,
        sourceLabel: isDraft ? 'Hansard section (proof)' : 'Hansard section',
        status: isDraft ? 'proof' : 'final',
        docId: id,
      });
    });
    return n;
  };

  await pool([...dayFragments.entries()], 5, async ([id, ctx]) => {
    addFromFragment(id, await fragment(id), ctx);
  });

  // Where a day's XML total falls short of its PDF total, check every remaining section that day.
  const dayTotal = () => {
    const t = {};
    for (const r of records.values()) t[`${r.date}|${r.chamber}`] = (t[`${r.date}|${r.chamber}`] || 0) + r.mentions;
    for (const [k, v] of Object.entries(headingExtra)) t[k] = (t[k] || 0) + v;
    return t;
  };
  const short = scanned.filter((d) => d.pdfMentions && (dayTotal()[`${d.date}|${d.chamber}`] || 0) < d.pdfMentions);
  console.log(`${short.length} chamber-days still short after first pass; checking all their sections`);
  const failedDays = [];
  for (const d of short) {
    try {
      const by = await byDate(d.date);
      const house = (by.data || []).find((h) => h.PdfDocumentId === d.pdf) || (by.data || []).find((h) => h.HouseName === d.chamber);
      const details = (house && house.Details) || [];
      const ctx = { d, details };
      await pool(details, 3, async (x) => {
        if (!dayFragments.has(x.DocumentId)) addFromFragment(x.DocumentId, await fragment(x.DocumentId), ctx);
      });
    } catch (e) {
      failedDays.push(`${d.date} ${d.chamber}: ${e.message}`);
    }
  }
  if (failedDays.length) console.log('days that could not be fully checked:', failedDays.join('; '));

  const totals = dayTotal();
  const gaps = scanned
    .map((d) => ({ date: d.date, chamber: d.chamber, pdf: d.pdf, toc: d.toc, pdfMentions: d.pdfMentions || 0, xmlMentions: totals[`${d.date}|${d.chamber}`] || 0 }))
    .filter((d) => d.pdfMentions !== d.xmlMentions);
  const out = [...records.values()].sort((a, b) => (a.date < b.date ? 1 : -1));
  save('nsw_recall.json', {
    chamberDays: days.length,
    fragmentsFetched: fetched.size,
    pdfTotal: Object.values(pdfCounts).reduce((a, b) => a + b, 0),
    xmlTotal: out.reduce((n, r) => n + r.mentions, 0),
    headingMentions: Object.values(headingExtra).reduce((a, b) => a + b, 0),
    failedDays,
    gaps,
  });
  save('nsw.json', out);
  console.log(`NSW: ${out.length} speeches, ${out.reduce((n, r) => n + r.mentions, 0)} mentions in XML; ${Object.values(pdfCounts).reduce((a, b) => a + b, 0)} in PDFs; ${gaps.length} chamber-days differ`);
})().catch((e) => {
  console.error('NSW FAILED', e);
  process.exit(1);
});
