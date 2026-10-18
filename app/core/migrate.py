"""Apply the additive memory migration explicitly before a production deployment."""
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy import inspect
from app.core.db import engine


def migrate_memory(db_engine: Engine = engine) -> None:
    path = Path(__file__).resolve().parents[2] / "migrations" / "001_conversation_memory.sql"
    # This migration contains plain DDL only, without semicolons inside literals.
    statements = path.read_text(encoding="utf-8").split(";")
    with db_engine.begin() as connection:
        for statement in statements:
            if statement.strip():
                connection.execute(text(statement))


def migrate_auth(db_engine: Engine = engine) -> None:
    """Repeatable upgrade; production PostgreSQL gets composite ownership constraints."""
    migrate_memory(db_engine)
    with db_engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            path = Path(__file__).resolve().parents[2] / "migrations" / "002_user_auth.sql"
            # Trusted migration text contains a DO block: do not split on semicolons.
            connection.exec_driver_sql(path.read_text(encoding="utf-8"))
        elif connection.dialect.name == "sqlite":
            # Additive support for migration tests; production remains PostgreSQL.
            from app.models.user import User, UserSession, AuthRateLimit
            for table in [User.__table__, UserSession.__table__, AuthRateLimit.__table__]:
                table.create(connection, checkfirst=True)
            for table in ["conversations", "conversation_turns", "documents", "agent_audit_logs"]:
                inspector = inspect(connection)
                if inspector.has_table(table):
                    if "user_id" not in {c["name"] for c in inspector.get_columns(table)}:
                        connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN user_id VARCHAR(36) REFERENCES users(id)")
                    connection.exec_driver_sql(f"CREATE INDEX IF NOT EXISTS ix_{table}_user_id ON {table} (user_id)")
            connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_conversations_id_user ON conversations (id, user_id)")
            # SQLite cannot add composite FKs without rebuilding tables; no destructive rebuild.
        else:
            raise RuntimeError("Authentication migrations support PostgreSQL and SQLite test databases only.")


def migrate_history(db_engine: Engine = engine) -> None:
    migrate_auth(db_engine)
    with db_engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            path = Path(__file__).resolve().parents[2] / "migrations" / "003_persistent_history.sql"
            connection.exec_driver_sql(path.read_text(encoding="utf-8"))
        elif connection.dialect.name == "sqlite":
            columns = {c["name"] for c in inspect(connection).get_columns("conversations")}
            for name, definition in [("title", "VARCHAR(120) NOT NULL DEFAULT 'New chat'"),
                                     ("title_is_custom", "BOOLEAN NOT NULL DEFAULT 0"),
                                     ("deleted_at", "TIMESTAMP")]:
                if name not in columns:
                    connection.exec_driver_sql(f"ALTER TABLE conversations ADD COLUMN {name} {definition}")
            connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_conversations_owner_history "
                                       "ON conversations (user_id, deleted_at, updated_at, id)")
            if inspect(connection).has_table("agent_audit_logs"):
                audit_columns = {c["name"] for c in inspect(connection).get_columns("agent_audit_logs")}
                if "chat_id" not in audit_columns:
                    connection.exec_driver_sql("ALTER TABLE agent_audit_logs ADD COLUMN chat_id "
                                               "VARCHAR(64) REFERENCES conversations(id)")
                connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_agent_audit_logs_chat_id "
                                           "ON agent_audit_logs (chat_id)")
            connection.exec_driver_sql("""UPDATE conversations SET title = COALESCE((
                SELECT substr(trim(t.question),1,80) FROM conversation_turns t
                WHERE t.conversation_id=conversations.id AND t.user_id=conversations.user_id
                ORDER BY t.turn_number ASC LIMIT 1), title)
                WHERE user_id IS NOT NULL AND deleted_at IS NULL AND title='New chat' AND title_is_custom=0""")


if __name__ == "__main__":
    migrate_history()
    print("Conversation memory, authentication and persistent history migrations applied successfully.")
