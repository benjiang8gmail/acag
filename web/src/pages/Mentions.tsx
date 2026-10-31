import { Tab, TabList } from '@fluentui/react-components';
import { useApp } from '../ctx';
import { CODES, type Side } from '../urlState';
import { Chip, Pill, SecondaryBtn, SentBar, SentPill, SourceLink } from '../ui';

export function Mentions() {
  const { m, mob, set, openItem, markSeen, openDrawer } = useApp();
  const { mentions: x, by, s } = m;
  return (
    <>
      <TabList selectedValue={s.mTab} onTabSelect={(_, d) => set({ mTab: d.value as 'ag' | 'reports' })} style={{ borderBottom: '1px solid var(--line)' }}>
        <Tab value="ag">Auditors-General</Tab>
        <Tab value="reports">Reports</Tab>
      </TabList>

      {s.mTab === 'ag' && (
        <>
          <div className="card" style={{ padding: 8, gap: 0 }}>
            {!mob && (
              <div className="small muted" style={{ display: 'flex', gap: 12, padding: '6px 10px' }}>
                <span style={{ flex: '1 1 220px' }}>Office</span><span style={{ flex: '0 0 70px' }}>Own parl.</span><span style={{ flex: '0 0 70px' }}>Elsewhere</span>
                <span style={{ flex: '1 1 160px' }}>Sentiment</span><span style={{ flex: '0 0 50px' }}>Net</span><span style={{ flex: '0 0 270px' }}>By side</span>
              </div>
            )}
            {x.agRows.map(a => (
              <button key={a.c} className={'agrow' + (a.sel ? ' sel' : '')} aria-pressed={a.sel} onClick={() => set({ agSel: a.c })}>
                <span style={{ flex: '1 1 220px', display: 'flex', gap: 6, alignItems: 'baseline', minWidth: 0 }}>
                  <b style={{ fontWeight: 600 }}>{a.j.officeName}</b>
                  {a.you && <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--brand)' }}>You</span>}
                  <span className="muted" style={{ fontSize: 11 }}>{a.note}</span>
                </span>
                <span style={{ flex: '0 0 70px' }}>{a.own}</span>
                <span className="muted" style={{ flex: '0 0 70px' }}>{a.elsewhere}</span>
                <span style={{ flex: '1 1 160px' }}><SentBar b={a.bar} /></span>
                <span style={{ flex: '0 0 50px', fontWeight: 600 }}>{a.net}</span>
                <span className="note" style={{ flex: '0 0 270px' }}>{a.sides}</span>
              </button>
            ))}
          </div>
          <div className="card" style={{ gap: 10 }}>
            <div className="row-wrap" style={{ gap: 8 }}>
              <div className="card-title" style={{ flex: '1 1 220px' }}>Mentions of {by[x.agSel].officeName}</div>
              <div className="row-wrap">{(['All', 'Government', 'Opposition', 'Crossbench'] as Side[]).map(sd => <Chip key={sd} on={s.side === sd} onClick={() => set({ side: sd })}>{sd}</Chip>)}</div>
            </div>
            {x.agMentions.map(v => (
              <div key={v.it.id} style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '12px 0', borderTop: '1px solid var(--line2)' }}>
                <div className="row-wrap small"><SentPill v={v} /><span style={{ color: 'var(--fg2)' }}>{v.it.reason}</span>{v.isNew && <Pill kind="new">New</Pill>}</div>
                <div style={{ fontStyle: 'italic' }}>{v.quote}</div>
                <div className="note">{v.speaker} · {v.where}</div>
                <div className="row-wrap" style={{ gap: 8 }}><SourceLink v={v} onOpen={() => markSeen(v.it.id)} /><SecondaryBtn onClick={() => openItem(v.it.id)}>Details</SecondaryBtn></div>
              </div>
            ))}
            {x.agMentions.length === 0 && <div className="s13 muted">No mentions in this period.</div>}
          </div>
        </>
      )}

      {s.mTab === 'reports' && (
        <>
          <div className="row-wrap">
            {CODES.map(c => <Chip key={c} on={c === x.repOff} onClick={() => set({ repOff: c })}>{by[c].short}</Chip>)}
            <span style={{ flex: 1 }} />
            <Chip square on={s.notYet} onClick={() => set({ notYet: !s.notYet })}>{s.notYet ? '✓ ' : ''}Not yet mentioned only</Chip>
          </div>
          <div className="card" style={{ padding: '8px 16px', gap: 0 }}>
            <div className="s13 muted" style={{ padding: '8px 0' }}>{by[x.repOff].officeName} · report register · mentions across the stored window</div>
            {x.repRows.map(r => (
              <button key={r.r.id} className="listbtn" style={{ flexDirection: 'row', flexWrap: 'wrap', gap: '6px 16px', alignItems: 'center', padding: '12px 0' }} onClick={() => openDrawer({ k: 'rep', id: r.r.id })}>
                <span style={{ flex: '1 1 260px', display: 'flex', flexDirection: 'column', gap: 2 }}><b style={{ fontWeight: 600 }}>{r.r.title}</b><span className="note">{r.r.no} · Tabled {r.r.tabled}</span></span>
                <span className="s13" style={{ flex: '0 0 90px' }}>{r.n} mentions</span>
                {r.n > 0
                  ? <span style={{ flex: '1 1 160px', display: 'flex', flexDirection: 'column', gap: 3 }}><SentBar b={r.bar} /><span className="muted" style={{ fontSize: 11 }}>{r.last}</span></span>
                  : <span style={{ flex: '1 1 160px' }}><Pill>Not yet mentioned in Parliament</Pill></span>}
              </button>
            ))}
            {x.repRows.length === 0 && <div className="s13 muted" style={{ padding: '12px 0' }}>Every report has been mentioned.</div>}
          </div>
        </>
      )}
    </>
  );
}
