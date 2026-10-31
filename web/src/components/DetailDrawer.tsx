import { Button, DrawerBody, DrawerHeader, DrawerHeaderTitle, OverlayDrawer } from '@fluentui/react-components';
import { Dismiss24Regular } from '@fluentui/react-icons';
import { useApp } from '../ctx';
import { fmtDay, pct } from '../format';
import { COV, sentBar } from '../model';
import type { Code } from '../types';
import { CODES } from '../urlState';
import { INDEPENDENCE_NOTE } from '../pages/Gaps';
import { Meter, Pill, SecondaryBtn, SentBar, SentPill, SourceLink } from '../ui';

function ItemPanel({ id }: { id: string }) {
  const { m, openDrawer, openItem, adds, toggleAdd, copy, openShare } = useApp();
  const it = m.itemsAll.find(i => i.id === id);
  if (!it) return <Missing />;
  const v = m.itemView(it), j = v.j;
  let rel = m.itemsAll.filter(o => o.jur !== it.jur && o.theme === it.theme && o.sig >= 3 && m.inP(o)).slice(0, 3);
  if (!rel.length) rel = m.itemsAll.filter(o => o.jur !== it.jur && o.feat === it.feat && o.sig >= 3 && m.inP(o)).slice(0, 3);
  const inBrief = adds.includes(it.id), x = v.issue;
  const cite = `${it.speaker || j.office}, ${it.debate || 'website'}, ${j.parl}, ${fmtDay(it.date)} ${it.date.slice(0, 4)}, p. ${it.page}. ${it.url}`;
  return (
    <>
      <div className="row-wrap small">{[v.featLabel, it.theme, `Significance ${it.sig} of 5`].filter(Boolean).map(t => <Pill key={t} kind="plain">{t}</Pill>)}</div>
      <div style={{ fontSize: 20, fontWeight: 600, lineHeight: 1.25 }}>{it.headline}</div>
      <div className="s13 muted">{j.parl}{v.web ? '' : ' · ' + it.chamber} · {fmtDay(it.date)}</div>
      <div className="aibox">
        <div className="muted" style={{ fontSize: 11 }}>✦ AI summary — check the source</div>
        <div>{it.summary}</div>
        <div><b style={{ fontWeight: 600 }}>Why it matters:</b> {it.why}</div>
      </div>
      {v.sent && <div className="row-wrap s13"><SentPill v={v} /><span style={{ color: 'var(--fg2)' }}>{it.reason}</span></div>}
      {v.quote && <><div className="quote">{v.quote}</div>{!v.web && <div className="small" style={{ color: 'var(--ok)' }}>✓ Quote matches Hansard word for word</div>}</>}
      <div className="s13" style={{ color: 'var(--fg2)', borderTop: '1px solid var(--line)', paddingTop: 10 }}>{v.speaker}<br />{it.debate ? `${it.debate} · page ${it.page}` : 'Office website'}</div>
      <div className="row-wrap" style={{ gap: 8 }}>
        <SourceLink v={v} />
        <SecondaryBtn onClick={() => copy(cite, 'Citation copied')}>Copy citation</SecondaryBtn>
        <SecondaryBtn onClick={() => toggleAdd(it.id)}>{inBrief ? '✓ In your brief' : 'Add to brief'}</SecondaryBtn>
        <SecondaryBtn onClick={() => openShare(true)}>↗ Share</SecondaryBtn>
      </div>
      {x && (
        <button onClick={() => openDrawer({ k: 'issue', id: x.id })} style={{ display: 'flex', flexDirection: 'column', gap: 4, padding: 12, border: '1px solid var(--brand-line)', borderRadius: 4, background: 'var(--brand-tint2)', textAlign: 'left', font: 'inherit', color: 'inherit', cursor: 'pointer' }}>
          <span className="small" style={{ fontWeight: 600, color: 'var(--brand)' }}>↔ Compare across parliaments</span>
          <span className="s13">{x.label} — raised in {m.parlsFor(x).length} parliaments this period</span>
        </button>
      )}
      {rel.length > 0 && <>
        <div className="dsec">Related in other parliaments</div>
        {rel.map(o => { const ov = m.itemView(o); return <button key={o.id} className="reltn" onClick={() => openItem(o.id)}><span className="note">{ov.where}</span><span>{o.headline}</span></button>; })}
      </>}
    </>
  );
}

function GapPanel({ id }: { id: string }) {
  const { m, openItem, toast, openShare } = useApp();
  const gp = m.ds.gaps.find(g => g.id === id);
  if (!gp) return <Missing />;
  const g = m.gapView(gp);
  return (
    <>
      <div className="row-wrap small"><Pill style={{ background: g.covBg, color: g.covFg }}>{g.cov}</Pill><Pill kind="plain">{gp.theme}</Pill></div>
      <div style={{ fontSize: 20, fontWeight: 600, lineHeight: 1.25 }}>{g.issue}</div>
      <div className="s13"><b style={{ fontWeight: 600 }}>{gp.closest}.</b> {gp.why}</div>
      {g.hasPeers && <div className="s13" style={{ color: 'var(--fg2)', padding: '10px 12px', background: 'var(--brand-tint2)', borderRadius: 4 }}>↔ {g.peers}</div>}
      <div className="dsec">Why this score · {gp.score}/100</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {gp.parts.map(p => (
          <div key={p.n} className="small" style={{ display: 'grid', gridTemplateColumns: '150px 1fr 50px', gap: 8, alignItems: 'center' }}>
            <span>{p.n}</span><Meter w={pct(p.v, p.w)} color="var(--gap)" /><span className="muted" style={{ textAlign: 'right' }}>{p.v} / {p.w}</span>
          </div>
        ))}
      </div>
      <div className="dsec">Evidence · {g.evidence}</div>
      {g.evItems.map(o => { const ov = m.itemView(o); return <button key={o.id} className="reltn" onClick={() => openItem(o.id)}><span className="note">{ov.where}</span><span>{o.headline}</span></button>; })}
      <div className="row-wrap" style={{ gap: 8 }}>
        <SecondaryBtn onClick={() => toast('Added to the longlist export')}>Add to longlist export</SecondaryBtn>
        <SecondaryBtn onClick={() => openShare(true)}>↗ Share</SecondaryBtn>
      </div>
      <div className="note">{INDEPENDENCE_NOTE}</div>
    </>
  );
}

function ReportPanel({ id }: { id: string }) {
  const { m } = useApp();
  const r = m.ds.reports.find(x => x.id === id);
  if (!r) return <Missing />;
  const ms = m.mentions.reportMentions(r.jur, r.title), b = sentBar(ms), j = m.by[r.jur];
  return (
    <>
      <div style={{ fontSize: 20, fontWeight: 600, lineHeight: 1.25 }}>{r.title}</div>
      <div className="s13 muted">{j.officeName} · {r.no} · Tabled {r.tabled}</div>
      {ms.length > 0 ? <>
        <SentBar b={b} />
        <div className="note">{b.text}</div>
        {ms.map(it => { const v = m.itemView(it); return (
          <div key={it.id} style={{ display: 'flex', flexDirection: 'column', gap: 5, padding: '10px 0', borderTop: '1px solid var(--line2)' }}>
            <div className="row-wrap small"><SentPill v={v} /><span style={{ color: 'var(--fg2)' }}>{it.reason}</span></div>
            <div style={{ fontStyle: 'italic' }}>{v.quote}</div>
            <div className="note">{v.speaker} · {v.where}</div>
            <div><a href={it.url} target="_blank" rel="noopener" className="s13" style={{ fontWeight: 600 }}>{v.srcLabel}</a></div>
          </div>
        ); })}
      </> : <div className="s13" style={{ padding: 12, border: '1px dashed #bdbdbd', borderRadius: 4, color: 'var(--fg2)' }}>Not yet mentioned in Parliament since it was tabled.</div>}
      <div><a href={j.site} target="_blank" rel="noopener" className="s13" style={{ fontWeight: 600 }}>Open on the office website ↗</a></div>
    </>
  );
}

function IssuePanel({ id }: { id: string }) {
  const { m, tabTo, toast, openItem, openShare } = useApp();
  const x = m.ds.issues.find(i => i.id === id);
  if (!x) return <Missing />;
  const per = CODES.map(c => ({ c, n: m.rN(x, c) })), total = per.reduce((a, p) => a + p.n, 0), mx = Math.max(1, ...per.map(p => p.n));
  const linked = m.itemsAll.filter(i => i.x === x.id && m.inP(i)).sort((a, b) => b.date.localeCompare(a.date));
  const cols = 'minmax(0,1.3fr) minmax(0,1fr) 28px minmax(0,1fr)';
  return (
    <>
      <div className="row-wrap small"><Pill kind="plain">{x.theme}</Pill></div>
      <div style={{ fontSize: 20, fontWeight: 600, lineHeight: 1.25 }}>{x.label}</div>
      <div className="s13 muted">{total} mentions across {per.filter(p => p.n).length} parliaments · {m.P.range}</div>
      {!m.isAll && <div className="s13" style={{ padding: '10px 12px', background: 'var(--brand-tint2)', borderRadius: 4 }}><b style={{ fontWeight: 600 }}>{COV[m.covOf(x, m.s.jur as Code)].label}.</b> {m.peerLine(x, m.s.jur as Code)}</div>}
      <div>
        <div className="muted" style={{ display: 'grid', gridTemplateColumns: cols, gap: 8, fontSize: 11, padding: '0 6px 4px' }}><span>Parliament</span><span>Mentions</span><span /><span>Office program</span></div>
        {per.map(({ c, n }) => {
          const j = m.by[c], cv = m.covOf(x, c), you = c === m.s.jur;
          return (
            <div key={c} className="small" style={{ display: 'grid', gridTemplateColumns: cols, gap: 8, alignItems: 'center', padding: 6, borderRadius: 4, background: you ? 'var(--brand-tint2)' : 'transparent' }}>
              <span style={{ fontWeight: you ? 700 : 400 }}>{j.name}{you ? ' (you)' : ''}</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>{n > 0 ? <Meter w={pct(n, mx)} /> : <span className="muted nowrap" style={{ fontSize: 11 }}>{m.notSitting(c) ? 'Not sitting' : j.status === 'blocked' ? 'Not checked' : 'Not raised'}</span>}</span>
              <span style={{ textAlign: 'right' }}>{n || ''}</span>
              <span style={{ color: cv === 'not_covered' ? 'var(--fg3)' : cv === 'recent_report' ? 'var(--ok)' : 'var(--brand)' }}>{m.COV_SHORT[cv]}</span>
            </div>
          );
        })}
      </div>
      <div className="quote grey">“{x.quote}”</div>
      <div className="note">{x.by} · {m.by[x.from].parl} · <a href={m.by[x.from].url} target="_blank" rel="noopener">Open in Hansard ↗</a></div>
      <div className="row-wrap" style={{ gap: 8 }}>
        <Button appearance="primary" className="btn-m" onClick={() => tabTo('explore', { q: x.kw, expJur: false })}>Search all Hansard for this</Button>
        <SecondaryBtn onClick={() => toast('Added to your brief')}>Add to brief</SecondaryBtn>
        <SecondaryBtn onClick={() => openShare(true)}>↗ Share</SecondaryBtn>
      </div>
      {linked.length > 0 && <>
        <div className="dsec">Summarised items</div>
        {linked.map(o => { const ov = m.itemView(o); return <button key={o.id} className="reltn" onClick={() => openItem(o.id)}><span className="note">{ov.where}</span><span>{o.headline}</span></button>; })}
      </>}
    </>
  );
}

const Missing = () => <div className="s13 muted">This item is no longer in the stored window.</div>;

export function DetailDrawer() {
  const { m, mob, set } = useApp();
  const d = m.s.drawer;
  const title = d ? { item: 'Details', gap: 'Potential gap', rep: 'Report', issue: 'Across parliaments' }[d.k] : '';
  return (
    <OverlayDrawer position="end" open={!!d} onOpenChange={(_, e) => !e.open && set({ drawer: null })} style={{ width: mob ? '100%' : 480 }} aria-label={title}>
      <DrawerHeader style={{ borderBottom: '1px solid var(--line)', padding: '12px 12px 12px 20px' }}>
        <DrawerHeaderTitle action={<Button appearance="subtle" aria-label="Close" icon={<Dismiss24Regular />} onClick={() => set({ drawer: null })} />}>
          <span style={{ fontSize: 16 }}>{title}</span>
        </DrawerHeaderTitle>
      </DrawerHeader>
      <DrawerBody style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
        {d?.k === 'item' && <ItemPanel id={d.id} />}
        {d?.k === 'gap' && <GapPanel id={d.id} />}
        {d?.k === 'rep' && <ReportPanel id={d.id} />}
        {d?.k === 'issue' && <IssuePanel id={d.id} />}
      </DrawerBody>
    </OverlayDrawer>
  );
}
