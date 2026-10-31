import { Button } from '@fluentui/react-components';
import { addDays, fmtDay, fmtRange } from '../format';
import { PERIODS, type Model } from '../model';
import type { Code, JurCode, ScanSnapshot } from '../types';
import { CODES, type Period } from '../urlState';
import { MenuItem } from './MenuSurface';

export function JurMenu({ m, onPick }: { m: Model; onPick: (c: JurCode) => void }) {
  return (
    <div role="menu" aria-label="Jurisdiction">
      <div className="menu-head">Viewing as</div>
      {[...CODES, 'ALL' as const].map(c => {
        const n = m.newFor(c), name = c === 'ALL' ? 'All jurisdictions' : m.by[c].name, sub = c === 'ALL' ? 'ACAG — all offices' : m.by[c].officeName;
        return (
          <MenuItem key={c} on={m.s.jur === c} onClick={() => onPick(c)}>
            <span style={{ flex: 1, display: 'flex', flexDirection: 'column' }}><span>{name}</span><span className="note">{sub}</span></span>
            <span className="small" style={{ color: 'var(--brand)', fontWeight: 600 }}>{n ? `${n} new` : ''}</span>
          </MenuItem>
        );
      })}
      <div className="menu-foot">Saved on this device</div>
    </div>
  );
}

export function SectorMenu({ m, onPick }: { m: Model; onPick: (s: string | null) => void }) {
  return (
    <div role="menu" aria-label="Sector">
      <div className="menu-head">Filter every page by sector</div>
      <MenuItem on={!m.s.sector} onClick={() => onPick(null)}><span style={{ flex: 1 }}>All sectors</span></MenuItem>
      {m.ds.sectors.map(({ name }) => {
        const n = m.sectorCount(name);
        return <MenuItem key={name} on={m.s.sector === name} onClick={() => onPick(name)}><span style={{ flex: 1 }}>{name}</span><span className="note nowrap">{n ? `${n} ${n === 1 ? 'item' : 'items'}` : ''}</span></MenuItem>;
      })}
    </div>
  );
}

export function PeriodMenu({ m, onPick }: { m: Model; onPick: (p: Period) => void }) {
  return (
    <div role="menu" aria-label="Period">
      {(Object.keys(PERIODS) as Period[]).map(k => (
        <MenuItem key={k} on={m.s.period === k} onClick={() => onPick(k)}>
          <span style={{ flex: 1 }}>{PERIODS[k].menuLabel}</span><span className="note">{fmtRange(addDays(m.asOf, -PERIODS[k].days), m.asOf)}</span>
        </MenuItem>
      ))}
    </div>
  );
}

export function doneText(m: Model, scan: ScanSnapshot | null) {
  const s = scan?.summary;
  if (!s) return '';
  const mine = m.isAll ? '' : ` · ${s.newItemsMentioningOffice[m.s.jur as Code] ?? 0} mention your office`;
  return `${s.parliamentsSat} parliaments sat · ${s.newSittingDays} new sitting days · ${s.newItems} new items${mine} · ${s.registers}`;
}

interface StatusProps { m: Model; scan: ScanSnapshot | null; scanDone: boolean; signedIn: boolean; onRefresh: () => void; onShowNew: () => void; doneMsg: string }

export function StatusPanel({ m, scan, scanDone, signedIn, onRefresh, onShowNew, doneMsg }: StatusProps) {
  const st = m.ds.status, running = scan && !scan.done;
  const rowFor = (code: Code | 'REG') => scan?.sources.find(r => r.code === code);
  const icon = (state?: string) => state === 'done' ? ['✓', 'var(--ok)'] : state === 'checking' ? ['◐', 'var(--brand)'] : ['○', '#9e9e9e'];
  const reg = rowFor('REG');
  return (
    <div aria-live="polite">
      <div style={{ padding: '12px 12px 8px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        <div style={{ fontSize: 15, fontWeight: 600 }}>{running ? 'Refreshing…' : `Updated ${fmtDay(st.lastChecked)}`}</div>
        <div className="note">Hansard is checked automatically every morning. Stored window: {m.storedRange}.</div>
        {st.sampleData && <div className="note" style={{ color: 'var(--warn)' }}>Showing sample data until the Hansard connectors are built.</div>}
      </div>
      {st.sources.map(src => {
        const live = running ? rowFor(src.code) : null;
        const [ic, col] = live ? icon(live.state) : src.status === 'ok' ? ['✓', 'var(--ok)'] : src.status === 'blocked' ? ['⚠', 'var(--warn)'] : ['–', 'var(--fg3)'];
        const text = live ? (live.state === 'done' ? live.text : live.state === 'checking' ? 'Checking…' : 'Waiting') : src.text;
        return <div key={src.code} className="status-row"><span className="ic" style={{ color: col }}>{ic}</span><span className="nm">{src.parliament}</span><span className="tx">{text}</span></div>;
      })}
      {(() => {
        const [ic, col] = running ? icon(reg?.state) : ['✓', 'var(--ok)'];
        const text = running ? (reg?.state === 'done' ? reg.text : reg?.state === 'checking' ? 'Checking…' : 'Waiting') : st.registers;
        return <div className="status-row"><span className="ic" style={{ color: col }}>{ic}</span><span className="nm">Office registers (9)</span><span className="tx">{text}</span></div>;
      })()}
      {scanDone && !running && doneMsg && (
        <div style={{ margin: '8px 12px 0', padding: '10px 12px', borderRadius: 4, background: '#f1faf1', display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-start' }}>
          <span style={{ color: 'var(--ok)', fontSize: 13, fontWeight: 600 }}>✓ {doneMsg}</span>
          <Button appearance="primary" className="btn-m" onClick={onShowNew}>Show me</Button>
        </div>
      )}
      <div style={{ padding: 12, borderTop: '1px solid var(--line)', marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <Button appearance="secondary" className="btn-m" disabled={!!running} onClick={onRefresh}>↻ {running ? 'Refreshing…' : signedIn ? 'Refresh with the latest Hansard' : 'Sign in to refresh now'}</Button>
        <div className="note">{signedIn ? 'Signed in as acag. Refreshing runs paid AI analysis on anything new.' : 'Browsing is open to everyone. Refreshing runs paid AI analysis, so it needs the ACAG sign-in.'}</div>
      </div>
    </div>
  );
}
