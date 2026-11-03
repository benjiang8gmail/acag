// Checks that each record's page reference really holds the phrase, using the downloaded PDFs.
const fs = require('fs');
const path = require('path');
const { CACHE, ROOT, pdfPages, countMentions, clean } = require('./common');

const rows = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'mentions.json'), 'utf8'));
const cache = new Map();
const pagesOf = (file) => {
  if (!cache.has(file)) cache.set(file, fs.existsSync(file) ? pdfPages(file) : null);
  return cache.get(file);
};
const fileFor = (r) => {
  if (r.jur === 'QLD') return path.join(CACHE, 'qld', `${r.date}.pdf`);
  if (r.jur === 'ACT') return path.join(CACHE, 'act', `${r.date}.pdf`);
  if (r.jur === 'NT') return path.join(CACHE, 'nt', `${r.date}.pdf`);
  if (r.jur === 'VIC') return path.join(CACHE, 'vic', `${`${r.date}|${r.chamber}`.replace(/[^\w-]/g, '_')}.pdf`);
  return null;
};
const tally = {};
const bad = [];
for (const r of rows) {
  if (!r.page) continue;
  const t = (tally[r.jur] = tally[r.jur] || { checked: 0, ok: 0, nextPage: 0, missingFile: 0 });
  const pages = pagesOf(fileFor(r));
  if (!pages) { t.missingFile++; continue; }
  t.checked++;
  const here = countMentions(clean(pages[r.page - 1] || ''));
  const joined = countMentions(clean(`${pages[r.page - 1] || ''} ${(pages[r.page] || '').slice(0, 400)}`));
  if (here) t.ok++;
  else if (joined) t.nextPage++; // The phrase wraps across the page break.
  else bad.push(`${r.id} ${r.date} p${r.page} ${r.title.slice(0, 40)}`);
}
console.table(tally);
console.log(bad.length ? `not found on the stated page:\n${bad.join('\n')}` : 'every page reference holds the phrase');

// Links by kind, per jurisdiction.
const kinds = {};
for (const r of rows) {
  const k = /#page=/.test(r.url) ? 'PDF page' : /territorystories/.test(r.url) ? 'Territory Stories page' : /#/.test(r.url) ? 'speech or paragraph anchor' : /section=/.test(r.url) ? 'Hansard section' : 'day search result';
  (kinds[r.jur] = kinds[r.jur] || {})[k] = ((kinds[r.jur] || {})[k] || 0) + 1;
}
console.log(JSON.stringify(kinds, null, 0));
