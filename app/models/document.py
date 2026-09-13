import uuid
import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime
from sqlalchemy.orm import relationship
from app.core.db import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    chat_id = Column(String(64), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False, index=True)
    file_size = Column(Integer, nullable=False)
    status = Column(String(20), default="PROCESSING", index=True)
    error_message = Column(Text, nullable=True)

    # JSON-encoded array of extracted pages: [{"text": "...", "page_number": int|None}]
    extracted_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # Cascading relationship to DocumentChunk
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
