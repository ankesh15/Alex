import { test, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { askAlex, askAlexGeneral, clearAuthSession } from '../src/services/api.js';

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; clearAuthSession(); });

test('cookies and session-bound CSRF protect every mutation including uploads', async () => {
  const { signIn, uploadDocument, fetchDocuments, signOut, clearAuthSession } = await import('../src/services/api.js');
  clearAuthSession();
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, status: url.endsWith('/logout') ? 204 : 200,
      json: async () => ({ user: { id: 'alice' }, csrf_token: 'session-csrf' }) };
  };
  await signIn('alice@example.test', 'dummy test password');
  await askAlexGeneral('Hello', 'chat-a');
  await uploadDocument(new Blob(['Document']), 'chat-a');
  await fetchDocuments('chat-a');
  await signOut();
  assert.ok(calls.every(c => c.options.credentials === 'include'));
  assert.equal(calls[0].options.headers['X-CSRF-Token'], undefined);
  assert.equal(calls[1].options.headers['X-CSRF-Token'], 'session-csrf');
  assert.equal(calls[2].options.headers['X-CSRF-Token'], 'session-csrf');
  assert.equal(calls[2].options.headers['Content-Type'], undefined);
  assert.equal(calls[3].options.headers['X-CSRF-Token'], undefined);
  assert.equal(calls[4].options.headers['X-CSRF-Token'], 'session-csrf');
});

test('an expired session clears CSRF and exposes 401 to the protected gate', async () => {
  const { signIn } = await import('../src/services/api.js');
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({ csrf_token: 'old-csrf' }) });
  await signIn('alice@example.test', 'dummy');
  globalThis.fetch = async () => ({ ok: false, status: 401, json: async () => ({ detail: 'Session expired' }) });
  await assert.rejects(askAlexGeneral('Hello'), e => e.status === 401);
  globalThis.fetch = async (url, options) => {
    assert.equal(options.headers['X-CSRF-Token'], undefined);
    return { ok: true, status: 200, json: async () => ({ answer: 'test' }) };
  };
  await askAlexGeneral('Hello');
});

test('late 401 from an old request cannot invalidate a new login', async () => {
  const { signIn, clearAuthSession } = await import('../src/services/api.js');
  clearAuthSession();
  let release;
  globalThis.fetch = async url => {
    if (url.endsWith('/auth/login')) return { ok: true, status: 200, json: async () => ({ csrf_token: 'new-csrf' }) };
    return new Promise(resolve => { release = resolve; });
  };
  const stale = askAlexGeneral('Old request');
  await signIn('new@example.test', 'dummy');
  release({ ok: false, status: 401, json: async () => ({ detail: 'Old session expired' }) });
  await assert.rejects(stale);
  globalThis.fetch = async (url, options) => {
    assert.equal(options.headers['X-CSRF-Token'], 'new-csrf');
    return { ok: true, status: 200, json: async () => ({ answer: 'new session' }) };
  };
  await askAlexGeneral('New request');
});

test('both chat paths send the active conversation ID and retain citations', async () => {
  const calls = [];
  const reply = { answer: 'Answer', citations: [{ document_id: 'doc-a', filename: 'paper.txt' }] };
  globalThis.fetch = async (url, options) => {
    calls.push({ url, body: JSON.parse(options.body) });
    return { ok: true, json: async () => reply };
  };
  await askAlexGeneral(' First question ', 'chat-a');
  await askAlexGeneral('Follow-up', 'chat-a');
  assert.deepEqual(await askAlex('Explain it', 'doc-a', 3, 'chat-a'), reply);
  await askAlexGeneral('New conversation', 'chat-b');
  assert.deepEqual(calls.map(c => c.body.chat_id), ['chat-a', 'chat-a', 'chat-a', 'chat-b']);
  assert.equal(calls[0].body.question, 'First question');
  assert.equal(calls[2].body.document_id, 'doc-a');
  assert.equal(calls[2].body.top_k, 3);
  assert.equal(calls[0].url, '/api/v1/chat/general');
  assert.equal(calls[2].url, '/api/v1/chat');
});

test('legacy callers explicitly remain stateless', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(JSON.parse(options.body).chat_id, null);
    return { ok: true, json: async () => ({ answer: 'Hello' }) };
  };
  await askAlexGeneral('Hello');
  await askAlex('Hello');
});

test('concurrent-write conflicts surface without automatic duplicate generation', async () => {
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    return { ok: false, json: async () => ({ detail: 'Conversation changed. Please retry your question.' }) };
  };
  await assert.rejects(askAlexGeneral('Follow-up', 'chat-a'), /Conversation changed/);
  await assert.rejects(askAlex('Follow-up', null, 5, 'chat-a'), /Conversation changed/);
  assert.equal(calls, 2);
});

test('storage and validation failures produce useful error messages', async () => {
  globalThis.fetch = async () => ({ ok: false, json: async () => ({ detail: 'Chat storage is unavailable.' }) });
  await assert.rejects(askAlexGeneral('Hello', 'chat-a'), /storage is unavailable/);
  globalThis.fetch = async () => ({ ok: false, json: async () => ({ detail: [{ msg: 'String should have at most 64 characters' }] }) });
  await assert.rejects(askAlex('Hello', null, 5, 'x'.repeat(65)), /at most 64/);
});

test('network failure does not return a fabricated assistant answer', async () => {
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch'); };
  await assert.rejects(askAlexGeneral('Hello', 'chat-a'), /backend is currently unreachable/);
});

test('conversation CRUD and pagination use credentialed, CSRF-protected requests', async () => {
  const { signIn, createConversation, listConversations, fetchConversation, fetchMessages, renameConversation, deleteConversation } = await import('../src/services/api.js');
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, status: 200, json: async () => ({ csrf_token: 'csrf', id: 'owned' }) };
  };
  await signIn('alice@example.test', 'dummy test password');
  await createConversation('Title');
  await listConversations('opaque/cursor', 2);
  await fetchConversation('owned');
  await fetchMessages('owned', { beforeTurn: 5, throughTurn: 6, limit: 2 });
  await renameConversation('owned', 'Renamed');
  await deleteConversation('owned');
  for (const call of calls) assert.equal(call.options.credentials, 'include');
  assert.deepEqual(JSON.parse(calls[1].options.body), { title: 'Title' });
  assert.match(calls[2].url, /limit=2&cursor=opaque%2Fcursor/);
  assert.match(calls[4].url, /limit=2&before_turn=5&through_turn=6/);
  for (const index of [1, 5, 6]) assert.equal(calls[index].options.headers['X-CSRF-Token'], 'csrf');
  assert.equal(calls[5].options.method, 'PATCH');
  assert.equal(calls[6].options.method, 'DELETE');
});
