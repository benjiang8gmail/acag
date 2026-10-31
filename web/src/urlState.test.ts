import { describe, expect, it } from 'vitest';
import { fromQuery, toQuery, viewDefaults } from './urlState';

const SECTORS = ['Health', 'Local government'];

describe('shareable URLs', () => {
  it('round-trips a filtered view with an open panel', () => {
    const v = { ...viewDefaults('NSW', 'mentions'), period: '4w' as const, sector: 'Local government', mTab: 'reports' as const, repOff: 'NSW' as const, notYet: true, drawer: { k: 'rep' as const, id: 'NSW-r2' } };
    const qs = toQuery(v, true);
    expect(qs).toBe('view=mentions&jur=NSW&period=4w&sector=local-government&tab=reports&office=NSW&unmentioned=1&report=NSW-r2');
    expect({ ...viewDefaults('NSW'), ...fromQuery('?' + qs, SECTORS) }).toEqual(v);
  });

  it('leaves out defaults and the panel unless asked', () => {
    expect(toQuery({ ...viewDefaults('VIC'), drawer: { k: 'item', id: 'VIC-1' } }, false)).toBe('view=brief&jur=VIC');
  });

  it('is not a shared view without a valid jurisdiction', () => {
    expect(fromQuery('?view=gaps', SECTORS)).toBeNull();
    expect(fromQuery('?jur=XX', SECTORS)).toBeNull();
  });

  it('ignores unknown values', () => {
    expect(fromQuery('?jur=vic&view=nope&period=9y&sector=unknown&sentiment=angry', SECTORS)).toEqual({ jur: 'VIC' });
  });

  it('carries Explore filters', () => {
    const q = fromQuery('?view=explore&jur=QLD&q=consultants&scope=all&sentiment=negative&new=1', SECTORS);
    expect(q).toMatchObject({ tab: 'explore', q: 'consultants', expJur: false, expSent: 'Negative', newOnly: true });
  });
});
