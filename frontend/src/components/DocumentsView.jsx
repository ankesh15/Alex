import React from 'react';
import UploadDocument from './UploadDocument';
import DocumentList from './DocumentList';
import { ArrowLeft } from 'lucide-react';

export default function DocumentsView({
  documents,
  isLoading,
  error,
  onRetry,
  onUploadSuccess,
  onDocumentDeleted,
  onBackToChat,
}) {
  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 max-w-3xl w-full mx-auto space-y-6">
      {/* Header with quick back link */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-200">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Knowledge Base Documents</h2>
          <p className="text-xs text-slate-500">
            Upload PDF, DOCX, or TXT files to index them into pgvector for grounded retrieval.
          </p>
        </div>
        <button
          type="button"
          onClick={onBackToChat}
          className="inline-flex items-center space-x-1 text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200/80 px-2.5 py-1.5 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Chat</span>
        </button>
      </div>

      {/* Upload Component */}
      <UploadDocument onUploadSuccess={onUploadSuccess} />

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
