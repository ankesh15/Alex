import React, { useState, useRef, useEffect } from 'react';
import { Upload, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { uploadDocument } from '../services/api';

export default function UploadDocument({ onUploadSuccess, chatId }) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null); // 'success' | 'error' | null
  const [errorMessage, setErrorMessage] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);
  const successTimer = useRef(null);
  useEffect(() => () => clearTimeout(successTimer.current), []);

  const handleFile = async (file) => {
    if (!file || isUploading) return;
    clearTimeout(successTimer.current);

    // Check extension
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'docx', 'txt'].includes(ext)) {
      setUploadStatus('error');
      setErrorMessage(`Unsupported format .${ext}. Please upload a PDF, DOCX, or TXT file.`);
      return;
    }

    // Check size (20MB)
    if (file.size > 20 * 1024 * 1024) {
      setUploadStatus('error');
      setErrorMessage('File exceeds the 20 MB size limit.');
      return;
    }

    setIsUploading(true);
    setUploadStatus(null);
    setErrorMessage('');

    try {
      const document = await uploadDocument(file, chatId);
      if (document.status === 'FAILED') {
        if (onUploadSuccess) onUploadSuccess();
        throw new Error('This document could not be processed. Check the file and try again.');
      }
      setUploadStatus('success');
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (onUploadSuccess) onUploadSuccess();

      // Clear success notification after 4 seconds
      successTimer.current = setTimeout(() => {
        setUploadStatus(null);
      }, 4000);
    } catch (err) {
      setUploadStatus('error');
      setErrorMessage(err.message || 'Failed to upload document.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-5 shadow-sm">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-slate-900">Upload Document</h3>
        <p className="text-xs text-slate-500">Supports PDF, DOCX, and TXT files up to 20 MB.</p>
      </div>

      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}

        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          dragActive
            ? 'border-sky-500 bg-sky-50/50'
            : isUploading
            ? 'border-slate-200 bg-slate-50/50 cursor-wait'
            : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
        }`}
      >
        <button type="button" disabled={isUploading} onClick={() => fileInputRef.current?.click()}
          className="w-full rounded-lg py-2 min-h-28" aria-label="Choose a document to upload" aria-busy={isUploading}>
        {isUploading ? (
          <span role="status" className="flex flex-col items-center gap-2 text-sky-700">
            <Loader2 className="w-7 h-7 animate-spin" aria-hidden="true" />
            <span className="text-sm font-medium">Uploading and processing…</span>
            <span className="text-xs text-slate-500">Your document will appear below when it is ready.</span>
          </span>
        ) : (
          <span className="flex flex-col items-center gap-2">
            <span className="w-11 h-11 rounded-xl bg-slate-100 flex items-center justify-center"><Upload className="w-5 h-5 text-slate-600" aria-hidden="true" /></span>
            <span className="text-sm font-medium text-slate-700"><span className="text-sky-700 underline underline-offset-2">Choose a file</span> or drag it here</span>
            <span className="text-xs text-slate-500">PDF, DOCX, TXT · Up to 20 MB</span>
          </span>
        )}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          disabled={isUploading}
          onChange={(e) => handleFile(e.target.files?.[0])}
        />

      </div>

      {uploadStatus === 'success' && (
        <div role="status" className="mt-3 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>Document uploaded and indexed successfully! It is now searchable.</span>
        </div>
      )}

      {uploadStatus === 'error' && (
        <div role="alert" className="mt-3 p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
}
