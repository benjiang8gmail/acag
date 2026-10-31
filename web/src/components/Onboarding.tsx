import { Button } from '@fluentui/react-components';
import { useState } from 'react';
import type { Jurisdiction, JurCode } from '../types';
import type { Tab } from '../urlState';
import { Chip } from '../ui';

const STARTS: [Tab, string][] = [['brief', 'Brief'], ['compare', 'Compare'], ['mentions', 'Mentions'], ['dev', 'Developments'], ['gaps', 'Potential gaps'], ['explore', 'Explore']];

export function Onboarding({ jurisdictions, initialJur, initialStart, onFinish }: { jurisdictions: Jurisdiction[]; initialJur: JurCode | null; initialStart: Tab; onFinish: (j: JurCode, t: Tab) => void }) {
  const [jur, setJur] = useState<JurCode | null>(initialJur);
  const [start, setStart] = useState<Tab>(initialStart);
  const opts = [...jurisdictions.map(j => ({ code: j.code as JurCode, short: j.short, name: j.name, officeName: j.officeName })), { code: 'ALL' as JurCode, short: 'All', name: 'All jurisdictions', officeName: 'ACAG — all offices' }];
  return (
    <div className="ob">
      <div className="ob-scroll">
        <div className="ob-card">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div className="s13" style={{ fontWeight: 600, color: 'var(--brand)' }}>Hansard Watch</div>
            <h1 style={{ fontSize: 22, lineHeight: 1.25 }}>Which jurisdiction are you from?</h1>
            <div className="muted">We’ll start with your Parliament and audit office, then show how the other 8 compare. You can switch at any time from the top bar.</div>
          </div>
          <div className="ob-grid" role="radiogroup" aria-label="Your jurisdiction">
            {opts.map(o => (
              <button key={o.code} role="radio" aria-checked={jur === o.code} className={'ob-jur' + (jur === o.code ? ' on' : '')} onClick={() => setJur(o.code)}>
                <div className="ob-badge">{o.short}</div>
                <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}><div style={{ fontWeight: 600 }}>{o.name}</div><div className="note">{o.officeName}</div></div>
                <div style={{ color: 'var(--brand)', fontWeight: 700 }}>{jur === o.code ? '✓' : ''}</div>
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontWeight: 600 }}>What do you want to see first?</div>
            <div className="row-wrap">{STARTS.map(([k, l]) => <Chip key={k} square on={start === k} onClick={() => setStart(k)}>{l}</Chip>)}</div>
          </div>
        </div>
      </div>
      <div className="ob-foot">
        <div>
          <div className="note" style={{ flex: 1 }}>{jur ? 'Saved on this device · no sign-in needed' : 'Choose your jurisdiction to continue'}</div>
          <Button appearance="primary" size="large" disabled={!jur} onClick={() => jur && onFinish(jur, start)} style={{ minHeight: 44, padding: '0 24px' }}>Continue</Button>
        </div>
      </div>
    </div>
  );
}
