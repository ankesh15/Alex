import React, { useState, useCallback, useEffect, useRef } from 'react';
import InlineStatus from './components/InlineStatus';
import { isNewConversationShortcut } from './utils/workspaceLayout';
import { AuthProvider, useAuth } from './auth/AuthProvider';
import AuthScreen from './auth/AuthScreen';
import Header from './components/Header';
import Chat from './components/Chat';
import ChatInput from './components/ChatInput';
import DocumentsView from './components/DocumentsView';
import ConversationSidebar from './components/ConversationSidebar';
import { useConversationWorkspace } from './state/useConversationWorkspace';

export default function App() {
  return <AuthProvider><ProtectedApp /></AuthProvider>;
}
function ProtectedApp() {
  const { user, loading, error, restore } = useAuth();
  if (loading) return <main className="min-h-screen flex items-center justify-center bg-slate-50" role="status">Checking your session…</main>;
  if (error) return <main className="min-h-screen flex flex-col items-center justify-center bg-slate-50 gap-3"><p role="alert">{error}</p><button onClick={restore} className="text-sky-700 underline">Try again</button></main>;
  return user ? <Workspace key={user.id} /> : <AuthScreen />;
}
function Workspace() {
  const { user, logout } = useAuth();
  const [logoutError, setLogoutError] = useState(null);
  const [attachmentError, setAttachmentError] = useState(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const handleLogout = async () => {
    setIsLoggingOut(true); setLogoutError(null);
    try { await logout(); } catch (err) { setLogoutError(err.message); }
    finally { setIsLoggingOut(false); }
  };
  const [activeTab, setActiveTab] = useState('chat');
  const [desktop, setDesktop] = useState(() => window.matchMedia('(min-width: 1024px)').matches);
  const [historyOpen, setHistoryOpen] = useState(desktop);
  const shellRef = useRef(null);
  const sidebarToggleRef = useRef(null);
  const closeHistory = useCallback(() => setHistoryOpen(false), []);
  const [state, controller] = useConversationWorkspace(user.id);
  const readyDocuments = state.documents.filter(document => document.status === 'READY');
  const currentId = state.active?.id;
  const selection = state.selectionVersion;
  const newChat = useCallback(async () => { setActiveTab('chat'); await controller.create(); }, [controller]);
  const navigate = tab => { setActiveTab(tab); if (!desktop) setHistoryOpen(false); };
  useEffect(() => {
    const media = window.matchMedia('(min-width: 1024px)');
    const resize = event => { setDesktop(event.matches); setHistoryOpen(event.matches); };
    media.addEventListener('change', resize);
    return () => media.removeEventListener('change', resize);
  }, []);
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previousOverflow; };
  }, []);
  useEffect(() => {
    const viewport = window.visualViewport;
    if (!viewport) return;
    const resize = () => {
      if (viewport.scale === 1) shellRef.current?.style.setProperty('--alex-workspace-height', `${viewport.height}px`);
    };
    resize();
    viewport.addEventListener('resize', resize);
    return () => viewport.removeEventListener('resize', resize);
  }, []);
  useEffect(() => {
    const shortcut = event => {
      if (!document.querySelector('dialog[open]') && isNewConversationShortcut(event)) {
        event.preventDefault();
        if (!desktop) setHistoryOpen(false);
        newChat();
      }
    };
    document.addEventListener('keydown', shortcut);
    return () => document.removeEventListener('keydown', shortcut);
  }, [newChat, desktop]);
  const selectChat = id => { setActiveTab('chat'); controller.open(id); };
  const attachFile = file => {
    if (!file) return;
    setAttachmentError(null);
    const extension = file.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'docx', 'txt'].includes(extension)) { setAttachmentError('Please attach a PDF, DOCX, or TXT file.'); return; }
    if (file.size > 20 * 1024 * 1024) { setAttachmentError('File exceeds the 20 MB size limit.'); return; }
    controller.upload(file);
  };
  return (
    <div ref={shellRef} className="app-shell flex flex-col bg-slate-50 text-slate-900 overflow-hidden">
      <Header toggleRef={sidebarToggleRef} drawerOpen={!desktop && historyOpen}
        onNewChat={newChat} userEmail={user.email} onLogout={handleLogout} isLoggingOut={isLoggingOut}
        onToggleHistory={() => setHistoryOpen(value => !value)} historyOpen={historyOpen} isCreating={state.creating} />
      {logoutError && <InlineStatus error onDismiss={() => setLogoutError(null)}>{logoutError}</InlineStatus>}
      <div className="flex-1 flex min-h-0 relative">
        <ConversationSidebar toggleRef={sidebarToggleRef} desktop={desktop} activeTab={activeTab} onNavigate={navigate} documentCount={readyDocuments.length}
          onExpand={() => setHistoryOpen(true)} open={historyOpen} onClose={closeHistory} state={state} controller={controller} onSelect={selectChat} onNew={newChat} />
        <main inert={!desktop && historyOpen ? '' : undefined} id="workspace" className="flex-1 min-w-0 flex flex-col overflow-hidden relative">
          <div className="px-4 sm:px-6 py-3 border-b border-slate-200/70 bg-white">
            <h1 className="max-w-3xl mx-auto text-sm font-medium text-slate-700 truncate">{state.active?.title || 'Start a conversation'}</h1>
          </div>
          {state.notice && <InlineStatus onDismiss={state.cleanupRetryId ? undefined : () => controller.dismissNotice()}>{state.notice}{state.cleanupRetryId && <button type="button" disabled={!!state.mutationId} onClick={() => controller.delete(state.cleanupRetryId).catch(() => {})} className="ml-2 text-sky-700 underline">Retry file cleanup</button>}</InlineStatus>}
          {state.documentsError && activeTab === 'chat' && <InlineStatus error>{state.documentsError}</InlineStatus>}
          {attachmentError && <InlineStatus error onDismiss={() => setAttachmentError(null)}>{attachmentError}</InlineStatus>}
          {activeTab === 'chat' ? (
            <>
              <Chat key={`${currentId || 'empty'}:${selection}`} messages={state.messages} isLoading={state.isSending} hasReadyDocuments={readyDocuments.length > 0}
                onSelectSuggestion={(text, scope) => controller.send(text, scope)} historyLoading={state.historyLoading}
                historyError={state.historyError} onRetryHistory={() => currentId ? controller.open(currentId) : controller.create()}
                hasOlder={state.beforeTurn !== null} olderLoading={state.olderLoading} onLoadOlder={() => controller.loadOlder()} onRecover={() => currentId && controller.open(currentId)} />
              <div className="composer-dock">
                <ChatInput key={`${currentId || 'empty'}:${selection}`} onSendMessage={(text, scope) => controller.send(text, scope)}
                isLoading={state.isSending || state.historyLoading || state.creating || (!!state.historyError && !state.messages.length)}
                documents={state.documents} selectedScope={state.scope} onScopeChange={scope => controller.setScope(scope)}
                onAttachFile={attachFile} attachedFiles={state.attachedFiles} onRemoveAttachment={id => controller.removeAttachment(id)}
                isUploadingAttachment={state.isUploading} />
              </div>
            </>
          ) : currentId && !state.historyLoading ? (
            <DocumentsView key={`${currentId}:${selection}`} documents={state.documents} chatId={currentId}
              isLoading={state.documentsLoading} error={state.documentsError} onRetry={() => controller.refreshDocuments(selection)}
              onUploadSuccess={() => controller.refreshDocuments(selection)} onDocumentDeleted={id => controller.documentDeleted(id, selection)}
              onBackToChat={() => setActiveTab('chat')} />
          ) : <div className="p-6 text-center text-sm text-slate-500">{state.historyLoading ? 'Loading conversation…' : 'Create or select a conversation to upload documents.'}<button type="button" onClick={newChat} disabled={state.creating} className="block mx-auto mt-3 text-sky-700 underline">New conversation</button></div>}
        </main>
      </div>
    </div>
  );
}
