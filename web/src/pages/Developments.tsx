import { useApp } from '../ctx';
import { Chip, Pill, SecondaryBtn, SourceLink } from '../ui';

export function Developments() {
  const { m, set, openItem, markSeen } = useApp();
  const { dev, s } = m;
  return (
    <>
      <div className="row-wrap">{dev.devTypes.map(o => <Chip key={o.t} on={s.devType === o.t} onClick={() => set({ devType: o.t })}>{o.t} {o.n}</Chip>)}</div>
      <div className="stack">
        {dev.devList.map(v => (
          <div key={v.it.id} className="card" style={{ padding: '14px 16px' }}>
            <div className="row-wrap small">
              <Pill kind="brand">{v.featLabel}</Pill>
              <Pill style={v.web ? { background: '#fff4ec', color: 'var(--warn)' } : undefined}>{v.web ? 'Office website' : 'Hansard'}</Pill>
              {v.isNew && <Pill kind="new">New</Pill>}
              <span className="muted nowrap">{v.where}</span>
            </div>
            <button className="headline-btn" onClick={() => openItem(v.it.id)}>{v.it.headline}</button>
            <div className="s13" style={{ color: 'var(--fg2)' }}><b style={{ fontWeight: 600 }}>Why it matters:</b> {v.it.why}</div>
            <div className="row-wrap" style={{ gap: 8, paddingTop: 2 }}><SourceLink v={v} onOpen={() => markSeen(v.it.id)} /><SecondaryBtn onClick={() => openItem(v.it.id)}>Details</SecondaryBtn></div>
          </div>
        ))}
        {dev.devList.length === 0 && <div className="card dashed s13 muted">No developments in this period.</div>}
      </div>
      {dev.devElse.length > 0 && (
        <div className="card" style={{ gap: 4 }}>
          <div className="card-title">Meanwhile, at other audit offices</div>
          <div className="note" style={{ marginBottom: 6 }}>Major changes elsewhere that could set a precedent for you</div>
          {dev.devElse.map(v => (
            <button key={v.it.id} className="listbtn" style={{ flexDirection: 'row', flexWrap: 'wrap', gap: '4px 10px', alignItems: 'baseline' }} onClick={() => openItem(v.it.id)}>
              <Pill kind="brand thin">{v.featLabel}</Pill><span style={{ flex: '1 1 240px', fontWeight: 600 }}>{v.it.headline}</span><span className="small muted nowrap">{v.where}</span>
            </button>
          ))}
        </div>
      )}
    </>
  );
}
