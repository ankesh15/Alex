import React from 'react';
import { Plus, Menu, LogOut, Loader2 } from 'lucide-react';

export default function Header({ onNewChat, userEmail, onLogout, isLoggingOut,
  onToggleHistory, historyOpen, isCreating, drawerOpen, toggleRef }) {
  return (
    <header inert={drawerOpen ? '' : undefined} className="app-header shrink-0 bg-white border-b border-slate-200 z-30">
      <div className="header-inner">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <button ref={toggleRef} type="button" onClick={onToggleHistory} aria-label="Toggle sidebar"
            aria-expanded={historyOpen} aria-controls="conversation-history" className="icon-button">
            <Menu className="w-5 h-5" aria-hidden="true" />
          </button>
          <div className="w-9 h-9 rounded-xl bg-slate-900 flex items-center justify-center text-white font-semibold shrink-0">A</div>
          <div className="min-w-0">
            <p className="font-bold text-sm tracking-wide text-slate-900">ALEX</p>
            <p className="hidden md:block text-xs text-slate-500">Knowledge &amp; Research</p>
          </div>
        </div>
        <div className="header-actions flex items-center justify-end gap-1 sm:gap-2">
          <button type="button" onClick={onNewChat} disabled={isCreating} aria-label="Start a new conversation"
            aria-keyshortcuts="N" title="New chat (N outside text fields)" className="secondary-button gap-2">
            {isCreating ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Plus className="w-4 h-4" aria-hidden="true" />}
            <span className="text-xs">{isCreating ? 'Creating…' : 'New chat'}</span>
          </button>
          <button type="button" onClick={onLogout} disabled={isLoggingOut} aria-label={isLoggingOut ? 'Signing out' : 'Sign out'}
            title={userEmail ? `Sign out of ${userEmail}` : 'Sign out'} className="icon-button sm:w-auto sm:px-3 gap-2">
            <LogOut className="w-4 h-4" aria-hidden="true" /><span className="hidden sm:inline text-xs">{isLoggingOut ? 'Signing out…' : 'Sign out'}</span>
          </button>
        </div>
      </div>
    </header>
  );
}
