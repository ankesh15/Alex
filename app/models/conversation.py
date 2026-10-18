"""Durable owned exchanges; NULL owners are quarantined legacy records."""
import datetime
import uuid
from sqlalchemy import (
    Column, String, Text, Integer, DateTime, ForeignKey, ForeignKeyConstraint,
    Boolean, JSON, Index, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship
from app.core.db import Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_conversations_id_user"),
        Index("ix_conversations_owner_history", "user_id", "deleted_at", "updated_at", "id"),
    )

    id = Column(String(64), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String(120), nullable=False, default="New chat", server_default="New chat")
    title_is_custom = Column(Boolean, nullable=False, default=False, server_default="false")
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    revision = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False,
                        server_default=func.now(),
                        default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False,
                        server_default=func.now(),
                        default=lambda: datetime.datetime.now(datetime.timezone.utc))
    turns = relationship("ConversationTurn", cascade="all, delete-orphan", back_populates="conversation")


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"
    __table_args__ = (
        UniqueConstraint("conversation_id", "turn_number", name="uq_conversation_turn_number"),
        ForeignKeyConstraint(["conversation_id", "user_id"], ["conversations.id", "conversations.user_id"],
                             ondelete="CASCADE", name="fk_turn_conversation_owner"),
        Index("ix_conversation_turns_history", "conversation_id", "scope", "status", "turn_number"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(64), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    turn_number = Column(Integer, nullable=False)
    scope = Column(String(64), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    citations = Column(JSON, nullable=False, default=list)
    token_usage = Column(JSON, nullable=False, default=dict)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        server_default=func.now(),
                        default=lambda: datetime.datetime.now(datetime.timezone.utc))
    conversation = relationship("Conversation", back_populates="turns")
