// Joins data/sentiment/parts/<CODE>.*.json into data/sentiment/<CODE>.json and validates it against SENTIMENT.md.
// Usage: node scanner/join_sentiment.js VIC
const fs = require('fs');
const path = require('path');

const jur = process.argv[2];
const root = path.join(__dirname, '..', 'data');
const dir = path.join(root, 'sentiment');
const parts = path.join(dir, 'parts');
const rows = JSON.parse(fs.readFileSync(path.join(root, 'mentions.json'), 'utf8')).filter((r) => r.jur === jur);

const items = {};
const problems = [];
let themes = { attack: [], praise: [] };
for (const f of fs.readdirSync(parts).filter((n) => n.startsWith(`${jur}.`)).sort()) {
  const data = JSON.parse(fs.readFileSync(path.join(parts, f), 'utf8'));
  if (f === `${jur}.themes.json`) { themes = data; continue; }
  for (const [id, it] of Object.entries(data)) {
    if (items[id]) problems.push(`${id}: labelled twice (${f})`);
    items[id] = it;
  }
}

const S = ['attack', 'praise', 'neutral'];
const WHO = ['government', 'opposition', 'auditor-general', 'other'];
const words = (s) => String(s || '').trim().split(/\s+/).filter(Boolean).length;
const numbers = (s) => String(s).replace(/(\d),(\d)/g, '$1$2').match(/\d+(?:\.\d+)?/g) || [];
const GENDERED = /\b(he|she|his|her|him|hers)\b/i;
const STOP = new Set('auditor general auditor-general said says cited claimed argued asked noted that this with from which were have been their about would could should also than then they them report reports member members minister government committee'.split(' '));
const content = (s) => String(s).toLowerCase().replace(/[^a-z0-9' -]/g, ' ').split(/[\s-]+/).filter((w) => w.length > 3 && !STOP.has(w));

const ids = new Set(rows.map((r) => r.id));
for (const r of rows) {
  const it = items[r.id];
  if (!it) { problems.push(`${r.id}: missing`); continue; }
  if (!S.includes(it.s)) problems.push(`${r.id}: bad s "${it.s}"`);
  if (it.s === 'neutral') {
    if (it.who || it.what) problems.push(`${r.id}: who and what must be empty for neutral`);
    continue;
  }
  if (!WHO.includes(it.who)) problems.push(`${r.id}: bad who "${it.who}"`);
  if (!it.what) { problems.push(`${r.id}: what is required for ${it.s}`); continue; }
  if (words(it.what) > 16) problems.push(`${r.id}: what over 16 words`);
  if (GENDERED.test(it.what)) problems.push(`${r.id}: gendered pronoun in what`);
  const source = `${r.passage} ${r.title} ${r.proceeding || ''} ${r.speaker || ''}`;
  const known = new Set(numbers(`${source} ${r.date}`));
  const missing = numbers(it.what).filter((n) => !known.has(n));
  if (missing.length) problems.push(`${r.id}: figure not in the extract [${missing.join(', ')}]: ${it.what}`);
  const inSource = new Set(content(source));
  const cw = [...new Set(content(it.what))];
  const share = cw.length ? cw.filter((w) => inSource.has(w) || inSource.has(w.replace(/s$/, '')) || inSource.has(`${w}s`)).length / cw.length : 1;
  if (cw.length >= 3 && share < 0.25) problems.push(`${r.id}: what shares few words with its extract, check it belongs here: ${it.what}`);
}
for (const id of Object.keys(items)) if (!ids.has(id)) problems.push(`${id}: not a ${jur} record`);

for (const side of ['attack', 'praise']) {
  const list = themes[side] || [];
  if (!Array.isArray(list) || list.length > 5) problems.push(`${side} themes must be an array of up to 5`);
  const eligible = rows.filter((r) => items[r.id] && items[r.id].s === side).length;
  if (eligible >= 3 && !list.length) problems.push(`${eligible} records could support a ${side} theme, but none was written`);
  for (const t of list) {
    if (!t.label || words(t.label) > 9) problems.push(`${side} theme label missing or over 9 words: ${t.label}`);
    if (!t.note || words(t.note) > 24) problems.push(`${side} theme note missing or over 24 words: ${t.label}`);
    if (GENDERED.test(`${t.label} ${t.note}`)) problems.push(`gendered pronoun in ${side} theme: ${t.label}`);
    if (!Array.isArray(t.ids) || !t.ids.length) problems.push(`${side} theme has no ids: ${t.label}`);
    for (const id of t.ids || []) {
      if (!ids.has(id)) problems.push(`${side} theme "${t.label}" has unknown id ${id}`);
      else if (items[id] && items[id].s !== side) problems.push(`${side} theme "${t.label}" uses ${id}, labelled ${items[id].s}`);
    }
  }
}

if (problems.length) {
  console.log(`${jur}: ${problems.length} problems, nothing written`);
  console.log(problems.slice(0, 60).join('\n'));
  process.exit(1);
}
const ordered = Object.fromEntries(rows.map((r) => [r.id, items[r.id]]));
fs.writeFileSync(path.join(dir, `${jur}.json`), JSON.stringify({ jur, items: ordered, themes }, null, 1));
const tally = {};
for (const it of Object.values(ordered)) {
  tally[it.s] = (tally[it.s] || 0) + 1;
  if (it.who) tally[`${it.s}:${it.who}`] = (tally[`${it.s}:${it.who}`] || 0) + 1;
}
console.log(`${jur}: OK, ${rows.length} records, ${themes.attack.length} attack and ${themes.praise.length} praise themes`, tally);
