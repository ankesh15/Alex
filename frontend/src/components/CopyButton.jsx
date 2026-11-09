import React, { useEffect, useRef, useState } from 'react';
import { Copy, Check } from 'lucide-react';

export default function CopyButton({ text, label = 'Copy response' }) {
  const [state, setState] = useState('idle');
  const active = useRef(true);
  const timer = useRef(null);
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; clearTimeout(timer.current); };
  }, []);
  const copy = async () => {
    if (state === 'copying') return;
    clearTimeout(timer.current);
    setState('copying');
    try {
      await navigator.clipboard.writeText(text);
      if (active.current) setState('copied');
    } catch { if (active.current) setState('error'); }
    if (active.current) timer.current = setTimeout(() => setState('idle'), 4000);
  };
  return <span className="inline-flex flex-wrap items-center gap-2">
    <button type="button" onClick={copy} disabled={state === 'copying'} aria-label={label}
      title={label} className="message-action">
      {state === 'copied' ? <Check className="w-3.5 h-3.5" aria-hidden="true" /> : <Copy className="w-3.5 h-3.5" aria-hidden="true" />}
      {state === 'copied' ? 'Copied' : label === 'Copy code' ? 'Copy' : label}
    </button>
    <span role="status" className={state === 'error' ? 'text-xs text-red-700' : 'sr-only'}>
      {state === 'error' ? 'Copy unavailable. Select the text to copy.' : state === 'copied' ? `${label === 'Copy code' ? 'Code' : 'Response'} copied.` : ''}
    </span>
  </span>;
}
