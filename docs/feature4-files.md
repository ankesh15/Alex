# Feature 4 file manifest

Compared against the saved, tested Feature 1 source snapshot, not the Git HEAD which predates Feature 1.

| File | Change |
| --- | --- |
| `.env.example` | Modified |
| `README.md` | Modified |
| `app/agents/rag_agent.py` | Modified |
| `app/api/dependencies.py` | Added |
| `app/api/main.py` | Modified |
| `app/api/schemas.py` | Modified |
| `app/api/v1/endpoints/auth.py` | Added |
| `app/api/v1/endpoints/chat.py` | Modified |
| `app/api/v1/endpoints/documents.py` | Modified |
| `app/api/v1/router.py` | Modified |
| `app/config.py` | Modified |
| `app/core/auth.py` | Added |
| `app/core/db.py` | Modified |
| `app/core/migrate.py` | Modified |
| `app/core/passwords.py` | Added |
| `app/models/__init__.py` | Modified |
| `app/models/audit_log.py` | Modified |
| `app/models/conversation.py` | Modified |
| `app/models/document.py` | Modified |
| `app/models/user.py` | Added |
| `app/services/authorization.py` | Added |
| `app/services/conversation_memory.py` | Modified |
| `app/services/rag_service.py` | Modified |
| `app/services/vector_store.py` | Modified |
| `docs/feature1-memory.md` | Modified |
| `docs/feature1-review.md` | Added |
| `docs/feature4-authentication.md` | Added |
| `docs/upgrade-plan.md` | Modified |
| `docs/verification/auth-login.jpg` | Added |
| `docs/verification/auth-memory.jpg` | Added |
| `frontend/.env.example` | Modified |
| `frontend/src/App.jsx` | Modified |
| `frontend/src/auth/AuthProvider.jsx` | Added |
| `frontend/src/auth/AuthScreen.jsx` | Added |
| `frontend/src/components/Header.jsx` | Modified |
| `frontend/src/services/api.js` | Modified |
| `frontend/tests/api.test.js` | Modified |
| `migrations/002_user_auth.sql` | Added |
| `pytest.ini` | Modified |
| `tests/conftest.py` | Added |
| `tests/test_auth.py` | Added |
| `tests/test_auth_postgres.py` | Added |
| `tests/test_chat_api.py` | Modified |
| `tests/test_chat_isolation.py` | Modified |
| `tests/test_conversation_memory.py` | Modified |
| `tests/test_documents_api.py` | Modified |
| `tests/test_memory_postgres.py` | Modified |
| `tests/test_rag_agent.py` | Modified |
| `tests/test_rag_service.py` | Modified |
| `tests/test_vector_store.py` | Modified |

Additional review artifacts: `docs/feature4-files.md` and `docs/feature4-auth-only.patch`. Binary screenshots are listed above but excluded from the source patch. The unrelated `:memory:.ses` and secret environment files are not changed or included.
