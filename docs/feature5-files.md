# Feature 5 changed files

Compared with the local Feature 4 working-tree snapshot taken before this increment.
Previous Feature 1/authentication changes remain intact and uncommitted.

| File | Change |
| --- | --- |
| [.env.example](../.env.example) | Modified |
| [README.md](../README.md) | Modified |
| [app/api/schemas.py](../app/api/schemas.py) | Modified |
| [app/api/v1/endpoints/chat.py](../app/api/v1/endpoints/chat.py) | Modified |
| [app/api/v1/endpoints/conversations.py](../app/api/v1/endpoints/conversations.py) | Added |
| [app/api/v1/endpoints/documents.py](../app/api/v1/endpoints/documents.py) | Modified |
| [app/api/v1/router.py](../app/api/v1/router.py) | Modified |
| [app/core/db.py](../app/core/db.py) | Modified |
| [app/core/migrate.py](../app/core/migrate.py) | Modified |
| [app/models/audit_log.py](../app/models/audit_log.py) | Modified |
| [app/models/conversation.py](../app/models/conversation.py) | Modified |
| [app/services/authorization.py](../app/services/authorization.py) | Modified |
| [app/services/conversation_memory.py](../app/services/conversation_memory.py) | Modified |
| [app/services/conversation_service.py](../app/services/conversation_service.py) | Added |
| [app/services/rag_service.py](../app/services/rag_service.py) | Modified |
| [app/services/vector_store.py](../app/services/vector_store.py) | Modified |
| [docs/feature1-memory.md](../docs/feature1-memory.md) | Modified |
| [docs/feature4-authentication.md](../docs/feature4-authentication.md) | Modified |
| [docs/feature5-history.md](../docs/feature5-history.md) | Added |
| [docs/upgrade-plan.md](../docs/upgrade-plan.md) | Modified |
| [docs/verification/feature5-backend.txt](../docs/verification/feature5-backend.txt) | Added |
| [docs/verification/feature5-desktop.jpg](../docs/verification/feature5-desktop.jpg) | Added |
| [docs/verification/feature5-mobile.jpg](../docs/verification/feature5-mobile.jpg) | Added |
| [docs/verification/feature5-style-lint.txt](../docs/verification/feature5-style-lint.txt) | Added |
| [frontend/.env.example](../frontend/.env.example) | Modified |
| [frontend/src/App.jsx](../frontend/src/App.jsx) | Modified |
| [frontend/src/components/Chat.jsx](../frontend/src/components/Chat.jsx) | Modified |
| [frontend/src/components/ChatInput.jsx](../frontend/src/components/ChatInput.jsx) | Modified |
| [frontend/src/components/ConversationSidebar.jsx](../frontend/src/components/ConversationSidebar.jsx) | Added |
| [frontend/src/components/DocumentsView.jsx](../frontend/src/components/DocumentsView.jsx) | Modified |
| [frontend/src/components/Header.jsx](../frontend/src/components/Header.jsx) | Modified |
| [frontend/src/services/api.js](../frontend/src/services/api.js) | Modified |
| [frontend/src/state/conversationWorkspace.js](../frontend/src/state/conversationWorkspace.js) | Added |
| [frontend/src/state/useConversationWorkspace.js](../frontend/src/state/useConversationWorkspace.js) | Added |
| [frontend/tests/api.test.js](../frontend/tests/api.test.js) | Modified |
| [frontend/tests/conversationWorkspace.test.js](../frontend/tests/conversationWorkspace.test.js) | Added |
| [migrations/003_persistent_history.sql](../migrations/003_persistent_history.sql) | Added |
| [tests/test_auth.py](../tests/test_auth.py) | Modified |
| [tests/test_auth_postgres.py](../tests/test_auth_postgres.py) | Modified |
| [tests/test_chat_isolation.py](../tests/test_chat_isolation.py) | Modified |
| [tests/test_conversation_memory.py](../tests/test_conversation_memory.py) | Modified |
| [tests/test_conversations.py](../tests/test_conversations.py) | Added |
| [tests/test_history_postgres.py](../tests/test_history_postgres.py) | Added |
| [tests/test_memory_postgres.py](../tests/test_memory_postgres.py) | Modified |
| [docs/feature5-files.md](feature5-files.md) | Added: this manifest |
| [docs/feature5-history-only.patch](feature5-history-only.patch) | Added: source-only review patch |

The patch includes source, tests, migrations and documentation. Binary screenshots and
verification logs are linked in the report and excluded from the source patch. Secrets,
dependencies, generated builds and the unrelated existing `:memory:.ses` file are excluded.
No commit, staging, push, deployment or application database migration was performed.
