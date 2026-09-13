import React, { useState } from 'react';
import { FileText, Trash2, CheckCircle, Clock, XCircle, AlertTriangle } from 'lucide-react';
import { deleteDocument } from '../services/api';

export default function DocumentList({ documents, isLoading, error, onRetry, onDocumentDeleted }) {
  const [deletingId, setDeletingId] = useState(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [deleteError, setDeleteError] = useState('');

  const handleDelete = async (docId) => {
    setDeletingId(docId);
    setDeleteError('');
    try {
      await deleteDocument(docId);
      setConfirmDeleteId(null);
      if (onDocumentDeleted) onDocumentDeleted(docId);
    } catch (err) {
      setDeleteError(err.message || 'Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const renderStatusBadge = (status) => {
    switch (status) {
      case 'READY':
        return (
          <span className="inline-flex items-center space-x-1 text-[11px] font-medium bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full border border-emerald-200/50">
            <CheckCircle className="w-3 h-3" />
            <span>READY</span>
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center space-x-1 text-[11px] font-medium bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full border border-amber-200/50">
            <Clock className="w-3 h-3 animate-spin" />
            <span>PROCESSING</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center space-x-1 text-[11px] font-medium bg-red-50 text-red-700 px-2 py-0.5 rounded-full border border-red-200/50">
            <XCircle className="w-3 h-3" />
            <span>FAILED</span>
          </span>
        );
      default:
        return (
          <span className="text-[11px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Documents ({documents.length})</h3>
          <p className="text-xs text-slate-500">Indexed documents available for RAG question answering.</p>
        </div>
      </div>

      {deleteError && (
        <div className="mb-3 p-2.5 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs">
          {deleteError}
        </div>
      )}

      {error ? (
        <div className="py-6 px-4 text-center bg-red-50 border border-red-200 rounded-lg">
          <AlertTriangle className="w-6 h-6 text-red-500 mx-auto mb-2" />
          <p className="text-xs font-medium text-red-800">{error}</p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-2 text-xs text-sky-600 hover:text-sky-700 font-medium underline"
            >
              Try again
            </button>
          )}
        </div>
      ) : isLoading ? (
        <div className="py-8 text-center text-xs text-slate-400">Loading documents...</div>
      ) : documents.length === 0 ? (
        <div className="py-8 text-center border border-dashed border-slate-200 rounded-lg">
          <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
          <p className="text-xs font-medium text-slate-600">No documents uploaded yet</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Upload a PDF, DOCX, or TXT file to begin</p>
        </div>
      ) : (
        <div className="divide-y divide-slate-100">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-slate-50/50 rounded-lg px-2 transition-colors"
            >
              {/* Document Info */}
              <div className="flex items-center space-x-3 min-w-0">
                <div className="w-8 h-8 rounded bg-slate-100 flex items-center justify-center text-slate-600 shrink-0 uppercase font-semibold text-[10px]">
                  {doc.file_type}
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-medium text-slate-900 truncate" title={doc.filename}>
                    {doc.filename}
                  </div>
                  <div className="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5">
                    <span>{formatFileSize(doc.file_size)}</span>
                    <span>•</span>
                    <span>{formatDate(doc.created_at)}</span>
                  </div>
                </div>
              </div>

              {/* Status & Actions */}
              <div className="flex items-center justify-between sm:justify-end space-x-3 shrink-0">
                {renderStatusBadge(doc.status)}

                {confirmDeleteId === doc.id ? (
                  <div className="flex items-center space-x-1.5 bg-red-50 p-1 rounded-md border border-red-200">
                    <span className="text-[11px] text-red-700 px-1">Confirm?</span>
                    <button
                      type="button"
                      disabled={deletingId === doc.id}
                      onClick={() => handleDelete(doc.id)}
                      className="text-[11px] font-semibold bg-red-600 hover:bg-red-700 text-white px-2 py-0.5 rounded transition-colors"
                    >
                      {deletingId === doc.id ? '...' : 'Delete'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmDeleteId(null)}
                      className="text-[11px] text-slate-500 hover:text-slate-800 px-1"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setConfirmDeleteId(doc.id)}
                    className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
