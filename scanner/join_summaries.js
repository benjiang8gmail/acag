// Joins data/summaries/parts/<CODE>.*.json (batches of items) and <CODE>.meta.json into data/summaries/<CODE>.json.
// Usage: node scanner/join_summaries.js VIC
const fs = require('fs');
const path = require('path');

const jur = process.argv[2];
const dir = path.join(__dirname, '..', 'data', 'summaries');
const parts = path.join(dir, 'parts');
const out = { jur, overview: '', issues: [], debates: [], items: {} };
for (const f of fs.readdirSync(parts)) {
  if (!f.startsWith(`${jur}.`) || !f.endsWith('.json')) continue;
  const j = JSON.parse(fs.readFileSync(path.join(parts, f), 'utf8'));
  if (f === `${jur}.meta.json`) Object.assign(out, { overview: j.overview, issues: j.issues || [], debates: j.debates || [] });
  else Object.assign(out.items, j.items || j);
}
fs.writeFileSync(path.join(dir, `${jur}.json`), JSON.stringify(out, null, 1));
console.log(`${jur}: joined ${Object.keys(out.items).length} items`);
