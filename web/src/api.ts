import type { Dataset, Gap, Issue, Item, Jurisdiction, Report, ScanSnapshot, Sector, Status } from './types';

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { credentials: 'same-origin', ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } });
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch { /* not JSON */ }
    throw new ApiError(r.status, msg);
  }
  return r.json();
}

export async function loadDataset(): Promise<Dataset> {
  const [status, jurisdictions, items, issues, gaps, reports, sectors] = await Promise.all([
    call<Status>('/api/status'), call<Jurisdiction[]>('/api/offices'), call<Item[]>('/api/items'), call<Issue[]>('/api/issues'),
    call<Gap[]>('/api/gaps'), call<Report[]>('/api/reports'), call<Sector[]>('/api/sectors'),
  ]);
  return { status, jurisdictions, items, issues, gaps, reports, sectors };
}

export const me = () => call<{ user: string | null }>('/api/auth/me');
export const login = (username: string, password: string) => call<{ user: string }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
export const logout = () => call('/api/auth/logout', { method: 'POST' });
export const startScan = () => call<ScanSnapshot>('/api/scans', { method: 'POST' });

export function watchScan(id: number, onEvent: (s: ScanSnapshot) => void): () => void {
  const es = new EventSource(`/api/scans/${id}/events`);
  es.onmessage = e => { const s: ScanSnapshot = JSON.parse(e.data); onEvent(s); if (s.done) es.close(); };
  return () => es.close();
}

/** Download a server export; resolves to an error message when the export isn't available. */
export async function download(path: string): Promise<string | null> {
  const r = await fetch(path, { credentials: 'same-origin' });
  if (!r.ok) { try { return (await r.json()).detail; } catch { return 'Export failed.'; } }
  const blob = await r.blob();
  const name = /filename="([^"]+)"/.exec(r.headers.get('Content-Disposition') || '')?.[1] || 'export';
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  return null;
}
