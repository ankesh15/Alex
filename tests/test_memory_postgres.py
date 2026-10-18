"""Optional real PostgreSQL checks. Point only at a disposable alex_memory_test database.

MEMORY_TEST_DATABASE_URL=postgresql://.../alex_memory_test pytest tests/test_memory_postgres.py -v
No application DATABASE_URL is used and no existing tables/data are deleted.
"""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from app.core.migrate import migrate_history as migrate_memory
from app.models.conversation import Conversation, ConversationTurn
from app.models.user import User
from app.services.conversation_memory import ConversationMemory, ConversationConflict


@pytest.fixture(scope="module")
def pg_engine():
    url = os.environ.get("MEMORY_TEST_DATABASE_URL")
    if not url:
        pytest.skip("MEMORY_TEST_DATABASE_URL is not set; real PostgreSQL integration requires a disposable database")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").startswith("alex_memory_test"):
        pytest.fail("Use a disposable PostgreSQL database named alex_memory_test* for memory integration tests")
    engine = create_engine(url, pool_pre_ping=True)
    migrate_memory(engine)
    with sessionmaker(bind=engine)() as session:
        if session.get(User, "test-user") is None:
            session.add(User(id="test-user", email="pipeline@example.test", password_hash="unused-test-hash"))
            session.commit()
    yield engine
    engine.dispose()


def test_postgres_migration_repeatable_and_json_roundtrip(pg_engine):
    chat_id = str(uuid.uuid4())
    citations = [{"document_id": "doc-a", "filename": "report.pdf", "page_number": 2,
                  "chunk_id": "chunk-a", "relevance_score": 0.9}]
    factory = sessionmaker(bind=pg_engine)
    with factory() as session:
        snapshot = ConversationMemory.load(session, chat_id, "document:doc-a", user_id="test-user")
        ConversationMemory.save(session, snapshot, "Question", "Answer", citations, {"total_tokens": 9}, "SUCCESS")
    migrate_memory(pg_engine)
    with factory() as reopened:
        turn = reopened.query(ConversationTurn).filter_by(conversation_id=chat_id).one()
        assert turn.citations == citations
        assert turn.token_usage == {"total_tokens": 9}
        assert turn.created_at.tzinfo is not None
        assert reopened.get(Conversation, chat_id).revision == 1
        assert [m.content for m in ConversationMemory.load(reopened, chat_id, "document:doc-a", user_id="test-user").messages] == ["Question", "Answer"]
    assert any(i["name"] == "ix_conversation_turns_history" for i in inspect(pg_engine).get_indexes("conversation_turns"))


def test_postgres_concurrent_first_turns_only_one_commits(pg_engine):
    chat_id = str(uuid.uuid4())
    factory = sessionmaker(bind=pg_engine)
    before_load, after_load = Barrier(2), Barrier(2)
    def submit(label):
        with factory() as session:
            before_load.wait(timeout=10)
            snapshot = ConversationMemory.load(session, chat_id, "general", user_id="test-user")
            after_load.wait(timeout=10)
            try:
                ConversationMemory.save(session, snapshot, label, "Answer", [], {}, "SUCCESS")
                return "saved"
            except ConversationConflict:
                return "conflict"
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(submit, ["first", "second"]))
    assert sorted(results) == ["conflict", "saved"]
    with factory() as session:
        assert session.query(ConversationTurn).filter_by(conversation_id=chat_id).count() == 1
        assert session.get(Conversation, chat_id).revision == 1


def test_postgres_separate_conversations_never_share_history(pg_engine):
    factory = sessionmaker(bind=pg_engine)
    first, second = str(uuid.uuid4()), str(uuid.uuid4())
    with factory() as session:
        snapshot = ConversationMemory.load(session, first, "general", user_id="test-user")
        ConversationMemory.save(session, snapshot, "Secret topic", "Secret answer", [], {}, "SUCCESS")
    with factory() as session:
        assert ConversationMemory.load(session, second, "general", user_id="test-user").messages == []
