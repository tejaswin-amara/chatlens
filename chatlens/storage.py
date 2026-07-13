"""SQLite-backed message store with FTS5 full-text search."""

import hashlib
import json
import sqlite3
from typing import Any

from google import genai
from chatlens import config


class MessageStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or config.DB_PATH
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._embedding_client: genai.Client | None = None
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                chat_name TEXT,
                sender TEXT,
                timestamp TEXT,
                text TEXT,
                reply_to INTEGER,
                forwarded_from TEXT,
                metadata_json TEXT,
                content_hash TEXT UNIQUE
            );
            CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_name);
            CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(timestamp);
            CREATE TABLE IF NOT EXISTS message_embeddings (
                message_id INTEGER PRIMARY KEY,
                embedding vector NOT NULL,
                embedding_model TEXT NOT NULL,
                FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_message_embeddings_model ON message_embeddings(embedding_model);
        """)
        # FTS5 virtual table — separate from main table
        # ponytail: content='' (external content) would save space but complicates inserts.
        try:
            self._conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts "
                "USING fts5(text, content=messages, content_rowid=id)"
            )
        except sqlite3.OperationalError:
            pass  # already exists or FTS5 not compiled in
        self._conn.commit()

    @staticmethod
    def _content_hash(msg: dict) -> str:
        key = f"{msg.get('platform')}|{msg.get('chat_name')}|{msg.get('sender')}|{msg.get('timestamp')}|{msg.get('text')}"
        return hashlib.sha256(key.encode()).hexdigest()

    def _embed_text_batch(self, texts: list[str]) -> list[list[float]] | None:
        if not texts or not config.GEMINI_API_KEY:
            return None
        if self._embedding_client is None:
            self._embedding_client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = self._embedding_client.models.embed_content(
            model=config.GEMINI_EMBEDDING_MODEL,
            contents=texts,
        )
        embeddings: list[Any] = response.embeddings or []
        if len(embeddings) != len(texts):
            return None
        vectors: list[list[float]] = []
        for item in embeddings:
            values = getattr(item, "values", None)
            if not isinstance(values, list):
                return None
            vectors.append(values)
        return vectors

    def _store_embeddings(self, rows: list[tuple[int, str | None]]):
        if not rows:
            return
        for i in range(0, len(rows), config.EMBEDDING_BATCH_SIZE):
            batch = rows[i : i + config.EMBEDDING_BATCH_SIZE]
            texts = [text or "" for _, text in batch]
            try:
                vectors = self._embed_text_batch(texts)
            except Exception:
                continue
            if not vectors:
                continue
            self._conn.executemany(
                "INSERT OR REPLACE INTO message_embeddings (message_id, embedding, embedding_model) "
                "VALUES (?, ?, ?)",
                [
                    (message_id, json.dumps(vector), config.GEMINI_EMBEDDING_MODEL)
                    for (message_id, _), vector in zip(batch, vectors, strict=True)
                ],
            )

    def ingest(self, messages: list[dict]) -> int:
        """Bulk insert messages, skipping duplicates. Returns count of inserted rows."""
        inserted = 0
        inserted_rows: list[tuple[int, str | None]] = []
        for msg in messages:
            h = self._content_hash(msg)
            try:
                cur = self._conn.execute(
                    "INSERT INTO messages (platform, chat_name, sender, timestamp, text, "
                    "reply_to, forwarded_from, metadata_json, content_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        msg.get("platform"),
                        msg.get("chat_name"),
                        msg.get("sender"),
                        msg.get("timestamp"),
                        msg.get("text"),
                        msg.get("reply_to"),
                        msg.get("forwarded_from"),
                        json.dumps(msg.get("metadata")) if msg.get("metadata") else None,
                        h,
                    ),
                )
                # Keep FTS in sync
                self._conn.execute(
                    "INSERT INTO messages_fts(rowid, text) VALUES (?, ?)",
                    (cur.lastrowid, msg.get("text")),
                )
                inserted_rows.append((cur.lastrowid, msg.get("text")))
                inserted += 1
            except sqlite3.IntegrityError:
                continue  # duplicate
        self._store_embeddings(inserted_rows)
        self._conn.commit()
        return inserted

    def search(self, query: str, limit: int = 50) -> list[dict]:
        """Full-text search across messages."""
        rows = self._conn.execute(
            "SELECT m.* FROM messages m "
            "JOIN messages_fts f ON m.id = f.rowid "
            "WHERE messages_fts MATCH ? "
            "ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_chat_names(self) -> list[dict]:
        """List all chats with message counts."""
        rows = self._conn.execute(
            "SELECT chat_name AS name, platform, COUNT(*) AS message_count "
            "FROM messages GROUP BY chat_name, platform ORDER BY message_count DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_messages(
        self,
        chat_name: str,
        limit: int = 500,
        offset: int = 0,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        """Retrieve messages for a chat with optional date filtering."""
        sql = "SELECT * FROM messages WHERE chat_name = ?"
        params: list = [chat_name]
        if date_from:
            sql += " AND timestamp >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND timestamp <= ?"
            params.append(date_to)
        sql += " ORDER BY timestamp ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        """Return summary statistics about the stored messages."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS total, "
            "COUNT(DISTINCT chat_name) AS chats, "
            "MIN(timestamp) AS earliest, "
            "MAX(timestamp) AS latest "
            "FROM messages"
        ).fetchone()
        platforms = self._conn.execute(
            "SELECT platform, COUNT(*) AS count FROM messages GROUP BY platform"
        ).fetchall()
        return {
            "total_messages": row["total"],
            "total_chats": row["chats"],
            "date_range": {"from": row["earliest"], "to": row["latest"]},
            "per_platform": {r["platform"]: r["count"] for r in platforms},
        }

    def close(self):
        self._conn.close()
