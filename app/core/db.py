from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings


def normalize_database_url(database_url: str) -> str:
    """Use the installed psycopg2 driver regardless of SQLAlchemy's default."""
    for prefix in ("postgres://", "postgresql://"):
        if database_url.startswith(prefix):
            return "postgresql+psycopg2://" + database_url[len(prefix):]
    # Respect explicitly configured drivers and non-PostgreSQL test databases.
    return database_url


DATABASE_URL = normalize_database_url(settings.DATABASE_URL)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Re-export AgentAuditLog for backward compatibility
from app.models.audit_log import AgentAuditLog  # noqa: F401, E402


def init_db():
    # Import models to ensure they are registered on Base.metadata
    from app.models.document import Document  # noqa: F401
    from app.models.document_chunk import DocumentChunk  # noqa: F401
    from app.models.conversation import Conversation, ConversationTurn  # noqa: F401
    from app.models.user import User, UserSession, AuthRateLimit  # noqa: F401

    # 1. Enable pgvector extension if connected to PostgreSQL
    if "postgresql" in DATABASE_URL:
        try:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
        except Exception as e:
            raise RuntimeError("Could not initialize pgvector; verify database provisioning.") from e

    # 2. Create tables
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        raise RuntimeError("Could not initialize database tables.") from e

    # Ownership is security-critical: refuse to serve a partially migrated schema.
    inspector = inspect(engine)
    for table in ["documents", "conversations", "conversation_turns", "agent_audit_logs"]:
        if "user_id" not in {c["name"] for c in inspector.get_columns(table)}:
            raise RuntimeError("Authentication schema is missing. Run python -m app.core.migrate before deployment.")
    if engine.dialect.name == "postgresql":
        for table, constraint in [("documents", "fk_document_conversation_owner"),
                                  ("conversation_turns", "fk_turn_conversation_owner")]:
            if constraint not in {fk["name"] for fk in inspector.get_foreign_keys(table)}:
                raise RuntimeError("Ownership constraints are missing. Run python -m app.core.migrate before deployment.")
    if not {"title", "title_is_custom", "deleted_at"}.issubset(
        {c["name"] for c in inspector.get_columns("conversations")}
    ):
        raise RuntimeError("History schema is missing. Run python -m app.core.migrate before deployment.")
    if "chat_id" not in {c["name"] for c in inspector.get_columns("agent_audit_logs")}:
        raise RuntimeError("History audit schema is missing. Run python -m app.core.migrate before deployment.")
