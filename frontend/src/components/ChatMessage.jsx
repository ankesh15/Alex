import React from 'react';
import { Sparkles, AlertCircle, User } from 'lucide-react';
import Citations from './Citations';

export default function ChatMessage({ message }) {
  const { role, content, citations, error, tokenUsage } = message;

  if (role === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="bg-slate-100 hover:bg-slate-200/70 transition-colors text-slate-900 rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[85%] sm:max-w-[75%] text-sm leading-relaxed whitespace-pre-wrap break-words">
          {content}
        </div>
      </div>
    );
  }

  // Assistant message or error
  return (
    <div className="flex items-start space-x-3 mb-6 text-left">
      <div className="w-7 h-7 rounded-lg bg-slate-900 flex items-center justify-center text-white shrink-0 mt-0.5 shadow-sm">
        <Sparkles className="w-3.5 h-3.5 text-sky-400" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-semibold text-slate-900">Alex</span>
          {tokenUsage && tokenUsage.total_tokens > 0 && (
            <span className="text-[10px] text-slate-400 font-mono">
              {tokenUsage.total_tokens} tokens
            </span>
          )}
        </div>

        {error ? (
          <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-800 flex items-start space-x-2">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Error</p>
              <p className="mt-0.5">{content}</p>
            </div>
          </div>
        ) : (
          <div className="text-sm text-slate-800 leading-relaxed whitespace-pre-wrap break-words">
            {content}
          </div>
        )}

        {citations && citations.length > 0 && (
          <Citations citations={citations} />
        )}
      </div>
    </div>
  );
}
