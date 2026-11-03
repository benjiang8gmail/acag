// Flags summaries for review: numbers that aren't in the source passage, identical summaries on different records,
// and summaries sharing few words with their passage (a sign the summary belongs to another record).
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..', 'data');
const rows = JSON.parse(fs.readFileSync(path.join(root, 'mentions.json'), 'utf8'));
const items = {};
for (const j of ['NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT']) Object.assign(items, JSON.parse(fs.readFileSync(path.join(root, 'summaries', `${j}.json`), 'utf8')).items);

const numbers = (s) => (String(s).replace(/(\d),(\d)/g, '$1$2').match(/\d+(?:\.\d+)?/g) || []);
const STOP = new Set('auditor general auditor-general said says cited claimed argued asked noted that this with from which were have been their about would could should also than then they them report reports member members minister government committee'.split(' '));
const words = (s) => String(s).toLowerCase().replace(/[^a-z0-9' -]/g, ' ').split(/[\s-]+/).filter((w) => w.length > 3 && !STOP.has(w));
const flagged = [];
const weak = [];
const seen = new Map();
for (const r of rows) {
  const it = items[r.id];
  if (!it) { flagged.push(`${r.id}: no summary`); continue; }
  const src = new Set(numbers(`${r.passage} ${r.title} ${r.proceeding || ''} ${r.date}`));
  const missing = numbers(it.summary).filter((n) => !src.has(n));
  if (missing.length) flagged.push(`${r.id} [${missing.join(', ')}] ${it.summary}`);
  const key = it.summary.toLowerCase();
  if (seen.has(key)) flagged.push(`${r.id} duplicates ${seen.get(key)}: ${it.summary.slice(0, 110)}`);
  else seen.set(key, r.id);
  const pw = new Set(words(`${r.passage} ${r.title} ${r.proceeding || ''}`));
  const sw = [...new Set(words(it.summary))];
  const share = sw.length ? sw.filter((w) => pw.has(w) || pw.has(w.replace(/s$/, '')) || pw.has(`${w}s`)).length / sw.length : 1;
  if (share < 0.45) weak.push({ id: r.id, share: Number(share.toFixed(2)), speaker: r.speaker, debate: r.title.slice(0, 40), sum: it.summary, src: r.passage.slice(0, 500) });
}
console.log(`${rows.length} records; ${flagged.length} number or duplicate flags; ${weak.length} with low word overlap`);
console.log(flagged.join('\n'));
weak.sort((a, b) => a.share - b.share);
for (const w of weak) console.log(`\n${w.id} overlap ${w.share} | ${w.speaker} | ${w.debate}\n SUM: ${w.sum}\n SRC: ${w.src}`);
