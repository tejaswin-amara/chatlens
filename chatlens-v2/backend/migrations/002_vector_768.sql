ALTER TABLE messages ALTER COLUMN embedding TYPE vector(768);
CREATE INDEX IF NOT EXISTS idx_messages_embedding ON messages USING hnsw (embedding vector_cosine_ops);
