"""Self-check tests for embedding ingestion. Run: python -m tests.test_storage_embeddings"""

import json
import os
import tempfile

from chatlens.storage import MessageStore


class _FakeEmbeddingStore(MessageStore):
    def _embed_text_batch(self, texts: list[str]) -> list[list[float]] | None:
        return [[float(len(t)), 1.0] for t in texts]


def test_ingest_stores_embeddings():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    messages = [
        {
            "platform": "telegram",
            "chat_name": "Team",
            "sender": "Alice",
            "timestamp": "2024-01-01T10:00:00",
            "text": "hello world",
        },
        {
            "platform": "telegram",
            "chat_name": "Team",
            "sender": "Bob",
            "timestamp": "2024-01-01T10:01:00",
            "text": "ship it",
        },
    ]

    store = None
    try:
        store = _FakeEmbeddingStore(db_path=db_path)
        inserted = store.ingest(messages)
        assert inserted == 2, f"Expected 2 inserted rows, got {inserted}"

        rows = store._conn.execute(
            "SELECT message_id, embedding, embedding_model FROM message_embeddings ORDER BY message_id"
        ).fetchall()
        assert len(rows) == 2, f"Expected 2 embedding rows, got {len(rows)}"
        assert rows[0]["embedding_model"], "Expected embedding_model to be stored"
        assert json.loads(rows[0]["embedding"]) == [11.0, 1.0]
        assert json.loads(rows[1]["embedding"]) == [7.0, 1.0]
        print("✓ test_ingest_stores_embeddings passed")
    finally:
        if store is not None:
            store.close()
        os.unlink(db_path)


if __name__ == "__main__":
    test_ingest_stores_embeddings()
    print("\nAll embedding storage tests passed ✓")
