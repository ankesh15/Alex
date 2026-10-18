"""Indexed, bounded memory with atomic exchange persistence and stale-write detection."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from sqlalchemy import update, case, and_
from sqlalchemy.orm import Session
from app.config import settings
from app.models.conversation import Conversation, ConversationTurn
from app.services.authorization import owned_conversation


class ConversationConflict(Exception):
    """Another request completed against the same conversation snapshot."""


@dataclass(frozen=True)
class MemorySnapshot:
    chat_id: str
    user_id: str
    scope: str
    revision: int
    messages: list[BaseMessage]


class ConversationMemory:
    @staticmethod
    def load(db: Session, chat_id: str, scope: str, *, user_id: str) -> MemorySnapshot:
        conversation = owned_conversation(db, chat_id, user_id, create=True)
        revision = conversation.revision
        turns = (
            db.query(ConversationTurn)
            .filter(ConversationTurn.conversation_id == chat_id,
                    ConversationTurn.user_id == user_id,
                    ConversationTurn.scope == scope,
                    ConversationTurn.status == "SUCCESS",
                    ConversationTurn.turn_number <= revision)
            .order_by(ConversationTurn.turn_number.desc())
            .limit(settings.MEMORY_MAX_TURNS).all()
        )
        remaining = settings.MEMORY_MAX_CHARS
        pairs: list[tuple[str, str]] = []
        for turn in turns:
            question, answer = turn.question, turn.answer
            size = len(question) + len(answer)
            if size > remaining:
                if not pairs:
                    # Preserve roles and both halves of the latest exchange.
                    question = question[:min(len(question), remaining // 2)]
                    answer = answer[:remaining - len(question)]
                    pairs.append((question, answer))
                break
            pairs.append((question, answer))
            remaining -= size
        messages: list[BaseMessage] = []
        for question, answer in reversed(pairs):
            messages.extend([HumanMessage(content=question), AIMessage(content=answer)])
        # Do not hold a read transaction/connection while waiting for Gemini.
        db.commit()
        return MemorySnapshot(chat_id, user_id, scope, revision, messages)

    @staticmethod
    def save(db: Session, snapshot: MemorySnapshot, question: str, answer: str,
             citations: list[dict[str, Any]], token_usage: dict[str, int], status: str) -> None:
        if status not in {"SUCCESS", "NO_CONTEXT"} or not answer.strip():
            return
        try:
            result = db.execute(
                update(Conversation)
                .where(Conversation.id == snapshot.chat_id, Conversation.user_id == snapshot.user_id,
                       Conversation.deleted_at.is_(None),
                       Conversation.revision == snapshot.revision)
                .values(revision=snapshot.revision + 1, updated_at=datetime.now(timezone.utc),
                        title=case((and_(Conversation.revision == 0, Conversation.title_is_custom.is_(False)),
                                    " ".join(question.split())[:80]), else_=Conversation.title))
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                raise ConversationConflict("Conversation changed while generating. Please retry your question.")
            db.add(ConversationTurn(
                conversation_id=snapshot.chat_id, turn_number=snapshot.revision + 1,
                user_id=snapshot.user_id,
                scope=snapshot.scope, question=question, answer=answer,
                citations=citations, token_usage=token_usage, status=status,
            ))
            db.commit()
        except Exception:
            db.rollback()
            raise
