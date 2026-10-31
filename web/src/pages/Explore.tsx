import { Input } from '@fluentui/react-components';
import { Search20Regular } from '@fluentui/react-icons';
import { useApp } from '../ctx';
import type { SentFilter } from '../urlState';
import { Chip, Pill, SecondaryBtn, SentPill } from '../ui';

function Highlight({ text, q }: { text: string; q: string }) {
  if (!q) return <>{text}</>;
  const out: React.ReactNode[] = [], low = text.toLowerCase();
  let k = 0;
  for (let n = 0; n < 20; n++) {
    const f = low.indexOf(q, k);
    if (f < 0) break;
    out.push(text.slice(k, f), <mark key={n} className="hl" style={{ color: 'inherit' }}>{text.slice(f, f + q.length)}</mark>);
    k = f + q.length;
  }
  out.push(text.slice(k));
  return <>{out}</>;
}

export function Explore() {
  const { m, set, openItem } = useApp();
  const { explore: e, s, isAll, cur, by } = m;
  return (
    <>
      <div style={{ display: 'flex', gap: 8 }}>
        <Input value={s.q} onChange={(_, d) => set({ q: d.value })} placeholder="Search Hansard — try “consultants” or “wait times”" aria-label="Search Hansard"
          contentBefore={<Search20Regular />} size="large" style={{ flex: 1 }} />
        {s.q && <SecondaryBtn onClick={() => set({ q: '' })}>Clear</SecondaryBtn>}
      </div>
      <div className="row-wrap">
        <Chip on={!isAll && s.expJur} onClick={() => set({ expJur: !s.expJur })}>{isAll ? 'All jurisdictions' : s.expJur ? `Only ${cur!.name}` : 'All 9 jurisdictions'}</Chip>
        <Chip on={s.newOnly} onClick={() => set({ newOnly: !s.newOnly })}>New since your last visit</Chip>
        {(['Any', 'Positive', 'Neutral', 'Negative', 'Mixed'] as SentFilter[]).map(x => <Chip key={x} on={s.expSent === x} onClick={() => set({ expSent: x })}>{x === 'Any' ? 'Any sentiment' : x}</Chip>)}
      </div>
      <div className="s13" style={{ fontWeight: 600 }} role="status">{e.count} {e.count === 1 ? 'result' : 'results'}{s.expJur && !isAll ? ` in ${cur!.name}` : ' across 9 parliaments'}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {e.results.map(v => (
          <button key={v.it.id} className="tile" style={{ gap: 5 }} onClick={() => openItem(v.it.id)}>
            <div className="row-wrap small">
              <span className="dot" style={{ background: by[v.it.jur].color }} />
              <span className="muted nowrap">{v.where}</span><span className="muted">· {v.it.debate || 'Office website'}</span>
              <SentPill v={v} thin />{v.isNew && <Pill kind="new thin">New</Pill>}
            </div>
            <div style={{ fontSize: 15, fontWeight: 600 }}>{v.it.headline}</div>
            <div className="s13" style={{ color: 'var(--fg2)' }}><Highlight text={v.quote || v.it.summary} q={e.q} /></div>
            <div className="note">{v.speaker}</div>
          </button>
        ))}
        {e.count === 0 && <div className="card dashed s13 muted">No matches. Try fewer words, or include all 9 jurisdictions.</div>}
      </div>
    </>
  );
}
