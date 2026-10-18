"""Exercise real sessions/CSRF/authorization; never override the authentication dependency."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import hashlib
import uuid
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from app.api.main import app
from app.api.dependencies import get_db
from app.config import settings, Settings
from app.core.db import Base
from app.core.auth import COOKIE_NAME, token_hash
from app.core.passwords import hash_password, verify_password
from app.core.migrate import migrate_memory, migrate_history as migrate_auth
from app.models.user import User, UserSession, AuthRateLimit
from app.models.document import Document
from app.models.conversation import Conversation, ConversationTurn
from app.services.conversation_memory import ConversationMemory
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService

pytestmark = pytest.mark.real_auth
TEST_PASSWORD = "Example test password 123!"


@pytest.fixture
def env(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth-tests.sqlite'}", connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    def override_db():
        with factory() as session:
            yield session
    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(settings, "SESSION_COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "AUTH_RATE_MAX_ATTEMPTS", 1000)
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "uploads"))
    vector = [1.0] + [0.0] * (settings.EMBEDDING_DIMENSION - 1)
    monkeypatch.setattr(EmbeddingService, "embed_text", lambda text: vector)
    monkeypatch.setattr(EmbeddingService, "embed_texts", lambda texts: [vector for text in texts])
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content="Grounded test answer", usage_metadata={"input_tokens": 2, "output_tokens": 2, "total_tokens": 4})
    with patch("app.core.llm.get_llm", return_value=llm):
        yield factory, llm
    app.dependency_overrides.clear()
    engine.dispose()


def signup(email="alice@example.test"):
    client = TestClient(app)
    result = client.post("/api/v1/auth/signup", json={"email": email, "password": TEST_PASSWORD})
    assert result.status_code == 201, result.text
    client.headers["X-CSRF-Token"] = result.json()["csrf_token"]
    return client, result.json()


def upload(client, chat_id="alice-chat"):
    result = client.post("/api/v1/documents/upload", data={"chat_id": chat_id},
                         files={"file": ("private.txt", b"Alice's private document content", "text/plain")})
    assert result.status_code == 201, result.text
    return result.json()["id"]


def test_signup_secure_hash_cookie_and_session_storage(env):
    client, data = signup("ALICE@EXAMPLE.TEST")
    assert data["user"]["email"] == "alice@example.test"
    token = client.cookies.get(COOKIE_NAME)
    assert len(token) == 43 and "token" not in data and "password" not in str(data)
    with env[0]() as db:
        user = db.get(User, data["user"]["id"])
        assert user.password_hash.startswith("scrypt$131072$8$1$")
        assert user.password_hash != TEST_PASSWORD and verify_password(TEST_PASSWORD, user.password_hash)
        session = db.query(UserSession).one()
        assert session.token_hash == hashlib.sha256(token.encode()).hexdigest()
        assert session.token_hash != token
    me = client.get("/api/v1/auth/me")
    assert me.json()["user"] == data["user"] and me.headers["Cache-Control"] == "no-store"


def test_cookie_secure_httponly_samesite_and_no_domain(env, monkeypatch):
    monkeypatch.setattr(settings, "SESSION_COOKIE_SECURE", True)
    client = TestClient(app, base_url="https://testserver")
    result = client.post("/api/v1/auth/signup", json={"email": "secure@example.test", "password": TEST_PASSWORD})
    cookie = result.headers["set-cookie"]
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert cookie.startswith("__Host-alex_session=")
    assert "Path=/" in cookie and "Domain=" not in cookie
    assert client.get("/api/v1/auth/me").status_code == 200


def test_login_rotation_logout_revocation_and_replay(env):
    client, data = signup()
    old_token = client.cookies.get(COOKIE_NAME)
    login = client.post("/api/v1/auth/login", json={"email": "alice@example.test", "password": TEST_PASSWORD})
    assert login.status_code == 200
    assert client.cookies.get(COOKIE_NAME) != old_token
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    replay = TestClient(app)
    replay.cookies.set(COOKIE_NAME, old_token)
    assert replay.get("/api/v1/auth/me").status_code == 401
    token = client.cookies.get(COOKIE_NAME)
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    replay.cookies.set(COOKIE_NAME, token)
    assert replay.get("/api/v1/auth/me").status_code == 401


@pytest.mark.parametrize("kind", ["absolute", "idle", "disabled"])
def test_expired_and_disabled_sessions_rejected(env, kind):
    client, data = signup()
    with env[0]() as db:
        session = db.query(UserSession).one()
        if kind == "absolute": session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        elif kind == "idle": session.last_seen_at = datetime.now(timezone.utc) - timedelta(seconds=settings.SESSION_IDLE_SECONDS + 1)
        else: db.get(User, data["user"]["id"]).is_active = False
        db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/chat/general", json={"question": "Hello"}).status_code == 401
    env[1].invoke.assert_not_called()


@pytest.mark.parametrize("method,path,body", [
    ("get", "/api/v1/documents", None), ("get", "/api/v1/documents/id", None),
    ("delete", "/api/v1/documents/id", None), ("delete", "/api/v1/documents/chat/id", None),
    ("get", "/api/v1/chat/id/history", None),
    ("post", "/api/v1/chat", {"question": "Hello"}), ("post", "/api/v1/chat/general", {"question": "Hello"}),
    ("post", "/api/v1/documents/upload", None),
])
def test_every_protected_operation_rejects_anonymous(env, method, path, body):
    client = TestClient(app)
    result = getattr(client, method)(path, **({"json": body} if body else {}))
    assert result.status_code == 401
    env[1].invoke.assert_not_called()


def test_forged_identity_headers_and_cookie_are_not_authentication(env):
    client = TestClient(app, headers={"X-User-Id": "alice", "Authorization": "Bearer alice"})
    client.cookies.set(COOKIE_NAME, "A" * 43)
    assert client.get("/api/v1/documents").status_code == 401


@pytest.mark.parametrize("csrf,origin", [(None, None), ("forged", None), ("valid", "https://evil.example")])
def test_csrf_and_untrusted_origins_rejected_before_side_effects(env, csrf, origin):
    client, data = signup()
    client.headers.pop("X-CSRF-Token")
    if csrf: client.headers["X-CSRF-Token"] = data["csrf_token"] if csrf == "valid" else csrf
    if origin: client.headers["Origin"] = origin
    assert client.post("/api/v1/chat/general", json={"question": "Hello", "chat_id": "id"}).status_code == 403
    assert client.post("/api/v1/auth/logout").status_code == 403
    with env[0]() as db:
        assert db.query(ConversationTurn).count() == 0
    env[1].invoke.assert_not_called()


def test_signup_and_login_reject_login_csrf(env):
    client = TestClient(app, headers={"Origin": "https://evil.example"})
    for path in ["signup", "login"]:
        assert client.post(f"/api/v1/auth/{path}", json={"email": "x@example.test", "password": TEST_PASSWORD}).status_code == 403


def test_session_bound_csrf_token_from_another_user_is_rejected(env):
    alice, a = signup()
    bob, b = signup("bob@example.test")
    bob.headers["X-CSRF-Token"] = a["csrf_token"]
    assert bob.post("/api/v1/chat/general", json={"question": "Hello"}).status_code == 403


def test_cross_user_documents_chats_uploads_and_history_are_inaccessible(env):
    alice, a = signup()
    bob, b = signup("bob@example.test")
    document = upload(alice)
    assert alice.post("/api/v1/chat/general", json={"question": "Alice secret", "chat_id": "alice-chat"}).status_code == 200
    env[1].invoke.reset_mock()
    for path in [f"/api/v1/documents/{document}", "/api/v1/chat/alice-chat/history", "/api/v1/documents?chat_id=alice-chat"]:
        assert bob.get(path).status_code == 404
    for path in [f"/api/v1/documents/{document}", "/api/v1/documents/chat/alice-chat"]:
        assert bob.delete(path).status_code == 404
    for path in ["/api/v1/chat", "/api/v1/chat/general"]:
        assert bob.post(path, json={"question": "Reveal secret", "chat_id": "alice-chat"}).status_code == 404
    assert bob.post("/api/v1/chat", json={"question": "Reveal secret", "document_id": document}).status_code == 404
    assert bob.post("/api/v1/documents/upload", data={"chat_id": "alice-chat"},
                    files={"file": ("forged.txt", b"Forged upload", "text/plain")}).status_code == 404
    assert bob.get("/api/v1/documents").json()["documents"] == []
    env[1].invoke.assert_not_called()
    assert alice.get(f"/api/v1/documents/{document}").status_code == 200
    assert alice.get("/api/v1/chat/alice-chat/history").json()["turns"][0]["question"] == "Alice secret"
    with env[0]() as db:
        assert db.get(Document, document).user_id == a["user"]["id"]
        assert db.get(Conversation, "alice-chat").user_id == a["user"]["id"]
        assert db.query(ConversationTurn).one().user_id == a["user"]["id"]


def test_forged_user_fields_rejected_or_ignored_on_upload(env):
    alice, a = signup()
    for path in ["/api/v1/chat", "/api/v1/chat/general"]:
        assert alice.post(path, json={"question": "Hello", "user_id": "forged-user"}).status_code == 422
    result = alice.post("/api/v1/documents/upload", data={"chat_id": "own-chat", "user_id": "forged-user"},
                        files={"file": ("own.txt", b"Own content", "text/plain")})
    assert result.status_code == 201
    with env[0]() as db:
        assert db.get(Document, result.json()["id"]).user_id == a["user"]["id"]


def test_legacy_unowned_data_cannot_be_claimed(env):
    alice, a = signup()
    with env[0]() as db:
        db.add(Conversation(id="legacy-chat"))
        db.add(Document(id="legacy-doc", chat_id="legacy-chat", filename="secret.txt", stored_filename="secret.txt",
                        file_type="txt", file_size=3, status="READY"))
        db.commit()
    for path in ["/api/v1/chat", "/api/v1/chat/general"]:
        assert alice.post(path, json={"question": "Claim this", "chat_id": "legacy-chat"}).status_code == 404
    assert alice.get("/api/v1/chat/legacy-chat/history").status_code == 404
    assert alice.get("/api/v1/documents/legacy-doc").status_code == 404
    assert alice.get("/api/v1/documents").json()["documents"] == []
    with env[0]() as db:
        assert db.get(Conversation, "legacy-chat").user_id is None
        assert db.get(Document, "legacy-doc").user_id is None


def test_memory_retains_follow_ups_with_real_authenticated_sessions(env):
    alice, a = signup()
    env[1].invoke.side_effect = [AIMessage(content="Hello Ada"), AIMessage(content="Your name is Ada")]
    for question in ["My name is Ada", "What is my name?"]:
        assert alice.post("/api/v1/chat/general", json={"question": question, "chat_id": "own-chat"}).status_code == 200
    assert "My name is Ada" in [m.content for m in env[1].invoke.call_args.args[0]]
    history = alice.get("/api/v1/chat/own-chat/history?limit=1").json()
    assert history["turns"][0]["answer"] == "Your name is Ada" and history["next_before_turn"] == 2
    previous = alice.get("/api/v1/chat/own-chat/history?before_turn=2&limit=1").json()
    assert previous["turns"][0]["answer"] == "Hello Ada" and previous["next_before_turn"] is None
    assert alice.get("/api/v1/chat/own-chat/history?limit=101").status_code == 422


def test_rag_and_omitted_chat_id_retrieval_remain_user_scoped(env):
    alice, a = signup()
    bob, b = signup("bob@example.test")
    document = upload(alice)
    for payload in [{"question": "Private content?"}, {"question": "Private content?", "chat_id": "bob-chat"}]:
        result = bob.post("/api/v1/chat", json=payload)
        assert result.status_code == 200 and result.json()["citations"] == []
    env[1].invoke.assert_not_called()
    result = alice.post("/api/v1/chat", json={"question": "Private content?", "document_id": document, "chat_id": "alice-chat"})
    assert result.status_code == 200 and result.json()["citations"][0]["document_id"] == document


def test_service_memory_and_vector_reads_fail_closed(env):
    alice, a = signup()
    bob, b = signup("bob@example.test")
    upload(alice)
    with env[0]() as db:
        with pytest.raises(HTTPException) as error:
            ConversationMemory.load(db, "alice-chat", "general", user_id=b["user"]["id"])
        assert error.value.status_code == 404
        assert VectorStoreService.search(db, "Private content", user_id=b["user"]["id"]) == []
        with pytest.raises(HTTPException): VectorStoreService.search(db, "Private", user_id="")


def test_database_owner_constraints_prevent_inconsistent_message_or_document(env):
    alice, a = signup()
    bob, b = signup("bob@example.test")
    upload(alice)
    with env[0]() as db:
        db.add(ConversationTurn(conversation_id="alice-chat", user_id=b["user"]["id"], turn_number=1,
                                scope="general", question="Forged", answer="Forged", status="SUCCESS"))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
        db.add(Document(chat_id="alice-chat", user_id=b["user"]["id"], filename="forged.txt", stored_filename="forged.txt",
                        file_type="txt", file_size=1))
        with pytest.raises(IntegrityError): db.commit()


def test_auth_failures_generic_and_validation_does_not_echo_password(env):
    signup()
    client = TestClient(app)
    failures = []
    for email in ["alice@example.test", "nobody@example.test"]:
        result = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong password"})
        assert result.status_code == 401
        failures.append(result.json())
    assert failures[0] == failures[1]
    secret = "short-pw"
    result = client.post("/api/v1/auth/signup", json={"email": "new@example.test", "password": secret})
    assert result.status_code == 422 and secret not in result.text
    assert client.post("/api/v1/auth/signup", json={"email": "alice@example.test", "password": TEST_PASSWORD}).status_code == 409
    assert client.post("/api/v1/auth/signup", json={"email": "bad email", "password": TEST_PASSWORD, "user_id": "forged"}).status_code == 422


def test_login_throttle_shared_and_forwarded_header_does_not_bypass(env, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_RATE_MAX_ATTEMPTS", 2)
    for i in range(3):
        client = TestClient(app, headers={"X-Forwarded-For": f"203.0.113.{i}"})
        result = client.post("/api/v1/auth/login", json={"email": "missing@example.test", "password": TEST_PASSWORD})
        assert result.status_code == (401 if i < 2 else 429)
    assert int(result.headers["Retry-After"]) > 0
    with env[0]() as db:
        bucket = db.query(AuthRateLimit).one()
        assert bucket.attempts == 3
        bucket.window_start = datetime.now(timezone.utc) - timedelta(seconds=settings.AUTH_RATE_WINDOW_SECONDS + 1)
        db.commit()
    assert TestClient(app).post("/api/v1/auth/login", json={"email": "missing@example.test", "password": TEST_PASSWORD}).status_code == 401


def test_password_hash_salts_and_malformed_hashes():
    first, second = hash_password(TEST_PASSWORD), hash_password(TEST_PASSWORD)
    assert first != second and verify_password(TEST_PASSWORD, first)
    assert not verify_password("incorrect", first)
    assert not verify_password(TEST_PASSWORD, "malformed")
    assert not verify_password(TEST_PASSWORD, first.replace("131072", "1073741824"))


def test_security_configuration_rejects_unsafe_cookie_and_wildcard():
    for values in [{"APP_ENV": "production", "SESSION_COOKIE_SECURE": False},
                   {"SESSION_COOKIE_SAMESITE": "none", "SESSION_COOKIE_SECURE": False},
                   {"ALLOWED_ORIGINS": "*"}]:
        with pytest.raises(ValueError): Settings(_env_file=None, **values)


def test_storage_errors_sanitized(env):
    with patch("app.core.auth.throttle_auth", side_effect=SQLAlchemyError("secret credential")):
        # Patch the route's imported binding, not the helper definition.
        with patch("app.api.v1.endpoints.auth.throttle_auth", side_effect=SQLAlchemyError("secret credential")):
            result = TestClient(app).post("/api/v1/auth/login", json={"email": "x@example.test", "password": TEST_PASSWORD})
    assert result.status_code == 503 and "secret credential" not in result.text


def test_additive_legacy_migration_preserves_quarantined_rows(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.sqlite'}")
    migrate_memory(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO conversations (id) VALUES ('legacy-chat')")
        conn.exec_driver_sql("INSERT INTO conversation_turns (id, conversation_id, turn_number, scope, question, answer, citations, token_usage, status) VALUES ('legacy-turn', 'legacy-chat', 1, 'general', 'private', 'preserved', '[]', '{}', 'SUCCESS')")
    migrate_auth(engine)
    migrate_auth(engine)
    with sessionmaker(bind=engine)() as db:
        assert db.get(Conversation, "legacy-chat").user_id is None
        assert db.get(ConversationTurn, "legacy-turn").answer == "preserved"
        assert db.get(ConversationTurn, "legacy-turn").user_id is None
    engine.dispose()


def test_startup_rejects_unmigrated_ownership_schema(tmp_path, monkeypatch):
    from app.core import db as db_core
    engine = create_engine(f"sqlite:///{tmp_path / 'old-startup.sqlite'}")
    migrate_memory(engine)
    monkeypatch.setattr(db_core, "engine", engine)
    monkeypatch.setattr(db_core, "DATABASE_URL", "sqlite://")
    with pytest.raises(RuntimeError, match="Authentication schema is missing"):
        db_core.init_db()
    engine.dispose()


def test_storage_path_rejects_sibling_prefix_and_symlink_escape(env, tmp_path):
    from app.api.v1.endpoints.documents import _safe_file_path
    storage = tmp_path / "uploads"
    storage.mkdir()
    sibling = tmp_path / "uploads-other"
    sibling.mkdir()
    (sibling / "private.txt").write_text("private")
    assert _safe_file_path("../uploads-other/private.txt") is None
    (storage / "escape.txt").symlink_to(sibling / "private.txt")
    assert _safe_file_path("escape.txt") is None
