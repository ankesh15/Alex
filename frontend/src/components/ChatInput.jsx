import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, Loader2, Globe, Library, FileText, ChevronDown, Plus, X } from 'lucide-react';

export default function ChatInput({
  onSendMessage,
  isLoading,
  documents = [],
  selectedScope,
  onScopeChange,
  onAttachFile,
  attachedFiles = [],
  onRemoveAttachment,
  isUploadingAttachment = false,
}) {
  const [text, setText] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const textareaRef = useRef(null);
  const dropdownRef = useRef(null);
  const fileInputRef = useRef(null);

  const readyDocs = documents.filter((d) => d.status === 'READY');

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [text]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!text.trim() || isLoading || isUploadingAttachment) return;
    onSendMessage(text.trim());
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileSelected = (e) => {
    const file = e.target.files?.[0];
    if (file && onAttachFile) {
      onAttachFile(file);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  // Determine active scope label and icon
  const getActiveScopeLabel = () => {
    if (selectedScope === 'general') return { icon: Globe, label: 'General' };
    if (selectedScope === 'all') return { icon: Library, label: 'All Documents' };
    const doc = readyDocs.find((d) => d.id === selectedScope);
    if (doc) return { icon: FileText, label: doc.filename };
    return { icon: Globe, label: 'General' };
  };

  const activeScopeInfo = getActiveScopeLabel();
  const ScopeIcon = activeScopeInfo.icon;

  const getPlaceholder = () => {
    if (attachedFiles.length > 0) {
      return `Ask a question about ${attachedFiles.map((f) => f.filename).join(', ')}...`;
    }
    if (selectedScope === 'general') {
      return 'Ask Alex anything...';
    }
    if (selectedScope === 'all') {
      return readyDocs.length === 0
        ? 'Attach a file or ask a general question...'
        : 'Ask a question across all documents...';
    }
    return `Ask about ${activeScopeInfo.label}...`;
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4 sm:pb-6">
      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        className="hidden"
        disabled={isLoading || isUploadingAttachment}
        onChange={handleFileSelected}
      />

      {/* Compact Attachment Previews Above Input */}
      {(attachedFiles.length > 0 || isUploadingAttachment) && (
        <div className="mb-2 flex flex-wrap gap-2 items-center">
          {attachedFiles.map((file) => (
            <div
              key={file.id || file.filename}
              className="inline-flex items-center space-x-2 bg-slate-100 hover:bg-slate-200/80 border border-slate-200 rounded-xl px-2.5 py-1.5 text-left text-xs transition-colors"
            >
              <FileText className="w-4 h-4 text-slate-600 shrink-0" />
              <div className="min-w-0 max-w-[180px]">
                <div className="font-medium text-slate-900 truncate" title={file.filename}>
                  {file.filename}
                </div>
                <div className="text-[10px] text-slate-500">
                  {file.file_type?.toUpperCase() || 'FILE'} • {formatFileSize(file.file_size)}
                </div>
              </div>
              <button
                type="button"
                onClick={() => onRemoveAttachment(file.id)}
                className="text-slate-400 hover:text-slate-700 p-0.5 rounded transition-colors ml-1"
                title="Remove attachment"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}

          {isUploadingAttachment && (
            <div className="inline-flex items-center space-x-1.5 bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-xs text-slate-500">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-600" />
              <span>Attaching file...</span>
            </div>
          )}
        </div>
      )}

      {/* Main Rounded Input Box */}
      <div className="relative bg-white border border-slate-300 hover:border-slate-400 focus-within:border-slate-500 focus-within:ring-2 focus-within:ring-slate-100 rounded-2xl shadow-sm transition-all p-2.5">
        <div className="flex items-start space-x-2">
          {/* ChatGPT-style '+' Attachment Button */}
          <button
            type="button"
            disabled={isLoading || isUploadingAttachment}
            onClick={() => fileInputRef.current?.click()}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-full transition-colors mt-0.5 shrink-0"
            title="Attach a document (PDF, DOCX, TXT)"
          >
            <Plus className="w-4 h-4" />
          </button>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={getPlaceholder()}
            rows={1}
            disabled={isLoading}
            className="w-full text-sm text-slate-900 placeholder:text-slate-400 bg-transparent resize-none focus:outline-none max-h-44 leading-relaxed pr-2 pl-1 py-1"
          />
        </div>

        {/* Bottom Bar: Scope Selector on Left, Send Button on Right */}
        <div className="flex items-center justify-between pt-2 mt-1 border-t border-slate-100 pl-1">
          {/* Scope Selector Control */}
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              disabled={isLoading}
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="inline-flex items-center space-x-1.5 text-xs font-medium text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200/80 px-2.5 py-1 rounded-lg transition-colors"
            >
              <ScopeIcon className="w-3.5 h-3.5 text-slate-500" />
              <span className="max-w-[150px] truncate">{activeScopeInfo.label}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {/* Scope Dropdown Menu */}
            {dropdownOpen && (
              <div className="absolute bottom-full mb-2 left-0 w-64 bg-white border border-slate-200 rounded-xl shadow-lg py-1.5 z-50 text-xs">
                <div className="px-3 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                  Context Scope
                </div>

                {/* General Option */}
                <button
                  type="button"
                  onClick={() => {
                    onScopeChange('general');
                    setDropdownOpen(false);
                  }}
                  className={`w-full text-left px-3 py-2 flex items-start space-x-2 hover:bg-slate-50 transition-colors ${
                    selectedScope === 'general' ? 'bg-slate-50 font-medium text-slate-900' : 'text-slate-700'
                  }`}
                >
                  <Globe className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
                  <div>
                    <div className="font-medium">General</div>
                    <div className="text-[10px] text-slate-400">Gemini chat • No documents / no citations</div>
                  </div>
                </button>

                {/* All Documents Option */}
                <button
                  type="button"
                  onClick={() => {
                    onScopeChange('all');
                    setDropdownOpen(false);
                  }}
                  className={`w-full text-left px-3 py-2 flex items-start space-x-2 hover:bg-slate-50 transition-colors ${
                    selectedScope === 'all' ? 'bg-slate-50 font-medium text-slate-900' : 'text-slate-700'
                  }`}
                >
                  <Library className="w-4 h-4 text-slate-500 mt-0.5 shrink-0" />
                  <div>
                    <div className="font-medium">All Chat Documents ({readyDocs.length})</div>
                    <div className="text-[10px] text-slate-400">RAG search across current chat's files</div>
                  </div>
                </button>

                {/* Specific Ready Documents */}
                {readyDocs.length > 0 && (
                  <>
                    <div className="my-1 border-t border-slate-100" />
                    <div className="px-3 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                      Specific Document
                    </div>
                    {readyDocs.map((doc) => (
                      <button
                        key={doc.id}
                        type="button"
                        onClick={() => {
                          onScopeChange(doc.id);
                          setDropdownOpen(false);
                        }}
                        className={`w-full text-left px-3 py-1.5 flex items-center space-x-2 hover:bg-slate-50 transition-colors ${
                          selectedScope === doc.id ? 'bg-slate-50 font-medium text-slate-900' : 'text-slate-700'
                        }`}
                      >
                        <FileText className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span className="truncate flex-1">{doc.filename}</span>
                      </button>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Right Action: Loading or Send Button */}
          <div className="flex items-center space-x-2">
            {isLoading && (
              <div className="flex items-center space-x-1.5 text-xs text-slate-500 pr-1">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-600" />
                <span className="hidden sm:inline">Alex is thinking...</span>
              </div>
            )}

            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading || !text.trim() || isUploadingAttachment}
              className="w-8 h-8 rounded-full bg-slate-900 hover:bg-slate-800 disabled:bg-slate-200 text-white disabled:text-slate-400 flex items-center justify-center transition-colors shadow-sm disabled:cursor-not-allowed"
              title="Send message (Enter)"
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Subtle Disclaimer */}
      <div className="text-[11px] text-center text-slate-400 mt-2">
        Files are temporary and isolated to this chat session. Use New Chat to start fresh.
      </div>
    </div>
  );
}
