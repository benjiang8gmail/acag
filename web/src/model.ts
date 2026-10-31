/**
 * Derived view data. The rules here come from the design prototype; once the
 * Phase 4–5 pipeline exists, most of these numbers move server-side (e.g.
 * `/api/brief`), and these functions become thin formatting helpers.
 */
import { addDays, cap, fmtDay, fmtRange, lc, median, ord, pct, plural, signed } from './format';
import type { Code, Coverage, Dataset, Gap, Issue, Item, Jurisdiction, Sentiment } from './types';
import { CODES, type ViewState } from './urlState';

export const PERIODS = {
  '2w': { days: 14, label: 'Last 2 weeks', menuLabel: 'Last 2 weeks', title: 'This fortnight in 30 seconds', f: 1 },
  '4w': { days: 28, label: 'Last 4 weeks', menuLabel: 'Last 4 weeks', title: 'The last 4 weeks in 30 seconds', f: 1.7 },
  '2m': { days: 61, label: 'Last 2 months', menuLabel: 'Full stored window', title: 'The last 2 months in 30 seconds', f: 3.2 },
} as const;

export const SENT: Record<Sentiment, { icon: string; label: string; fg: string; bg: string }> = {
  positive: { icon: '▲', label: 'Positive', fg: '#0e700e', bg: '#f1faf1' },
  neutral: { icon: '●', label: 'Neutral', fg: '#424242', bg: '#f0f0f0' },
  negative: { icon: '▼', label: 'Negative', fg: '#b10e1c', bg: '#fdf3f4' },
  mixed: { icon: '◆', label: 'Mixed', fg: '#bc4b09', bg: '#fff4ec' },
};

export const COV: Record<Coverage, { label: string; fg: string; bg: string }> = {
  planned: { label: 'Planned in your program', fg: '#0f6cbd', bg: '#ebf3fc' },
  in_progress: { label: 'In progress in your program', fg: '#0f6cbd', bg: '#ebf3fc' },
  recent_report: { label: 'You audited this recently', fg: '#0e700e', bg: '#f1faf1' },
  not_covered: { label: 'Not in your program', fg: '#b10e1c', bg: '#fdf3f4' },
  na: { label: 'About audit offices', fg: '#424242', bg: '#f0f0f0' },
};
const COV_SHORT: Record<Coverage, string> = { planned: 'Planned', in_progress: 'In progress', recent_report: 'Audited recently', not_covered: 'Not in program', na: '—' };
const COV_PEER: Partial<Record<Coverage, string>> = { planned: 'planned', in_progress: 'in progress', recent_report: 'audited recently' };
const FEAT: Record<string, string> = { F1: 'Auditor-General mention', F2: 'Report mention', F4: 'Risk signal' };

export interface SentBar { pos: string; neu: string; neg: string; mix: string; t: number; net: number; short: string; text: string }

export function sentBar(list: Item[]): SentBar {
  const c = { positive: 0, neutral: 0, negative: 0, mixed: 0 };
  list.forEach(i => { if (i.sent) c[i.sent]++; });
  const t = list.length;
  return {
    pos: pct(c.positive, t), neu: pct(c.neutral, t), neg: pct(c.negative, t), mix: pct(c.mixed, t), t,
    net: t ? Math.round(((c.positive - c.negative) / t) * 100) : 0,
    short: t ? `${c.positive} positive · ${c.negative} negative${c.mixed ? ` · ${c.mixed} mixed` : ''}` : 'No mentions this period',
    text: t ? [c.positive && `${c.positive} positive`, c.neutral && `${c.neutral} neutral`, c.mixed && `${c.mixed} mixed`, c.negative && `${c.negative} negative`].filter(Boolean).join(' · ') : 'No mentions this period',
  };
}

export type Model = ReturnType<typeof derive>;

export function derive(ds: Dataset, s: ViewState, seenIds: string[]) {
  const by = Object.fromEntries(ds.jurisdictions.map(j => [j.code, j])) as Record<Code, Jurisdiction>;
  const isAll = s.jur === 'ALL';
  const cur = isAll ? null : by[s.jur as Code];
  const asOf = ds.status.asOf;
  const per = PERIODS[s.period];
  const st = addDays(asOf, -per.days), prevSt = addDays(st, -per.days);
  const P = { ...per, st, range: fmtRange(st, asOf) };
  const seen = new Set(seenIds);

  const secOk = (t: string) => !s.sector || t === s.sector;
  const itemsAll = ds.items;
  const items = itemsAll.filter(i => secOk(i.theme));
  const gapsAll = ds.gaps.filter(g => secOk(g.theme));
  const X = ds.issues.filter(x => secOk(x.theme));
  const issueById = (id: string | null) => (id ? ds.issues.find(x => x.id === id) ?? null : null);
  const secShort = s.sector ? ds.sectors.find(t => t.name === s.sector)?.short ?? s.sector : '';

  const inP = (i: Item) => i.date >= st;
  const inPrev = (i: Item) => i.date < st && i.date >= prevSt;
  const mine = (i: Item) => isAll || i.jur === s.jur;
  const isNew = (i: Item) => i.date > ds.status.previousCheck && !seen.has(i.id);
  const notSitting = (c: Code) => by[c].sittingDays[1] < st;

  /** Mentions of an issue in a parliament this period (sample data scales by period length). */
  const rN = (x: Issue, c: Code) => { const n = x.raised[c] || 0; if (!n || notSitting(c)) return 0; return Math.max(1, Math.round(n * P.f)); };
  const parlsFor = (x: Issue) => CODES.filter(c => rN(x, c) > 0);
  const covOf = (x: Issue, c: Code): Coverage => x.cov[c] || x.cov._ || 'not_covered';
  const peerLine = (x: Issue | null, excl: Code | null) => {
    if (!x) return '';
    if (x.cov._ === 'na') return 'Affects every audit office';
    const p = CODES.filter(c => c !== excl && COV_PEER[covOf(x, c)]).map(c => `${by[c].office} ${COV_PEER[covOf(x, c)]}`);
    return p.length ? 'Peers: ' + p.slice(0, 3).join(' · ') : 'No other office has this in its program';
  };

  const itemView = (it: Item) => {
    const j = by[it.jur], web = it.source !== 'Hansard', x = issueById(it.x);
    const ps = x ? parlsFor(x).filter(c => c !== it.jur) : [];
    return {
      it, j, web, sent: it.sent ? SENT[it.sent] : null,
      where: (isAll || it.jur !== s.jur ? j.short + ' · ' : '') + (web ? 'Office website' : it.chamber) + ' · ' + fmtDay(it.date),
      featLabel: it.feat === 'F3' ? it.devType ?? '' : FEAT[it.feat], isNew: isNew(it),
      srcLabel: web ? 'Open website ↗' : 'Open in Hansard ↗',
      speaker: it.speaker ? `${it.speaker}, ${it.role}${it.side ? ' · ' + it.side : ''}` : `Published on the ${j.office} website`,
      quote: it.quote ? `“${it.quote}”` : '', echo: ps.length ? 'Also raised in ' + ps.map(c => by[c].short).join(', ') : '', issue: x,
    };
  };

  const xs = X.map(x => {
    const perC = CODES.map(c => ({ c, n: rN(x, c) }));
    const here = isAll ? 0 : rN(x, s.jur as Code);
    const others = perC.filter(p => p.c !== s.jur && p.n > 0);
    return { x, per: perC, here, others, total: perC.reduce((a, p) => a + p.n, 0) };
  });
  type IssueStat = (typeof xs)[number];
  const quiet = isAll ? [] : xs.filter(e => e.here === 0 && e.others.length >= 2).sort((a, b) => b.total - a.total);
  const shared = (isAll ? xs.filter(e => e.others.length >= 2) : xs.filter(e => e.here > 0 && e.others.length >= 1)).sort((a, b) => b.total - a.total);
  const issueRow = (e: IssueStat) => {
    const cv = COV[isAll ? 'na' : covOf(e.x, s.jur as Code)], oth = e.total - e.here, mx = Math.max(1, e.here, oth);
    return {
      id: e.x.id, label: e.x.label, where: e.others.map(p => by[p.c].short).join(' · '),
      count: `${oth} mentions in ${e.others.length} other parliament${e.others.length === 1 ? '' : 's'}`,
      cov: isAll ? e.x.theme : cv.label, covFg: cv.fg, covBg: cv.bg, peers: peerLine(e.x, isAll ? null : (s.jur as Code)),
      youW: pct(e.here, mx), othW: pct(oth, mx), youTxt: `${e.here} here`, othTxt: `${oth} in ${e.others.length} other${e.others.length === 1 ? '' : 's'}`,
    };
  };

  const agOf = (c: Code) => items.filter(i => i.jur === c && inP(i) && i.ofc && i.sent);
  const repOf = (c: Code) => items.filter(i => i.jur === c && inP(i) && i.rep && i.sent);
  const devOf = (c: Code) => items.filter(i => i.jur === c && inP(i) && i.feat === 'F3');
  const gapsOf = (c: Code) => gapsAll.filter(g => g.jur === c && g.score >= 40);

  const gapView = (g: Gap, k = 0) => {
    const ev = g.ev.map(id => itemsAll.find(i => i.id === id)).filter((i): i is Item => !!i);
    const ds_ = ev.map(i => i.date).sort();
    const x = issueById(g.x);
    return {
      g, rank: k + 1, issue: cap(g.issue), office: isAll ? by[g.jur].office + ' · ' : '',
      cov: g.coverage === 'partly' ? 'Partly covered' : 'Not covered', covBg: g.coverage === 'partly' ? '#fff4ec' : '#fdf3f4', covFg: g.coverage === 'partly' ? '#bc4b09' : '#b10e1c',
      evidence: plural(ev.length, 'Hansard item'), evItems: ev,
      raised: ds_.length ? `first raised ${fmtDay(ds_[0])}, last ${fmtDay(ds_[ds_.length - 1])}` : '',
      peers: peerLine(x, g.jur), hasPeers: !!x,
    };
  };
  const gapsMine = gapsAll.filter(g => isAll || g.jur === s.jur).sort((a, b) => b.score - a.score);
  const gapsShown = gapsMine.filter(g => g.score >= 40).slice(0, isAll ? 10 : 6);

  // ---- Brief
  const pool = items.filter(i => mine(i) && inP(i));
  const prevPool = items.filter(i => mine(i) && inPrev(i));
  const top = (f: Item['feat']) => pool.filter(i => i.feat === f && i.sig >= 3).sort((a, b) => b.sig - a.sig || b.date.localeCompare(a.date))[0];
  const heroItems = (['F1', 'F2', 'F3'] as const).map(top).filter((i): i is Item => !!i);
  const agL = pool.filter(i => i.ofc && i.sent), repL = pool.filter(i => i.rep && i.sent), devL = pool.filter(i => i.feat === 'F3');
  const othersC = CODES.filter(c => c !== s.jur);
  const delta = (a: number, b: number) => (a === b ? 'No change' : a > b ? `▲ ${a - b}` : `▼ ${b - a}`);
  const rankTxt = (fn: (c: Code) => number) => {
    if (isAll) return '';
    const v = fn(s.jur as Code), all = CODES.map(fn);
    return `${ord(1 + all.filter(o => o > v).length)} of 9 · others’ median ${median(othersC.map(fn))}`;
  };
  const bA = sentBar(agL), bR = sentBar(repL);
  const tiles = [
    { key: 'ag', label: 'Auditor-General mentions', n: agL.length, delta: delta(agL.length, prevPool.filter(i => i.ofc && i.sent).length), bar: bA as SentBar | null, sub: bA.short, cmp: rankTxt(c => agOf(c).length) },
    { key: 'rep', label: 'Report mentions', n: repL.length, delta: delta(repL.length, prevPool.filter(i => i.rep && i.sent).length), bar: bR as SentBar | null, sub: bR.short, cmp: rankTxt(c => repOf(c).length) },
    { key: 'dev', label: 'New developments', n: devL.length, delta: delta(devL.length, prevPool.filter(i => i.feat === 'F3').length), bar: null, sub: `${devL.filter(i => i.source !== 'Hansard').length} from office websites`, cmp: rankTxt(c => devOf(c).length) },
    { key: 'gaps', label: 'Potential program gaps', n: gapsMine.filter(g => g.score >= 40).length, delta: 'Score 40 or more', bar: null, sub: isAll ? 'Across all 9 offices' : cur!.program ? (cur!.confirmed ? 'Program confirmed' : 'Draft — program not yet confirmed') : 'Compared with recent reports only', cmp: rankTxt(c => gapsOf(c).length) },
  ];

  const BLUE = ['#fafafa', '#ebf3fc', '#cfe4fa', '#96c6fa', '#62abf5'], ORNG = ['#fafafa', '#fff4ec', '#fdcfb4', '#f9a77a'];
  const maxM = Math.max(1, ...CODES.map(c => agOf(c).length));
  const mapTiles = CODES.map(c => {
    const j = by[c], l = agOf(c), b = sentBar(l);
    let val: string, bg: string;
    if (s.mapMode === 'mentions') { val = String(l.length); bg = BLUE[Math.ceil((l.length / maxM) * 4)]; }
    else if (s.mapMode === 'net') { val = l.length >= 5 ? signed(b.net) : `n = ${l.length}`; bg = !l.length ? '#fafafa' : b.net > 15 ? '#c9eac9' : b.net < -15 ? '#f6c9cd' : '#f0f0f0'; }
    else { const n = gapsOf(c).length; val = String(n); bg = ORNG[Math.min(3, n)]; }
    return { c, j, val, bg, note: j.status === 'blocked' ? 'Blocked' : notSitting(c) ? 'Not sitting' : '', you: c === s.jur };
  });
  const allRows = CODES.map(c => { const b = sentBar(agOf(c)); return { c, name: by[c].office, ag: agOf(c).length, net: b.t >= 5 ? signed(b.net) : '', rep: repOf(c).length, dev: devOf(c).length, gaps: gapsOf(c).length }; });
  const newCount = itemsAll.filter(i => mine(i) && isNew(i) && i.sig >= 2).length;

  const bySec = ds.sectors.map(({ name, short }) => {
    const xsT = ds.issues.filter(x => x.theme === name);
    const here = isAll ? 0 : xsT.reduce((a, x) => a + rN(x, s.jur as Code), 0);
    const all = xsT.reduce((a, x) => a + CODES.reduce((b, c) => b + rN(x, c), 0), 0);
    return { name, short, here, oth: all - here, all };
  }).filter(o => o.all > 0).sort((a, b) => (isAll ? b.all - a.all : b.here - a.here || b.oth - a.oth)).slice(0, 6);
  const secMax = Math.max(1, ...bySec.map(o => (isAll ? o.all : o.here)));
  const secRows = bySec.map(o => ({ name: o.name, label: o.short, w: pct(isAll ? o.all : o.here, secMax), n: String(isAll ? o.all : o.here), oth: isAll ? '' : `+${o.oth} elsewhere`, on: s.sector === o.name }));

  // ---- Compare
  const cmpMetrics = isAll ? [] : ([
    ['ag', 'Auditor-General mentions', (c: Code) => agOf(c).length],
    ['rep', 'Report mentions', (c: Code) => repOf(c).length],
    ['dev', 'Developments', (c: Code) => devOf(c).length],
    ['gaps', 'Potential program gaps', (c: Code) => gapsOf(c).length],
  ] as const).map(([key, label, fn]) => {
    const you = fn(s.jur as Code), all = CODES.map(fn), md = median(othersC.map(fn)), mx = Math.max(1, ...all);
    return { key, label, you, med: md, youW: pct(you, mx), medW: pct(md, mx), rank: `${ord(1 + all.filter(v => v > you).length)} of 9` };
  });
  const netYou = isAll ? null : sentBar(agOf(s.jur as Code));
  const netLine = netYou ? `Sentiment toward ${cur!.office}: ${netYou.t >= 5 ? 'net ' + signed(netYou.net) : plural(netYou.t, 'mention')} · others’ median net ${signed(median(othersC.map(c => sentBar(agOf(c)).net)))}` : '';
  const HB = ['#fafafa', '#ebf3fc', '#cfe4fa', '#96c6fa', '#62abf5'];
  const heatAll = ds.sectors.map(({ name, short }) => {
    const xsT = ds.issues.filter(x => x.theme === name);
    return {
      name, short, on: s.sector === name,
      cells: CODES.map(c => {
        const n = xsT.reduce((a, x) => a + rN(x, c), 0);
        const topX = [...xsT].sort((a, b) => rN(b, c) - rN(a, c))[0];
        return { c, n, bg: HB[Math.min(4, Math.ceil(n / 2))], you: c === s.jur, issueId: topX?.id ?? null, aria: `${short} in ${by[c].name}: ${n}${by[c].status === 'blocked' ? ' (partial — access blocked)' : ''}` };
      }),
    };
  });
  const heat = heatAll.filter(h => h.cells.some(c => c.n));

  // ---- Mentions
  const agSel: Code = s.agSel || (isAll ? 'VIC' : (s.jur as Code));
  const agRows = CODES.map(c => {
    const l = agOf(c), b = sentBar(l), j = by[c], sd = (['Government', 'Opposition', 'Crossbench'] as const).map(x => l.filter(i => i.side === x).length);
    return {
      c, j, bar: b, own: l.length, elsewhere: l.length ? Math.round((j.elsewhere * per.days) / 14) : 0,
      net: b.t >= 5 ? signed(b.net) : b.t ? 'Few' : '—', sides: `Government ${sd[0]} · Opposition ${sd[1]} · Crossbench ${sd[2]}`,
      sel: c === agSel, you: c === s.jur, note: notSitting(c) ? 'Not sitting' : j.status === 'blocked' ? 'Partial' : '',
    };
  });
  const agMentions = items.filter(i => i.jur === agSel && inP(i) && i.ofc && i.sent && (s.side === 'All' || i.side === s.side)).sort((a, b) => b.date.localeCompare(a.date) || b.sig - a.sig).map(itemView);
  const repOff: Code = s.repOff || (isAll ? 'VIC' : (s.jur as Code));
  const reportMentions = (jur: Code, title: string) => itemsAll.filter(i => i.jur === jur && i.rep === title && i.sent).sort((a, b) => b.date.localeCompare(a.date));
  const repRows = ds.reports.filter(r => r.jur === repOff && secOk(r.sector)).map(r => {
    const m = items.filter(i => i.jur === repOff && i.rep === r.title && i.sent);
    return { r, n: m.length, bar: sentBar(m), last: m.length ? 'Last mentioned ' + fmtDay(m.map(i => i.date).sort().at(-1)!) : '' };
  }).filter(r => !s.notYet || r.n === 0);

  // ---- Developments
  const devAll = pool.filter(i => i.feat === 'F3').sort((a, b) => b.date.localeCompare(a.date) || b.sig - a.sig);
  const devTypes = ['All', 'Mandate', 'Resourcing', 'Governance', 'Audit requests', 'Program', 'Responses', 'New reports']
    .map(t => ({ t, n: t === 'All' ? devAll.length : devAll.filter(i => i.devType === t).length })).filter(o => o.t === 'All' || o.n > 0);
  const devList = devAll.filter(i => s.devType === 'All' || i.devType === s.devType).map(itemView);
  const devElse = isAll ? [] : items.filter(i => i.jur !== s.jur && inP(i) && i.feat === 'F3' && i.sig >= 5).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 4).map(itemView);

  // ---- Explore
  const q = s.q.trim().toLowerCase();
  let ex = items.filter(i => inP(i) && i.sig >= 2);
  if (s.expJur && !isAll) ex = ex.filter(i => i.jur === s.jur);
  if (s.expSent !== 'Any') ex = ex.filter(i => i.sent === s.expSent.toLowerCase());
  if (s.newOnly) ex = ex.filter(isNew);
  if (q) ex = ex.filter(i => [i.headline, i.summary, i.quote, i.speaker, i.debate, by[i.jur].name].join(' ').toLowerCase().includes(q));
  ex.sort((a, b) => b.date.localeCompare(a.date) || b.sig - a.sig);

  // ---- Page header
  const hansTo = fmtDay(ds.status.hansardTo);
  const scope = (isAll ? 'ACAG — all offices' : `${cur!.name} · ${cur!.office}`) + ' · ' + P.range + (s.sector ? ' · ' + s.sector : '');
  const storedRange = `${fmtRange(ds.status.storedFrom, asOf)} ${asOf.slice(0, 4)}`;
  const page = {
    brief: [scope, P.title, `Hansard to ${hansTo} · WA isn’t checked automatically (access blocked)`],
    compare: [`${P.range} · all 9 parliaments${s.sector ? ' · ' + s.sector : ''}`, isAll ? 'Across Australia' : `How ${cur!.name} compares`, isAll ? 'What the 9 parliaments are discussing, side by side.' : `What other parliaments are discussing, and where ${cur!.office} stands.`],
    mentions: [scope, 'Mentions', 'What Parliament says about each Auditor-General and their reports. Sentiment is the speaker’s stance toward the office or report.'],
    dev: [scope, 'Developments', isAll ? 'Changes affecting all 9 offices, newest first.' : `Changes affecting ${cur!.officeName}, newest first.`],
    gaps: [scope, 'Potential gaps in the forward program', isAll ? 'Top potential gaps across all 9 offices.' : `Issues raised in ${cur!.parl} that ${cur!.office}’s program may not cover.`],
    explore: [`All 9 parliaments · ${storedRange}${s.sector ? ' · ' + s.sector : ''}`, 'Explore', 'Search everything stored, with exact quotes and links you can cite.'],
  }[s.tab];

  return {
    ds, s, by, isAll, cur, P, asOf, secShort, itemsAll, items, issueById, inP, isNew, notSitting, rN, parlsFor, covOf, peerLine,
    itemView, issueRow, gapView, agOf, page, storedRange, lc,
    brief: {
      hero: heroItems.map(itemView), heroItems, gapHero: gapsShown[0] ? gapView(gapsShown[0]) : null, tiles, mapTiles, allRows,
      elseRows: (isAll ? shared : quiet).slice(0, 3).map(issueRow), secRows, newCount,
    },
    compare: { metrics: cmpMetrics, netLine, quiet: quiet.map(issueRow), shared: shared.map(issueRow), heat, heatHidden: ds.sectors.length - heat.length },
    mentions: { agSel, agRows, agMentions, repOff, repRows, reportMentions },
    dev: { devTypes, devList, devElse },
    gaps: { gapsMine, shown: gapsShown.map(gapView), hidden: gapsMine.length - gapsShown.length },
    explore: { results: ex.slice(0, 40).map(itemView), count: ex.length, q },
    sectorCount: (name: string) => itemsAll.filter(i => mine(i) && inP(i) && i.theme === name && i.sig >= 2).length,
    newFor: (c: Code | 'ALL') => itemsAll.filter(i => (c === 'ALL' || i.jur === c) && isNew(i) && i.sig >= 2).length,
    COV_SHORT,
  };
}

export type ItemView = ReturnType<Model['itemView']>;
export type GapView = ReturnType<Model['gapView']>;
export type IssueRow = ReturnType<Model['issueRow']>;
