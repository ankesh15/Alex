-- PostgreSQL: additive ownership migration. NULL legacy owners stay quarantined.
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY, email VARCHAR(254) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL, is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE TABLE IF NOT EXISTS user_sessions (
    token_hash VARCHAR(64) PRIMARY KEY, user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    csrf_token VARCHAR(64) NOT NULL, created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_expires_at ON user_sessions (expires_at);
CREATE TABLE IF NOT EXISTS auth_rate_limits (
    key VARCHAR(64) PRIMARY KEY, window_start TIMESTAMP WITH TIME ZONE NOT NULL, attempts INTEGER NOT NULL
);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS user_id VARCHAR(36) REFERENCES users(id);
ALTER TABLE conversation_turns ADD COLUMN IF NOT EXISTS user_id VARCHAR(36) REFERENCES users(id);
ALTER TABLE IF EXISTS documents ADD COLUMN IF NOT EXISTS user_id VARCHAR(36) REFERENCES users(id);
ALTER TABLE IF EXISTS documents ADD COLUMN IF NOT EXISTS chat_id VARCHAR(64);
ALTER TABLE IF EXISTS agent_audit_logs ADD COLUMN IF NOT EXISTS user_id VARCHAR(36) REFERENCES users(id);
CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations (user_id);
CREATE INDEX IF NOT EXISTS ix_conversation_turns_user_id ON conversation_turns (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_conversations_id_user ON conversations (id, user_id);
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_turn_conversation_owner'
                   AND conrelid = 'conversation_turns'::regclass) THEN
        ALTER TABLE conversation_turns ADD CONSTRAINT fk_turn_conversation_owner
            FOREIGN KEY (conversation_id, user_id) REFERENCES conversations(id, user_id) ON DELETE CASCADE;
    END IF;
    IF to_regclass('documents') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS ix_documents_user_id ON documents (user_id);
        CREATE INDEX IF NOT EXISTS ix_documents_chat_id ON documents (chat_id);
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_document_conversation_owner'
                       AND conrelid = 'documents'::regclass) THEN
            ALTER TABLE documents ADD CONSTRAINT fk_document_conversation_owner
                FOREIGN KEY (chat_id, user_id) REFERENCES conversations(id, user_id);
        END IF;
    END IF;
    IF to_regclass('agent_audit_logs') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS ix_agent_audit_logs_user_id ON agent_audit_logs (user_id);
    END IF;
END $$;
