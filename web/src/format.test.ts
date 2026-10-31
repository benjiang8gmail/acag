import { describe, expect, it } from 'vitest';
import { addDays, fmtDay, fmtRange } from './format';

describe('dates', () => {
  it('formats sitting days the way the design does', () => {
    expect(fmtDay('2026-10-29')).toBe('Thu 29 Oct');
    expect(fmtRange(addDays('2026-10-31', -14), '2026-10-31')).toBe('17–31 Oct');
    expect(fmtRange(addDays('2026-10-31', -61), '2026-10-31')).toBe('31 Aug – 31 Oct');
  });
});
