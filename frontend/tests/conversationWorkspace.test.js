import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createConversationWorkspace } from '../src/state/conversationWorkspace.js';

const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
const page = (label, options = {}) => ({ messages: [
  { id: `${label}:user`, role: 'user', content: `${label} question` },
  { id: `${label}:assistant`, role: 'assistant', content: `${label} answer`, citations: [{ filename: 'paper.txt' }], tokenUsage: { total_tokens: 4 } },
], next_before_turn: null, through_turn: 1, ...options });

function harness(extra = {}, storage = null) {
  const rows = new Map(['a', 'b'].map(id => [id, { id, title: `Chat ${id}`, updated_at: '2026-10-13T00:00:00Z', last_scope: 'general' }]));
  const history = new Map(['a', 'b'].map(id => [id, page(id)]));
  let counter = 0;
  const calls = [];
  const api = {
    async listConversations(cursor) { calls.push(['list', cursor]); return { conversations: [...rows.values()], next_cursor: null }; },
    async fetchConversation(id) { if (!rows.has(id)) throw Object.assign(new Error('Unavailable'), { status: 404 }); return { ...rows.get(id) }; },
    async fetchMessages(id, options) { calls.push(['history', id, options]); return history.get(id) || { messages: [], next_before_turn: null, through_turn: 0 }; },
    async fetchDocuments(id) { calls.push(['documents', id]); return { documents: [] }; },
    async createConversation() { const id = `created-${++counter}`; const row = { id, title: 'New chat', last_scope: 'general' }; rows.set(id, row); return row; },
    async renameConversation(id, title) { const row = { ...rows.get(id), title }; rows.set(id, row); return row; },
    async deleteConversation(id) { calls.push(['delete', id]); rows.delete(id); history.delete(id); return { id, cleanup_pending: 0 }; },
    async askAlexGeneral(question, id) { calls.push(['general', question, id]); const response = { answer: `${id} persisted reply` };
      history.set(id, page(id, { messages: [...(history.get(id)?.messages || []), { id: 'server-user', role: 'user', content: question }, { id: 'server-assistant', role: 'assistant', content: response.answer }], through_turn: 2 }));
      rows.set(id, { ...rows.get(id), title: 'Saved title' }); return response; },
    async askAlex(question, documentId, topK, id) { calls.push(['rag', question, documentId, topK, id]); return { answer: 'Document reply', citations: [{ filename: 'paper.txt' }] }; },
    async uploadDocument(file, id) { calls.push(['upload', id]); return { id: 'uploaded', status: 'READY', filename: file.name }; },
    ...extra,
  };
  return { controller: createConversationWorkspace({ api, userId: 'alice', storage }), api, rows, history, calls };
}

test('reopening uses saved messages and continues the same server conversation', async () => {
  const { controller, calls } = harness();
  await controller.open('a');
  assert.equal(controller.getState().messages[1].content, 'a answer');
  await controller.send('Follow-up');
  assert.deepEqual(calls.find(c => c[0] === 'general'), ['general', 'Follow-up', 'a']);
  await controller.open('b');
  await controller.open('a');
  assert.equal(controller.getState().messages.at(-1).content, 'a persisted reply');
  assert.equal(controller.getState().active.title, 'Saved title');
});

test('conversation pagination appends, deduplicates and terminates', async () => {
  const { controller, calls } = harness({ async listConversations(cursor) {
    calls.push(['page', cursor]);
    return cursor ? { conversations: [{ id: 'a' }, { id: 'b' }], next_cursor: null } : { conversations: [{ id: 'a' }], next_cursor: 'next' };
  } });
  await controller.refreshList();
  await controller.loadMore();
  await controller.loadMore();
  assert.deepEqual(controller.getState().conversations.map(c => c.id), ['a', 'b']);
  assert.equal(calls.filter(c => c[0] === 'page').length, 2);
});

test('older message pagination keeps chronological order and the initial upper bound', async () => {
  const { controller, calls } = harness({ async fetchMessages(id, options) {
    calls.push(['page', options]);
    return options?.beforeTurn ? page('old') : page('new', { next_before_turn: 3, through_turn: 4 });
  } });
  await controller.open('a');
  await controller.loadOlder();
  assert.deepEqual(controller.getState().messages.map(m => m.content), ['old question', 'old answer', 'new question', 'new answer']);
  assert.deepEqual(calls.find(c => c[0] === 'page' && c[1])[1], { beforeTurn: 3, throughTurn: 4 });
  assert.equal(controller.getState().beforeTurn, null);
});

test('late history responses cannot overwrite another selected conversation', async () => {
  const slow = deferred();
  const { controller } = harness({ fetchMessages: id => id === 'a' ? slow.promise : Promise.resolve(page('b')) });
  const old = controller.open('a');
  await controller.open('b');
  slow.resolve(page('old-a'));
  await old;
  assert.equal(controller.getState().active.id, 'b');
  assert.equal(controller.getState().messages[0].content, 'b question');
});

test('A to B to A switching rejects the first A response using a generation', async () => {
  const first = deferred();
  let loads = 0;
  const { controller } = harness({ fetchMessages: id => id === 'a' && ++loads === 1 ? first.promise : Promise.resolve(page(`latest-${id}`)) });
  const old = controller.open('a');
  await controller.open('b');
  await controller.open('a');
  first.resolve(page('stale-a'));
  await old;
  assert.equal(controller.getState().messages[0].content, 'latest-a question');
});

test('a late generation response never appears in a different chat', async () => {
  const response = deferred();
  const { controller } = harness({ askAlexGeneral: () => response.promise });
  await controller.open('a');
  const pending = controller.send('Old request');
  await controller.open('b');
  response.resolve({ answer: 'Private A response' });
  await pending;
  assert.equal(controller.getState().active.id, 'b');
  assert.ok(controller.getState().messages.every(m => !m.content.includes('Private A')));
  assert.equal(controller.getState().isSending, false);
});

test('create does not delete previous documents or chat history', async () => {
  const { controller, calls } = harness();
  await controller.open('a');
  await controller.create();
  assert.equal(controller.getState().active.id, 'created-1');
  assert.equal(calls.filter(c => c[0] === 'delete').length, 0);
  await controller.open('a');
  assert.equal(controller.getState().messages[0].content, 'a question');
});

test('delete clears selected messages and cannot be undone by an in-flight reply', async () => {
  const response = deferred();
  const storage = new Map();
  const { controller } = harness({ askAlexGeneral: () => response.promise }, { setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) });
  await controller.open('a');
  const pending = controller.send('Old request');
  await controller.delete('a');
  assert.equal(controller.getState().active, null);
  assert.deepEqual(controller.getState().messages, []);
  assert.equal(storage.size, 0);
  response.resolve({ answer: 'Late deleted answer' });
  await pending;
  assert.deepEqual(controller.getState().messages, []);
  assert.ok(controller.getState().conversations.every(c => c.id !== 'a'));
});

test('rename updates the list and active title, while cleanup remains retryable', async () => {
  let retries = 0;
  const { controller } = harness({ async deleteConversation(id) { return { id, cleanup_pending: ++retries === 1 ? 1 : 0 }; } });
  await controller.refreshList();
  await controller.open('a');
  await controller.rename('a', 'Research');
  assert.equal(controller.getState().active.title, 'Research');
  assert.equal(controller.getState().conversations.find(c => c.id === 'a').title, 'Research');
  await controller.delete('a');
  assert.equal(controller.getState().cleanupRetryId, 'a');
  await controller.delete('a');
  assert.equal(controller.getState().cleanupRetryId, null);
});

test('last selection is a per-user ID preference, never a stored transcript', async () => {
  const writes = [];
  const { controller } = harness({}, { getItem: key => key === 'alex.activeConversation.alice' ? 'b' : null, setItem: (...args) => writes.push(args) });
  await controller.initialize();
  assert.equal(controller.getState().active.id, 'b');
  assert.deepEqual(writes.at(-1), ['alex.activeConversation.alice', 'b']);
});

test('a stale selection preference falls back without exposing a foreign conversation', async () => {
  const { controller } = harness({}, { getItem: () => 'foreign', removeItem() {}, setItem() {} });
  await controller.initialize();
  assert.equal(controller.getState().active.id, 'a');
  assert.ok(controller.getState().messages.every(m => !m.content.includes('foreign')));
});

test('a missing old document restores RAG scope without switching to general knowledge', async () => {
  const { controller, calls } = harness({ async fetchConversation(id) { return { id, title: 'Document chat', last_scope: 'document:removed' }; } });
  await controller.open('a');
  assert.equal(controller.getState().scope, 'all');
  await controller.send('Follow-up');
  assert.deepEqual(calls.find(c => c[0] === 'rag'), ['rag', 'Follow-up', null, 5, 'a']);
});

test('logout/deactivation discards in-flight responses and does not fetch another account', async () => {
  const response = deferred();
  const { controller, calls } = harness({ askAlexGeneral: () => response.promise });
  await controller.open('a');
  const pending = controller.send('Old request');
  controller.deactivate();
  response.resolve({ answer: 'Private response' });
  await pending;
  assert.ok(controller.getState().messages.every(m => m.content !== 'Private response'));
  assert.equal(calls.filter(c => c[0] === 'list').length, 0);
});

test('late uploads cannot change documents or scope of another selected conversation', async () => {
  const response = deferred();
  const { controller } = harness({ uploadDocument: () => response.promise });
  await controller.open('a');
  const pending = controller.upload({ name: 'old.txt' });
  await controller.open('b');
  response.resolve({ id: 'old-upload', status: 'READY' });
  await pending;
  assert.deepEqual(controller.getState().documents, []);
  assert.equal(controller.getState().scope, 'general');
  assert.equal(controller.getState().isUploading, false);
});
