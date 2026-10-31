import { DrawerBody, OverlayDrawer, Popover, PopoverSurface, PopoverTrigger } from '@fluentui/react-components';
import { cloneElement, type ReactElement, type ReactNode } from 'react';

export type MenuId = 'jur' | 'period' | 'sector' | 'status' | 'export' | 'more' | null;

interface Props {
  id: Exclude<MenuId, null>; menu: MenuId; setMenu: (m: MenuId) => void; mob: boolean;
  trigger: ReactElement<{ onClick?: () => void }>; width: number; align?: 'start' | 'end'; label: string; children: ReactNode;
}

/** A dropdown on desktop, a bottom sheet on phones. */
export function MenuSurface({ id, menu, setMenu, mob, trigger, width, align = 'start', label, children }: Props) {
  const open = menu === id;
  if (mob) {
    return (
      <>
        {cloneElement(trigger, { onClick: () => setMenu(open ? null : id) })}
        <OverlayDrawer position="bottom" open={open} onOpenChange={(_, d) => !d.open && setMenu(null)} aria-label={label}
          style={{ height: 'auto', maxHeight: '82%', borderRadius: '12px 12px 0 0' }}>
          <DrawerBody style={{ padding: 4 }}>{open && children}</DrawerBody>
        </OverlayDrawer>
      </>
    );
  }
  return (
    <Popover open={open} onOpenChange={(_, d) => setMenu(d.open ? id : null)} positioning={align === 'end' ? 'below-end' : 'below-start'} trapFocus>
      <PopoverTrigger disableButtonEnhancement>{trigger}</PopoverTrigger>
      <PopoverSurface aria-label={label} style={{ width, padding: 4, maxHeight: 640, overflow: 'auto', borderRadius: 8, boxSizing: 'border-box' }}>{children}</PopoverSurface>
    </Popover>
  );
}

export function MenuItem({ on, onClick, children, check = true }: { on?: boolean; onClick: () => void; children: ReactNode; check?: boolean }) {
  return (
    <button className={'menu-item' + (on ? ' on' : '')} role="menuitemradio" aria-checked={!!on} onClick={onClick}>
      {check && <span className="check">{on ? '✓' : ''}</span>}
      {children}
    </button>
  );
}
