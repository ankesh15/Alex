from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Re-export AgentAuditLog for backward compatibility
from app.models.audit_log import AgentAuditLog  # noqa: F401, E402


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

    # 3. Lightweight migration safety for documents.chat_id
    if "postgresql" in DATABASE_URL:
        try:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS chat_id VARCHAR(64);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_chat_id ON documents (chat_id);"))
                conn.commit()
        except Exception as e:
            import logging
            logging.warning(f"Could not verify or apply chat_id column migration: {e}")
