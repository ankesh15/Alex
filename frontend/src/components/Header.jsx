import React from 'react';
import { Plus, Sparkles, FileText, FlaskConical } from 'lucide-react';

export default function Header({
  activeTab,
  onTabChange,
  documentCount = 0,
  onNewChat,
}) {
  return (
    <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-sm border-b border-slate-200">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center text-white font-semibold text-sm shadow-sm">
            A
          </div>
          <div className="flex flex-col">
            <div className="flex items-center space-x-2">
              <span className="font-bold text-sm tracking-tight text-slate-900">ALEX</span>
              <span className="text-[10px] font-medium bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                AI Assistant
              </span>
            </div>
            <span className="text-[11px] text-slate-400 hidden sm:inline -mt-0.5">
              Knowledge & Research
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center space-x-1 sm:space-x-2">
          {/* Ask Alex Tab */}
          <button
            type="button"
            onClick={() => onTabChange('chat')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === 'chat'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            Ask Alex
          </button>

          {/* Documents Tab */}
          <button
            type="button"
            onClick={() => onTabChange('documents')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center space-x-1.5 ${
              activeTab === 'documents'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <span>Documents</span>
            {documentCount > 0 && (
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full font-semibold ${
                  activeTab === 'documents'
                    ? 'bg-slate-800 text-slate-200'
                    : 'bg-slate-200 text-slate-700'
                }`}
              >
                {documentCount}
              </span>
            )}
          </button>

          {/* Research Soon Tab */}
          <button
            type="button"
            disabled
            className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-400 cursor-not-allowed flex items-center space-x-1 opacity-60"
            title="Web Research & Reports coming in next phase"
          >
            <span>Research</span>
            <span className="text-[9px] uppercase tracking-wider bg-slate-100 text-slate-500 px-1 py-0.2 rounded border border-slate-200">
              Soon
            </span>
          </button>

          {/* New Chat Button */}
          <button
            type="button"
            onClick={onNewChat}
            className="inline-flex items-center space-x-1 text-xs font-medium text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-200 shadow-xs transition-colors ml-1"
            title="Start a new chat (cleans up temporary session files)"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">New Chat</span>
          </button>
        </div>
      </div>
    </header>
  );
}
