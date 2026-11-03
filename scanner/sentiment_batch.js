// Prints a slice of one jurisdiction's records for sentiment labelling, plus how many there are in total.
// Usage: node scanner/sentiment_batch.js VIC 0 40
const fs = require('fs');
const path = require('path');

const [jur, start = '0', count = '40'] = process.argv.slice(2);
const rows = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'mentions.json'), 'utf8')).filter((r) => r.jur === jur);
const from = Number(start);
const slice = rows.slice(from, from + Number(count));
console.log(`${jur}: records ${from + 1} to ${from + slice.length} of ${rows.length}`);
for (const r of slice) console.log(`\n[${r.id}] ${r.speaker || 'No speaker (tabled paper or procedural record)'} | ${r.title}${r.proceeding ? ` | ${r.proceeding}` : ''}\n${r.passage}`);
