import React, { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useAuth } from './AuthProvider';

export default function AuthScreen() {
  const { authenticate } = useAuth();
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const submit = async (event) => {
    event.preventDefault();
    if (busy) return;
    if (mode === 'signup' && password !== confirm) { setError('Passwords do not match.'); return; }
    setBusy(true);
    setError(null);
    try { await authenticate(mode, email, password); setPassword(''); setConfirm(''); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center p-4 text-slate-900">
      <section className="w-full max-w-sm bg-white border border-slate-200 rounded-2xl p-6 shadow-sm" aria-labelledby="auth-title">
        <div className="w-10 h-10 bg-slate-900 text-white rounded-xl flex items-center justify-center font-bold mb-4">A</div>
        <p className="text-xs text-slate-500 mb-1">ALEX · Knowledge &amp; Research</p>
        <h1 id="auth-title" className="text-xl font-semibold mb-5">{mode === 'signup' ? 'Create your account' : 'Sign in to ALEX'}</h1>
        <form onSubmit={submit} className="space-y-4">
          <div><label htmlFor="auth-email" className="block text-sm mb-1">Email</label>
            <input id="auth-email" type="email" required autoComplete="email" maxLength={254} value={email} onChange={e => setEmail(e.target.value)} disabled={busy} className="w-full border border-slate-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-sky-500" /></div>
          <div><label htmlFor="auth-password" className="block text-sm mb-1">Password</label>
            <input id="auth-password" type="password" required minLength={mode === 'signup' ? 12 : 1} maxLength={128} autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} disabled={busy} aria-describedby={mode === 'signup' ? 'password-help' : undefined} className="w-full border border-slate-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-sky-500" />
            {mode === 'signup' && <p id="password-help" className="text-xs text-slate-500 mt-1">Use at least 12 characters.</p>}</div>
          {mode === 'signup' && <div><label htmlFor="auth-confirm" className="block text-sm mb-1">Confirm password</label>
            <input id="auth-confirm" type="password" required autoComplete="new-password" value={confirm} onChange={e => setConfirm(e.target.value)} disabled={busy} className="w-full border border-slate-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-sky-500" /></div>}
          {error && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-lg p-3">{error}</p>}
          <button type="submit" disabled={busy} className="w-full bg-slate-900 text-white rounded-lg p-2.5 text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2">
            {busy && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}{busy ? 'Please wait…' : mode === 'signup' ? 'Create account' : 'Sign in'}
          </button>
        </form>
        <button type="button" disabled={busy} onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setPassword(''); setConfirm(''); setError(null); }} className="mt-4 text-sm text-sky-700 underline">
          {mode === 'login' ? 'Create an account' : 'Already have an account? Sign in'}
        </button>
      </section>
    </main>
  );
}
