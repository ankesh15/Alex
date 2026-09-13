const API_BASE = import.meta.env.VITE_API_URL || '';

function parseErrorMessage(errData, fallback) {
  if (!errData) return fallback;
  if (typeof errData.detail === 'string') return errData.detail;
  if (Array.isArray(errData.detail) && errData.detail.length > 0) {
    return errData.detail.map((e) => e.msg || JSON.stringify(e)).join(', ');
  }
  return errData.message || fallback;
}

export async function fetchDocuments(chatId = null) {
  try {
    const url = chatId
      ? `${API_BASE}/api/v1/documents?chat_id=${encodeURIComponent(chatId)}`
      : `${API_BASE}/api/v1/documents`;
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(parseErrorMessage(err, 'Failed to fetch documents'));
    }
    return await res.json();
  } catch (err) {
    if (err.name === 'TypeError' || err.message?.includes('fetch')) {
      throw new Error('Alex backend is currently unreachable. Please verify the server is running.');
    }
    throw err;
  }
}

export async function uploadDocument(file, chatId = null) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    if (chatId) {
      formData.append('chat_id', chatId);
    }

    const res = await fetch(`${API_BASE}/api/v1/documents/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(parseErrorMessage(err, 'Failed to upload document'));
    }
    return await res.json();
  } catch (err) {
    if (err.name === 'TypeError' || err.message?.includes('fetch')) {
      throw new Error('Alex backend is currently unreachable. Please verify the server is running.');
    }
    throw err;
  }
}

export async function deleteDocument(documentId) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/documents/${documentId}`, {
      method: 'DELETE',
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(parseErrorMessage(err, 'Failed to delete document'));
    }
    return await res.json();
  } catch (err) {
    if (err.name === 'TypeError' || err.message?.includes('fetch')) {
      throw new Error('Alex backend is currently unreachable. Please verify the server is running.');
    }
    throw err;
  }
}

export async function deleteChatDocuments(chatId) {
  if (!chatId) return { deleted_count: 0 };
  try {
    const res = await fetch(`${API_BASE}/api/v1/documents/chat/${encodeURIComponent(chatId)}`, {
      method: 'DELETE',
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(parseErrorMessage(err, 'Failed to clean up chat documents'));
    }
    return await res.json();
  } catch (err) {
    if (err.name === 'TypeError' || err.message?.includes('fetch')) {
      throw new Error('Alex backend is currently unreachable. Please verify the server is running.');
    }
    throw err;
  }
}

export async function askAlex(question, documentId = null, topK = 5, chatId = null) {
  try {
    const payload = {
      question: question.trim(),
      document_id: documentId || null,
      chat_id: chatId || null,
      top_k: topK,
    };

    const res = await fetch(`${API_BASE}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(parseErrorMessage(err, 'Failed to get answer from Alex'));
    }
    return await res.json();
  } catch (err) {
    if (err.name === 'TypeError' || err.message?.includes('fetch')) {
      throw new Error('Alex backend is currently unreachable. Please verify the server is running.');
    }
    throw err;
  }
}

export async function askAlexGeneral(question) {
  try {
    const payload = {
      question: question.trim(),
    };

    const res = await fetch(`${API_BASE}/api/v1/chat/general`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(parseErrorMessage(err, 'Failed to get answer from Alex'));
    }
    return await res.json();
  } catch (err) {
    if (err.name === 'TypeError' || err.message?.includes('fetch')) {
      throw new Error('Alex backend is currently unreachable. Please verify the server is running.');
    }
    throw err;
  }
}
