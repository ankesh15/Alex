"""Real additive upgrade and owner constraints in isolated test-only schemas."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException, Request
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from app.core.migrate import migrate_memory, migrate_history as migrate_auth
from app.core.auth import throttle_auth
from app.models.user import User, AuthRateLimit
from app.models.conversation import Conversation, ConversationTurn
from app.models.document import Document
from app.services.authorization import owned_conversation, owned_document

pytestmark = pytest.mark.real_auth


@pytest.fixture
def legacy_engine():
    url = os.environ.get("MEMORY_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Real PostgreSQL requires a disposable MEMORY_TEST_DATABASE_URL database")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").startswith("alex_memory_test"):
        pytest.fail("Use only a disposable alex_memory_test* PostgreSQL database")
    schema = "auth_test_" + uuid.uuid4().hex
    bootstrap = create_engine(url)
    with bootstrap.begin() as connection:
        connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    bootstrap.dispose()
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema},public"})
    migrate_memory(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("""CREATE TABLE documents (
            id VARCHAR(36) PRIMARY KEY, chat_id VARCHAR(64), filename VARCHAR(255) NOT NULL,
            stored_filename VARCHAR(255) NOT NULL, file_type VARCHAR(10) NOT NULL, file_size INTEGER NOT NULL,
            status VARCHAR(20), error_message TEXT, extracted_text TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP)""")
        conn.exec_driver_sql("CREATE TABLE agent_audit_logs (task_id VARCHAR(64) PRIMARY KEY, output_result TEXT)")
        conn.exec_driver_sql("INSERT INTO conversations (id) VALUES ('legacy-chat')")
        conn.exec_driver_sql("INSERT INTO conversation_turns (id,conversation_id,turn_number,scope,question,answer,citations,token_usage,status) VALUES ('legacy-turn','legacy-chat',1,'general','private question','preserved answer','[]','{}','SUCCESS')")
        conn.exec_driver_sql("INSERT INTO documents (id,chat_id,filename,stored_filename,file_type,file_size,status) VALUES ('legacy-doc','legacy-chat','private.txt','private.txt','txt',7,'READY')")
        conn.exec_driver_sql("INSERT INTO agent_audit_logs (task_id,output_result) VALUES ('legacy-audit','preserved')")
    migrate_auth(engine)
    yield engine
    # No DROP/TRUNCATE: all schemas belong to the disposable database/container.
    engine.dispose()


def test_real_postgres_upgrade_is_additive_repeatable_and_quarantines(legacy_engine):
    migrate_auth(legacy_engine)
    with sessionmaker(bind=legacy_engine)() as db:
        assert db.get(Conversation, "legacy-chat").user_id is None
        turn = db.get(ConversationTurn, "legacy-turn")
        assert turn.answer == "preserved answer" and turn.user_id is None
        document = db.get(Document, "legacy-doc")
        assert document.filename == "private.txt" and document.user_id is None
        assert db.execute(text("SELECT output_result,user_id FROM agent_audit_logs WHERE task_id='legacy-audit'")).one() == ("preserved", None)
        db.add(User(id="owner", email="owner@example.test", password_hash="unused-test-hash"))
        db.commit()
        with pytest.raises(HTTPException): owned_conversation(db, "legacy-chat", "owner", create=True)
        with pytest.raises(HTTPException): owned_document(db, "legacy-doc", "owner")


def test_real_postgres_rejects_message_and_document_owner_mismatches(legacy_engine):
    with sessionmaker(bind=legacy_engine)() as db:
        for name in ["alice", "bob"]:
            db.add(User(id=name, email=f"{name}@example.test", password_hash="unused-test-hash"))
        db.commit()
        db.add(Conversation(id="alice-chat", user_id="alice"))
        db.commit()
        db.add(ConversationTurn(conversation_id="alice-chat", user_id="bob", turn_number=1,
                                scope="general", question="forged", answer="forged", status="SUCCESS"))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
        db.add(Document(chat_id="alice-chat", user_id="bob", filename="forged.txt", stored_filename="forged.txt",
                        file_type="txt", file_size=1, status="READY"))
        with pytest.raises(IntegrityError): db.commit()
        db.rollback()
        assert db.query(ConversationTurn).filter_by(conversation_id="alice-chat").count() == 0


def test_real_postgres_auth_throttle_counts_concurrent_workers(legacy_engine):
    factory = sessionmaker(bind=legacy_engine)
    def attempt(_):
        with factory() as db:
            throttle_auth(Request({"type": "http", "method": "POST", "headers": [],
                                   "client": ("198.51.100.42", 1)}), db)
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(attempt, range(8)))
    with factory() as db:
        assert db.query(AuthRateLimit).one().attempts == 8
