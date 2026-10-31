import { createContext, useContext } from 'react';
import type { Model } from './model';
import type { Code, JurCode } from './types';
import type { DrawerRef, Tab, ViewState } from './urlState';

export interface Actions {
  m: Model;
  mob: boolean;
  set: (p: Partial<ViewState>) => void;
  tabTo: (tab: Tab, extra?: Partial<ViewState>) => void;
  openDrawer: (d: DrawerRef) => void;
  openItem: (id: string) => void;
  markSeen: (id: string) => void;
  pickSector: (name: string | null) => void;
  setJur: (c: JurCode) => void;
  toast: (msg: string) => void;
  adds: string[];
  toggleAdd: (id: string) => void;
  copy: (text: string, msg: string) => void;
  openShare: (withDrawer: boolean) => void;
}

export const Ctx = createContext<Actions | null>(null);
export const useApp = () => useContext(Ctx)!;
export type { Code };
