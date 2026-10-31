const WD = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MO = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const parse = (iso: string) => new Date(iso + 'T00:00:00Z');

/** "Thu 29 Oct" */
export const fmtDay = (iso: string) => { const d = parse(iso); return `${WD[d.getUTCDay()]} ${d.getUTCDate()} ${MO[d.getUTCMonth()]}`; };
/** "29 Oct" */
export const fmtShort = (iso: string) => { const d = parse(iso); return `${d.getUTCDate()} ${MO[d.getUTCMonth()]}`; };

export const addDays = (iso: string, n: number) => { const d = parse(iso); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };

/** "17–31 Oct" or "31 Aug – 31 Oct" */
export const fmtRange = (from: string, to: string) => {
  const a = parse(from), b = parse(to);
  return a.getUTCMonth() === b.getUTCMonth() ? `${a.getUTCDate()}–${fmtShort(to)}` : `${fmtShort(from)} – ${fmtShort(to)}`;
};

export const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
export const lc = (s: string) => s.charAt(0).toLowerCase() + s.slice(1);
export const pct = (a: number, t: number) => (t ? Math.round((a / t) * 100) : 0) + '%';
export const signed = (n: number) => (n > 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n);
export const ord = (n: number) => n + (n === 1 ? 'st' : n === 2 ? 'nd' : n === 3 ? 'rd' : 'th');
export const median = (arr: number[]) => { const a = [...arr].sort((x, y) => x - y); return a.length ? a[Math.floor((a.length - 1) / 2)] : 0; };
export const plural = (n: number, one: string, many = one + 's') => `${n} ${n === 1 ? one : many}`;
export const slug = (t: string) => t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
