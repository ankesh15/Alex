import React from 'react';
import { FileText } from 'lucide-react';

export default function Citations({ citations }) {
  if (!citations || citations.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 pt-3 border-t border-slate-100">
      <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center space-x-1">
        <span>Sources</span>
      </div>

      <div className="flex flex-wrap gap-2">
        {citations.map((cite, index) => {
          const matchPercent = Math.round((cite.relevance_score || 0) * 100);
          return (
            <div
              key={`${cite.filename}-${cite.page_number || 'full'}-${index}`}
              className="inline-flex items-center space-x-2 bg-slate-50 hover:bg-slate-100/90 transition-colors border border-slate-200 rounded-lg px-2.5 py-1.5 text-left max-w-xs"
            >
              <FileText className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-xs font-medium text-slate-800 truncate" title={cite.filename}>
                  {cite.filename}
                </div>
                <div className="text-[10px] text-slate-500">
                  {cite.page_number ? `Page ${cite.page_number}` : 'Document reference'}
                  {matchPercent > 0 && ` • ${matchPercent}% match`}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
