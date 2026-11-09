import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

// Compile JSX with the project's existing Vite toolchain; no browser or HTTP access.
let compiler;
let Header, Sidebar, ChatInput, ChatMessage;
before(async () => {
  compiler = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  Header = (await compiler.ssrLoadModule('/src/components/Header.jsx')).default;
  Sidebar = (await compiler.ssrLoadModule('/src/components/ConversationSidebar.jsx')).default;
  ChatInput = (await compiler.ssrLoadModule('/src/components/ChatInput.jsx')).default;
  ChatMessage = (await compiler.ssrLoadModule('/src/components/ChatMessage.jsx')).default;
});
after(async () => { await compiler?.close(); });
const render = (Component, props = {}) => renderToStaticMarkup(React.createElement(Component, props));
const state = { conversations: [{ id: 'owned', title: 'Research notes', updated_at: '2026-10-23T00:00:00Z' }],
  active: { id: 'owned' }, busyIds: [] };

test('header keeps only branding, navigation toggle, New Chat and authentication', () => {
  const html = render(Header, { historyOpen: true, userEmail: 'fixture@example.test' });
  assert.match(html, /Toggle sidebar/);
  assert.match(html, /Start a new conversation/);
  assert.match(html, /Sign out/);
  assert.doesNotMatch(html, /Ask Alex|Documents|Research — coming soon/);
});

test('expanded sidebar contains ordered destinations, disabled Research and owned history actions', () => {
  const html = render(Sidebar, { open: true, desktop: true, activeTab: 'documents', documentCount: 2, state });
  const ask = html.indexOf('aria-label="Ask Alex"');
  const documents = html.indexOf('aria-label="Documents"');
  const research = html.indexOf('aria-label="Research"');
  assert.ok(ask < documents && documents < research && research < html.indexOf('Conversations'));
  assert.match(html, /aria-label="Documents" aria-pressed="true"/);
  assert.match(html, /disabled="" aria-label="Research"/);
  assert.match(html, /Rename Research notes/);
  assert.match(html, /Delete Research notes/);
  assert.match(html, /<time/);
});

test('collapsed sidebar retains labelled icon navigation without rendering the history', () => {
  const html = render(Sidebar, { open: false, desktop: true, activeTab: 'chat', state });
  assert.match(html, /Expand sidebar/);
  assert.match(html, /aria-label="Ask Alex" aria-pressed="true"/);
  assert.match(html, /aria-label="Documents"/);
  assert.doesNotMatch(html, /Research notes|Rename|Delete|New conversation/);
});

test('mobile expanded sidebar has modal semantics and an explicit close action', () => {
  const html = render(Sidebar, { open: true, desktop: false, activeTab: 'chat', state });
  assert.match(html, /role="dialog" aria-modal="true"/);
  assert.match(html, /aria-label="Close sidebar"/);
});

test('composer keeps its existing picker, scope and labelled controls for long filenames', () => {
  const html = render(ChatInput, { selectedScope: 'general', documents: [], attachedFiles: [
    { id: 'doc', filename: 'a-long-research-filename.txt', file_size: 100, file_type: 'txt' },
  ] });
  assert.match(html, /type="file" accept=".pdf,.docx,.txt"/);
  assert.match(html, /aria-label="Message Alex"/);
  assert.match(html, /aria-label="Attach a document/);
  assert.match(html, /Remove attachment a-long-research-filename.txt/);
  assert.match(html, /aria-label="Send message"/);
});

test('assistant actions copy real content and preserve source metadata while escaping HTML', () => {
  const html = render(ChatMessage, { message: { role: 'assistant', content: '**Evidence**\n\n<script>alert(1)</script>\n\n```js\nconst evidence = 1;\n```',
    citations: [{ filename: 'actual-source.txt', page_number: 3, relevance_score: 0.8 }] } });
  assert.match(html, /Copy response/);
  assert.match(html, /Copy code/);
  assert.match(html, /actual-source.txt/);
  assert.match(html, /Page 3/);
  assert.match(html, /80% similarity/);
  assert.match(html, /&lt;script&gt;/);
  assert.doesNotMatch(html, /<script>/);
});

test('failed messages offer reload recovery, not an unsupported regeneration endpoint', () => {
  const html = render(ChatMessage, { message: { role: 'assistant', content: 'Storage unavailable', error: true }, onRecover() {} });
  assert.match(html, /Reload conversation/);
  assert.doesNotMatch(html, /Copy response|Regenerate/);
});
