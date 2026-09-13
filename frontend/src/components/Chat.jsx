import React, { useRef, useEffect } from 'react';
import { Sparkles, Loader2, BookOpen, Brain, Terminal, Cpu } from 'lucide-react';
import ChatMessage from './ChatMessage';

export default function Chat({
  messages = [],
  isLoading,
  onSelectSuggestion,
  hasReadyDocuments = false,
}) {
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of conversation
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const suggestions = [
    {
      title: 'Explain machine learning',
      desc: 'Core principles & how models learn',
      icon: Brain,
      scope: 'general',
      prompt: 'Explain machine learning in simple terms with a clear real-world analogy.',
    },
    {
      title: 'Summarize my documents',
      desc: hasReadyDocuments ? 'Synthesize insights from uploaded files' : 'Upload documents first to summarize',
      icon: BookOpen,
      scope: hasReadyDocuments ? 'all' : 'general',
      prompt: hasReadyDocuments
        ? 'What are the main findings and key points across all uploaded documents?'
        : 'What is document RAG and how does it summarize knowledge bases?',
    },
    {
      title: 'What is RAG?',
      desc: 'Retrieval-Augmented Generation',
      icon: Cpu,
      scope: 'general',
      prompt: 'What is Retrieval-Augmented Generation (RAG) and why is it useful?',
    },
    {
      title: 'What is LangGraph?',
      desc: 'Stateful agent workflows',
      icon: Terminal,
      scope: 'general',
      prompt: 'What is LangGraph and how does it structure cyclic agent workflows?',
    },
  ];

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 max-w-3xl w-full mx-auto">
      {/* Empty State Welcome Screen */}
      {messages.length === 0 ? (
        <div className="h-full flex flex-col items-center justify-center text-center py-10 sm:py-16">
          <div className="w-12 h-12 rounded-2xl bg-slate-900 flex items-center justify-center text-white shadow-md mb-4">
            <Sparkles className="w-6 h-6 text-sky-400" />
          </div>

          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 mb-2">
            How can I help you today?
          </h1>

          <p className="text-sm text-slate-500 max-w-md mb-8 leading-relaxed">
            Ask general questions, query your uploaded documents with grounded citations, or analyze research topics.
          </p>

          {/* Quick Suggestions Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-xl text-left">
            {suggestions.map((sug) => {
              const Icon = sug.icon;
              return (
                <button
                  key={sug.title}
                  type="button"
                  onClick={() => onSelectSuggestion(sug.prompt, sug.scope)}
                  className="p-3.5 bg-white hover:bg-slate-50 border border-slate-200 hover:border-slate-300 rounded-xl transition-all text-left group shadow-xs"
                >
                  <div className="flex items-center space-x-2.5 mb-1">
                    <Icon className="w-4 h-4 text-slate-500 group-hover:text-slate-900 transition-colors" />
                    <span className="text-xs font-semibold text-slate-800 group-hover:text-slate-900">
                      {sug.title}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 pl-6 leading-normal">
                    {sug.desc}
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        /* Conversation Stream */
        <div className="space-y-2 pb-6">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {/* Assistant Thinking Loading Indicator */}
          {isLoading && (
            <div className="flex items-start space-x-3 mb-6 text-left animate-pulse">
              <div className="w-7 h-7 rounded-lg bg-slate-900 flex items-center justify-center text-white shrink-0 mt-0.5 shadow-sm">
                <Sparkles className="w-3.5 h-3.5 text-sky-400" />
              </div>
              <div className="flex-1">
                <div className="text-xs font-semibold text-slate-900 mb-1">Alex</div>
                <div className="flex items-center space-x-2 text-xs text-slate-500 py-1">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-600" />
                  <span>Alex is thinking...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  );
}
