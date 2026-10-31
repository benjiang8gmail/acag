import { Button } from '@fluentui/react-components';
import type { ReactNode } from 'react';
import type { SentBar as SentBarData } from './model';
import type { ItemView } from './model';

export function SentBar({ b, thin }: { b: Pick<SentBarData, 'pos' | 'neu' | 'mix' | 'neg'>; thin?: boolean }) {
  return (
    <div className={'sbar' + (thin ? ' thin' : '')} aria-hidden>
      <span style={{ width: b.pos, background: '#107c10' }} />
      <span style={{ width: b.neu, background: '#bdbdbd' }} />
      <span style={{ width: b.mix, background: '#f7630c' }} />
      <span style={{ width: b.neg, background: '#c50f1f' }} />
    </div>
  );
}

export const Meter = ({ w, color = '#0f6cbd', h8 }: { w: string; color?: string; h8?: boolean }) => (
  <span className={'meter' + (h8 ? ' h8' : '')} aria-hidden><span style={{ width: w, background: color }} /></span>
);

export const SentPill = ({ v, thin }: { v: ItemView; thin?: boolean }) =>
  v.sent ? <span className={'pill' + (thin ? ' thin' : '')} style={{ background: v.sent.bg, color: v.sent.fg }}>{v.sent.icon} {v.sent.label}</span> : null;

export const Pill = ({ children, kind = '', style }: { children: ReactNode; kind?: string; style?: React.CSSProperties }) =>
  <span className={'pill ' + kind} style={style}>{children}</span>;

export function Chip({ on, onClick, children, square }: { on: boolean; onClick: () => void; children: ReactNode; square?: boolean }) {
  return <button className={'chip' + (on ? ' on' : '') + (square ? ' square' : '')} aria-pressed={on} onClick={onClick}>{children}</button>;
}

export function Segmented<T extends string>({ value, options, onChange, label }: { value: T; options: [T, string][]; onChange: (v: T) => void; label: string }) {
  return (
    <div className="seg" role="radiogroup" aria-label={label}>
      {options.map(([k, l]) => <button key={k} role="radio" aria-checked={value === k} className={value === k ? 'on' : ''} onClick={() => onChange(k)}>{l}</button>)}
    </div>
  );
}

/** "Open in Hansard ↗" — the primary action on every item. */
export const SourceLink = ({ v, onOpen }: { v: ItemView; onOpen?: () => void }) => (
  <Button as="a" appearance="primary" className="btn-m" href={v.it.url} target="_blank" rel="noopener" onClick={onOpen}>{v.srcLabel}</Button>
);

export const SecondaryBtn = ({ children, onClick }: { children: ReactNode; onClick: () => void }) => (
  <Button appearance="secondary" className="btn-m" onClick={onClick}>{children}</Button>
);
