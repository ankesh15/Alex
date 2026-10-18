"""History checks against an explicitly disposable PostgreSQL database."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.core.migrate import migrate_auth, migrate_history
from app.models.conversation import Conversation, ConversationTurn
from app.services.conversation_memory import ConversationMemory, ConversationConflict
from app.services.conversation_service import ConversationService
from tests.test_memory_postgres import pg_engine  # noqa: F401


def test_postgres_upgrade_backfills_owned_titles_without_claiming_legacy(pg_engine):
    schema = "history_test_" + uuid.uuid4().hex
    with pg_engine.begin() as connection:
        connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    isolated = create_engine(pg_engine.url, connect_args={"options": f"-csearch_path={schema},public"})
    try:
        migrate_auth(isolated)  # Feature 4 schema, before the new history columns.
        with isolated.begin() as connection:
            connection.exec_driver_sql("INSERT INTO users (id,email,password_hash) VALUES ('owner','history-upgrade@example.test','test-only')")
            connection.exec_driver_sql("INSERT INTO conversations (id,user_id) VALUES ('owned','owner'),('unowned',NULL)")
            connection.exec_driver_sql("""INSERT INTO conversation_turns
                (id,conversation_id,user_id,turn_number,scope,question,answer,citations,token_usage,status)
                VALUES ('owned-turn','owned','owner',1,'general','My   research topic','Preserved','[]','{}','SUCCESS'),
                ('legacy-turn','unowned',NULL,1,'general','Quarantined secret','Preserved','[]','{}','SUCCESS')""")
        migrate_history(isolated)
        migrate_history(isolated)
        with isolated.connect() as connection:
            assert connection.execute(text("SELECT title,user_id FROM conversations WHERE id='owned'")).one() == ("My research topic", "owner")
            assert connection.execute(text("SELECT title,user_id FROM conversations WHERE id='unowned'")).one() == ("New chat", None)
            assert connection.execute(text("SELECT count(*) FROM conversation_turns WHERE answer='Preserved'")).scalar() == 2
    finally:
        isolated.dispose()  # Entire disposable database is removed after verification.


def test_history_postgres_migration_repeatable_and_pagination(pg_engine):
    with pg_engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(pg_engine)
    migrate_history(pg_engine)
    migrate_history(pg_engine)
    assert {"title", "title_is_custom", "deleted_at"} <= {
        column["name"] for column in inspect(pg_engine).get_columns("conversations")}
    assert "chat_id" in {column["name"] for column in inspect(pg_engine).get_columns("agent_audit_logs")}
    factory = sessionmaker(bind=pg_engine)
    with factory() as session:
        chat = ConversationService.create(session, "test-user", "PostgreSQL history")
        for number in range(4):
            snapshot = ConversationMemory.load(session, chat["id"], "general", user_id="test-user")
            ConversationMemory.save(session, snapshot, f"Question {number}", f"Answer {number}", [], {}, "SUCCESS")
        first = ConversationService.messages(session, "test-user", chat["id"], 2)
        second = ConversationService.messages(session, "test-user", chat["id"], 2,
                                               first["next_before_turn"], first["through_turn"])
        assert [message["content"] for message in second["messages"] + first["messages"]] == [
            value for number in range(4) for value in [f"Question {number}", f"Answer {number}"]]
        assert second["next_before_turn"] is None


def test_postgres_delete_and_inflight_save_cannot_resurrect(pg_engine):
    with pg_engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(pg_engine)
    factory = sessionmaker(bind=pg_engine)
    chat_id = str(uuid.uuid4())
    with factory() as session:
        snapshot = ConversationMemory.load(session, chat_id, "general", user_id="test-user")
        ConversationMemory.save(session, snapshot, "Private question", "Private answer", [], {}, "SUCCESS")
    ready = Barrier(2)

    def generate():
        with factory() as session:
            snapshot = ConversationMemory.load(session, chat_id, "general", user_id="test-user")
            session.commit()  # Generation does not hold a database transaction open.
            ready.wait(timeout=10)
            try:
                ConversationMemory.save(session, snapshot, "Late question", "Late answer", [], {}, "SUCCESS")
                return "saved"
            except ConversationConflict:
                return "conflict"

    def delete():
        with factory() as session:
            ready.wait(timeout=10)
            return ConversationService.delete(session, "test-user", chat_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        save_future, delete_future = executor.submit(generate), executor.submit(delete)
        assert save_future.result(timeout=20) in {"saved", "conflict"}
        assert delete_future.result(timeout=20)["status"] == "deleted"
    with factory() as session:
        assert session.get(Conversation, chat_id).deleted_at is not None
        assert session.query(ConversationTurn).filter_by(conversation_id=chat_id).count() == 0
