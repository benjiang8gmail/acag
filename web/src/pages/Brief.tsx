import { Button } from '@fluentui/react-components';
import { useApp } from '../ctx';
import type { ItemView } from '../model';
import { Meter, Segmented, SecondaryBtn, SentBar, SentPill, SourceLink, Pill } from '../ui';

function HeroCard({ v }: { v: ItemView }) {
  const { openItem, markSeen, openDrawer } = useApp();
  return (
    <div className="card raised">
      <div className="row-wrap small">
        <Pill kind="brand">{v.featLabel}</Pill>
        {v.isNew && <Pill kind="new">New</Pill>}
        <span className="muted nowrap">{v.where}</span>
      </div>
      <button className="headline-btn" onClick={() => openItem(v.it.id)}>{v.it.headline}</button>
      <div className="s13" style={{ color: 'var(--fg2)' }}>{v.it.why}</div>
      {v.sent && <div className="row-wrap"><SentPill v={v} /></div>}
      {v.echo && v.issue && <button className="linkbtn small" style={{ minHeight: 0, padding: 0, textAlign: 'left', fontWeight: 400 }} onClick={() => openDrawer({ k: 'issue', id: v.issue!.id })}>↔ {v.echo}</button>}
      <div className="actions">
        <SourceLink v={v} onOpen={() => markSeen(v.it.id)} />
        <SecondaryBtn onClick={() => openItem(v.it.id)}>Details</SecondaryBtn>
      </div>
    </div>
  );
}

export function Brief() {
  const { m, set, tabTo, openDrawer, setJur, pickSector, adds, openItem } = useApp();
  const { brief: b, isAll, cur, s } = m;
  const gh = b.gapHero;
  const quiet = b.hero.length === 0 && (!isAll || !!s.sector);
  const goTile = (k: string) => k === 'ag' ? tabTo('mentions', { mTab: 'ag' }) : k === 'rep' ? tabTo('mentions', { mTab: 'reports' }) : tabTo(k === 'dev' ? 'dev' : 'gaps');
  const added = adds.map(id => m.itemsAll.find(i => i.id === id)).filter(Boolean).map(i => m.itemView(i!));

  return (
    <>
      <div className="grid g-hero">
        {b.hero.map(v => <HeroCard key={v.it.id} v={v} />)}
        {gh && (
          <div className="card raised">
            <div className="row-wrap small"><Pill kind="gap">Potential program gap</Pill><span className="muted nowrap">{gh.office}{gh.g.theme}</span></div>
            <button className="headline-btn" onClick={() => openDrawer({ k: 'gap', id: gh.g.id })}>{gh.issue}</button>
            <div className="s13" style={{ color: 'var(--fg2)' }}>{gh.g.closest}</div>
            <div className="row-wrap small muted" style={{ flexWrap: 'nowrap', gap: 8 }}><Meter w={gh.g.score + '%'} color="var(--gap)" /><span className="nowrap">Attention {gh.g.score}/100</span></div>
            {gh.hasPeers && <div className="small" style={{ color: 'var(--fg2)' }}>↔ {gh.peers}</div>}
            <div className="actions"><Button appearance="primary" className="btn-m" onClick={() => openDrawer({ k: 'gap', id: gh.g.id })}>See the evidence</Button></div>
          </div>
        )}
        {quiet && (
          <div className="card dashed">
            <div style={{ fontSize: 15, fontWeight: 600 }}>{s.sector ? `Nothing on ${m.lc(m.secShort)} in ${isAll ? 'any parliament' : cur!.parl} this period.` : `${cur!.parl}: ${m.lc(cur!.statusText)}.`}</div>
            <div className="s13 muted">{s.sector ? 'Try another sector, or widen the period.' : 'This is expected — the territory parliaments sit less often. Other parliaments’ activity is still below.'}</div>
            <div><SecondaryBtn onClick={() => s.sector ? pickSector(null) : set({ period: '4w' })}>{s.sector ? 'Show all sectors' : 'Show the last 4 weeks'}</SecondaryBtn></div>
          </div>
        )}
      </div>
      <div className="note" style={{ marginTop: -8 }}>✦ Summaries are AI-generated — check the source before relying on them.</div>

      <div className="grid g-tiles">
        {b.tiles.map(t => (
          <button key={t.key} className="tile" onClick={() => goTile(t.key)}>
            <div className="s13 muted">{t.label}</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}><div className="tile-n">{t.n}</div><div className="small nowrap" style={{ color: 'var(--fg2)' }}>{t.delta}</div></div>
            {t.bar && <SentBar b={t.bar} thin />}
            <div className="note">{t.sub}</div>
            {!isAll && <div className="cmp">{t.cmp}</div>}
          </button>
        ))}
      </div>

      <div className="grid g-300">
        <div className="card" style={{ gap: 12 }}>
          {!isAll ? (
            <>
              <div className="row-wrap" style={{ gap: 8 }}>
                <div className="card-title nowrap" style={{ flex: 1 }}>Across Australia</div>
                <Segmented label="Map shows" value={s.mapMode} onChange={v => set({ mapMode: v })} options={[['mentions', 'Mentions'], ['net', 'Net sentiment'], ['gaps', 'Gaps']]} />
              </div>
              <div className="ausmap">
                {b.mapTiles.map(t => (
                  <button key={t.c} className={t.you ? 'you' : ''} aria-label={`${t.j.name}: ${t.val}`} onClick={() => setJur(t.c)}
                    style={{ gridRow: t.j.tilePos[0], gridColumn: t.j.tilePos[1], background: t.bg }}>
                    <span className="s13" style={{ fontWeight: 600 }}>{t.j.short}</span><span className="s13">{t.val}</span><span style={{ fontSize: 10, color: 'var(--fg3)' }}>{t.note}</span>
                  </button>
                ))}
              </div>
              <div className="note">{{ mentions: 'Darker = more mentions of that Auditor-General.', net: 'Green = more positive, red = more negative. Counts shown under 5 mentions.', gaps: 'Potential program gaps per office.' }[s.mapMode]} Your jurisdiction is outlined — tap another to see it.</div>
            </>
          ) : (
            <>
              <div className="card-title">All 9 offices</div>
              <div className="trow small muted" style={{ gridTemplateColumns: 'minmax(0,1.6fr) repeat(4,minmax(0,1fr))', border: 'none', cursor: 'default', minHeight: 0, padding: '0 8px', background: 'none' }}>
                <span>Office</span><span title="Auditor-General mentions">Mentions</span><span title="Report mentions">Reports</span><span>Developments</span><span title="Potential program gaps">Gaps</span>
              </div>
              <div>
                {b.allRows.map(r => (
                  <button key={r.c} className="trow" style={{ gridTemplateColumns: 'minmax(0,1.6fr) repeat(4,minmax(0,1fr))' }} onClick={() => setJur(r.c)}>
                    <span style={{ fontWeight: 600 }}>{r.name}</span><span>{r.ag} <span className="muted" style={{ fontSize: 11 }}>{r.net}</span></span><span>{r.rep}</span><span>{r.dev}</span><span>{r.gaps}</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
        <div className="card">
          <div className="card-head"><div className="card-title">{isAll ? 'Raised in several parliaments' : 'Raised elsewhere, not yet here'}</div><button className="linkbtn" onClick={() => tabTo('compare')}>Compare ›</button></div>
          <div className="note" style={{ marginBottom: 4 }}>{isAll ? 'Issues more than one parliament is discussing' : `Issues other parliaments are discussing that ${cur!.parl} hasn’t raised this period`}</div>
          {b.elseRows.map(e => (
            <button key={e.id} className="listbtn" onClick={() => openDrawer({ k: 'issue', id: e.id })}>
              <div className="listbtn-top"><span>{e.label}</span><span className="small muted nowrap">{e.where}</span></div>
              <div className="row-wrap small"><Pill kind="thin" style={{ background: e.covBg, color: e.covFg }}>{e.cov}</Pill><span className="muted">{e.peers}</span></div>
            </button>
          ))}
          {b.elseRows.length === 0 && <div className="s13 muted">Nothing raised elsewhere that isn’t also being discussed here.</div>}
        </div>
      </div>

      <div className="grid g-300">
        <div className="card" style={{ gap: 2 }}>
          <div className="card-head"><div className="card-title">By sector</div><button className="linkbtn" onClick={() => tabTo('compare')}>All sectors ›</button></div>
          <div className="note" style={{ marginBottom: 6 }}>{isAll ? 'Mentions across all 9 parliaments' : `Mentions in ${cur!.parl}, and in the other 8`}</div>
          {b.secRows.map(o => (
            <button key={o.name} className="trow s13" aria-pressed={o.on} onClick={() => pickSector(o.on ? null : o.name)}
              style={{ gridTemplateColumns: 'minmax(0,1.3fr) minmax(0,1fr) 96px', gap: 8, padding: '4px 6px', background: o.on ? 'var(--brand-tint2)' : undefined }}>
              <span style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{o.label}</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Meter w={o.w} /><span style={{ fontWeight: 600, minWidth: 18, textAlign: 'right' }}>{o.n}</span></span>
              <span className="note nowrap">{o.oth}</span>
            </button>
          ))}
          <div className="note" style={{ marginTop: 6 }}>Select a sector to filter every page. Select it again to clear.</div>
        </div>
        <div className="card">
          <div className="card-title">Coming up</div>
          {m.ds.status.upcomingSittings.map(n => (
            <div key={n.d} className="s13" style={{ display: 'flex', gap: 12, padding: '6px 0', borderBottom: '1px solid var(--line2)' }}><div style={{ width: 96, flex: 'none', fontWeight: 600 }}>{n.d}</div><div style={{ flex: 1, color: 'var(--fg2)' }}>{n.p}</div></div>
          ))}
          <div className="note">Hansard is checked automatically every morning.</div>
        </div>
        {added.length > 0 && (
          <div className="card">
            <div className="card-title">Added to your brief</div>
            {added.map(v => (
              <button key={v.it.id} className="listbtn" style={{ flexDirection: 'row', gap: 8, padding: '8px 0' }} onClick={() => openItem(v.it.id)}>
                <span style={{ flex: 1, fontWeight: 600 }}>{v.it.headline}</span><span className="small muted nowrap">{v.where}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
