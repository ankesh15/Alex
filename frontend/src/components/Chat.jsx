import React, { useRef, useEffect, useLayoutEffect, useState } from 'react';
import { Sparkles, Loader2, BookOpen, Brain, Terminal, Cpu, ArrowDown } from 'lucide-react';
import ChatMessage from './ChatMessage';
import { isNearLatest, scrollAdjustment } from '../utils/workspaceLayout';

export default function Chat({
  messages = [],
  isLoading,
  onSelectSuggestion,
  hasReadyDocuments = false,
  historyLoading = false,
  historyError = null,
  onRetryHistory,
  hasOlder = false,
  olderLoading = false,
  onLoadOlder,
  onRecover,
}) {
  const scrollRef = useRef(null);
  const contentRef = useRef(null);
  const previous = useRef(null);
  const followLatest = useRef(true);
  const [awayFromLatest, setAwayFromLatest] = useState(false);
  const [newMessages, setNewMessages] = useState(false);
  const recordScroll = () => {
    const element = scrollRef.current;
    if (!element) return;
    const near = isNearLatest(element);
    followLatest.current = near;
    setAwayFromLatest(!near);
    if (near) setNewMessages(false);
    if (previous.current) previous.current.scrollTop = element.scrollTop;
  };
  useLayoutEffect(() => {
    const element = scrollRef.current;
    if (!element) return;
    const next = { first: messages[0]?.id, last: messages.at(-1)?.id,
      scrollHeight: element.scrollHeight, scrollTop: element.scrollTop };
    const adjustment = scrollAdjustment(previous.current, next, followLatest.current);
    if (adjustment.top !== null) element.scrollTop = adjustment.top;
    if (adjustment.newMessages) setNewMessages(true);
    previous.current = { ...next, scrollTop: element.scrollTop };
    recordScroll();
  }, [messages, isLoading]);
  useEffect(() => {
    const observer = new ResizeObserver(() => {
      const element = scrollRef.current;
      if (!element) return;
      if (followLatest.current) element.scrollTop = element.scrollHeight;
      if (previous.current) previous.current.scrollHeight = element.scrollHeight;
      recordScroll();
    });
    observer.observe(scrollRef.current);
    observer.observe(contentRef.current);
    return () => observer.disconnect();
  }, []);
  const jumpToLatest = () => {
    const element = scrollRef.current;
    followLatest.current = true;
    setNewMessages(false);
    element?.scrollTo({ top: element.scrollHeight,
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  };

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
    <section className="relative flex-1 min-h-0" aria-label="Chat messages">
      <div ref={scrollRef} onScroll={recordScroll} className="chat-scroll-region h-full overflow-y-auto overscroll-contain" tabIndex={0} role="region" aria-label="Conversation messages">
      <div ref={contentRef} className={`px-4 sm:px-6 py-6 sm:py-8 max-w-3xl w-full min-h-full mx-auto ${messages.length === 0 ? 'flex flex-col' : ''}`}>
      {historyLoading && <p role="status" className="text-sm text-slate-500 py-8 text-center">Loading conversation…</p>}
      {historyError && <div role="alert" className="text-sm text-red-700 bg-red-50 rounded-lg p-3 mb-4">{historyError}<button type="button" onClick={onRetryHistory} className="block underline mt-2">Retry messages</button></div>}
      {hasOlder && <button type="button" onClick={onLoadOlder} disabled={olderLoading} className="block mx-auto mb-4 text-xs text-sky-700 underline disabled:opacity-50">{olderLoading ? 'Loading older messages…' : 'Load older messages'}</button>}
      {/* Empty State Welcome Screen */}
      {historyLoading || (historyError && !messages.length) ? null : messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center py-6 sm:py-10">
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
                  className="p-3.5 bg-white hover:bg-slate-50 border border-slate-200 hover:border-slate-300 rounded-xl transition-colors text-left group shadow-sm"
                >
                  <div className="flex items-center space-x-2.5 mb-1">
                    <Icon className="w-4 h-4 text-slate-500 group-hover:text-slate-900 transition-colors" />
                    <span className="text-sm font-semibold text-slate-800 group-hover:text-slate-900">
                      {sug.title}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 pl-6 leading-normal">
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
            <ChatMessage key={msg.id} message={msg} onRecover={onRecover} recoveryDisabled={isLoading || historyLoading} />
          ))}

          {/* Assistant Thinking Loading Indicator */}
          {isLoading && (
            <div role="status" aria-live="polite" className="flex items-start space-x-3 mb-6 text-left">
              <div className="w-7 h-7 rounded-lg bg-slate-900 flex items-center justify-center text-white shrink-0 mt-0.5 shadow-sm">
                <Sparkles className="w-3.5 h-3.5 text-sky-400" />
              </div>
              <div className="flex-1">
                <div className="text-sm font-semibold text-slate-900 mb-1">Alex</div>
                <div className="flex items-center space-x-2 text-xs text-slate-500 py-1">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-600" />
                  <span>Alex is thinking...</span>
                </div>
              </div>
            </div>
          )}

          <div aria-hidden="true" className="h-2" />
        </div>
      )}
      </div>
      </div>
      {awayFromLatest && messages.length > 0 && <div className="absolute bottom-4 inset-x-0 flex justify-center pointer-events-none">
        <button type="button" onClick={jumpToLatest} className="secondary-button pointer-events-auto rounded-full shadow-md gap-2 text-xs" aria-label="Jump to latest messages">
          <ArrowDown className="w-4 h-4" aria-hidden="true" />{newMessages ? 'New messages · Jump to latest' : 'Jump to latest'}
        </button>
      </div>}
    </section>
  );
}
