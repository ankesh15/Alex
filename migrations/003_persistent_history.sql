-- Additive, repeatable. No reassignment/deletion of legacy records.
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS title VARCHAR(120) NOT NULL DEFAULT 'New chat';
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS title_is_custom BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
CREATE INDEX IF NOT EXISTS ix_conversations_owner_history ON conversations (user_id, deleted_at, updated_at, id);
ALTER TABLE IF EXISTS agent_audit_logs ADD COLUMN IF NOT EXISTS chat_id VARCHAR(64) REFERENCES conversations(id);
DO $$ BEGIN
    IF to_regclass('agent_audit_logs') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS ix_agent_audit_logs_chat_id ON agent_audit_logs (chat_id);
    END IF;
END $$;
-- Populate display titles only for authenticated owners; NULL owners remain quarantined.
UPDATE conversations AS c SET title = COALESCE((
    SELECT LEFT(regexp_replace(t.question, '\s+', ' ', 'g'), 80)
    FROM conversation_turns AS t WHERE t.conversation_id = c.id AND t.user_id = c.user_id
    ORDER BY t.turn_number ASC LIMIT 1
), c.title)
WHERE c.user_id IS NOT NULL AND c.deleted_at IS NULL AND c.title = 'New chat' AND NOT c.title_is_custom;
