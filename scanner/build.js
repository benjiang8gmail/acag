// Builds the dashboard from data/mentions.json and data/summaries/*.json.
// Writes index.html (standalone) and scanner/dist/artifact.html (the same page without the document wrapper).
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const DATA = path.join(ROOT, 'data');
const load = (f) => JSON.parse(fs.readFileSync(path.join(DATA, f), 'utf8'));
const rows = load('mentions.json');

const KINDS = ['Cites audit findings', 'Report tabled or noted', 'Seeks audit or referral', 'Office, powers or funding', 'Passing reference'];
const SECTORS = ['Health', 'Education and training', 'Transport and roads', 'Housing and planning', 'Justice and police', 'Finance and budget', 'Energy and environment', 'Local government', 'Integrity and governance', 'Community and social services', 'Major projects and procurement', 'Other'];

const META = [
  {
    code: 'NSW', name: 'New South Wales', parliament: 'Legislative Assembly and Legislative Council',
    homeUrl: 'https://www.parliament.nsw.gov.au/parliamentary-business/hansard',
    searchUrl: 'https://www.parliament.nsw.gov.au/parliamentary-business/hansard/hansard-advanced-search?query=%22Auditor-General%22&sort=date',
    searchLabel: 'Search NSW Hansard', scope: 'Every daily transcript for both houses (100 chamber-days).',
    method: 'Parliament’s public Hansard API. Full text of each daily PDF, then the XML section for speaker and text. PDF and XML counts were reconciled.',
    linkNote: 'The Hansard section on the Parliament’s site.',
  },
  {
    code: 'VIC', name: 'Victoria', parliament: 'Legislative Assembly and Legislative Council',
    homeUrl: 'https://www.parliament.vic.gov.au/parliamentary-activity/hansard/',
    searchUrl: 'https://www.parliament.vic.gov.au/hansardsearch?page=1&pageSize=25&sortType=15&term=%22Auditor-General%22',
    searchLabel: 'Search Victorian Hansard', scope: 'VIC_SCOPE',
    method: 'Full text of each daily PDF. The Parliament’s search missed some mentions, so it was used only to find exact speech links, party and electorate.',
    linkNote: 'The speech within the debate page where it could be matched, otherwise the exact page of the daily PDF.',
  },
  {
    code: 'QLD', name: 'Queensland', parliament: 'Legislative Assembly (single house)',
    homeUrl: 'https://www.parliament.qld.gov.au/Work-of-the-Assembly/Record-of-Proceedings',
    searchUrl: 'https://www.parliament.qld.gov.au/Work-of-the-Assembly/Sitting-Dates/Latest-Sitting-Week',
    searchLabel: 'Latest Queensland sitting week', scope: 'Every Record of Proceedings for the window (36 sitting days).',
    method: 'Full text of each sitting-day PDF, with speakers and debate titles taken from the transcript and its contents pages.',
    linkNote: 'The exact page of the PDF.',
  },
  {
    code: 'WA', name: 'Western Australia', parliament: 'Legislative Assembly and Legislative Council',
    homeUrl: 'https://www.parliament.wa.gov.au/hansard/search',
    searchUrl: 'https://www.parliament.wa.gov.au/hansard/search/results?query=%22Auditor%20General%22&orderby=date&orderByDir=desc',
    searchLabel: 'Search WA Hansard', scope: 'Debates returned by the Parliament’s Hansard search for the phrase, its variants and “Auditor”, both houses.',
    method: 'Read in a normal browser, one page at a time, because the site refuses scripted requests. Full text of every matching debate page.',
    linkNote: 'The paragraph within the debate page.',
  },
  {
    code: 'SA', name: 'South Australia', parliament: 'House of Assembly and Legislative Council',
    homeUrl: 'https://hansardsearch.parliament.sa.gov.au/',
    searchUrl: 'https://hansardsearch.parliament.sa.gov.au/search/results?query=%22Auditor-General%22',
    searchLabel: 'Search SA Hansard', scope: 'Debates returned by the Parliament’s Hansard search for the phrase, its variants and “Auditor”, both houses and Estimates Committees.',
    method: 'Read in a normal browser, one page at a time, because the site refuses scripted requests. Full text of every matching debate page.',
    linkNote: 'The paragraph within the debate page.',
  },
  {
    code: 'TAS', name: 'Tasmania', parliament: 'House of Assembly and Legislative Council',
    homeUrl: 'https://www.parliament.tas.gov.au/hansard',
    searchUrl: 'https://search.parliament.tas.gov.au/adv/hahansard',
    searchLabel: 'Tasmanian Hansard search', scope: 'TAS_SCOPE',
    method: 'Full text of each day’s transcript (DOCX), with speakers and headings from the document’s structure.',
    linkNote: 'That day\u2019s search result, which can take a minute or two to load; select Download Document to open the transcript. Tasmania has no stable link to a page or speech.',
  },
  {
    code: 'ACT', name: 'Australian Capital Territory', parliament: 'Legislative Assembly (single house)',
    homeUrl: 'https://www.parliament.act.gov.au/parliamentary-business/watch,-read-and-listen/hansard',
    searchUrl: 'https://www.hansard.act.gov.au/hansard/11th-assembly/2026/debates(PDF).htm',
    searchLabel: 'Latest ACT daily Hansards', scope: 'Every daily Hansard PDF listed for the window (34 sitting days). Committee hearing transcripts are not included.',
    method: 'Full text of each PDF, with speakers and debate titles from the transcript and its contents pages.',
    linkNote: 'The exact page of the PDF.',
  },
  {
    code: 'NT', name: 'Northern Territory', parliament: 'Legislative Assembly (single house)',
    homeUrl: 'https://parliament.nt.gov.au/business/parliamentary-record',
    searchUrl: 'https://territorystories.nt.gov.au/?collection=debates%20and%20questions%20for%2015th%20assembly%202024%20-&ntdl_type=debate&sort=date_new&source=parliament%20nt&query=%22Auditor-General%22',
    searchLabel: 'Search Territory Stories', scope: 'Every Debates and Questions document for the window (31 sitting days), including draft daily Hansards.',
    method: 'Territory Stories API for the document list, then the full text of each PDF.',
    linkNote: 'The exact page in Territory Stories.',
  },
];

const summaries = {};
const gists = {};
const debateKey = (r) => `${r.jur}|${r.date}|${r.chamber}|${r.title}`;
const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
for (const m of META) {
  const f = path.join(DATA, 'summaries', `${m.code}.json`);
  if (!fs.existsSync(f)) { console.warn(`no summaries yet for ${m.code}`); continue; }
  const s = JSON.parse(fs.readFileSync(f, 'utf8'));
  summaries[m.code] = s;
  for (const g of s.debates || []) {
    const first = byId[(g.ids || [])[0]];
    if (first && g.gist) gists[debateKey(first)] = g.gist;
  }
}

const tasTally = fs.existsSync(path.join(DATA, 'raw', 'tas_tally.json')) ? load('raw/tas_tally.json') : { tally: [], noDoc: [], failed: [] };
const tasDocs = tasTally.tally.length;
const vicTally = fs.existsSync(path.join(DATA, 'raw', 'vic_tally.json')) ? load('raw/vic_tally.json') : { tally: [] };
const scopes = {
  TAS_SCOPE: `Every transcript the Parliament's search returned for the window, found by searching each month (${tasDocs} across both houses, including three Estimates transcripts, after removing duplicates and drafts).`,
  VIC_SCOPE: `Every daily Hansard for both houses in the window (${vicTally.tally.length} chamber-days). The last sitting day in the window was 24 September 2026.`,
};

// Some Tasmanian records named the wrong person, because question headings were missed. Corrected from the transcripts.
const speakerFixes = load('speaker_fixes.json');
const records = rows.map((r) => {
  const it = ((summaries[r.jur] || {}).items || {})[r.id] || {};
  const out = { id: r.id, j: r.jur, d: r.date, c: r.chamber, t: r.title, m: r.mentions, x: r.passage, u: r.url };
  if (r.proceeding) out.p = r.proceeding;
  const fixed = speakerFixes[r.id];
  if (fixed || r.speaker) out.s = fixed || r.speaker;
  if (r.electorate && !fixed) out.e = r.electorate;
  if (r.party && !fixed) out.pa = r.party;
  if (r.sourceLabel) out.l = r.sourceLabel;
  if (r.status === 'proof') out.st = 'proof';
  if (it.summary) out.sum = it.summary;
  if (it.kind) out.k = it.kind;
  if (it.sector) out.sec = it.sector;
  if (it.ag) out.ag = it.ag;
  return out;
});

const months = [];
for (let y = 2025, m = 11; y < 2026 || (y === 2026 && m <= 10); m === 12 ? ((m = 1), y++) : m++) months.push(`${y}-${String(m).padStart(2, '0')}`);

const narrative = fs.existsSync(path.join(DATA, 'summaries', 'national.json')) ? load('summaries/national.json') : { national: ['National summary pending.'] };

const totalMentions = records.reduce((n, r) => n + r.m, 0);
const debateCount = new Set(records.map((r) => `${r.j}|${r.d}|${r.c}|${r.t}`)).size;
const byJur = {};
for (const r of records) byJur[r.j] = (byJur[r.j] || 0) + r.m;
const top3 = Object.values(byJur).sort((a, b) => b - a).slice(0, 3).reduce((a, b) => a + b, 0);
const fill = (t) => t
  .replace('{{mentions}}', totalMentions.toLocaleString('en-AU'))
  .replace('{{turns}}', records.length.toLocaleString('en-AU'))
  .replace('{{debates}}', debateCount.toLocaleString('en-AU'))
  .replace('{{top3}}', String(Math.round((top3 / totalMentions) * 100)));
const payload = {
  window: { from: '2025-11-01', to: '2026-10-31' },
  months,
  kinds: KINDS,
  sectors: SECTORS,
  heatBins: [5, 15, 30, 60],
  lede: 'Every mention of an Auditor-General in the Hansard of Australia’s six states and two territories over the past 12 months, summarised and linked back to the original record.',
  national: narrative.national.map(fill),
  methodSub: `Scanned on 1 November 2026. Window: 1 November 2025 to 31 October 2026. ${totalMentions.toLocaleString('en-AU')} mentions in ${records.length.toLocaleString('en-AU')} member contributions.`,
  jurisdictions: META.map((m) => {
    const s = summaries[m.code] || {};
    return {
      ...m,
      scope: scopes[m.scope] || m.scope,
      overview: s.overview || 'Summary pending.',
      issues: s.issues || [],
    };
  }),
  notes: [
    {
      title: 'What counts as a mention',
      items: [
        'The words \u201cAuditor-General\u201d or \u201cAuditor General\u201d in any form, including plurals and possessives, wherever they appear in a debate. Contents pages are not counted, and a debate\u2019s heading only counts when nothing under that heading mentions the Auditor-General.',
        'References only to an audit office, such as \u201cVAGO\u201d or \u201cAudit Office\u201d, are not counted unless the phrase also appears.',
        'One member\u2019s contribution in one debate is normally one record, which can hold several mentions. A \u2026 in an extract shows that text was skipped.',
      ],
    },
    {
      title: 'How it was checked',
      items: [
        'NSW: mentions in the Hansard sections and their headings match the daily PDFs exactly across all 100 chamber-days.',
        'Victoria, Queensland, the ACT and the NT: every PDF page reference was re-checked and holds the phrase. A sample of Victorian speech links was opened and landed on the right speech.',
        'WA and SA: every debate on 12 sample chamber-days (547 debates) was read in full, and all 18 debate pages with a mention were already in the data.',
        'Summaries: independent AI reviewers read every summary, overview, issue and debate summary against its source, and every number in every summary was compared with its passage by script. Each flagged item was then checked against the transcript or live Hansard page, and the errors found were corrected.',
      ],
    },
    {
      title: 'Read this before relying on a summary',
      items: [
        'Summaries and the type and policy-area labels are AI-generated from the extract shown with each record. Check the original Hansard before quoting or citing anything.',
        'Summaries report what members said in debate. They are not findings of any Auditor-General, and members\u2019 claims have not been verified.',
        'Some extracts are short, so a summary can only reflect that part of a speech.',
        'Records marked Proof come from uncorrected transcripts, and the wording can change.',
      ],
    },
    {
      title: 'What is not covered',
      items: [
        'Anything before 1 November 2025 or after 31 October 2026.',
        'WA and SA rely on those parliaments\u2019 own search engines to find debates, so a miss is still possible there. The other six parliaments were read in full.',
        'Tasmania: a search for 6 May 2026 returned no transcript, and it could not be confirmed whether the House sat that day.',
        'Tasmania: the House of Assembly transcript for 5 November 2025 could not be read. Parliament\u2019s search holds a copy of the 2 December transcript under that date, so it was left out.',
        'The Commonwealth Parliament and New Zealand, and committee hearing transcripts unless a parliament publishes them in its Hansard, as SA, WA and Tasmania do for Estimates.',
      ],
    },
  ],
  footer: 'Built from public parliamentary records. Hansard text remains the copyright of each parliament; follow the links for the authoritative record.',
  gists,
  records,
};

const fragment = fs.readFileSync(path.join(__dirname, 'app.fragment.html'), 'utf8');
const json = JSON.stringify(payload).replace(/<\//g, '<\\/').replace(/<!--/g, '<\\!--');
const page = fragment.replace('/*__DATA__*/', () => json);
const [head, body] = page.split('<!--BODY-->');

const standalone = `<!doctype html>\n<html lang="en-AU">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n${head}</head>\n<body>${body}</body>\n</html>\n`;
fs.writeFileSync(path.join(ROOT, 'index.html'), standalone);
const dist = path.join(__dirname, 'dist');
fs.mkdirSync(dist, { recursive: true });
fs.writeFileSync(path.join(dist, 'artifact.html'), head + body);

const missing = records.filter((r) => !r.sum).length;
console.log(`index.html ${(standalone.length / 1024 / 1024).toFixed(2)} MB; ${records.length} records; ${totalMentions} mentions; ${Object.keys(gists).length} debate gists; ${missing} records without a summary`);

// hansards.html: a separate version of the page that adds sentiment, from data/sentiment/*.json and hansards.fragment.html.
const SENTIMENT = path.join(DATA, 'sentiment');
if (META.every((m) => fs.existsSync(path.join(SENTIMENT, `${m.code}.json`)))) {
  const sentiment = Object.fromEntries(META.map((m) => [m.code, JSON.parse(fs.readFileSync(path.join(SENTIMENT, `${m.code}.json`), 'utf8'))]));
  const labelled = records.map((r) => {
    const it = sentiment[r.j].items[r.id];
    const out = { ...r, sn: it.s };
    if (it.who) out.who = it.who;
    if (it.what) out.what = it.what;
    return out;
  });
  const count = (value) => labelled.filter((r) => r.sn === value).length;
  const share = (n) => Math.round((n / labelled.length) * 100);
  const nationalFile = path.join(SENTIMENT, 'national.json');
  const national = fs.existsSync(nationalFile) ? JSON.parse(fs.readFileSync(nationalFile, 'utf8')) : { attack: [], praise: [] };
  // A national theme gathers jurisdiction themes by label, so every number and record behind it stays traceable.
  const gather = (side) => (national[side] || []).map((t) => {
    const ids = new Set();
    for (const [code, labels] of Object.entries(t.from)) {
      for (const label of labels) {
        const source = sentiment[code].themes[side].find((x) => x.label === label);
        if (!source) throw new Error(`national ${side} theme "${t.label}" names a theme ${code} doesn't have: ${label}`);
        source.ids.forEach((id) => ids.add(id));
      }
    }
    return { label: t.label, note: t.note, jur: Object.keys(t.from), ids: [...ids] };
  });
  const agreementFile = path.join(SENTIMENT, 'agreement.json');
  const agreement = fs.existsSync(agreementFile) ? JSON.parse(fs.readFileSync(agreementFile, 'utf8')) : null;
  const sentimentPayload = {
    ...payload,
    lede: 'Every mention of an Auditor-General in the Hansard of Australia’s six states and two territories over the past 12 months, summarised, marked as attack, praise or neutral, and linked back to the original record.',
    methodSub: `${payload.methodSub} Sentiment labels cover all ${labelled.length.toLocaleString('en-AU')} contributions: ${share(count('attack'))}% attack, ${share(count('praise'))}% praise and ${share(count('neutral'))}% neutral.`,
    notes: [
      {
        title: 'How sentiment was worked out',
        items: [
          'AI read each contribution’s Hansard extract against a written rulebook (scanner/SENTIMENT.md) and asked one question: what is the member using the reference to the Auditor-General for?',
          'Red means used to attack the government or another party. Blue means used to praise the government or another party. Grey means neither, which includes tabling, procedure, plain questions, and bad or good news reported without blame or credit.',
          'Red doesn’t mean the Auditor-General is being criticised, and blue doesn’t mean the Auditor-General is being praised. Every red or blue record also names its target, so those cases can be seen separately.',
          ...(agreement ? [agreement.note] : []),
          'Only the sentences around the mention were judged, not the whole speech. Some extracts are short, so a label can only reflect that part of a speech.',
          'Labels record how a member used the reference. They don’t say whether the member was right, and they aren’t the view of any Auditor-General’s office.',
          'Small groups swing easily, so compare jurisdictions and months with care. The Northern Territory has only 23 contributions.',
        ],
      },
      ...payload.notes,
    ],
    sentiment: {
      national: { attack: gather('attack'), praise: gather('praise') },
      jurisdictions: Object.fromEntries(META.map((m) => [m.code, sentiment[m.code].themes])),
    },
    records: labelled,
  };
  const [sentHead, sentBody] = fs.readFileSync(path.join(__dirname, 'hansards.fragment.html'), 'utf8')
    .replace('/*__FONTS__*/', () => fs.readFileSync(path.join(__dirname, 'fonts.embed.css'), 'utf8'))
    .replace('/*__DATA__*/', () => JSON.stringify(sentimentPayload).replace(/<\//g, '<\\/').replace(/<!--/g, '<\\!--'))
    .split('<!--BODY-->');
  const sentPage = `<!doctype html>\n<html lang="en-AU">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n${sentHead}</head>\n<body>${sentBody}</body>\n</html>\n`;
  fs.writeFileSync(path.join(ROOT, 'hansards.html'), sentPage);
  const onAg = (side) => labelled.filter((r) => r.sn === side && r.who === 'auditor-general').length;
  console.log(`hansards.html ${(sentPage.length / 1024 / 1024).toFixed(2)} MB; ${share(count('attack'))}% attack, ${share(count('praise'))}% praise, ${share(count('neutral'))}% neutral; Auditor-General attacked in ${onAg('attack')} and praised in ${onAg('praise')}`);
} else {
  console.warn('hansards.html not built: sentiment labels are not finished for every jurisdiction');
}
