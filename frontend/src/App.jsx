import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import Chat from './components/Chat';
import ChatInput from './components/ChatInput';
import DocumentsView from './components/DocumentsView';
import {
  fetchDocuments,
  uploadDocument,
  deleteChatDocuments,
  askAlex,
  askAlexGeneral
} from './services/api';

const generateChatId = () =>
  `chat-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'documents'
  const [chatId, setChatId] = useState(generateChatId);

  // Chat-scoped documents state
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [docsError, setDocsError] = useState(null);

  // Scope: 'general' | 'all' | document_id
  const [selectedScope, setSelectedScope] = useState('general');

  // Active composer file attachments
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [isUploadingAttachment, setIsUploadingAttachment] = useState(false);

  // Conversational chat state
  const [messages, setMessages] = useState([]);
  const [isAsking, setIsAsking] = useState(false);

  const loadDocuments = useCallback(async (currentChatId = chatId) => {
    if (!currentChatId) return;
    setIsLoadingDocs(true);
    setDocsError(null);
    try {
      const data = await fetchDocuments(currentChatId);
      setDocuments(data.documents || []);
    } catch (err) {
      setDocsError(err.message || 'Unable to connect to Alex backend.');
    } finally {
      setIsLoadingDocs(false);
    }
  }, [chatId]);

  useEffect(() => {
    loadDocuments(chatId);
  }, [chatId, loadDocuments]);

  // Handle attaching a document inside the chat composer
  const handleAttachFile = async (file) => {
    if (!file) return;

    // Check extension
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'docx', 'txt'].includes(ext)) {
      alert(`Unsupported format .${ext}. Please attach a PDF, DOCX, or TXT file.`);
      return;
    }

    // Check size limit (20MB)
    if (file.size > 20 * 1024 * 1024) {
      alert('File exceeds the 20 MB size limit.');
      return;
    }

    setIsUploadingAttachment(true);
    try {
      const uploadedDoc = await uploadDocument(file, chatId);
      setAttachedFiles((prev) => [...prev, uploadedDoc]);
      await loadDocuments(chatId);

      // Auto-switch scope to this attached document or All Documents
      setSelectedScope(uploadedDoc.id || 'all');
    } catch (err) {
      alert(err.message || 'Failed to attach document.');
    } finally {
      setIsUploadingAttachment(false);
    }
  };

  const handleRemoveAttachment = (docId) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== docId));
    if (selectedScope === docId) {
      setSelectedScope(attachedFiles.length > 1 ? 'all' : 'general');
    }
  };

  const handleSendMessage = async (text, overrideScope = null) => {
    const scopeToUse = overrideScope || selectedScope;
    const currentPromptAttachments = [...attachedFiles];

    // Clear pending composer attachments once message is sent
    setAttachedFiles([]);

    const userMsgId = `user-${Date.now()}`;
    const userMsg = {
      id: userMsgId,
      role: 'user',
      content: text,
      attachments: currentPromptAttachments,
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
        // Document RAG Mode: All documents for this chat or specific document id
        const docId = scopeToUse === 'all' ? null : scopeToUse;
        res = await askAlex(text, docId, 5, chatId);
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

  // Start a New Chat: purge previous temporary files and reset state
  const handleNewChat = async () => {
    const oldChatId = chatId;
    const nextChatId = generateChatId();

    // 1. Immediately reset client state
    setMessages([]);
    setAttachedFiles([]);
    setDocuments([]);
    setSelectedScope('general');
    setActiveTab('chat');
    setChatId(nextChatId);

    // 2. Asynchronously delete previous temporary chat documents from backend & disk
    try {
      await deleteChatDocuments(oldChatId);
    } catch (err) {
      // Non-blocking cleanup failure logging
    }
  };

  const handleDocumentDeleted = (deletedId) => {
    setDocuments((prev) => prev.filter((d) => d.id !== deletedId));
    setAttachedFiles((prev) => prev.filter((f) => f.id !== deletedId));
    if (selectedScope === deletedId) {
      setSelectedScope('general');
    }
  };

  const readyDocuments = documents.filter((d) => d.status === 'READY');

  return (
    <div className="h-screen flex flex-col bg-slate-50 text-slate-900 font-sans overflow-hidden">
      {/* Shared Minimal Header */}
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        documentCount={readyDocuments.length}
        onNewChat={handleNewChat}
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

            {/* Pinned Bottom Input with '+' Attach and Scope Selector */}
            <ChatInput
              onSendMessage={handleSendMessage}
              isLoading={isAsking}
              documents={documents}
              selectedScope={selectedScope}
              onScopeChange={setSelectedScope}
              onAttachFile={handleAttachFile}
              attachedFiles={attachedFiles}
              onRemoveAttachment={handleRemoveAttachment}
              isUploadingAttachment={isUploadingAttachment}
            />
          </>
        ) : (
          /* Focused Documents Panel Sharing the Design Language */
          <DocumentsView
            documents={documents}
            chatId={chatId}
            isLoading={isLoadingDocs}
            error={docsError}
            onRetry={() => loadDocuments(chatId)}
            onUploadSuccess={() => loadDocuments(chatId)}
            onDocumentDeleted={handleDocumentDeleted}
            onBackToChat={() => setActiveTab('chat')}
          />
        )}
      </main>
    </div>
  );
}
