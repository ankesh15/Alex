"""Owner-authorized history operations using the real auth fixture and FK enforcement."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError
from app.models.conversation import Conversation, ConversationTurn
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.audit_log import AgentAuditLog
from app.core.migrate import migrate_auth, migrate_history
from app.services.conversation_memory import ConversationMemory, ConversationConflict
from app.services.conversation_service import ConversationService
from app.services.rag_service import RAGService
from app.services.vector_store import VectorStoreService
from app.config import settings
from test_auth import env, signup, upload

pytestmark = pytest.mark.real_auth


def create(client, title=None):
    result = client.post('/api/v1/conversations', json={} if title is None else {'title': title})
    assert result.status_code == 201, result.text
    return result.json()


def ask(client, identifier, question='Remember this', route='general'):
    result = client.post(f'/api/v1/chat/{route}' if route else '/api/v1/chat', json={'question': question, 'chat_id': identifier})
    assert result.status_code == 200, result.text
    return result.json()


def test_create_retrieve_rename_titles_and_memory_continuity(env):
    client, user = signup()
    conversation = create(client)
    identifier = conversation['id']
    assert conversation['title'] == 'New chat' and conversation['revision'] == 0
    env[1].invoke.side_effect = [AIMessage(content='Hello Ada'), AIMessage(content='Your name is Ada')]
    ask(client, identifier, 'My name is Ada')
    detail = client.get(f'/api/v1/conversations/{identifier}').json()
    assert detail['title'] == 'My name is Ada' and detail['last_scope'] == 'general'
    first = client.get(f'/api/v1/conversations/{identifier}/messages').json()
    assert [m['role'] for m in first['messages']] == ['user', 'assistant']
    assert first['messages'][1]['content'] == 'Hello Ada'
    renamed = client.patch(f'/api/v1/conversations/{identifier}', json={'title': '  Ada   research  '})
    assert renamed.status_code == 200 and renamed.json()['title'] == 'Ada research'
    assert renamed.json()['revision'] == 1
    assert renamed.json()['updated_at'] >= detail['updated_at']
    ask(client, identifier, 'What is my name?')
    assert 'My name is Ada' in [m.content for m in env[1].invoke.call_args.args[0]]
    reopened = client.get(f'/api/v1/conversations/{identifier}/messages').json()
    assert reopened['messages'][-1]['content'] == 'Your name is Ada'
    assert client.get(f'/api/v1/conversations/{identifier}').json()['title'] == 'Ada research'
    with env[0]() as db:
        assert db.query(ConversationTurn).filter_by(conversation_id=identifier, user_id=user['user']['id']).count() == 2


def test_explicit_title_is_not_overridden_and_rename_does_not_conflict_with_memory(env):
    client, user = signup()
    conversation = create(client, 'New chat')
    identifier = conversation['id']
    with env[0]() as db:
        snapshot = ConversationMemory.load(db, identifier, 'general', user_id=user['user']['id'])
        assert client.patch(f'/api/v1/conversations/{identifier}', json={'title': 'Custom title'}).status_code == 200
        ConversationMemory.save(db, snapshot, 'First prompt', 'Answer', [], {}, 'SUCCESS')
    assert client.get(f'/api/v1/conversations/{identifier}').json()['title'] == 'Custom title'


def test_cursor_pagination_ties_owner_isolation_and_empty_page(env):
    alice, user = signup()
    bob, _ = signup('bob@example.test')
    ids = [create(alice, f'Title {i}')['id'] for i in range(7)]
    create(bob, 'Bob private')
    timestamp = datetime(2026, 10, 13, 1, 0, tzinfo=timezone.utc)
    with env[0]() as db:
        db.query(Conversation).filter(Conversation.user_id == user['user']['id']).update({'updated_at': timestamp})
        db.commit()
    observed, cursor = [], None
    while True:
        page = alice.get('/api/v1/conversations', params={'limit': 2, **({'cursor': cursor} if cursor else {})}).json()
        observed.extend(c['id'] for c in page['conversations'])
        cursor = page['next_cursor']
        if cursor is None: break
    assert observed == sorted(ids, reverse=True)
    assert len(observed) == len(set(observed))
    assert bob.get('/api/v1/conversations', params={'limit': 100}).json()['conversations'][0]['title'] == 'Bob private'
    empty = alice.get('/api/v1/conversations', params={'cursor': __import__('base64').urlsafe_b64encode(
        b'["2000-01-01T00:00:00+00:00","lowest"]').decode()}).json()
    assert empty == {'conversations': [], 'next_cursor': None}


def test_message_pages_keep_pairs_and_exclude_new_turns_from_older_snapshot(env):
    client, _ = signup()
    identifier = create(client)['id']
    for i in range(6): ask(client, identifier, f'Question {i}')
    newest = client.get(f'/api/v1/conversations/{identifier}/messages?limit=2').json()
    assert [m['content'] for m in newest['messages'] if m['role'] == 'user'] == ['Question 4', 'Question 5']
    assert newest['through_turn'] == 6 and newest['next_before_turn'] == 5
    ask(client, identifier, 'Later message')
    older = client.get(f'/api/v1/conversations/{identifier}/messages', params={
        'limit': 2, 'before_turn': newest['next_before_turn'], 'through_turn': newest['through_turn']}).json()
    assert [m['content'] for m in older['messages'] if m['role'] == 'user'] == ['Question 2', 'Question 3']
    oldest = client.get(f'/api/v1/conversations/{identifier}/messages?limit=2&before_turn=3&through_turn=6').json()
    assert [m['content'] for m in oldest['messages'] if m['role'] == 'user'] == ['Question 0', 'Question 1']
    assert oldest['next_before_turn'] is None
    assert len({m['id'] for page in [oldest, older, newest] for m in page['messages']}) == 12
    legacy = client.get(f'/api/v1/chat/{identifier}/history?limit=2').json()
    assert legacy['turns'][-1]['question'] == 'Later message'


@pytest.mark.parametrize('method,path,payload', [
    ('post', '/api/v1/conversations', {}), ('get', '/api/v1/conversations', None),
    ('get', '/api/v1/conversations/id', None), ('get', '/api/v1/conversations/id/messages', None),
    ('patch', '/api/v1/conversations/id', {'title': 'forged'}), ('delete', '/api/v1/conversations/id', None),
])
def test_all_conversation_operations_require_auth(env, method, path, payload):
    from fastapi.testclient import TestClient
    client = TestClient(__import__('app.api.main', fromlist=['app']).app)
    assert getattr(client, method)(path, **({'json': payload} if payload is not None else {})).status_code == 401


def test_cross_user_and_quarantined_ids_cannot_read_rename_delete_or_recreate(env):
    alice, user = signup()
    bob, _ = signup('bob@example.test')
    identifier = create(alice)['id']
    ask(alice, identifier, 'Alice private content')
    with env[0]() as db:
        db.add(Conversation(id='quarantined'))
        db.commit()
    for target in [identifier, 'quarantined']:
        for suffix in ['', '/messages']:
            assert bob.get(f'/api/v1/conversations/{target}{suffix}').status_code == 404
        assert bob.patch(f'/api/v1/conversations/{target}', json={'title': 'Claim'}).status_code == 404
        assert bob.delete(f'/api/v1/conversations/{target}').status_code == 404
        assert bob.post('/api/v1/chat/general', json={'chat_id': target, 'question': 'Claim'}).status_code == 404
    assert alice.post('/api/v1/conversations', json={'title': 'forged', 'user_id': 'other'}).status_code == 422
    assert alice.get('/api/v1/conversations').json()['conversations'][0]['id'] == identifier


def test_mutations_require_csrf(env):
    client, _ = signup()
    identifier = create(client)['id']
    client.headers.pop('X-CSRF-Token')
    assert client.post('/api/v1/conversations', json={}).status_code == 403
    assert client.patch(f'/api/v1/conversations/{identifier}', json={'title': 'forged'}).status_code == 403
    assert client.delete(f'/api/v1/conversations/{identifier}').status_code == 403
    assert client.get(f'/api/v1/conversations/{identifier}').status_code == 200


@pytest.mark.parametrize('query', ['limit=0', 'limit=101', 'cursor=invalid!', 'cursor=bnVsbA=='])
def test_list_pagination_validation(env, query):
    client, _ = signup()
    assert client.get(f'/api/v1/conversations?{query}').status_code == 422


@pytest.mark.parametrize('title', ['', '   ', 'x' * 121, None])
def test_rename_title_validation(env, title):
    client, _ = signup()
    identifier = create(client)['id']
    assert client.patch(f'/api/v1/conversations/{identifier}', json={'title': title}).status_code == 422


def test_new_conversation_preserves_old_documents_and_citations(env):
    client, user = signup()
    identifier = create(client)['id']
    document = upload(client, identifier)
    result = ask(client, identifier, 'Document content', route='')
    second = create(client)['id']
    assert second != identifier
    assert client.get(f'/api/v1/documents/{document}').status_code == 200
    reopened = client.get(f'/api/v1/conversations/{identifier}/messages').json()
    assert reopened['messages'][-1]['citations'] == result['citations']
    again = ask(client, identifier, 'What does it say?', route='')
    assert again['citations'][0]['document_id'] == document


def test_deletion_removes_messages_documents_embeddings_and_scrubs_linked_audit(env):
    client, user = signup()
    identifier = create(client)['id']
    document = upload(client, identifier)
    ask(client, identifier, 'Document content', route='')
    other = create(client)['id']
    other_document = upload(client, other)
    with env[0]() as db:
        file = Path(settings.STORAGE_DIR) / db.get(Document, document).stored_filename
        assert db.query(AgentAuditLog).filter_by(chat_id=identifier).one().input_data is not None
    assert file.exists()
    result = client.delete(f'/api/v1/conversations/{identifier}')
    assert result.status_code == 200 and result.json()['cleanup_pending'] == 0
    assert not file.exists()
    assert client.get(f'/api/v1/conversations/{identifier}').status_code == 404
    assert client.get(f'/api/v1/conversations/{identifier}/messages').status_code == 404
    assert client.get(f'/api/v1/documents/{document}').status_code == 404
    assert client.get(f'/api/v1/documents/{other_document}').status_code == 200
    assert client.delete(f'/api/v1/conversations/{identifier}').status_code == 200  # Safe retry.
    with env[0]() as db:
        assert db.query(ConversationTurn).filter_by(conversation_id=identifier).count() == 0
        assert db.query(DocumentChunk).filter_by(document_id=document).count() == 0
        assert db.get(Document, document) is None
        tombstone = db.get(Conversation, identifier)
        assert tombstone.deleted_at is not None and tombstone.title == 'Deleted conversation'
        audit = db.query(AgentAuditLog).filter_by(chat_id=identifier).one()
        assert audit.input_data is None and audit.output_result is None and audit.total_tokens == 4
        assert VectorStoreService.search(db, 'Content', chat_id=identifier, user_id=user['user']['id']) == []


def test_deleted_ids_and_late_memory_snapshots_cannot_resurrect_history(env):
    client, user = signup()
    identifier = create(client)['id']
    with env[0]() as db:
        snapshot = ConversationMemory.load(db, identifier, 'general', user_id=user['user']['id'])
        assert client.delete(f'/api/v1/conversations/{identifier}').status_code == 200
        with pytest.raises(ConversationConflict):
            ConversationMemory.save(db, snapshot, 'late', 'late private answer', [], {}, 'SUCCESS')
    env[1].invoke.reset_mock()
    assert client.post('/api/v1/chat/general', json={'question': 'Resurrect', 'chat_id': identifier}).status_code == 404
    assert client.post('/api/v1/documents/upload', data={'chat_id': identifier},
                       files={'file': ('late.txt', b'Late', 'text/plain')}).status_code == 404
    env[1].invoke.assert_not_called()


def test_failed_disk_cleanup_is_hidden_and_retryable(env):
    client, _ = signup()
    identifier = create(client)['id']
    document = upload(client, identifier)
    with patch('app.services.conversation_service.Path.unlink', side_effect=PermissionError('not permitted')):
        result = client.delete(f'/api/v1/conversations/{identifier}')
    assert result.status_code == 200 and result.json()['cleanup_pending'] == 1
    assert client.get('/api/v1/documents').json()['documents'] == []
    assert client.get(f'/api/v1/documents/{document}').status_code == 404
    with env[0]() as db:
        pending = db.get(Document, document)
        file = Path(settings.STORAGE_DIR) / pending.stored_filename
        assert pending.status == 'DELETING' and pending.extracted_text is None
        assert db.query(DocumentChunk).filter_by(document_id=document).count() == 0
    assert file.exists()
    assert client.delete(f'/api/v1/conversations/{identifier}').json()['cleanup_pending'] == 0
    assert not file.exists()


def test_deletion_rollback_keeps_transcripts_and_files(env):
    client, user = signup()
    identifier = create(client)['id']
    document = upload(client, identifier)
    ask(client, identifier)
    with env[0]() as db:
        file = Path(settings.STORAGE_DIR) / db.get(Document, document).stored_filename
        with patch.object(db, 'commit', side_effect=SQLAlchemyError('write failed')):
            with pytest.raises(SQLAlchemyError): ConversationService.delete(db, user['user']['id'], identifier)
        db.rollback()
    assert file.exists()
    assert client.get(f'/api/v1/conversations/{identifier}/messages').json()['messages']


def test_upload_finishing_after_deletion_is_rejected(env):
    client, user = signup()
    identifier = create(client)['id']
    def extraction(*args):
        with env[0]() as db:
            ConversationService.delete(db, user['user']['id'], identifier)
        return [{'text': 'Late uploaded text', 'page_number': None}]
    with patch('app.api.v1.endpoints.documents.DocumentProcessor.extract_text', side_effect=extraction):
        result = client.post('/api/v1/documents/upload', data={'chat_id': identifier},
                             files={'file': ('late.txt', b'Late uploaded text', 'text/plain')})
    assert result.status_code == 404
    with env[0]() as db:
        assert db.query(Document).filter_by(chat_id=identifier).count() == 0
        assert db.query(DocumentChunk).count() == 0


def test_audit_written_after_deletion_contains_metrics_without_private_text(env):
    client, user = signup()
    identifier = create(client)['id']
    client.delete(f'/api/v1/conversations/{identifier}')
    with env[0]() as db:
        RAGService.log_audit(db, 'late-audit', 'private', 'private answer', {'total_tokens': 7},
                            user_id=user['user']['id'], chat_id=identifier)
        audit = db.get(AgentAuditLog, 'late-audit')
        assert audit.input_data is None and audit.output_result is None and audit.total_tokens == 7


def test_history_migration_is_additive_repeatable_and_preserves_quarantine(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "history-upgrade.sqlite"}')
    migrate_auth(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("INSERT INTO users (id,email,password_hash) VALUES ('owner','owner@example.test','unused')")
        connection.exec_driver_sql("INSERT INTO conversations (id,user_id,revision) VALUES ('owned','owner',1), ('unowned',NULL,0)")
        connection.exec_driver_sql("INSERT INTO conversation_turns (id,conversation_id,user_id,turn_number,scope,question,answer,citations,token_usage,status) VALUES ('turn','owned','owner',1,'general','Existing question','Existing answer','[]','{}','SUCCESS')")
    migrate_history(engine)
    migrate_history(engine)
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT title,deleted_at FROM conversations WHERE id='owned'").one() == ('Existing question', None)
        assert connection.exec_driver_sql("SELECT user_id,title FROM conversations WHERE id='unowned'").one() == (None, 'New chat')
        assert connection.exec_driver_sql("SELECT answer FROM conversation_turns WHERE id='turn'").scalar() == 'Existing answer'
    assert any(i['name'] == 'ix_conversations_owner_history' for i in inspect(engine).get_indexes('conversations'))
    engine.dispose()
