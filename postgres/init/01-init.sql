-- =============================================
-- PostgreSQL Initialization for n8n AI Workflows
-- =============================================
-- This script runs automatically on first container creation.
-- It creates the custom table used by the message storage workflow.
-- =============================================

-- Create table for storing incoming agent messages
-- Used by workflows requiring message persistence

CREATE TABLE IF NOT EXISTS agent_messages (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    sender_id BIGINT NOT NULL,
    sender_username TEXT,
    chat_id BIGINT NOT NULL,
    message_text TEXT NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE
);

-- Index for common query patterns
CREATE INDEX IF NOT EXISTS idx_agent_messages_sender ON agent_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_timestamp ON agent_messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_messages_processed ON agent_messages(processed);

-- Grant permissions (for future non-superuser app roles if needed)
GRANT ALL PRIVILEGES ON TABLE agent_messages TO CURRENT_USER;
GRANT USAGE, SELECT ON SEQUENCE agent_messages_id_seq TO CURRENT_USER;

-- Confirmation log
DO $$
BEGIN
    RAISE NOTICE 'Schema initialization complete: agent_messages table created.';
END $$;
