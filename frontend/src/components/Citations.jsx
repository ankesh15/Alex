import React from 'react';
import { FileText } from 'lucide-react';

export default function Citations({ citations }) {
  if (!citations || citations.length === 0) {
    return null;
  }

  return (
    <div className="mt-5 pt-4 border-t border-slate-100">
      <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center space-x-1">
        <span>Sources · {citations.length}</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {citations.map((cite, index) => {
          const matchPercent = Number.isFinite(cite.relevance_score) ? Math.round(Math.max(0, Math.min(1, cite.relevance_score)) * 100) : null;
          return (
            <div
              key={`${cite.filename}-${cite.page_number || 'full'}-${index}`}
              className="inline-flex items-center space-x-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-left min-w-0"
            >
              <FileText className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-xs font-medium text-slate-800 truncate" title={cite.filename}>
                  {cite.filename}
                </div>
                <div className="text-xs text-slate-500">
                  {cite.page_number ? `Page ${cite.page_number}` : 'Document reference'}
                  {matchPercent > 0 && ` • ${matchPercent}% similarity`}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
