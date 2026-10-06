"""Hash-based deduplication cache to prevent re-processing identical messages."""

import hashlib
import sqlite3
import time

from src.config import settings
from src.utils.db import get_connection


class MessageDeduplicator:
    def __init__(self, ttl_seconds: int = 86400 * 7) -> None:
        self.ttl_seconds = ttl_seconds
        self.db_path = settings.spark_db
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return get_connection()

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_state (
                    chat_id INTEGER PRIMARY KEY,
                    last_id INTEGER NOT NULL,
                    updated REAL
                );
                CREATE TABLE IF NOT EXISTS pending (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_json TEXT,
                    status TEXT,
                    created REAL
                );
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS seen (
                    key TEXT PRIMARY KEY,
                    ts REAL NOT NULL
                );
                """
            )

    def _compute_hash(self, chat_id: int | str, message_id: int | str, content: str = "") -> str:
        raw_key = f"{chat_id}:{message_id}:{content.strip()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def add_pending(self, event_json: str) -> int:
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO pending (event_json, status, created) VALUES (?, 'PENDING', ?)",
                (event_json, __import__("time").time()),
            )
            return cur.lastrowid or 0

    def is_duplicate(self, chat_id: int | str, message_id: int | str, content: str = "") -> bool:
        msg_hash = self._compute_hash(chat_id, message_id, content)
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT ts FROM seen WHERE key = ?", (msg_hash,))
            row = cursor.fetchone()
            if row:
                if time.time() - row[0] < self.ttl_seconds:
                    return True
                else:
                    conn.execute("DELETE FROM seen WHERE key = ?", (msg_hash,))
        return False

    def mark_processed(self, chat_id: int | str, message_id: int | str, content: str = "") -> str:
        msg_hash = self._compute_hash(chat_id, message_id, content)
        now = time.time()
        with self._get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO seen (key, ts) VALUES (?, ?)", (msg_hash, now))
        return msg_hash

    def get_chat_state(self, chat_id: int) -> int | None:
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT last_id FROM chat_state WHERE chat_id = ?", (chat_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def update_chat_state(self, chat_id: int, last_id: int) -> None:
        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO chat_state (chat_id, last_id, updated)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    last_id = MAX(last_id, excluded.last_id),
                    updated = excluded.updated
                """,
                (chat_id, last_id, now),
            )

    def meta_set(self, key: str, value: str) -> None:
        with self._get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))

    def meta_get(self, key: str) -> str | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
            return row[0] if row else None


deduplicator = MessageDeduplicator()
