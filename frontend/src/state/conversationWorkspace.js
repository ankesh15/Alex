// A client view of the API, never a second persistent message store.
export function createConversationWorkspace({ api, userId, storage = null }) {
  const storageKey = `alex.activeConversation.${userId}`;
  let epoch = 0;
  let listEpoch = 0;
  let alive = true;
  let sequence = 0;
  const listeners = new Set();
  const busy = new Set();
  const deleted = new Set();
  let state = {
    conversations: [], nextCursor: null, listLoading: false, listError: null,
    active: null, messages: [], documents: [], attachedFiles: [], scope: 'general',
    selectionVersion: 0, historyLoading: false, historyError: null, beforeTurn: null,
    throughTurn: null, olderLoading: false, isSending: false, isUploading: false,
    creating: false, mutationId: null, documentsLoading: false, documentsError: null, notice: null,
    busyIds: [], cleanupRetryId: null,
  };
  const patch = values => {
    if (!alive) return;
    state = { ...state, ...values };
    listeners.forEach(listener => listener(state));
  };
  const current = token => alive && token === epoch;
  const remember = id => {
    try { if (id) storage?.setItem(storageKey, id); else storage?.removeItem(storageKey); } catch { /* Private mode may disable storage. */ }
  };
  const reset = values => patch({ active: null, messages: [], documents: [], attachedFiles: [], scope: 'general',
    historyError: null, beforeTurn: null, throughTurn: null, olderLoading: false, documentsError: null,
    isSending: false, isUploading: false, ...values });
  const unique = items => [...new Map(items.map(item => [item.id, item])).values()];

  const controller = {
    getState: () => state,
    subscribe(listener) { listeners.add(listener); listener(state); return () => listeners.delete(listener); },
    deactivate() { alive = false; epoch += 1; listEpoch += 1; },
    async initialize() {
      alive = true;
      const token = ++epoch;
      const page = await controller.refreshList();
      if (!current(token)) return;
      let preferred = null;
      try { preferred = storage?.getItem(storageKey); } catch { /* Preferences are optional. */ }
      if (preferred) {
        const preferredEpoch = epoch + 1;
        const opened = await controller.open(preferred);
        if (opened || state.historyError || !alive || epoch !== preferredEpoch) return;
        // A deleted preference falls back to the first owned conversation.
      }
      if (page?.conversations.length && !state.active) await controller.open(page.conversations[0].id);
    },
    async refreshList() {
      const token = ++listEpoch;
      patch({ listLoading: true, listError: null });
      try {
        const page = await api.listConversations();
        if (alive && token === listEpoch) patch({ conversations: page.conversations.filter(c => !deleted.has(c.id)), nextCursor: page.next_cursor });
        return page;
      } catch (error) {
        if (alive && token === listEpoch) patch({ listError: error.message });
        return null;
      } finally { if (alive && token === listEpoch) patch({ listLoading: false }); }
    },
    async loadMore() {
      if (!state.nextCursor || state.listLoading) return;
      const token = ++listEpoch;
      const cursor = state.nextCursor;
      patch({ listLoading: true, listError: null });
      try {
        const page = await api.listConversations(cursor);
        if (alive && token === listEpoch) patch({ conversations: unique([...state.conversations, ...page.conversations]).filter(c => !deleted.has(c.id)), nextCursor: page.next_cursor });
      } catch (error) { if (alive && token === listEpoch) patch({ listError: error.message }); }
      finally { if (alive && token === listEpoch) patch({ listLoading: false }); }
    },
    async open(id) {
      if (deleted.has(id)) return false;
      const token = ++epoch;
      reset({ selectionVersion: token, active: state.conversations.find(c => c.id === id) || { id, title: 'Conversation' },
        historyLoading: true, isSending: busy.has(id), creating: false });
      try {
        const [conversation, history, docs] = await Promise.all([
          api.fetchConversation(id), api.fetchMessages(id), api.fetchDocuments(id),
        ]);
        if (!current(token)) return false;
        let scope = conversation.last_scope || 'general';
        let notice = null;
        if (scope.startsWith('document:')) {
          scope = scope.slice('document:'.length);
          if (!docs.documents.some(d => d.id === scope && d.status === 'READY')) {
            scope = 'all'; notice = 'The previous document is unavailable. Using all remaining conversation documents.';
          }
        }
        patch({ active: conversation, messages: history.messages, documents: docs.documents,
          beforeTurn: history.next_before_turn, throughTurn: history.through_turn, scope, notice });
        remember(id);
        return true;
      } catch (error) {
        if (!current(token)) return false;
        if (error.status === 404) { reset({ active: null, historyLoading: false, notice: 'That conversation is no longer available.' }); remember(null); }
        else patch({ historyError: error.message });
        return false;
      } finally { if (current(token)) patch({ historyLoading: false }); }
    },
    async create() {
      if (state.creating) return null;
      const token = ++epoch;
      reset({ selectionVersion: token, creating: true, historyLoading: true, notice: null });
      try {
        const conversation = await api.createConversation();
        if (alive) controller.refreshList();
        if (!current(token)) return null;
        return await controller.open(conversation.id) ? conversation : null;
      } catch (error) { if (current(token)) patch({ historyError: error.message }); return null; }
      finally { if (current(token)) patch({ creating: false, historyLoading: false }); }
    },
    async loadOlder() {
      if (!state.active || state.beforeTurn === null || state.olderLoading || state.historyLoading) return;
      const token = epoch;
      const id = state.active.id;
      patch({ olderLoading: true, historyError: null });
      try {
        const page = await api.fetchMessages(id, { beforeTurn: state.beforeTurn, throughTurn: state.throughTurn });
        if (current(token)) patch({ messages: unique([...page.messages, ...state.messages]), beforeTurn: page.next_before_turn });
      } catch (error) { if (current(token)) patch({ historyError: error.message }); }
      finally { if (current(token)) patch({ olderLoading: false }); }
    },
    async rename(id, title) {
      if (busy.has(id) || state.mutationId) return;
      patch({ mutationId: id });
      try {
        const conversation = await api.renameConversation(id, title);
        if (!alive) return;
        patch({ conversations: state.conversations.map(c => c.id === id ? conversation : c),
          active: state.active?.id === id ? { ...state.active, ...conversation } : state.active });
        await controller.refreshList();
      } finally { patch({ mutationId: null }); }
    },
    async delete(id) {
      if (state.mutationId) return;
      patch({ mutationId: id });
      try {
        const result = await api.deleteConversation(id);
        if (!alive) return;
        deleted.add(id);
        listEpoch += 1;
        if (state.active?.id === id) { epoch += 1; reset({ selectionVersion: epoch, historyLoading: false }); remember(null); }
        patch({ conversations: state.conversations.filter(c => c.id !== id),
          notice: result.cleanup_pending ? 'Conversation deleted. Some files still need cleanup.' : 'Conversation deleted.',
          cleanupRetryId: result.cleanup_pending ? id : null });
        await controller.refreshList();
      } finally { patch({ mutationId: null }); }
    },
    setScope(scope) { patch({ scope }); },
    removeAttachment(id) { patch({ attachedFiles: state.attachedFiles.filter(d => d.id !== id), scope: state.scope === id ? 'all' : state.scope }); },
    documentDeleted(id, token = epoch) {
      if (!current(token)) return;
      patch({ documents: state.documents.filter(d => d.id !== id), attachedFiles: state.attachedFiles.filter(d => d.id !== id),
        scope: state.scope === id ? 'all' : state.scope });
    },
    async refreshDocuments(token = epoch) {
      if (!state.active || !current(token)) return;
      const id = state.active.id;
      patch({ documentsLoading: true, documentsError: null });
      try { const page = await api.fetchDocuments(id); if (current(token)) patch({ documents: page.documents }); }
      catch (error) { if (current(token)) patch({ documentsError: error.message }); }
      finally { if (current(token)) patch({ documentsLoading: false }); }
    },
    async upload(file) {
      if (state.isUploading || state.historyLoading) return;
      if (!state.active && !await controller.create()) return;
      const token = epoch;
      const id = state.active.id;
      patch({ isUploading: true, documentsError: null });
      try {
        const document = await api.uploadDocument(file, id);
        if (current(token)) patch({ documents: unique([...state.documents, document]), attachedFiles: [...state.attachedFiles, document], scope: document.id });
        if (alive) controller.refreshList();
      } catch (error) { if (current(token)) patch({ documentsError: error.message }); }
      finally {
        if (current(token)) patch({ isUploading: false });
        else if (alive && state.active?.id === id) await controller.refreshDocuments(epoch);
      }
    },
    async send(text, overrideScope = null) {
      if (!text.trim() || state.historyLoading || state.isUploading || state.mutationId || busy.has(state.active?.id)) return;
      if (!state.active && !await controller.create()) return;
      const token = epoch;
      const id = state.active.id;
      const scope = overrideScope || state.scope;
      busy.add(id);
      patch({ messages: [...state.messages, { id: `pending-user-${++sequence}`, role: 'user', content: text, attachments: state.attachedFiles }],
        attachedFiles: [], scope, isSending: true, busyIds: [...busy], notice: null });
      try {
        const response = scope === 'general' ? await api.askAlexGeneral(text, id) : await api.askAlex(text, scope === 'all' ? null : scope, 5, id);
        if (current(token)) {
          patch({ messages: [...state.messages, { id: `pending-assistant-${++sequence}`, role: 'assistant', content: response.answer,
            citations: response.citations || [], tokenUsage: response.token_usage || null }] });
          try {
            const conversation = await api.fetchConversation(id);
            if (current(token)) patch({ active: conversation });
          } catch { if (current(token)) patch({ notice: 'The answer finished, but the conversation details could not be refreshed.' }); }
        }
      } catch (error) {
        if (current(token)) patch({ messages: [...state.messages, { id: `error-${++sequence}`, role: 'assistant', content: error.message, error: true }] });
      } finally {
        busy.delete(id);
        patch({ busyIds: [...busy] });
        if (current(token)) patch({ isSending: false });
        else if (alive && state.active?.id === id && !deleted.has(id)) await controller.open(id);
        if (alive) controller.refreshList();
      }
    },
  };
  return controller;
}
