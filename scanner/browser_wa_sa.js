// WA and SA Hansard sites only answer a real browser. Paste this into the browser console on the site's search page:
//   WA: https://www.parliament.wa.gov.au/hansard/search        SA: https://hansardsearch.parliament.sa.gov.au/search
// It reads one page at a time, then posts the results to scanner/receiver.js (node scanner/receiver.js 8767), which
// writes data/raw/wa.json or data/raw/sa.json. Stop if the site shows a CAPTCHA: don't try to get around it.
(async () => {
  const isWA = location.hostname.includes('parliament.wa.gov.au');
  const prefix = isWA ? '/hansard' : '';
  const name = isWA ? 'wa.json' : 'sa.json';
  const startDate = '1/11/2025'; // Change these two dates to scan a different window.
  const endDate = '31/10/2026';
  const queries = ['"Auditor-General"', '"Auditor General"', 'Auditor', 'Auditors'];

  const RE = /\bauditors?[\s ]*[-‐‑‒–—]?[\s ]*generals?\b/i;
  const REG = new RegExp(RE.source, 'gi');
  const clean = (s) => String(s || '').replace(/[ \s]+/g, ' ').trim();
  const parser = new DOMParser();
  const rows = new Map();

  for (const q of queries) {
    for (let page = 1; page < 60; page++) {
      const url = `${prefix}/search/results?query=${encodeURIComponent(q)}&startDate=${encodeURIComponent(startDate)}&endDate=${encodeURIComponent(endDate)}&pagesize=100&orderby=date&orderByDir=desc&page=${page}`;
      const res = await fetch(url);
      if (!res.ok) break;
      const doc = parser.parseFromString(await res.text(), 'text/html');
      const links = isWA
        ? [...doc.querySelectorAll('.table-row .search-results-subject a')].filter((a) => /\/daily\//.test(a.getAttribute('href')))
        : [...doc.querySelectorAll('h2 a[href*="/daily/"]')];
      if (!links.length) break;
      for (const a of links) {
        const m = a.getAttribute('href').match(/\/daily\/([a-z]+)\/(\d{4}-\d{2}-\d{2})\/(\d+)/);
        if (!m) continue;
        const key = prefix + m[0];
        if (rows.has(key)) continue;
        const holder = isWA ? a.closest('.table-row') : a.closest('.row') || a.parentElement.parentElement;
        const cell = (c) => clean((holder.querySelector(c) || {}).textContent);
        rows.set(key, isWA
          ? { path: key, house: m[1], date: m[2], heading: clean(a.textContent), type: cell('.search-results-type'), chamber: cell('.search-results-house'), members: cell('.search-results-members'), tags: [...holder.querySelectorAll('.search-results-tags a')].map((t) => clean(t.textContent)) }
          : { path: key, house: m[1], date: m[2], heading: clean(a.textContent), tags: [...holder.querySelectorAll('.search-result-tag')].map((t) => clean(t.textContent)) });
      }
      if (links.length < 90) break;
    }
    console.log(`${q}: ${rows.size} debate pages so far`);
  }

  const records = [];
  let done = 0;
  for (const row of rows.values()) {
    const res = await fetch(row.path);
    done++;
    if (!res.ok) continue;
    const doc = parser.parseFromString(await res.text(), 'text/html');
    const root = doc.querySelector('.HpsHansard') || doc.body;
    const subject = clean((root.querySelector('.HpsSubjectHeading') || {}).textContent);
    const ps = [...root.querySelectorAll('p')];
    let speaker = null;
    let sub = null;
    const groups = new Map();
    ps.forEach((p, i) => {
      const sh = p.querySelector('.HpsSubproceedingHeading');
      if (sh) sub = clean(sh.textContent);
      const by = p.querySelector('.HpsByToc') || p.querySelector('.HpsBy');
      if (by) speaker = clean(by.textContent).replace(/:$/, '');
      const text = clean(p.textContent);
      if (!RE.test(text)) return;
      const key = (speaker || '').replace(/\s*\(.*$/, '') || '(no speaker)';
      if (!groups.has(key)) groups.set(key, { speakerRaw: speaker, anchor: p.id, sub, mentions: 0, idx: new Set() });
      const g = groups.get(key);
      g.mentions += (text.match(REG) || []).length;
      g.idx.add(i - 1).add(i).add(i + 1);
      // A witness's name can sit on its own line, with their words in the next paragraph.
      if (ps[i + 1] && /^[^.?!]{2,70}:$/.test(clean(ps[i + 1].textContent))) g.idx.add(i + 2);
    });
    for (const { idx, ...g } of groups.values()) {
      // Mark every jump, so an extract never reads as if paragraphs that aren't adjacent follow each other.
      const parts = [];
      const seen = new Set();
      let last = null;
      for (const k of [...idx].filter((n) => n >= 0 && n < ps.length).sort((a, b) => a - b)) {
        const t = clean(ps[k].textContent);
        if (!t || seen.has(t)) continue;
        seen.add(t);
        if (last !== null && k > last + 1) parts.push('…');
        parts.push(t);
        last = k;
      }
      records.push({ ...row, subject, ...g, parts });
    }
    if (done % 25 === 0) console.log(`${done} of ${rows.size} debate pages read`);
  }

  console.log(`${records.length} contributions; saving`);
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = `http://127.0.0.1:8767/${name}`;
  form.enctype = 'application/x-www-form-urlencoded';
  const field = document.createElement('textarea');
  field.name = 'payload';
  field.value = JSON.stringify(records);
  form.appendChild(field);
  document.body.appendChild(form);
  form.submit();
})();
