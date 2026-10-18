import React, { useEffect, useRef, useState } from 'react';
import { X, Pencil, Trash2, Plus, Loader2 } from 'lucide-react';

export default function ConversationSidebar({ open, onClose, state, controller, onSelect, onNew }) {
  const asideRef = useRef(null);
  const dialogRef = useRef(null);
  const [action, setAction] = useState(null);
  const [title, setTitle] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open || !window.matchMedia('(max-width: 1023px)').matches) return;
    const previous = document.activeElement;
    asideRef.current?.querySelector('button')?.focus();
    const handleKey = event => {
      if (dialogRef.current?.open) return;
      if (event.key === 'Escape') { event.preventDefault(); onClose(); }
      if (event.key === 'Tab') {
        const nodes = [...asideRef.current.querySelectorAll('button:not(:disabled), input')];
        if (event.shiftKey && document.activeElement === nodes[0]) { event.preventDefault(); nodes.at(-1)?.focus(); }
        else if (!event.shiftKey && document.activeElement === nodes.at(-1)) { event.preventDefault(); nodes[0]?.focus(); }
      }
    };
    document.addEventListener('keydown', handleKey);
    return () => { document.removeEventListener('keydown', handleKey); previous?.focus(); };
  }, [open, onClose]);

  useEffect(() => {
    if (action && dialogRef.current && !dialogRef.current.open) dialogRef.current.showModal();
  }, [action]);

  if (!open) return null;
  const begin = (type, conversation) => { setAction({ type, conversation }); setTitle(conversation.title); setError(null); };
  const closeAction = () => { if (!busy) { dialogRef.current?.close(); setAction(null); } };
  const submit = async event => {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError(null);
    try {
      if (action.type === 'delete') await controller.delete(action.conversation.id);
      else await controller.rename(action.conversation.id, title);
      dialogRef.current?.close(); setAction(null);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const choose = id => {
    onSelect(id);
    if (window.matchMedia('(max-width: 1023px)').matches) onClose();
  };
  return (
    <>
      <button type="button" aria-label="Dismiss chat history" onClick={onClose} className="fixed inset-0 top-14 bg-slate-900/30 z-40 lg:hidden" />
      <aside id="conversation-history" ref={asideRef} aria-label="Conversation history" className="fixed top-14 bottom-0 left-0 z-50 w-72 lg:static lg:w-64 shrink-0 flex flex-col bg-white border-r border-slate-200 min-h-0">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <h2 className="text-sm font-semibold">Chat history</h2>
          <button type="button" onClick={onClose} aria-label="Close chat history" className="p-1.5 rounded-lg hover:bg-slate-100"><X className="w-4 h-4" /></button>
        </div>
        <button type="button" onClick={onNew} disabled={state.creating} className="m-3 px-3 py-2 text-sm text-left border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50 flex items-center gap-2"><Plus className="w-4 h-4" />New conversation</button>
        <div className="flex-1 overflow-y-auto px-2 pb-3">
          {!state.conversations.length && !state.listLoading && !state.listError && <p className="px-3 py-6 text-xs text-slate-500">No conversations yet. Start a new chat to save your research.</p>}
          {state.conversations.map(conversation => (
            <div key={conversation.id} className={`group rounded-lg mb-1 border ${state.active?.id === conversation.id ? 'bg-slate-100 border-slate-200' : 'border-transparent hover:bg-slate-50'}`}>
              <button type="button" onClick={() => choose(conversation.id)} aria-current={state.active?.id === conversation.id ? 'page' : undefined} className="w-full text-left p-3 pb-1.5 rounded-lg focus-visible:outline-sky-500">
                <span className="block truncate text-sm font-medium" title={conversation.title}>{conversation.title}</span>
                <time dateTime={conversation.updated_at} className="block text-[10px] text-slate-500 mt-1">{new Date(conversation.updated_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</time>
              </button>
              <div className="flex justify-end gap-1 px-2 pb-1">
                <button type="button" aria-label={`Rename ${conversation.title}`} disabled={!!state.mutationId || state.busyIds?.includes(conversation.id)} onClick={() => begin('rename', conversation)} className="p-1.5 rounded hover:bg-slate-200 text-slate-500 disabled:opacity-40"><Pencil className="w-3.5 h-3.5" /></button>
                <button type="button" aria-label={`Delete ${conversation.title}`} disabled={!!state.mutationId} onClick={() => begin('delete', conversation)} className="p-1.5 rounded hover:bg-red-50 text-slate-500 hover:text-red-700 disabled:opacity-40"><Trash2 className="w-3.5 h-3.5" /></button>
              </div>
            </div>
          ))}
          {state.listError && <div role="alert" className="text-xs text-red-700 p-3">{state.listError}<button type="button" onClick={() => controller.refreshList()} className="block mt-2 underline">Retry history</button></div>}
          {state.listLoading && <p role="status" className="text-xs text-slate-500 p-3 flex gap-2"><Loader2 className="w-3 h-3 animate-spin" />Loading conversations…</p>}
          {state.nextCursor && <button type="button" onClick={() => controller.loadMore()} disabled={state.listLoading} className="w-full text-xs text-sky-700 py-3 underline disabled:opacity-50">Load more conversations</button>}
        </div>
      </aside>
      {action && <dialog ref={dialogRef} aria-labelledby="conversation-action-title" onCancel={event => { if (busy) event.preventDefault(); else setAction(null); }} className="rounded-xl border border-slate-200 p-5 w-[calc(100%_-_2rem)] max-w-sm shadow-xl backdrop:bg-slate-900/40">
        <form onSubmit={submit} className="space-y-4">
          <h2 id="conversation-action-title" className="font-semibold text-slate-900">{action.type === 'delete' ? 'Delete conversation?' : 'Rename conversation'}</h2>
          {action.type === 'delete' ? <p className="text-sm text-slate-600">Delete “{action.conversation.title}” and its messages, attached documents and embeddings? This cannot be undone.</p> : <div><label htmlFor="conversation-title" className="block text-sm mb-1">Title</label><input id="conversation-title" autoFocus required maxLength={120} value={title} onChange={event => setTitle(event.target.value)} disabled={busy} className="border border-slate-300 rounded-lg p-2 w-full focus:outline-none focus:ring-2 focus:ring-sky-500" /></div>}
          {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" disabled={busy} onClick={closeAction} className="px-3 py-2 text-sm border border-slate-200 rounded-lg">Cancel</button>
            <button type="submit" disabled={busy || (action.type === 'rename' && !title.trim())} className={`px-3 py-2 text-sm text-white rounded-lg disabled:opacity-50 ${action.type === 'delete' ? 'bg-red-600' : 'bg-slate-900'}`}>{busy ? 'Please wait…' : action.type === 'delete' ? 'Delete conversation' : 'Save title'}</button>
          </div>
        </form>
      </dialog>}
    </>
  );
}
