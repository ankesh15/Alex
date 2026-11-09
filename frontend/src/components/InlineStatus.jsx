import React from 'react';
import { CheckCircle2, AlertCircle, X } from 'lucide-react';

export default function InlineStatus({ children, error = false, onDismiss }) {
  return <div role={error ? 'alert' : 'status'} className={`inline-status ${error ? 'border-red-200 bg-red-50 text-red-800' : 'border-slate-200 bg-white text-slate-600'}`}>
    {error ? <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" /> : <CheckCircle2 className="w-4 h-4 shrink-0 text-sky-700" aria-hidden="true" />}
    <div className="min-w-0 flex-1">{children}</div>
    {onDismiss && <button type="button" aria-label="Dismiss notification" onClick={onDismiss} className="icon-button w-8 h-8"><X className="w-4 h-4" aria-hidden="true" /></button>}
  </div>;
}
