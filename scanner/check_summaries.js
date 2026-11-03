// Validates one jurisdiction's summary file: every record covered, allowed labels only, lengths sensible.
// Usage: node scanner/check_summaries.js VIC
const fs = require('fs');
const path = require('path');

const KINDS = ['Cites audit findings', 'Report tabled or noted', 'Seeks audit or referral', 'Office, powers or funding', 'Passing reference'];
const SECTORS = ['Health', 'Education and training', 'Transport and roads', 'Housing and planning', 'Justice and police', 'Finance and budget', 'Energy and environment', 'Local government', 'Integrity and governance', 'Community and social services', 'Major projects and procurement', 'Other'];
const AGS = ['Home', 'Commonwealth', 'Another jurisdiction', 'Unclear'];

const jur = process.argv[2];
const root = path.join(__dirname, '..', 'data');
const input = JSON.parse(fs.readFileSync(path.join(root, 'to_summarise', `${jur}.json`), 'utf8'));
const file = path.join(root, 'summaries', `${jur}.json`);
const out = JSON.parse(fs.readFileSync(file, 'utf8'));
const ids = new Set(input.map((r) => r.id));
const debateOf = Object.fromEntries(input.map((r) => [r.id, `${r.date}|${r.chamber}|${r.debate}`]));
const debateCounts = {};
for (const r of input) debateCounts[debateOf[r.id]] = (debateCounts[debateOf[r.id]] || 0) + 1;
const problems = [];
const words = (s) => String(s || '').trim().split(/\s+/).filter(Boolean).length;

for (const r of input) {
  const it = (out.items || {})[r.id];
  if (!it) { problems.push(`${r.id}: missing`); continue; }
  if (!it.summary || words(it.summary) < 5) problems.push(`${r.id}: summary too short`);
  if (words(it.summary) > 50) problems.push(`${r.id}: summary over 50 words (${words(it.summary)})`);
  if (/\b(he|she|his|her|him|hers)\b/i.test(it.summary)) problems.push(`${r.id}: gendered pronoun in summary`);
  if (!KINDS.includes(it.kind)) problems.push(`${r.id}: bad kind "${it.kind}"`);
  if (!SECTORS.includes(it.sector)) problems.push(`${r.id}: bad sector "${it.sector}"`);
  if (!AGS.includes(it.ag)) problems.push(`${r.id}: bad ag "${it.ag}"`);
}
for (const k of Object.keys(out.items || {})) if (!ids.has(k)) problems.push(`${k}: not in the input`);
if (!out.overview || words(out.overview) > 95 || words(out.overview) < 25) problems.push(`overview must be 25 to 95 words (got ${words(out.overview)})`);
if (/\b(he|she|his|her|him|hers)\b/i.test(out.overview || '')) problems.push('gendered pronoun in overview');
if (!Array.isArray(out.issues) || out.issues.length < 2 || out.issues.length > 6) problems.push('issues must be an array of 2 to 6');
for (const iss of out.issues || []) {
  if (!iss.label || words(iss.label) > 9) problems.push(`issue label too long or missing: ${iss.label}`);
  if (!iss.note || words(iss.note) > 28) problems.push(`issue note too long or missing: ${iss.label}`);
  if (!Array.isArray(iss.ids) || !iss.ids.length) problems.push(`issue has no ids: ${iss.label}`);
  for (const id of iss.ids || []) if (!ids.has(id)) problems.push(`issue "${iss.label}" has unknown id ${id}`);
}
const covered = new Set();
for (const g of out.debates || []) {
  const k = debateOf[(g.ids || [])[0]];
  if (!k) { problems.push(`debate gist has unknown ids: ${JSON.stringify(g.ids)}`); continue; }
  covered.add(k);
  if (!g.gist || words(g.gist) > 55) problems.push(`debate gist too long or missing: ${k}`);
  if (/\b(he|she|his|her|him|hers)\b/i.test(g.gist || '')) problems.push(`gendered pronoun in gist: ${k}`);
}
for (const [k, n] of Object.entries(debateCounts)) if (n >= 3 && !covered.has(k)) problems.push(`debate with ${n} speakers needs a gist: ${k}`);

if (problems.length) {
  console.log(`${jur}: ${problems.length} problems`);
  console.log(problems.slice(0, 60).join('\n'));
  process.exit(1);
}
console.log(`${jur}: OK, ${input.length} records, ${(out.issues || []).length} issues, ${(out.debates || []).length} debate gists`);
