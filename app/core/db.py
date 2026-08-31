from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, text
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime
from app.config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AgentAuditLog(Base):
    __tablename__ = "agent_audit_logs"

    task_id = Column(String, primary_key=True, index=True)
    module_name = Column(String, index=True)
    status = Column(String, default="PENDING")
    input_data = Column(Text)
    output_result = Column(Text, nullable=True)

    # Token Metrics
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


def init_db():
    # Import models to ensure they are registered on Base.metadata
    from app.models.document import Document  # noqa: F401
    from app.models.document_chunk import DocumentChunk  # noqa: F401

    # 1. Enable pgvector extension if connected to PostgreSQL
    if "postgresql" in DATABASE_URL:
        try:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
        except Exception as e:
            import logging
            logging.warning(f"Could not enable pgvector extension: {e}")

    # 2. Create tables
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        import logging
        logging.warning(f"Could not initialize DB tables on startup: {e}")
