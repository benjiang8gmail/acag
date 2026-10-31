import { Button, Spinner, Tab, TabList, Toast, ToastTitle, Toaster, useId, useToastController } from '@fluentui/react-components';
import {
  ArrowDownload16Regular, ArrowUpRight16Regular, ChatMultiple24Regular, DataBarVertical24Regular, Home24Regular, MoreHorizontal20Regular,
  Search24Regular, ArrowSwap24Regular, Target24Regular,
} from '@fluentui/react-icons';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as api from './api';
import { DetailDrawer } from './components/DetailDrawer';
import { ShareDialog, SignInDialog } from './components/Dialogs';
import { MenuSurface, type MenuId } from './components/MenuSurface';
import { Onboarding } from './components/Onboarding';
import { JurMenu, PeriodMenu, SectorMenu, StatusPanel, doneText } from './components/Panels';
import { Ctx, type Actions } from './ctx';
import { fmtDay, fmtShort } from './format';
import { derive } from './model';
import { Brief } from './pages/Brief';
import { Compare } from './pages/Compare';
import { Developments } from './pages/Developments';
import { Explore } from './pages/Explore';
import { Gaps } from './pages/Gaps';
import { Mentions } from './pages/Mentions';
import { loadPrefs, savePrefs, type Prefs } from './prefs';
import type { Code, Dataset, JurCode, ScanSnapshot } from './types';
import { fromQuery, shareUrl, toQuery, viewDefaults, type Tab as TabKey, type ViewState } from './urlState';

const TABS: [TabKey, string][] = [['brief', 'Brief'], ['compare', 'Compare'], ['mentions', 'Mentions'], ['dev', 'Developments'], ['gaps', 'Potential gaps'], ['explore', 'Explore']];
const TAB_NAME = Object.fromEntries(TABS) as Record<TabKey, string>;
const MOB_ICONS: Partial<Record<TabKey, JSX.Element>> = {
  brief: <Home24Regular />, compare: <ArrowSwap24Regular />, mentions: <ChatMultiple24Regular />, dev: <DataBarVertical24Regular />, gaps: <Target24Regular />,
};
const OWN_URL = 'hw-own-url';

function useIsMobile() {
  const q = '(max-width: 767px)';
  const [mob, setMob] = useState(() => matchMedia(q).matches);
  useEffect(() => { const mq = matchMedia(q), f = () => setMob(mq.matches); mq.addEventListener('change', f); return () => mq.removeEventListener('change', f); }, []);
  return mob;
}

export function App() {
  const mob = useIsMobile();
  const [ds, setDs] = useState<Dataset | null>(null);
  const [loadErr, setLoadErr] = useState('');
  const [prefs, setPrefs] = useState<Prefs>(loadPrefs);
  const [stage, setStage] = useState<'loading' | 'onboard' | 'app'>('loading');
  const [view, setView] = useState<ViewState>(() => viewDefaults());
  const [shared, setShared] = useState({ view: false, hidden: false });
  const [menu, setMenu] = useState<MenuId>(null);
  const [share, setShare] = useState<false | { withDrawer: boolean }>(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [scan, setScan] = useState<ScanSnapshot | null>(null);
  const [scanDone, setScanDone] = useState(false);
  const [adds, setAdds] = useState<string[]>([]);
  const pending = useRef<(() => void) | null>(null);
  const mainRef = useRef<HTMLElement>(null);
  const toasterId = useId('toaster');
  const { dispatchToast } = useToastController(toasterId);

  const toast = useCallback((msg: string) => dispatchToast(<Toast appearance="inverted"><ToastTitle>{msg}</ToastTitle></Toast>, { position: 'bottom', timeout: 2600 }), [dispatchToast]);
  const updatePrefs = useCallback((p: Partial<Prefs>) => setPrefs(old => { const n = { ...old, ...p }; savePrefs(n); return n; }), []);

  const watch = useCallback((snap: ScanSnapshot) => {
    setScan(snap);
    api.watchScan(snap.id, s => {
      setScan(s);
      if (s.done) api.loadDataset().then(d => { setDs(d); setScanDone(true); });
    });
  }, []);

  // Load data, then decide where to start: a shared link, the saved jurisdiction, or first run.
  useEffect(() => {
    api.me().then(r => setSignedIn(!!r.user)).catch(() => {});
    api.loadDataset().then(d => {
      setDs(d);
      const q = fromQuery(location.search, d.sectors.map(s => s.name));
      const own = sessionStorage.getItem(OWN_URL) === location.search;
      if (q) { setView({ ...viewDefaults(q.jur!), ...q }); setStage('app'); setShared({ view: !own && q.jur !== prefs.jur, hidden: false }); }
      else if (prefs.jur) { setView(viewDefaults(prefs.jur, prefs.start)); setStage('app'); }
      else setStage('onboard');
      if (d.status.scanRunning) watch(d.status.scanRunning);
    }).catch(e => setLoadErr(String(e.message || e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep the address bar in step with the view, so the URL is always the shareable link.
  const lastQs = useRef<string | null>(null), lastTab = useRef<string>('');
  useEffect(() => {
    if (stage !== 'app') return;
    const qs = '?' + toQuery(view, !!view.drawer), key = view.tab + (view.drawer ? view.drawer.k + view.drawer.id : '');
    if (qs === lastQs.current) return;
    if (lastQs.current !== null && key !== lastTab.current) history.pushState(null, '', qs); else history.replaceState(null, '', qs);
    lastQs.current = qs; lastTab.current = key;
    try { sessionStorage.setItem(OWN_URL, qs); } catch { /* ignore */ }
  }, [view, stage]);
  useEffect(() => {
    const onPop = () => { if (!ds) return; const q = fromQuery(location.search, ds.sectors.map(s => s.name)); if (q) { lastQs.current = location.search; setView({ ...viewDefaults(q.jur!), ...q }); } };
    addEventListener('popstate', onPop); return () => removeEventListener('popstate', onPop);
  }, [ds]);

  const m = useMemo(() => (ds && stage === 'app' ? derive(ds, view, prefs.seen) : null), [ds, view, prefs.seen, stage]);

  const set = useCallback((p: Partial<ViewState>) => setView(v => ({ ...v, ...p })), []);
  const tabTo = useCallback((tab: TabKey, extra?: Partial<ViewState>) => { setView(v => ({ ...v, tab, drawer: null, ...extra })); setMenu(null); mainRef.current?.scrollTo({ top: 0 }); }, []);
  const markSeen = useCallback((id: string) => setPrefs(p => { if (p.seen.includes(id)) return p; const n = { ...p, seen: [...p.seen, id] }; savePrefs(n); return n; }), []);
  const setJur = useCallback((c: JurCode) => {
    setView(v => ({ ...v, jur: c, agSel: null, repOff: null })); setMenu(null); setShared({ view: false, hidden: false }); updatePrefs({ jur: c });
    toast('Now viewing ' + (c === 'ALL' ? 'all jurisdictions' : ds?.jurisdictions.find(j => j.code === c)?.name));
  }, [ds, toast, updatePrefs]);
  const pickSector = useCallback((t: string | null) => { setView(v => ({ ...v, sector: t, devType: 'All' })); setMenu(null); toast(t ? 'Showing ' + t : 'Showing all sectors'); }, [toast]);
  const copy = useCallback((text: string, msg: string) => { navigator.clipboard?.writeText(text).catch(() => {}); toast(msg); }, [toast]);

  const needAuth = (action: () => void) => { if (signedIn) { action(); return; } pending.current = action; setMenu(null); setAuthOpen(true); };
  const startScan = () => { setScanDone(false); setMenu('status'); api.startScan().then(watch).catch(e => toast(e.message)); };
  const signIn = async (u: string, p: string) => {
    try { await api.login(u, p); } catch (e) { return (e as Error).message; }
    setSignedIn(true); setAuthOpen(false); toast('Signed in for this session');
    const a = pending.current; pending.current = null; if (a) setTimeout(a, 60);
    return null;
  };

  if (loadErr) return <div className="page"><h1>Hansard Watch</h1><p>Couldn’t load data: {loadErr}. Is the API running?</p></div>;
  if (stage === 'loading' || !ds) return <div style={{ height: '100%', display: 'grid', placeItems: 'center' }}><Spinner label="Loading Hansard Watch" /></div>;

  if (stage === 'onboard' || !m) {
    return (
      <div className={'shell' + (mob ? ' mob' : '')}>
        <Onboarding jurisdictions={ds.jurisdictions} initialJur={prefs.jur ?? (shared.view ? view.jur : null)} initialStart={prefs.start}
          onFinish={(jur, start) => { updatePrefs({ jur, start }); setView(v => ({ ...viewDefaults(jur, start), ...(shared.view ? { ...v, jur } : {}) })); setShared({ view: false, hidden: false }); setStage('app'); }} />
      </div>
    );
  }

  const { cur, isAll, by } = m;
  const newN = m.brief.newCount;
  const running = scan && !scan.done;
  const doneMsg = doneText(m, scan);
  const sectorLabel = view.sector ? m.secShort : 'All sectors';
  const statusWarnCode = ds.status.sources.filter(s => s.status === 'blocked');
  const showNew = () => { tabTo('explore', { newOnly: true, q: '', expJur: true }); setScanDone(false); };

  const scopeQs = (extra: Record<string, string | undefined> = {}) => {
    const p = new URLSearchParams();
    Object.entries({ jur: view.jur, period: view.period, sector: view.sector ?? undefined, ...extra }).forEach(([k, v]) => v && p.set(k, v));
    return p.toString();
  };
  const dl = (path: string) => api.download(path).then(err => toast(err || 'Downloaded'));
  const briefText = () => `${m.P.title} — ${isAll ? 'ACAG' : cur!.office}\n` + m.brief.heroItems.map(i => `• ${i.headline} (${by[i.jur].short}, ${fmtDay(i.date)}) ${i.url}`).join('\n') + '\n' + shareUrl(view, false);
  const EXP: Partial<Record<TabKey, [string, () => void][]>> = {
    brief: [['Word document (.docx)', () => dl('/api/export/brief.docx')], ['PDF', () => dl('/api/export/brief.pdf')], ['Copy text for email or Teams', () => copy(briefText(), 'Brief copied — paste into email or Teams')]],
    mentions: [['Mentions (CSV)', () => dl('/api/export/mentions.csv?' + scopeQs())]],
    gaps: [['Longlist (CSV)', () => dl('/api/export/gaps.csv?' + scopeQs({ period: undefined }))], ['Longlist (Word)', () => dl('/api/export/gaps.docx')]],
    explore: [['Results (CSV)', () => dl('/api/export/items.csv?' + scopeQs({ q: view.q || undefined, jur: view.expJur ? view.jur : undefined }))]],
  };
  const exportOpts = EXP[view.tab] || [];

  const shareWith = !!(share && share.withDrawer && view.drawer);
  const shareBits = [TAB_NAME[view.tab], isAll ? 'All offices' : cur!.name, m.P.label];
  if (view.sector) shareBits.push('Sector: ' + view.sector);
  if (view.tab === 'mentions') shareBits.push(view.mTab === 'reports' ? `Reports · ${by[m.mentions.repOff].office}${view.notYet ? ' · not yet mentioned' : ''}` : `Auditors-General · ${by[m.mentions.agSel].office}${view.side !== 'All' ? ' · ' + view.side : ''}`);
  if (view.tab === 'dev' && view.devType !== 'All') shareBits.push(view.devType);
  if (view.tab === 'brief' && view.mapMode !== 'mentions') shareBits.push(view.mapMode === 'net' ? 'Map: net sentiment' : 'Map: gaps');
  if (view.tab === 'explore') { if (view.q) shareBits.push(`Search “${view.q}”`); shareBits.push(view.expJur && !isAll ? 'Only ' + cur!.name : 'All jurisdictions'); if (view.expSent !== 'Any') shareBits.push(view.expSent); if (view.newOnly) shareBits.push('New only'); }
  if (shareWith && view.drawer) {
    const d = view.drawer, label = d.k === 'item' ? ds.items.find(i => i.id === d.id)?.headline : d.k === 'gap' ? ds.gaps.find(g => g.id === d.id)?.issue : d.k === 'rep' ? ds.reports.find(r => r.id === d.id)?.title : ds.issues.find(x => x.id === d.id)?.label;
    shareBits.push('Open: ' + (label ?? ''));
  }
  const url = share ? shareUrl(view, shareWith) : '';

  const actions: Actions = {
    m, mob, set, tabTo, markSeen, pickSector, setJur, toast, copy, adds,
    openDrawer: d => { setView(v => ({ ...v, drawer: d })); setMenu(null); },
    openItem: id => { markSeen(id); setView(v => ({ ...v, drawer: { k: 'item', id } })); setMenu(null); },
    toggleAdd: id => { const inB = adds.includes(id); setAdds(inB ? adds.filter(a => a !== id) : [...adds, id]); toast(inB ? 'Removed from your brief' : 'Added to your brief'); },
    openShare: withDrawer => { setShare({ withDrawer }); setMenu(null); },
  };

  const statusPanel = <StatusPanel m={m} scan={scan} scanDone={scanDone} signedIn={signedIn} doneMsg={doneMsg} onRefresh={() => needAuth(startScan)} onShowNew={showNew} />;
  const moreMenu = (
    <div role="menu" aria-label="More options">
      {[
        ['Coverage and registers', () => setMenu('status')] as const,
        ['Change jurisdiction or start page', () => { setMenu(null); setStage('onboard'); }] as const,
        signedIn ? ['Sign out', () => { api.logout().finally(() => { setSignedIn(false); setMenu(null); toast('Signed out'); }); }] as const : ['Sign in (needed to refresh data)', () => needAuth(() => {})] as const,
      ].map(([l, f]) => <button key={l} className="menu-item" role="menuitem" onClick={f}>{l}</button>)}
    </div>
  );
  const menuProps = { menu, setMenu, mob };

  return (
    <Ctx.Provider value={actions}>
      <div className={'shell' + (mob ? ' mob' : '')}>
        <header className="hdr">
          {!mob ? (
            <>
              <div className="hdr-row">
                <div className="hdr-brand">Hansard Watch</div>
                <MenuSurface id="jur" {...menuProps} width={320} label="Jurisdiction" trigger={
                  <button className="picker" style={{ width: 200 }} aria-haspopup="menu" aria-label={'Jurisdiction: ' + (isAll ? 'ACAG — all offices' : cur!.name)}>
                    <span className="dot" style={{ background: isAll ? '#616161' : cur!.color }} /><span className="picker-label" style={{ fontWeight: 600 }}>{isAll ? 'ACAG — all offices' : `${cur!.name} · ${cur!.office}`}</span><span aria-hidden>▾</span>
                  </button>}><JurMenu m={m} onPick={setJur} /></MenuSurface>
                <MenuSurface id="period" {...menuProps} width={240} label="Period" trigger={
                  <button className="picker" style={{ width: 150 }} aria-haspopup="menu"><span className="picker-label">{m.P.label}</span><span aria-hidden>▾</span></button>}>
                  <PeriodMenu m={m} onPick={p => { set({ period: p }); setMenu(null); }} /></MenuSurface>
                <MenuSurface id="sector" {...menuProps} width={340} label="Sector" trigger={
                  <button className={'picker' + (view.sector ? ' on' : '')} style={{ width: 170 }} aria-haspopup="menu" aria-label={'Sector: ' + (view.sector ?? 'All sectors')}><span className="picker-label">{sectorLabel}</span><span aria-hidden>▾</span></button>}>
                  <SectorMenu m={m} onPick={pickSector} /></MenuSurface>
                <div style={{ flex: 1 }} />
                <MenuSurface id="status" {...menuProps} width={420} align="end" label="Update status" trigger={
                  <button className="statusbtn"><span className="dot" style={{ background: 'var(--ok-dot)' }} /><span>Updated {fmtDay(ds.status.lastChecked)}</span>{statusWarnCode.length > 0 && <span style={{ color: 'var(--warn)' }}>· {statusWarnCode.map(s => by[s.code].short).join(', ')} not checked</span>}</button>}>
                  {statusPanel}</MenuSurface>
                {newN > 0 && <button className="newbtn" onClick={showNew}>{newN} new</button>}
                <MenuSurface id="more" {...menuProps} width={280} align="end" label="More options" trigger={<button className="iconbtn" aria-label="More options"><MoreHorizontal20Regular /></button>}>{moreMenu}</MenuSurface>
              </div>
              <nav aria-label="Pages" style={{ padding: '0 12px' }}>
                <TabList selectedValue={view.tab} onTabSelect={(_, d) => tabTo(d.value as TabKey)} style={{ height: 44 }}>
                  {TABS.map(([k, l]) => <Tab key={k} value={k}>{l}</Tab>)}
                </TabList>
              </nav>
            </>
          ) : (
            <div className="hdr-mrow">
              <div style={{ flex: 1, fontSize: 17, fontWeight: 600 }}>Hansard Watch</div>
              <button className={'iconbtn' + (view.tab === 'explore' ? ' on' : '')} aria-label="Search Hansard" onClick={() => tabTo('explore')}><Search24Regular /></button>
              <MenuSurface id="jur" {...menuProps} width={320} label="Jurisdiction" trigger={
                <button className="jurpill" aria-haspopup="menu" aria-label={'Jurisdiction: ' + (isAll ? 'all' : cur!.name)}><span className="dot" style={{ background: isAll ? '#616161' : cur!.color }} />{isAll ? 'All' : cur!.short} ▾</button>}>
                <JurMenu m={m} onPick={setJur} /></MenuSurface>
              <MenuSurface id="more" {...menuProps} width={280} label="More options" trigger={<button className="iconbtn" aria-label="More options"><MoreHorizontal20Regular /></button>}>{moreMenu}</MenuSurface>
            </div>
          )}
          {running && (
            <button className="scanstrip" onClick={() => setMenu('status')}>
              <span style={{ flex: 1 }}>Refreshing — checking {scan.step < 9 ? by[scan.sources[scan.step].code as Code].parl : 'office registers'}…</span>
              <span className="progress" aria-hidden><span style={{ width: (scan.step / scan.total) * 100 + '%' }} /></span>
            </button>
          )}
          {scanDone && !running && (
            <div className="bar-strip" style={{ background: '#f1faf1' }} role="status">
              <span style={{ flex: '1 1 220px', color: 'var(--ok)', fontWeight: 600 }}>✓ {doneMsg}</span>
              <Button appearance="primary" className="btn-m" onClick={showNew}>Show me</Button>
              <Button appearance="transparent" aria-label="Dismiss" onClick={() => setScanDone(false)}>✕</Button>
            </div>
          )}
          {shared.view && !shared.hidden && (
            <div className="bar-strip" style={{ background: 'var(--bg)' }}>
              <span style={{ flex: '1 1 240px' }}>↪ Opened from a shared link · {TAB_NAME[view.tab]} · {isAll ? 'All offices' : cur!.name} · {m.P.label}</span>
              {(!prefs.jur || prefs.jur !== view.jur) && (
                <Button className="btn-m" onClick={() => prefs.jur ? setJur(prefs.jur) : setStage('onboard')}>{prefs.jur ? 'Switch to ' + (prefs.jur === 'ALL' ? 'all jurisdictions' : by[prefs.jur as Code].name) : 'Set my jurisdiction'}</Button>
              )}
              <Button appearance="transparent" aria-label="Dismiss" onClick={() => setShared(s => ({ ...s, hidden: true }))}>✕</Button>
            </div>
          )}
        </header>

        <main className="main" ref={mainRef}>
          <div className="page">
            <div className="pghead">
              <div className="pghead-text">
                <div className="kicker">{m.page[0]}</div>
                <h1>{m.page[1]}</h1>
                <div className="pgsub">{m.page[2]}</div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <Button appearance="secondary" className="btn-m" icon={<ArrowUpRight16Regular />} onClick={() => actions.openShare(false)}>Share</Button>
                {exportOpts.length > 0 && (
                  <MenuSurface id="export" {...menuProps} width={260} align="end" label="Export" trigger={<Button appearance="secondary" className="btn-m" icon={<ArrowDownload16Regular />} aria-haspopup="menu">Export ▾</Button>}>
                    <div role="menu" aria-label="Export">
                      {mob && <div style={{ padding: '12px 12px 6px', fontSize: 15, fontWeight: 600 }}>Export</div>}
                      {exportOpts.map(([l, f]) => <button key={l} className="menu-item" role="menuitem" style={{ minHeight: mob ? 48 : 40 }} onClick={() => { setMenu(null); f(); }}>{l}</button>)}
                    </div>
                  </MenuSurface>
                )}
              </div>
            </div>
            {mob && (
              <div className="mchips">
                <MenuSurface id="period" {...menuProps} width={240} label="Period" trigger={<button className="mchip">{m.P.label} ▾</button>}>
                  <PeriodMenu m={m} onPick={p => { set({ period: p }); setMenu(null); }} /></MenuSurface>
                <MenuSurface id="sector" {...menuProps} width={340} label="Sector" trigger={<button className={'mchip' + (view.sector ? ' on' : '')}>{sectorLabel} ▾</button>}>
                  <SectorMenu m={m} onPick={pickSector} /></MenuSurface>
                <MenuSurface id="status" {...menuProps} width={420} label="Update status" trigger={
                  <button className="mchip" style={{ color: 'var(--fg2)' }}><span className="dot" style={{ width: 7, height: 7, background: 'var(--ok-dot)' }} />Updated {fmtShort(ds.status.lastChecked)}{statusWarnCode.length > 0 && <span style={{ color: 'var(--warn)' }}>· {statusWarnCode.length} not checked</span>}</button>}>
                  {statusPanel}</MenuSurface>
                {newN > 0 && <button className="newbtn" onClick={showNew}>{newN} new</button>}
              </div>
            )}
            {view.tab === 'brief' && <Brief />}
            {view.tab === 'compare' && <Compare />}
            {view.tab === 'mentions' && <Mentions />}
            {view.tab === 'dev' && <Developments />}
            {view.tab === 'gaps' && <Gaps />}
            {view.tab === 'explore' && <Explore />}
          </div>
        </main>

        {mob && (
          <nav className="bnav" aria-label="Pages">
            {TABS.filter(([k]) => k !== 'explore').map(([k, l]) => (
              <button key={k} className={view.tab === k ? 'on' : ''} aria-current={view.tab === k ? 'page' : undefined} onClick={() => tabTo(k)}>{MOB_ICONS[k]}{l}</button>
            ))}
          </nav>
        )}

        <DetailDrawer />
        <SignInDialog open={authOpen} onCancel={() => { pending.current = null; setAuthOpen(false); }} onSignIn={signIn} />
        <ShareDialog open={!!share} url={url} bits={shareBits} title={'Hansard Watch — ' + shareBits.slice(0, 2).join(' · ')} onClose={() => setShare(false)} onCopy={() => copy(url, 'Link copied — paste it anywhere')} />
        <Toaster toasterId={toasterId} />
      </div>
    </Ctx.Provider>
  );
}
