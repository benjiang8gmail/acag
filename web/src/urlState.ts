/** Every view is addressable: the URL carries the page and its selections so a shared link opens the same view. */
import { slug } from './format';
import type { Code, JurCode } from './types';

export type Tab = 'brief' | 'compare' | 'mentions' | 'dev' | 'gaps' | 'explore';
export type Period = '2w' | '4w' | '2m';
export type Side = 'All' | 'Government' | 'Opposition' | 'Crossbench';
export type SentFilter = 'Any' | 'Positive' | 'Neutral' | 'Negative' | 'Mixed';
export type DrawerKind = 'item' | 'issue' | 'gap' | 'rep';
export interface DrawerRef { k: DrawerKind; id: string }

export interface ViewState {
  tab: Tab; jur: JurCode; period: Period; sector: string | null; mapMode: 'mentions' | 'net' | 'gaps';
  mTab: 'ag' | 'reports'; agSel: Code | null; side: Side; repOff: Code | null; notYet: boolean; devType: string;
  q: string; expJur: boolean; expSent: SentFilter; newOnly: boolean; drawer: DrawerRef | null;
}

export const CODES: Code[] = ['CTH', 'NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'ACT', 'NT'];
export const DEV_TYPES = ['Mandate', 'Resourcing', 'Governance', 'Audit requests', 'Program', 'Responses', 'New reports'];

export const viewDefaults = (jur: JurCode = 'VIC', tab: Tab = 'brief'): ViewState => ({
  tab, jur, period: '2w', sector: null, mapMode: 'mentions', mTab: 'ag', agSel: null, side: 'All', repOff: null, notYet: false,
  devType: 'All', q: '', expJur: true, expSent: 'Any', newOnly: false, drawer: null,
});

const VIEW_IN: Record<string, Tab> = { brief: 'brief', compare: 'compare', mentions: 'mentions', developments: 'dev', gaps: 'gaps', explore: 'explore' };
const DRAWER_KEYS: [string, DrawerKind][] = [['item', 'item'], ['issue', 'issue'], ['gap', 'gap'], ['report', 'rep']];

/** Parse a query string. Returns null when it doesn't name a jurisdiction (not a shared view). */
export function fromQuery(search: string, sectors: string[]): Partial<ViewState> | null {
  const p = new URLSearchParams(search), o: Partial<ViewState> = {};
  const jur = (p.get('jur') || '').toUpperCase();
  if (![...CODES, 'ALL'].includes(jur)) return null;
  o.jur = jur as JurCode;
  const view = VIEW_IN[p.get('view') || '']; if (view) o.tab = view;
  const period = p.get('period'); if (period === '2w' || period === '4w' || period === '2m') o.period = period;
  const map = p.get('map'); if (map === 'mentions' || map === 'net' || map === 'gaps') o.mapMode = map;
  if (p.get('tab')) o.mTab = p.get('tab') === 'reports' ? 'reports' : 'ag';
  const off = (p.get('office') || '').toUpperCase() as Code;
  if (CODES.includes(off)) { if (o.mTab === 'reports') o.repOff = off; else o.agSel = off; }
  const side = { government: 'Government', opposition: 'Opposition', crossbench: 'Crossbench' }[p.get('side') || ''] as Side | undefined; if (side) o.side = side;
  if (p.get('unmentioned') === '1') o.notYet = true;
  const type = DEV_TYPES.find(t => t.toLowerCase() === (p.get('type') || '').toLowerCase()); if (type) o.devType = type;
  if (p.get('q')) o.q = p.get('q')!;
  if (p.get('scope') === 'all') o.expJur = false;
  const se = p.get('sentiment') || '', SE = (se.charAt(0).toUpperCase() + se.slice(1)) as SentFilter;
  if (['Positive', 'Neutral', 'Negative', 'Mixed'].includes(SE)) o.expSent = SE;
  if (p.get('new') === '1') o.newOnly = true;
  for (const [k, dk] of DRAWER_KEYS) if (p.get(k)) o.drawer = { k: dk, id: p.get(k)! };
  const sec = p.get('sector'); if (sec) { const m = sectors.find(t => slug(t) === sec); if (m) o.sector = m; }
  return o;
}

export function toQuery(s: ViewState, withDrawer: boolean): string {
  const p = new URLSearchParams();
  p.set('view', s.tab === 'dev' ? 'developments' : s.tab); p.set('jur', s.jur);
  if (s.period !== '2w') p.set('period', s.period);
  if (s.sector) p.set('sector', slug(s.sector));
  if (s.tab === 'brief' && s.mapMode !== 'mentions') p.set('map', s.mapMode);
  if (s.tab === 'mentions') {
    p.set('tab', s.mTab === 'reports' ? 'reports' : 'auditors-general');
    if (s.mTab === 'ag') { if (s.agSel) p.set('office', s.agSel); if (s.side !== 'All') p.set('side', s.side.toLowerCase()); }
    else { if (s.repOff) p.set('office', s.repOff); if (s.notYet) p.set('unmentioned', '1'); }
  }
  if (s.tab === 'dev' && s.devType !== 'All') p.set('type', s.devType.toLowerCase());
  if (s.tab === 'explore') {
    if (s.q) p.set('q', s.q); if (!s.expJur) p.set('scope', 'all');
    if (s.expSent !== 'Any') p.set('sentiment', s.expSent.toLowerCase()); if (s.newOnly) p.set('new', '1');
  }
  if (withDrawer && s.drawer) p.set({ item: 'item', issue: 'issue', gap: 'gap', rep: 'report' }[s.drawer.k], s.drawer.id);
  return p.toString();
}

export const shareUrl = (s: ViewState, withDrawer: boolean) => `${location.origin}/?${toQuery(s, withDrawer)}`;
