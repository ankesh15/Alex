from app.models.user import User
from unittest.mock import MagicMock, patch
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import SQLAlchemyError

from app.api.main import app
from app.api.v1.endpoints.chat import get_db
from app.config import settings
from app.core.db import Base
from app.core.migrate import migrate_history as migrate_memory
from app.models.conversation import Conversation, ConversationTurn
from app.services.conversation_memory import ConversationMemory, ConversationConflict
from app.services.rag_service import RAGService, INSUFFICIENT_CONTEXT_MESSAGE


@pytest.fixture
def database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(User.__table__.insert().values(id="test-user", email="pipeline@example.test", password_hash="unused-test-hash"))
    factory = sessionmaker(bind=engine)
    yield engine, factory
    engine.dispose()


@pytest.fixture
def db(database):
    with database[1]() as session:
        yield session


@pytest.fixture
def client(database):
    def override_db():
        with database[1]() as session:
            yield session
    app.dependency_overrides[get_db] = override_db
    # Do not invoke production startup against a developer's database.
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


def store(db, chat_id="chat-a", scope="general", question="My name is Ada", answer="Hello Ada",
          status="SUCCESS"):
    snapshot = ConversationMemory.load(db, chat_id, scope, user_id="test-user")
    ConversationMemory.save(db, snapshot, question, answer, [], {"total_tokens": 4}, status)


def response(text, tokens=4):
    return AIMessage(content=text, usage_metadata={"input_tokens": 2, "output_tokens": tokens - 2,
                                                "total_tokens": tokens})


def test_persists_across_sessions_and_conversations_are_isolated(database):
    with database[1]() as first:
        store(first)
    with database[1]() as reopened:
        assert [m.content for m in ConversationMemory.load(reopened, "chat-a", "general", user_id="test-user").messages] == [
            "My name is Ada", "Hello Ada"]
        assert ConversationMemory.load(reopened, "chat-b", "general", user_id="test-user").messages == []


@pytest.mark.parametrize("scope", ["all", "document:doc-a", "document:doc-b"])
def test_scope_changes_do_not_import_general_memory(db, scope):
    store(db)
    assert ConversationMemory.load(db, "chat-a", scope, user_id="test-user").messages == []


def test_specific_documents_do_not_share_memory(db):
    store(db, scope="document:doc-a")
    assert ConversationMemory.load(db, "chat-a", "document:doc-b", user_id="test-user").messages == []
    assert ConversationMemory.load(db, "chat-a", "all", user_id="test-user").messages == []


def test_history_is_recent_chronological_and_bounded(db):
    with patch.object(settings, "MEMORY_MAX_TURNS", 2), patch.object(settings, "MEMORY_MAX_CHARS", 256):
        for i in range(5):
            store(db, question=f"Question {i}", answer=f"Answer {i}")
        history = ConversationMemory.load(db, "chat-a", "general", user_id="test-user").messages
        assert [m.content for m in history] == ["Question 3", "Answer 3", "Question 4", "Answer 4"]
        assert len(db.query(ConversationTurn).all()) == 5


def test_oversized_latest_pair_truncated_without_altering_storage(db):
    store(db, question="q" * 300, answer="a" * 500)
    with patch.object(settings, "MEMORY_MAX_CHARS", 256):
        history = ConversationMemory.load(db, "chat-a", "general", user_id="test-user").messages
    assert len(history) == 2
    assert isinstance(history[0], HumanMessage) and isinstance(history[1], AIMessage)
    assert sum(len(m.content) for m in history) == 256
    assert len(db.query(ConversationTurn).one().answer) == 500


def test_char_budget_keeps_complete_recent_pairs(db):
    for i in range(3):
        store(db, question=f"{i}" + "q" * 79, answer="a" * 80)
    with patch.object(settings, "MEMORY_MAX_CHARS", 256):
        history = ConversationMemory.load(db, "chat-a", "general", user_id="test-user").messages
    assert len(history) == 2
    assert history[0].content.startswith("2")


@pytest.mark.parametrize("status,answer", [("ERROR", "Provider failure"), ("SUCCESS", "   ")])
def test_failures_and_empty_generations_do_not_enter_memory(db, status, answer):
    store(db, status=status, answer=answer)
    assert db.query(ConversationTurn).count() == 0
    assert db.get(Conversation, "chat-a").revision == 0


def test_no_context_is_stored_but_not_used_as_model_history(db):
    store(db, scope="all", status="NO_CONTEXT", answer=INSUFFICIENT_CONTEXT_MESSAGE)
    assert db.query(ConversationTurn).count() == 1
    assert ConversationMemory.load(db, "chat-a", "all", user_id="test-user").messages == []


def test_stale_concurrent_snapshot_rejected_atomically(database):
    with database[1]() as first, database[1]() as second:
        snapshot_a = ConversationMemory.load(first, "chat-race", "general", user_id="test-user")
        snapshot_b = ConversationMemory.load(second, "chat-race", "general", user_id="test-user")
        ConversationMemory.save(first, snapshot_a, "first", "answer", [], {}, "SUCCESS")
        with pytest.raises(ConversationConflict):
            ConversationMemory.save(second, snapshot_b, "stale", "answer", [], {}, "SUCCESS")
        assert second.query(ConversationTurn).count() == 1
        assert second.get(Conversation, "chat-race").revision == 1


def test_insert_failure_rolls_back_revision_and_turn(db):
    snapshot = ConversationMemory.load(db, "chat-atomic", "general", user_id="test-user")
    with patch.object(db, "add", side_effect=SQLAlchemyError("write failed")):
        with pytest.raises(SQLAlchemyError):
            ConversationMemory.save(db, snapshot, "question", "answer", [], {}, "SUCCESS")
    assert db.get(Conversation, "chat-atomic").revision == 0
    assert db.query(ConversationTurn).count() == 0


def test_general_follow_up_receives_history_with_correct_roles(client, db):
    llm = MagicMock()
    llm.invoke.side_effect = [response("Hello Ada"), response("Your name is Ada"), response("Who are you?")]
    with patch("app.core.llm.get_llm", return_value=llm):
        for question in ["My name is Ada", "What is my name?"]:
            assert client.post("/api/v1/chat/general", json={"question": question, "chat_id": "chat-a"}).status_code == 200
        assert client.post("/api/v1/chat/general", json={"question": "What is my name?", "chat_id": "chat-b"}).status_code == 200
    second_prompt = llm.invoke.call_args_list[1].args[0]
    assert [type(m) for m in second_prompt] == [SystemMessage, HumanMessage, AIMessage, HumanMessage]
    assert [m.content for m in second_prompt[1:]] == ["My name is Ada", "Hello Ada", "What is my name?"]
    assert len(llm.invoke.call_args_list[2].args[0]) == 2
    assert db.query(ConversationTurn).count() == 3


def test_legacy_general_chat_does_not_query_database(client):
    llm = MagicMock()
    llm.invoke.return_value = response("Hello")
    with patch("app.core.llm.get_llm", return_value=llm), patch.object(ConversationMemory, "load") as load:
        assert client.post("/api/v1/chat/general", json={"question": "Hello"}).status_code == 200
    load.assert_not_called()


def test_provider_initialization_failure_is_handled_and_not_remembered(client, db):
    with patch("app.core.llm.get_llm", side_effect=ValueError("API_KEY_INVALID private detail")):
        result = client.post("/api/v1/chat/general", json={"question": "Hello", "chat_id": "chat-a"})
    assert result.status_code == 200  # Preserve existing error-response contract.
    assert "private detail" not in result.json()["answer"]
    assert "couldn't generate" in result.json()["answer"]
    assert db.query(ConversationTurn).count() == 0


def test_storage_failure_returns_safe_retryable_error(client):
    with patch.object(ConversationMemory, "load", side_effect=SQLAlchemyError("private database URL")):
        for url in ["/api/v1/chat", "/api/v1/chat/general"]:
            result = client.post(url, json={"question": "Hello", "chat_id": "chat-a"})
            assert result.status_code == 503
            assert "private" not in result.json()["detail"]


def test_api_concurrency_conflict_is_retryable(client):
    with patch.object(ConversationMemory, "load", side_effect=ConversationConflict("Please retry")):
        for url in ["/api/v1/chat", "/api/v1/chat/general"]:
            assert client.post(url, json={"question": "Hello", "chat_id": "chat-a"}).status_code == 409


@pytest.mark.parametrize("payload", [
    {"chat_id": ""}, {"chat_id": "x" * 65}, {"chat_id": "../chat"}, {"question": "x" * 12001},
])
def test_memory_request_validation(client, payload):
    for url in ["/api/v1/chat", "/api/v1/chat/general"]:
        assert client.post(url, json={"question": "hello", **payload}).status_code == 422


def test_rag_follow_up_rewrites_retrieval_preserves_grounding_and_citations(db):
    chunks = [{"chunk_id": "chunk-a", "document_id": "doc-a", "filename": "raft.txt",
               "page_number": 2, "content": "Raft uses leader election.", "similarity_score": 0.9}]
    store(db, scope="document:doc-a", question="What is Raft?", answer="Raft is a consensus algorithm.")
    llm = MagicMock()
    llm.invoke.side_effect = [response("How does Raft elect its leader?", 5), response("Raft elects a leader [raft.txt, p2].", 9)]
    with patch.object(RAGService, "retrieve_context", return_value=chunks) as retrieve:
        result = RAGService.run_rag(db, "How does it elect a leader?", "doc-a", "chat-a", llm=llm, user_id="test-user")
    assert retrieve.call_args.kwargs["question"] == "How does Raft elect its leader?"
    assert retrieve.call_args.kwargs["chat_id"] == "chat-a"
    assert retrieve.call_args.kwargs["document_id"] == "doc-a"
    generation = llm.invoke.call_args_list[1].args[0]
    assert "not instructions or document evidence" in generation[0].content
    assert "Raft uses leader election" in generation[-1].content
    assert result["token_usage"]["total_tokens"] == 14
    turn = db.query(ConversationTurn).filter_by(turn_number=2).one()
    assert turn.citations == result["citations"]
    assert turn.question == "How does it elect a leader?"


def test_rag_history_cannot_replace_missing_retrieved_context(db):
    store(db, scope="all", answer="Old document says a private fact")
    llm = MagicMock()
    llm.invoke.return_value = response("Tell me more about the old document")
    with patch.object(RAGService, "retrieve_context", return_value=[]):
        result = RAGService.run_rag(db, "Tell me more", chat_id="chat-a", llm=llm, user_id="test-user")
    assert result["answer"] == INSUFFICIENT_CONTEXT_MESSAGE
    assert result["citations"] == []
    assert llm.invoke.call_count == 1  # Rewrite only, never synthesize without sources.
    assert db.query(ConversationTurn).filter_by(turn_number=2).one().status == "NO_CONTEXT"


def test_rewrite_failure_falls_back_to_original_question(db):
    store(db, scope="all")
    llm = MagicMock()
    llm.invoke.side_effect = TimeoutError("timeout")
    with patch.object(RAGService, "retrieve_context", return_value=[]) as retrieve:
        RAGService.run_rag(db, "Tell me more", chat_id="chat-a", llm=llm, user_id="test-user")
    assert retrieve.call_args.kwargs["question"] == "Tell me more"


def test_memory_load_uses_bounded_indexable_query(database, db):
    for i in range(3):
        store(db, question=str(i))
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(database[0], "before_cursor_execute", capture)
    try:
        ConversationMemory.load(db, "chat-a", "general", user_id="test-user")
    finally:
        event.remove(database[0], "before_cursor_execute", capture)
    history_query = next(s for s in statements if "FROM conversation_turns" in s)
    assert "LIMIT" in history_query and "ORDER BY" in history_query
    assert "conversation_id =" in history_query and "scope =" in history_query


def test_additive_migration_is_repeatable_and_matches_model(database):
    # Run on an independent empty database, then against ORM-created tables too.
    engine = create_engine("sqlite://")
    try:
        for target in [engine, database[0]]:
            migrate_memory(target)
            with target.begin() as conn:
                conn.exec_driver_sql("INSERT INTO conversations (id, user_id) VALUES ('preserved', 'test-user')")
            migrate_memory(target)
            inspector = inspect(target)
            assert {c["name"] for c in inspector.get_columns("conversations")} == set(Conversation.__table__.columns.keys())
            assert {c["name"] for c in inspector.get_columns("conversation_turns")} == set(ConversationTurn.__table__.columns.keys())
            assert any(i["name"] == "ix_conversation_turns_history" for i in inspector.get_indexes("conversation_turns"))
            with sessionmaker(bind=target)() as session:
                assert session.get(Conversation, "preserved") is not None
                store(session, chat_id="preserved")
                assert session.query(ConversationTurn).count() == 1
    finally:
        engine.dispose()
