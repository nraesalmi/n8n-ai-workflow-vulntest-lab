-- =============================================
-- PostgreSQL Initialization for n8n AI Workflows
-- =============================================
-- This script runs automatically on first container creation.
-- It creates the custom table used by the message storage workflow.
-- =============================================

-- Create table for storing incoming Telegram messages
-- Used by Workflow 3 (Telegram → Database Storage)
-- and Workflow 4 (Telegram → Database → LLM Summary)

CREATE TABLE IF NOT EXISTS telegram_messages (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    sender_id BIGINT NOT NULL,
    sender_username TEXT,
    chat_id BIGINT NOT NULL,
    message_text TEXT NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE
);

-- Index for common query patterns
CREATE INDEX IF NOT EXISTS idx_telegram_messages_sender ON telegram_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_telegram_messages_timestamp ON telegram_messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_telegram_messages_processed ON telegram_messages(processed);

-- Grant permissions (for future non-superuser app roles if needed)
GRANT ALL PRIVILEGES ON TABLE telegram_messages TO CURRENT_USER;
GRANT USAGE, SELECT ON SEQUENCE telegram_messages_id_seq TO CURRENT_USER;

-- Confirmation log
DO $$
BEGIN
    RAISE NOTICE 'Schema initialization complete: telegram_messages table created.';
END $$;
