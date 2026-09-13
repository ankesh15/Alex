import React from 'react';
import UploadDocument from './UploadDocument';
import DocumentList from './DocumentList';
import { ArrowLeft, FileText, Info } from 'lucide-react';

export default function DocumentsView({
  documents,
  chatId,
  isLoading,
  error,
  onRetry,
  onUploadSuccess,
  onDocumentDeleted,
  onBackToChat,
}) {
  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 max-w-3xl w-full mx-auto space-y-5">
      {/* Header with back link */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-200">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Documents</h2>
          <p className="text-xs text-slate-500">
            Manage files for your current chat session.
          </p>
        </div>
        <button
          type="button"
          onClick={onBackToChat}
          className="inline-flex items-center space-x-1 text-xs font-medium text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200/80 px-2.5 py-1.5 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Chat</span>
        </button>
      </div>

      {/* Temporary Notice Pill */}
      <div className="p-3 bg-sky-50/70 border border-sky-200/60 rounded-xl text-xs text-sky-800 flex items-center space-x-2.5">
        <Info className="w-4 h-4 text-sky-600 shrink-0" />
        <span>
          Files belong only to this chat session. When you click <strong>New Chat</strong>, all files and embeddings for this chat are automatically deleted.
        </span>
      </div>

      {/* Upload Component */}
      <UploadDocument onUploadSuccess={onUploadSuccess} chatId={chatId} />

      {/* Document List Component */}
      <DocumentList
        documents={documents}
        isLoading={isLoading}
        error={error}
        onRetry={onRetry}
        onDocumentDeleted={onDocumentDeleted}
      />
    </div>
  );
}
