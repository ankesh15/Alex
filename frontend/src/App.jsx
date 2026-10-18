import React, { useState, useCallback } from 'react';
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
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const handleLogout = async () => {
    setIsLoggingOut(true); setLogoutError(null);
    try { await logout(); } catch (err) { setLogoutError(err.message); }
    finally { setIsLoggingOut(false); }
  };
  const [activeTab, setActiveTab] = useState('chat');
  const [historyOpen, setHistoryOpen] = useState(() => window.matchMedia('(min-width: 1024px)').matches);
  const closeHistory = useCallback(() => setHistoryOpen(false), []);
  const [state, controller] = useConversationWorkspace(user.id);
  const readyDocuments = state.documents.filter(document => document.status === 'READY');
  const currentId = state.active?.id;
  const selection = state.selectionVersion;
  const newChat = async () => { setActiveTab('chat'); await controller.create(); };
  const selectChat = id => { setActiveTab('chat'); controller.open(id); };
  const attachFile = file => {
    if (!file) return;
    const extension = file.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'docx', 'txt'].includes(extension)) { alert('Please attach a PDF, DOCX, or TXT file.'); return; }
    if (file.size > 20 * 1024 * 1024) { alert('File exceeds the 20 MB size limit.'); return; }
    controller.upload(file);
  };
  return (
    <div className="h-screen flex flex-col bg-slate-50 text-slate-900 font-sans overflow-hidden">
      <Header activeTab={activeTab} onTabChange={setActiveTab} documentCount={readyDocuments.length}
        onNewChat={newChat} userEmail={user.email} onLogout={handleLogout} isLoggingOut={isLoggingOut}
        onToggleHistory={() => setHistoryOpen(value => !value)} historyOpen={historyOpen} isCreating={state.creating} />
      {logoutError && <p role="alert" className="text-sm text-red-700 p-3 text-center">{logoutError}</p>}
      <div className="flex-1 flex min-h-0 relative">
        <ConversationSidebar open={historyOpen} onClose={closeHistory} state={state} controller={controller} onSelect={selectChat} onNew={newChat} />
        <main className="flex-1 min-w-0 flex flex-col overflow-hidden relative">
          <div className="px-4 sm:px-6 py-2 border-b border-slate-100 bg-white/50">
            <h1 className="max-w-3xl mx-auto text-xs font-medium text-slate-600 truncate">{state.active?.title || 'Start a conversation'}</h1>
          </div>
          {state.notice && <div role="status" className="text-xs text-slate-600 px-4 py-2">{state.notice}{state.cleanupRetryId && <button type="button" disabled={!!state.mutationId} onClick={() => controller.delete(state.cleanupRetryId).catch(() => {})} className="ml-2 text-sky-700 underline">Retry file cleanup</button>}</div>}
          {state.documentsError && activeTab === 'chat' && <p role="alert" className="text-xs text-red-700 px-4 py-2">{state.documentsError}</p>}
          {activeTab === 'chat' ? (
            <>
              <Chat messages={state.messages} isLoading={state.isSending} hasReadyDocuments={readyDocuments.length > 0}
                onSelectSuggestion={(text, scope) => controller.send(text, scope)} historyLoading={state.historyLoading}
                historyError={state.historyError} onRetryHistory={() => currentId ? controller.open(currentId) : controller.create()}
                hasOlder={state.beforeTurn !== null} olderLoading={state.olderLoading} onLoadOlder={() => controller.loadOlder()} />
              <ChatInput key={`${currentId || 'empty'}:${selection}`} onSendMessage={(text, scope) => controller.send(text, scope)}
                isLoading={state.isSending || state.historyLoading || state.creating || (!!state.historyError && !state.messages.length)}
                documents={state.documents} selectedScope={state.scope} onScopeChange={scope => controller.setScope(scope)}
                onAttachFile={attachFile} attachedFiles={state.attachedFiles} onRemoveAttachment={id => controller.removeAttachment(id)}
                isUploadingAttachment={state.isUploading} />
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
