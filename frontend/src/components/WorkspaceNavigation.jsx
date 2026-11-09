import React from 'react';
import { MessageSquare, Files, Telescope } from 'lucide-react';

export default function WorkspaceNavigation({ activeTab, onNavigate, documentCount, collapsed = false }) {
  return <nav aria-label="Workspace" className={collapsed ? 'flex flex-col items-center gap-2 p-2' : 'space-y-1 p-3'}>
    {[
      { id: 'chat', label: 'Ask Alex', Icon: MessageSquare },
      { id: 'documents', label: 'Documents', Icon: Files },
      { id: 'research', label: 'Research', Icon: Telescope, disabled: true },
    ].map(({ id, label, Icon, disabled }) => <button key={id} type="button"
      disabled={disabled} onClick={() => onNavigate(id)} aria-label={label}
      aria-pressed={disabled ? undefined : activeTab === id}
      title={disabled ? 'Research — coming soon' : label}
      className={`sidebar-nav-item ${collapsed ? 'justify-center w-11 px-0' : 'w-full px-3 gap-3'} ${activeTab === id ? 'sidebar-nav-item-active' : ''}`}>
      <Icon className="w-[18px] h-[18px] shrink-0" aria-hidden="true" />
      {!collapsed && <><span className="flex-1 text-left">{label}</span>
        {id === 'documents' && documentCount > 0 && <span className="text-xs rounded-full bg-slate-200/80 text-slate-700 px-2">{documentCount}</span>}
        {disabled && <span className="text-[10px] uppercase tracking-wide text-slate-400">Soon</span>}</>}
    </button>)}
  </nav>;
}
