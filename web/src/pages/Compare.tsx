import { useApp } from '../ctx';
import type { IssueRow } from '../model';
import { Meter, Pill } from '../ui';

function IssueButton({ e, showCount, showBars }: { e: IssueRow; showCount?: boolean; showBars?: boolean }) {
  const { openDrawer } = useApp();
  return (
    <button className="listbtn" style={{ gap: 6 }} onClick={() => openDrawer({ k: 'issue', id: e.id })}>
      <div className="listbtn-top"><span>{e.label}</span><span className="small muted nowrap">{e.where}</span></div>
      {showCount && <div className="small" style={{ color: 'var(--fg2)' }}>{e.count}</div>}
      {showBars && (
        <div className="small" style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 110px', gap: '4px 8px', alignItems: 'center', width: '100%' }}>
          <Meter w={e.youW} h8 /><span style={{ fontWeight: 600 }}>{e.youTxt}</span>
          <Meter w={e.othW} color="#9e9e9e" h8 /><span className="muted">{e.othTxt}</span>
        </div>
      )}
      <div className="row-wrap small"><Pill kind="thin" style={{ background: e.covBg, color: e.covFg }}>{e.cov}</Pill><span className="muted">{e.peers}</span></div>
    </button>
  );
}

export function Compare() {
  const { m, mob, tabTo, openDrawer, pickSector } = useApp();
  const { compare: c, isAll, cur, by } = m;
  const heatCols = `minmax(${mob ? '86px' : '170px'},1.6fr) repeat(9,minmax(0,1fr))`;
  const go = (k: string) => k === 'ag' ? tabTo('mentions', { mTab: 'ag' }) : k === 'rep' ? tabTo('mentions', { mTab: 'reports' }) : tabTo(k === 'dev' ? 'dev' : 'gaps');
  return (
    <>
      {!isAll && (
        <>
          <div className="grid g-200">
            {c.metrics.map(x => (
              <button key={x.key} className="tile" style={{ gap: 8 }} onClick={() => go(x.key)}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}><div className="s13 muted" style={{ flex: 1 }}>{x.label}</div><div className="cmp nowrap">{x.rank}</div></div>
                <div className="small" style={{ display: 'grid', gridTemplateColumns: '64px 1fr 28px', gap: '6px 8px', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600 }}>You</span><Meter w={x.youW} h8 /><span style={{ fontWeight: 600, textAlign: 'right' }}>{x.you}</span>
                  <span className="muted">Others’ median</span><Meter w={x.medW} color="#9e9e9e" h8 /><span className="muted" style={{ textAlign: 'right' }}>{x.med}</span>
                </div>
              </button>
            ))}
          </div>
          <div className="s13" style={{ color: 'var(--fg2)', marginTop: -8 }}>{c.netLine}</div>
        </>
      )}
      <div className="grid g-340">
        {!isAll && (
          <div className="card" style={{ gap: 4 }}>
            <div className="card-title">Raised elsewhere, not yet here</div>
            <div className="note" style={{ marginBottom: 6 }}>Early signals: topics that may reach your Parliament next</div>
            {c.quiet.map(e => <IssueButton key={e.id} e={e} showCount />)}
            {c.quiet.length === 0 && <div className="s13 muted" style={{ padding: '8px 0' }}>Nothing is being raised in two or more other parliaments that isn’t also raised here.</div>}
          </div>
        )}
        <div className="card" style={{ gap: 4 }}>
          <div className="card-title">{isAll ? 'Raised in several parliaments' : 'Shared with other parliaments'}</div>
          <div className="note" style={{ marginBottom: 6 }}>{isAll ? 'Ranked by total mentions' : `Issues ${cur!.parl} is discussing that others are too`}</div>
          {c.shared.map(e => <IssueButton key={e.id} e={e} showBars={!isAll} />)}
          {c.shared.length === 0 && <div className="s13 muted" style={{ padding: '8px 0' }}>No shared issues this period.</div>}
        </div>
      </div>
      <div className="card" style={{ gap: 8 }}>
        <div className="card-title">Sectors across parliaments</div>
        <div className="note">Your column is outlined. Select a sector name to filter every page, or a cell to see the issue behind it.</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3, marginTop: 4 }}>
          <div className="heat-row" style={{ gridTemplateColumns: heatCols, fontSize: 11 }}>
            <span />
            {m.ds.jurisdictions.map(j => <span key={j.code} style={{ textAlign: 'center', fontWeight: j.code === m.s.jur ? 700 : 600, color: j.code === m.s.jur ? 'var(--brand)' : 'var(--fg2)' }}>{j.short}</span>)}
          </div>
          {c.heat.map(row => (
            <div key={row.name} className="heat-row" style={{ gridTemplateColumns: heatCols }}>
              <button className={'lbl' + (row.on ? ' on' : '')} title={row.name} aria-pressed={row.on} onClick={() => pickSector(row.on ? null : row.name)}>{row.short}</button>
              {row.cells.map(cell => (
                <button key={cell.c} className={'cell' + (cell.you ? ' you' : '')} style={{ background: cell.bg }} aria-label={cell.aria}
                  onClick={() => cell.issueId && openDrawer({ k: 'issue', id: cell.issueId })}>{cell.n || ''}</button>
              ))}
            </div>
          ))}
        </div>
        <div className="note">Blank = not raised. Not-sitting parliaments show blank for the period. {by.WA.office} figures come from manual import only. {c.heatHidden ? `${c.heatHidden} sectors with no mentions this period are hidden.` : ''}</div>
      </div>
    </>
  );
}
