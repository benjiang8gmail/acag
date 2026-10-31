import { useApp } from '../ctx';
import { fmtRange } from '../format';
import { Meter, Pill, SecondaryBtn } from '../ui';

export const INDEPENDENCE_NOTE = 'Prepared from public sources. Each Auditor-General sets their own program; parliamentary attention is one input among many.';

export function Gaps() {
  const { m, openDrawer } = useApp();
  const { gaps, isAll, cur, ds } = m;
  return (
    <>
      <div className="info"><span style={{ color: 'var(--brand)' }}>ⓘ</span><span>{INDEPENDENCE_NOTE} Based on Hansard from {fmtRange(ds.status.storedFrom, ds.status.asOf)} {ds.status.asOf.slice(0, 4)}.</span></div>
      {!isAll && cur!.program && (
        <div className="card" style={{ padding: '14px 16px', flexDirection: 'row', flexWrap: 'wrap', gap: '8px 16px', alignItems: 'center' }}>
          <div style={{ flex: '1 1 240px', display: 'flex', flexDirection: 'column', gap: 2 }}>
            <div style={{ fontWeight: 600 }}>{cur!.program}</div>
            {cur!.counts && <div className="note">{cur!.counts[0]} planned · {cur!.counts[1]} in progress · {cur!.counts[2]} tabled</div>}
          </div>
          <Pill style={cur!.confirmed ? { background: '#f1faf1', color: 'var(--ok)' } : { background: '#fff4ec', color: 'var(--warn)' }}>{cur!.confirmed ? 'Topics confirmed' : 'Draft — program not yet confirmed'}</Pill>
        </div>
      )}
      {!isAll && !cur!.program && <div className="info warn"><span style={{ color: 'var(--warn)' }}>⚠</span><span>{cur!.office} has no published forward program. Issues are compared with its recent reports only.</span></div>}
      <div className="stack">
        {gaps.shown.map(g => (
          <div key={g.g.id} className="card" style={{ flexDirection: 'row', gap: 12, alignItems: 'flex-start' }}>
            <div style={{ flex: 'none', width: 28, height: 28, borderRadius: '50%', background: 'var(--line2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: 13 }}>{g.rank}</div>
            <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 7 }}>
              <button className="headline-btn" onClick={() => openDrawer({ k: 'gap', id: g.g.id })}>{g.issue}</button>
              <div className="row-wrap small"><Pill style={{ background: g.covBg, color: g.covFg }}>{g.cov}</Pill><span className="muted">{g.office}{g.g.theme} · {g.evidence} · {g.raised}</span></div>
              <div className="small" style={{ display: 'flex', alignItems: 'center', gap: 8, maxWidth: 360 }}><Meter w={g.g.score + '%'} color="var(--gap)" /><span className="nowrap" style={{ fontWeight: 600 }}>Attention {g.g.score}/100</span></div>
              <div className="s13"><b style={{ fontWeight: 600 }}>{g.g.closest}.</b> {g.g.why}</div>
              {g.g.lastAudited && <div className="note">{g.g.lastAudited}</div>}
              {g.hasPeers && <div className="small" style={{ color: 'var(--fg2)' }}>↔ {g.peers}</div>}
              <div><SecondaryBtn onClick={() => openDrawer({ k: 'gap', id: g.g.id })}>Evidence and score</SecondaryBtn></div>
            </div>
          </div>
        ))}
        {gaps.shown.length === 0 && <div className="card dashed s13 muted">No potential gaps scored 40 or more this period.</div>}
        {gaps.hidden > 0 && <div className="note">{gaps.hidden} {gaps.hidden === 1 ? 'issue' : 'issues'} below the threshold (score 40) not shown</div>}
      </div>
      {!isAll && cur!.program && (
        <div className="card" style={{ gap: 4 }}>
          <div className="card-title">Program topics in the spotlight</div>
          <div className="note" style={{ marginBottom: 6 }}>Planned topics Parliament is discussing now — useful for scoping and timing</div>
          {[[cur!.topicA, 'Raised 4 times this period'], [cur!.topicB, 'Raised twice this period']].map(([t, n]) => (
            <div key={t} className="s13" style={{ display: 'flex', gap: 8, padding: '8px 0', borderTop: '1px solid var(--line2)' }}><span style={{ flex: 1, fontWeight: 600 }}>{t}</span><span className="muted">{n}</span></div>
          ))}
        </div>
      )}
    </>
  );
}
