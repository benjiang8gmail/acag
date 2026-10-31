import { Button, Dialog, DialogActions, DialogBody, DialogContent, DialogSurface, DialogTitle, Field, Input, MessageBar } from '@fluentui/react-components';
import { Dismiss20Regular } from '@fluentui/react-icons';
import { useState } from 'react';

export function SignInDialog({ open, onCancel, onSignIn }: { open: boolean; onCancel: () => void; onSignIn: (u: string, p: string) => Promise<string | null> }) {
  const [user, setUser] = useState('acag');
  const [pass, setPass] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    const msg = await onSignIn(user, pass);
    setBusy(false);
    setErr(msg || '');
    if (!msg) setPass('');
  };
  return (
    <Dialog open={open} onOpenChange={(_, d) => { if (!d.open) { setErr(''); setPass(''); onCancel(); } }}>
      <DialogSurface style={{ maxWidth: 360 }}>
        <form onSubmit={submit}>
          <DialogBody>
            <DialogTitle>Sign in to refresh</DialogTitle>
            <DialogContent style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div className="s13 muted">Refreshing checks every parliament for new sitting days and runs AI analysis, which has a cost. Everything else stays open without signing in.</div>
              <Field label="Username"><Input value={user} onChange={(_, d) => setUser(d.value)} autoComplete="username" /></Field>
              <Field label="Password"><Input type="password" value={pass} onChange={(_, d) => setPass(d.value)} autoComplete="current-password" autoFocus /></Field>
              {err && <MessageBar intent="error" role="alert">{err}</MessageBar>}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => { setErr(''); setPass(''); onCancel(); }}>Cancel</Button>
              <Button type="submit" appearance="primary" disabled={busy}>Sign in and refresh</Button>
            </DialogActions>
          </DialogBody>
        </form>
      </DialogSurface>
    </Dialog>
  );
}

export function ShareDialog({ open, url, bits, title, onClose, onCopy }: { open: boolean; url: string; bits: string[]; title: string; onClose: () => void; onCopy: () => void }) {
  const mail = `mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(url)}`;
  const teams = `https://teams.microsoft.com/share?href=${encodeURIComponent(url)}&msgText=${encodeURIComponent(title)}`;
  return (
    <Dialog open={open} onOpenChange={(_, d) => !d.open && onClose()}>
      <DialogSurface style={{ maxWidth: 460 }}>
        <DialogBody>
          <DialogTitle action={<Button appearance="subtle" aria-label="Close" icon={<Dismiss20Regular />} onClick={onClose} />}>Share this view</DialogTitle>
          <DialogContent style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="s13 muted">The link opens this exact page — same jurisdiction, period and filters. No sign-in needed.</div>
            <div className="row-wrap">{bits.map(b => <span key={b} className="pill plain" style={{ padding: '2px 10px', color: 'var(--fg)' }}>{b}</span>)}</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <Input readOnly value={url} onFocus={e => e.target.select()} aria-label="Link to this view" style={{ flex: 1, minWidth: 0 }} />
              <Button appearance="primary" onClick={onCopy}>Copy link</Button>
            </div>
            <div className="row-wrap" style={{ gap: 8 }}>
              <Button as="a" href={mail} className="btn-m">✉ Email</Button>
              <Button as="a" href={teams} target="_blank" rel="noopener" className="btn-m">Teams ↗</Button>
            </div>
          </DialogContent>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
}
