const RAW_API_BASE = import.meta.env?.VITE_API_URL || '';
const API_BASE = RAW_API_BASE.replace(/\/+$/, '');
let csrfToken = null;
let sessionGeneration = 0;
function parseErrorMessage(data, fallback) {
  if (typeof data?.detail === 'string') return data.detail;
  if (Array.isArray(data?.detail)) return data.detail.map(e => e.msg).join(', ');
  return data?.message || fallback;
}
export function clearAuthSession() { csrfToken = null; sessionGeneration += 1; }
async function request(path, { method = 'GET', body, protectedRequest = true } = {}) {
  const generation = sessionGeneration;
  const headers = {};
  if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';
  if (protectedRequest && method !== 'GET' && csrfToken) headers['X-CSRF-Token'] = csrfToken;
  try {
    const res = await fetch(`${API_BASE}/api/v1${path}`, {
      method, credentials: 'include', headers,
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      if (res.status === 401 && protectedRequest && generation === sessionGeneration) {
        clearAuthSession();
        if (typeof window !== 'undefined') window.dispatchEvent(new Event('alex:unauthorized'));
      }
      const error = new Error(parseErrorMessage(data, `Request failed (${res.status})`));
      error.status = res.status;
      throw error;
    }
    return res.status === 204 ? null : await res.json();
  } catch (err) {
    if (err.name === 'TypeError') throw new Error('Alex backend is currently unreachable. Please verify the server is running.');
    throw err;
  }
}
function rememberSession(data) { csrfToken = data.csrf_token; sessionGeneration += 1; return data; }
export async function fetchCurrentUser() { return rememberSession(await request('/auth/me')); }
export async function signIn(email, password) {
  return rememberSession(await request('/auth/login', { method: 'POST', body: { email, password }, protectedRequest: false }));
}
export async function signUp(email, password) {
  return rememberSession(await request('/auth/signup', { method: 'POST', body: { email, password }, protectedRequest: false }));
}
export async function signOut() { await request('/auth/logout', { method: 'POST' }); clearAuthSession(); }
export function fetchDocuments(chatId = null) { return request(`/documents${chatId ? `?chat_id=${encodeURIComponent(chatId)}` : ''}`); }
export function uploadDocument(file, chatId = null) {
  const body = new FormData(); body.append('file', file);
  if (chatId) body.append('chat_id', chatId);
  return request('/documents/upload', { method: 'POST', body });
}
export function deleteDocument(id) { return request(`/documents/${encodeURIComponent(id)}`, { method: 'DELETE' }); }
export function deleteChatDocuments(id) {
  if (!id) return Promise.resolve({ deleted_count: 0 });
  return request(`/documents/chat/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
export function askAlex(question, documentId = null, topK = 5, chatId = null) {
  return request('/chat', { method: 'POST', body: { question: question.trim(), document_id: documentId || null, chat_id: chatId || null, top_k: topK } });
}
export function askAlexGeneral(question, chatId = null) {
  return request('/chat/general', { method: 'POST', body: { question: question.trim(), chat_id: chatId || null } });
}

export function createConversation(title = null) {
  return request('/conversations', { method: 'POST', body: title === null ? {} : { title } });
}
export function listConversations(cursor = null, limit = 25) {
  const query = new URLSearchParams({ limit: String(limit) });
  if (cursor) query.set('cursor', cursor);
  return request(`/conversations?${query}`);
}
export function fetchConversation(id) {
  return request(`/conversations/${encodeURIComponent(id)}`);
}
export function fetchMessages(id, { beforeTurn = null, throughTurn = null, limit = 25 } = {}) {
  const query = new URLSearchParams({ limit: String(limit) });
  if (beforeTurn !== null) query.set('before_turn', String(beforeTurn));
  if (throughTurn !== null) query.set('through_turn', String(throughTurn));
  return request(`/conversations/${encodeURIComponent(id)}/messages?${query}`);
}
export function renameConversation(id, title) {
  return request(`/conversations/${encodeURIComponent(id)}`, { method: 'PATCH', body: { title } });
}
export function deleteConversation(id) {
  return request(`/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
