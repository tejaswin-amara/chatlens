ALTER TABLE messages ADD COLUMN IF NOT EXISTS content_hash TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS ux_messages_content_hash ON messages (content_hash);
