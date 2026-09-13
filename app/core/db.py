from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL)
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
