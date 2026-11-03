// Measures how reliable the sentiment labels are, using a second reader who hasn't seen them.
//   node scanner/sentiment_agreement.js print 0 25    prints part of a fixed random sample of passages, without labels
//   node scanner/sentiment_agreement.js compare       compares data/sentiment/second_read/*.json with the first labels
// compare freezes its result in data/sentiment/agreement.json, so later corrections can't flatter the score.
// Pass --force to replace it after a full re-labelling.
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..', 'data');
const dir = path.join(root, 'sentiment');
const JURS = ['NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT'];
const WORKED_EXAMPLES = new Set(['VIC-0055', 'WA-0034', 'NSW-0076', 'VIC-0100', 'ACT-0052', 'NSW-0024', 'VIC-0030', 'VIC-0250', 'TAS-0106', 'VIC-0093', 'ACT-0020']);
const SIZE = 150;
const MIN_PER_JUR = 10;

const rows = JSON.parse(fs.readFileSync(path.join(root, 'mentions.json'), 'utf8'));
const byId = Object.fromEntries(rows.map((r) => [r.id, r]));

function sample() {
  let seed = 20261101;
  const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32;
  const picked = [];
  for (const j of JURS) {
    const pool = rows.filter((r) => r.jur === j && !WORKED_EXAMPLES.has(r.id)).map((r) => [rnd(), r]).sort((a, b) => a[0] - b[0]).map((x) => x[1]);
    picked.push(...pool.slice(0, Math.min(pool.length, Math.max(MIN_PER_JUR, Math.round((pool.length / rows.length) * SIZE)))));
  }
  // Shuffled, so a reader can't drift jurisdiction by jurisdiction.
  return picked.map((r) => [rnd(), r]).sort((a, b) => a[0] - b[0]).map((x) => x[1]);
}

const [mode, start = '0', count = '25'] = process.argv.slice(2);
if (mode === 'print') {
  const all = sample();
  const from = Number(start);
  const slice = all.slice(from, from + Number(count));
  console.log(`records ${from + 1} to ${from + slice.length} of ${all.length}`);
  for (const r of slice) console.log(`\n[${r.id}] ${r.speaker || 'No speaker (tabled paper or procedural record)'} | ${r.title}${r.proceeding ? ` | ${r.proceeding}` : ''}\n${r.passage}`);
  process.exit(0);
}
if (mode !== 'compare') { console.log('Usage: print <start> <count> | compare [--force]'); process.exit(1); }

const first = {};
for (const j of JURS) Object.assign(first, JSON.parse(fs.readFileSync(path.join(dir, `${j}.json`), 'utf8')).items);
const second = {};
const secondDir = path.join(dir, 'second_read');
for (const f of fs.readdirSync(secondDir)) Object.assign(second, JSON.parse(fs.readFileSync(path.join(secondDir, f), 'utf8')));
const ids = sample().map((r) => r.id);
const unread = ids.filter((id) => !second[id]);
if (unread.length) { console.log(`second reader hasn't labelled ${unread.length} records: ${unread.slice(0, 10).join(', ')}`); process.exit(1); }

const LABELS = ['attack', 'neutral', 'praise'];
let same = 0;
const a = { attack: 0, neutral: 0, praise: 0 };
const b = { attack: 0, neutral: 0, praise: 0 };
const confusion = {};
for (const id of ids) {
  const x = first[id].s;
  const y = second[id].s;
  a[x] += 1; b[y] += 1;
  if (x === y) same += 1;
  else confusion[`${x} > ${y}`] = (confusion[`${x} > ${y}`] || 0) + 1;
}
const n = ids.length;
const po = same / n;
const pe = LABELS.reduce((t, l) => t + (a[l] / n) * (b[l] / n), 0);
const agree = Number((po * 100).toFixed(1));
const kappa = Number(((po - pe) / (1 - pe)).toFixed(2));
const opposite = ids.filter((id) => ['attack|praise', 'praise|attack'].includes(`${first[id].s}|${second[id].s}`));
const bothTargeted = ids.filter((id) => first[id].s === second[id].s && first[id].s !== 'neutral');
const whoSame = bothTargeted.filter((id) => first[id].who === second[id].who).length;
const whoAgree = bothTargeted.length ? Number(((whoSame / bothTargeted.length) * 100).toFixed(1)) : null;
const note = `A second, independent AI read of ${n} randomly chosen contributions, without seeing the first labels, gave the same colour ${Math.round(agree)}% of the time. It called ${opposite.length === 0 ? 'none' : opposite.length} of them the opposite way (red against blue), and where both gave the same colour it named the same target ${Math.round(whoAgree)}% of the time.${opposite.length === 0 ? ' All the differences were red or blue against grey.' : ''}`;

console.log(JSON.stringify({ n, agree, kappa, first: a, second: b, confusion, opposite, whoAgree }, null, 1));
console.log(note);
const out = path.join(dir, 'agreement.json');
if (fs.existsSync(out) && !process.argv.includes('--force')) console.log('agreement.json already exists, so it was kept. Pass --force to replace it.');
else fs.writeFileSync(out, JSON.stringify({ n, agree, kappa, first: a, second: b, confusion, opposite, whoAgree, note }, null, 1));

console.log('\nDisagreements:');
for (const id of ids) {
  if (first[id].s === second[id].s && first[id].who === second[id].who) continue;
  const r = byId[id];
  console.log(`\n[${id}] first ${first[id].s}/${first[id].who || '-'}, second ${second[id].s}/${second[id].who || '-'} | ${r.speaker || 'no speaker'} | ${r.title.slice(0, 60)}\n  first what: ${first[id].what}\n  ${r.passage.slice(0, 600)}`);
}
