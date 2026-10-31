export type Code = 'CTH' | 'NSW' | 'VIC' | 'QLD' | 'SA' | 'WA' | 'TAS' | 'ACT' | 'NT';
export type JurCode = Code | 'ALL';
export type Sentiment = 'positive' | 'neutral' | 'negative' | 'mixed';
export type Coverage = 'planned' | 'in_progress' | 'recent_report' | 'not_covered' | 'na';

export interface Jurisdiction {
  code: Code; short: string; name: string; parl: string; office: string; officeName: string; color: string;
  chambers: string[]; status: 'ok' | 'blocked' | 'nosit'; statusText: string; sittingDays: string[];
  program: string | null; confirmed?: boolean; counts?: [number, number, number]; topicA?: string; topicB?: string;
  elsewhere: number; url: string; site: string; tilePos: [number, number];
}

export interface Issue {
  id: string; label: string; theme: string; kw: string; raised: Partial<Record<Code, number>>;
  cov: Partial<Record<Code | '_', Coverage>>; quote: string; from: Code; by: string;
}

export interface Item {
  id: string; jur: Code; url: string; theme: string; chamber: string; source: 'Hansard' | 'Office website'; page: number;
  feat: 'F1' | 'F2' | 'F3' | 'F4'; sig: number; date: string; sent: Sentiment | null; ofc: boolean; rep: string | null;
  x: string | null; devType: string | null; side?: string; speaker?: string; role?: string; debate?: string;
  headline: string; summary: string; why: string; reason?: string; quote?: string; pending: boolean;
}

export interface Gap {
  id: string; jur: Code; issue: string; score: number; coverage: 'not_covered' | 'partly'; ev: string[];
  closest: string; why: string; x: string | null; lastAudited: string; theme: string;
  parts: { n: string; w: number; v: number }[];
}

export interface Report { id: string; jur: Code; no: string; title: string; tabled: string; sector: string }
export interface Sector { name: string; short: string }

export interface ScanSnapshot {
  id: number; step: number; total: number; done: boolean;
  sources: { code: Code | 'REG'; state: 'done' | 'checking' | 'waiting'; text: string | null }[];
  summary: null | {
    parliamentsSat: number; newSittingDays: number; newItems: number; newItemsMentioningOffice: Partial<Record<Code, number>>; registers: string;
    speechesStored?: number; note?: string;   // real scans (SCAN_MODE=real), before AI analysis exists
  };
}

export interface Status {
  sampleData: boolean; asOf: string; lastChecked: string; previousCheck: string; hansardTo: string; storedFrom: string;
  refreshed: boolean; registers: string; scanRunning: ScanSnapshot | null;
  liveHansard?: Code[]; neverChecked?: boolean;   // real mode: parliaments whose Hansard is stored for real
  sources: { code: Code; parliament: string; status: Jurisdiction['status']; text: string }[];
  upcomingSittings: { d: string; p: string }[];
}

export interface Dataset {
  status: Status; jurisdictions: Jurisdiction[]; items: Item[]; issues: Issue[]; gaps: Gap[]; reports: Report[]; sectors: Sector[];
}
