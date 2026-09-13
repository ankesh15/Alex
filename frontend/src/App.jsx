import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Chat from './components/Chat';
import ChatInput from './components/ChatInput';
import DocumentsView from './components/DocumentsView';
import { fetchDocuments, askAlex, askAlexGeneral } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'documents'
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [docsError, setDocsError] = useState(null);

  // Scope: 'general' | 'all' | document_id
  const [selectedScope, setSelectedScope] = useState('general');

  // Conversational chat state
  const [messages, setMessages] = useState([]);
  const [isAsking, setIsAsking] = useState(false);

  const loadDocuments = async () => {
    setIsLoadingDocs(true);
    setDocsError(null);
    try {
      const data = await fetchDocuments();
      setDocuments(data.documents || []);
    } catch (err) {
      setDocsError(err.message || 'Unable to connect to Alex backend.');
    } finally {
      setIsLoadingDocs(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleSendMessage = async (text, overrideScope = null) => {
    const scopeToUse = overrideScope || selectedScope;
    const userMsgId = `user-${Date.now()}`;
    const userMsg = {
      id: userMsgId,
      role: 'user',
      content: text,
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsAsking(true);

    try {
      let res;
      if (scopeToUse === 'general') {
        // General Chat Mode: Gemini direct, no RAG, no citations
        res = await askAlexGeneral(text);
        const assistantMsg = {
          id: `alex-${Date.now()}`,
          role: 'assistant',
          content: res.answer,
          citations: [],
          tokenUsage: res.token_usage || null,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        // Document RAG Mode: All documents (null) or specific document id
        const docId = scopeToUse === 'all' ? null : scopeToUse;
        res = await askAlex(text, docId, 5);
        const assistantMsg = {
          id: `alex-${Date.now()}`,
          role: 'assistant',
          content: res.answer,
          citations: res.citations || [],
          tokenUsage: res.token_usage || null,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      }
    } catch (err) {
      const errorMsg = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: err.message || 'Alex encountered an error. Please try again.',
        error: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsAsking(false);
    }
  };

  const handleSelectSuggestion = (promptText, targetScope) => {
    setSelectedScope(targetScope);
    handleSendMessage(promptText, targetScope);
  };

  const handleNewChat = () => {
    setMessages([]);
  };

  const handleDocumentDeleted = (deletedId) => {
    setDocuments((prev) => prev.filter((d) => d.id !== deletedId));
    if (selectedScope === deletedId) {
      setSelectedScope('general');
    }
  };

  const readyDocuments = documents.filter((d) => d.status === 'READY');

  return (
    <div className="h-screen flex flex-col bg-slate-50 text-slate-900 font-sans overflow-hidden">
      {/* Sleek ChatGPT-style Header */}
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        documentCount={readyDocuments.length}
        onNewChat={handleNewChat}
        hasMessages={messages.length > 0}
      />

      {/* Main Viewport */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        {activeTab === 'chat' ? (
          <>
            {/* Centered Scrollable Conversation Area */}
            <Chat
              messages={messages}
              isLoading={isAsking}
              onSelectSuggestion={handleSelectSuggestion}
              hasReadyDocuments={readyDocuments.length > 0}
            />

            {/* Pinned Bottom Input */}
            <ChatInput
              onSendMessage={handleSendMessage}
              isLoading={isAsking}
              documents={documents}
              selectedScope={selectedScope}
              onScopeChange={setSelectedScope}
            />
          </>
        ) : (
          /* Focused Documents Panel */
          <DocumentsView
            documents={documents}
            isLoading={isLoadingDocs}
            error={docsError}
            onRetry={loadDocuments}
            onUploadSuccess={loadDocuments}
            onDocumentDeleted={handleDocumentDeleted}
            onBackToChat={() => setActiveTab('chat')}
          />
        )}
      </main>
    </div>
  );
}
