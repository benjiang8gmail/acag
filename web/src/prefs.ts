/** Personal settings live in the browser (spec §2): jurisdiction, start page and items already opened. */
import type { JurCode } from './types';
import type { Tab } from './urlState';

export interface Prefs { jur: JurCode | null; start: Tab; seen: string[] }

const KEY = 'hw-prefs-v1';

export function loadPrefs(): Prefs {
  try {
    const p = JSON.parse(localStorage.getItem(KEY) || '{}');
    return { jur: p.jur ?? null, start: p.start ?? 'brief', seen: Array.isArray(p.seen) ? p.seen : [] };
  } catch {
    return { jur: null, start: 'brief', seen: [] };
  }
}

export function savePrefs(p: Prefs) {
  try { localStorage.setItem(KEY, JSON.stringify(p)); } catch { /* private mode: settings last for this visit only */ }
}
