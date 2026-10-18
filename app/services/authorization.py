"""IDs identify records; only a server-authenticated owner grants access."""
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import or_, select
from app.models.conversation import Conversation
from app.models.document import Document


def active_documents(user_id: str):
    """Also exclude retained cleanup rows and documents in deleted conversations."""
    active_ids = select(Conversation.id).where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))
    return (Document.status != "DELETING",
            or_(Document.chat_id.is_(None), Document.chat_id.in_(active_ids)))


def owned_conversation(db: Session, chat_id: str, user_id: str, *, create: bool = False,
                       include_deleted: bool = False, lock: bool = False) -> Conversation:
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")
    conversation = db.get(Conversation, chat_id)
    if conversation is None and create:
        try:
            with db.begin_nested():
                db.add(Conversation(id=chat_id, user_id=user_id))
                db.flush()
        except IntegrityError:
            # Resolve a concurrent first request by verifying the committed owner.
            pass
        db.commit()
        conversation = db.get(Conversation, chat_id)
    if conversation is None or conversation.user_id != user_id:
        # Includes quarantined legacy records; never claim them from a supplied ID.
        raise HTTPException(status_code=404, detail="Conversation not found.")
    if lock:
        # Upload finalization and deletion acquire the parent before any child writes.
        with db.no_autoflush:
            conversation = (db.query(Conversation).filter_by(id=chat_id, user_id=user_id)
                            .populate_existing().with_for_update().first())
    if conversation is None or (conversation.deleted_at is not None and not include_deleted):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


def owned_document(db: Session, document_id: str, user_id: str, chat_id: str | None = None) -> Document:
    query = db.query(Document).filter(
        Document.id == document_id, Document.user_id == user_id, Document.status != "DELETING")
    if chat_id:
        query = query.filter(Document.chat_id == chat_id)
    document = query.first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if document.chat_id:
        owned_conversation(db, document.chat_id, user_id)
    return document
