"""Conversation management and history views over the existing turn store."""
import base64
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from app.config import settings
from app.models.conversation import Conversation, ConversationTurn
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.audit_log import AgentAuditLog
from app.services.authorization import owned_conversation


def summary(conversation: Conversation) -> dict:
    return {"id": conversation.id, "title": conversation.title, "revision": conversation.revision,
            "created_at": conversation.created_at, "updated_at": conversation.updated_at}


def encode_cursor(conversation: Conversation) -> str:
    updated = conversation.updated_at
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    data = json.dumps([updated.isoformat(), conversation.id], separators=(",", ":"))
    return base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        if len(cursor) > 512:
            raise ValueError()
        data = json.loads(base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True))
        if not isinstance(data, list) or len(data) != 2 or not isinstance(data[1], str) or not 1 <= len(data[1]) <= 64:
            raise ValueError()
        updated = datetime.fromisoformat(data[0])
        if updated.tzinfo is None:
            raise ValueError()
        return updated.astimezone(timezone.utc), data[1]
    except (ValueError, TypeError, UnicodeError):
        raise HTTPException(status_code=422, detail="Invalid conversation cursor.") from None


class ConversationService:
    @staticmethod
    def create(db: Session, user_id: str, title: str | None = None) -> dict:
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required.")
        conversation = Conversation(id=str(uuid.uuid4()), user_id=user_id,
                                    title=title or "New chat", title_is_custom=title is not None)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return summary(conversation)

    @staticmethod
    def list(db: Session, user_id: str, limit: int, cursor: str | None) -> dict:
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required.")
        query = db.query(Conversation).filter(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))
        if cursor:
            updated, identifier = decode_cursor(cursor)
            query = query.filter(or_(Conversation.updated_at < updated,
                                     and_(Conversation.updated_at == updated, Conversation.id < identifier)))
        rows = query.order_by(Conversation.updated_at.desc(), Conversation.id.desc()).limit(limit + 1).all()
        page = rows[:limit]
        return {"conversations": [summary(row) for row in page],
                "next_cursor": encode_cursor(page[-1]) if len(rows) > limit else None}

    @staticmethod
    def retrieve(db: Session, user_id: str, chat_id: str) -> dict:
        conversation = owned_conversation(db, chat_id, user_id)
        last = db.query(ConversationTurn.scope).filter_by(conversation_id=chat_id, user_id=user_id).order_by(
            ConversationTurn.turn_number.desc()).first()
        return {**summary(conversation), "last_scope": last[0] if last else "general"}

    @staticmethod
    def rename(db: Session, user_id: str, chat_id: str, title: str) -> dict:
        conversation = owned_conversation(db, chat_id, user_id, lock=True)
        conversation.title = title
        conversation.title_is_custom = True
        conversation.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(conversation)
        return summary(conversation)

    @staticmethod
    def history(db: Session, user_id: str, chat_id: str, limit: int,
                before_turn: int | None = None, through_turn: int | None = None) -> dict:
        conversation = owned_conversation(db, chat_id, user_id)
        upper = min(through_turn, conversation.revision) if through_turn is not None else conversation.revision
        query = db.query(ConversationTurn).filter(
            ConversationTurn.conversation_id == chat_id, ConversationTurn.user_id == user_id,
            ConversationTurn.turn_number <= upper)
        if before_turn is not None:
            query = query.filter(ConversationTurn.turn_number < before_turn)
        rows = query.order_by(ConversationTurn.turn_number.desc()).limit(limit + 1).all()
        page = rows[:limit]
        return {"chat_id": chat_id, "turns": [
            {"id": turn.id, "turn_number": turn.turn_number, "scope": turn.scope,
             "question": turn.question, "answer": turn.answer, "citations": turn.citations,
             "token_usage": turn.token_usage, "status": turn.status, "created_at": turn.created_at}
            for turn in reversed(page)
        ], "next_before_turn": page[-1].turn_number if len(rows) > limit else None, "through_turn": upper}

    @classmethod
    def messages(cls, db: Session, user_id: str, chat_id: str, limit: int,
                 before_turn: int | None = None, through_turn: int | None = None) -> dict:
        history = cls.history(db, user_id, chat_id, limit, before_turn, through_turn)
        messages = []
        for turn in history.pop("turns"):
            common = {"turn_number": turn["turn_number"], "scope": turn["scope"], "created_at": turn["created_at"]}
            messages.extend([
                {**common, "id": f"{turn['id']}:user", "role": "user", "content": turn["question"]},
                {**common, "id": f"{turn['id']}:assistant", "role": "assistant", "content": turn["answer"],
                 "citations": turn["citations"], "tokenUsage": turn["token_usage"]},
            ])
        return {**history, "messages": messages}

    @classmethod
    def delete(cls, db: Session, user_id: str, chat_id: str) -> dict:
        conversation = owned_conversation(db, chat_id, user_id, include_deleted=True, lock=True)
        if conversation.deleted_at is None:
            now = datetime.now(timezone.utc)
            conversation.deleted_at = now
            conversation.updated_at = now
            conversation.revision += 1
            conversation.title = "Deleted conversation"
            db.query(ConversationTurn).filter_by(
                conversation_id=chat_id, user_id=user_id).delete(synchronize_session=False)
            db.query(AgentAuditLog).filter_by(chat_id=chat_id, user_id=user_id).update(
                {"input_data": None, "output_result": None}, synchronize_session=False)
            documents = db.query(Document).filter_by(chat_id=chat_id, user_id=user_id).all()
            for document in documents:
                db.query(DocumentChunk).filter_by(document_id=document.id).delete(synchronize_session=False)
                document.status = "DELETING"
                document.extracted_text = None
                document.error_message = None
                document.filename = "Deleted document"
            db.commit()
        # Storage is not transactional. Keep DELETING metadata for retry on disk failure.
        pending = cls.cleanup_documents(db, user_id, chat_id)
        return {"id": chat_id, "status": "deleted", "cleanup_pending": pending}

    @staticmethod
    def cleanup_documents(db: Session, user_id: str, chat_id: str) -> int:
        documents = db.query(Document).filter_by(chat_id=chat_id, user_id=user_id, status="DELETING").all()
        storage = Path(settings.STORAGE_DIR).resolve()
        pending = 0
        for document in documents:
            path = (storage / document.stored_filename).resolve()
            if path == storage or storage not in path.parents:
                pending += 1
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pending += 1
                continue
            db.delete(document)
        db.commit()
        return pending
