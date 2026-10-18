import { useEffect, useMemo, useState } from 'react';
import * as api from '../services/api';
import { createConversationWorkspace } from './conversationWorkspace';

export function useConversationWorkspace(userId) {
  const controller = useMemo(() => {
    let storage = null;
    try { storage = window.localStorage; } catch { /* Preferences are optional. */ }
    return createConversationWorkspace({ api, userId, storage });
  }, [userId]);
  const [state, setState] = useState(controller.getState);
  useEffect(() => {
    const unsubscribe = controller.subscribe(setState);
    controller.initialize();
    return () => { unsubscribe(); controller.deactivate(); };
  }, [controller]);
  return [state, controller];
}
