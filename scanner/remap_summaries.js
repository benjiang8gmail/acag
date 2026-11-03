// Carries finished summaries across when a re-scan renumbers records.
// Usage: node scanner/remap_summaries.js QLD [path/to/previous.json]
// Compares what was summarised (data/to_summarise_prev/<CODE>.json by default) with data/to_summarise/<CODE>.json.
// Matching is strict: identical text first, then the same speaker on the same day, then very similar text.
const fs = require('fs');
const path = require('path');

const jur = process.argv[2];
const root = path.join(__dirname, '..', 'data');
const prevFile = process.argv[3] || path.join(root, 'to_summarise_prev', `${jur}.json`);
const prev = JSON.parse(fs.readFileSync(prevFile, 'utf8'));
const now = JSON.parse(fs.readFileSync(path.join(root, 'to_summarise', `${jur}.json`), 'utf8'));
const file = path.join(root, 'summaries', `${jur}.json`);
const sum = JSON.parse(fs.readFileSync(file, 'utf8'));

const flat = (s) => String(s).toLowerCase().replace(/[^a-z0-9]/g, '');
const who = (s) => flat(String(s || '').replace(/question to.*$/i, ''));
const words = (s) => new Set(String(s).toLowerCase().replace(/[-‐-―]/g, '').replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter((w) => w.length > 3));
const jaccard = (a, b) => {
  let n = 0;
  for (const w of a) if (b.has(w)) n++;
  return n / (a.size + b.size - n || 1);
};

const map = {}; // old id -> [new ids]
const items = {};
const unmatched = [];
const weak = [];
const taken = new Set();
// Exact text matches claim their record first, so similar speeches can't steal it.
const prevFlat = prev.map((p) => ({ p, flat: flat(p.passage), words: words(p.passage) }));
const assign = (r, p) => {
  items[r.id] = sum.items[p.id];
  (map[p.id] = map[p.id] || []).push(r.id);
  taken.add(p.id);
};
const rest = [];
for (const r of now) {
  const f = flat(r.passage);
  const exact = prevFlat.find((x) => x.p.date === r.date && x.p.chamber === r.chamber && x.flat === f && who(x.p.speaker) === who(r.speaker) && !taken.has(x.p.id));
  if (exact) assign(r, exact.p);
  else rest.push(r);
}
for (const r of rest) {
  const w = words(r.passage);
  let best = null;
  let score = 0;
  for (const x of prevFlat) {
    if (x.p.date !== r.date || x.p.chamber !== r.chamber) continue;
    const same = who(x.p.speaker) === who(r.speaker);
    const j = jaccard(x.words, w);
    const s = j + (same ? 0.4 : 0) + (taken.has(x.p.id) ? -0.05 : 0);
    if ((same && j >= 0.12 && s > score) || (!same && j >= 0.75 && s > score)) { best = x.p; score = s; }
  }
  if (!best) { unmatched.push(r); continue; }
  assign(r, best);
  weak.push({ id: r.id, from: best.id, speaker: r.speaker, score: Number(score.toFixed(2)) });
}
const remapIds = (ids) => [...new Set((ids || []).flatMap((id) => map[id] || []))];
sum.items = items;
sum.issues = (sum.issues || []).map((i) => ({ ...i, ids: remapIds(i.ids) })).filter((i) => i.ids.length);
sum.debates = (sum.debates || []).map((g) => ({ ...g, ids: remapIds(g.ids) })).filter((g) => g.ids.length);
fs.writeFileSync(file, JSON.stringify(sum, null, 1));
console.log(`${jur}: ${Object.keys(items).length} of ${now.length} carried over (${now.length - rest.length} identical, ${weak.length} similar); ${unmatched.length} need a new summary`);
if (weak.length) console.log('similar:', JSON.stringify(weak));
if (unmatched.length) console.log(JSON.stringify(unmatched.map((r) => ({ id: r.id, date: r.date, debate: r.debate, proceeding: r.proceeding, speaker: r.speaker, mentions: r.mentions, passage: r.passage })), null, 1));
