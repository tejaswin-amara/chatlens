"""Hash-based deduplication cache to prevent re-processing identical messages."""

import contextlib
import hashlib
import json
import sqlite3
import time

from src.config import settings


class MessageDeduplicator:
    def __init__(self, ttl_seconds: int = 86400 * 7, db_path: str | None = None) -> None:
        self.ttl_seconds = ttl_seconds
        self._db_path = db_path
        self._initialized = False

    @property
    def db_path(self) -> str:
        return self._db_path or settings.spark_db

    @db_path.setter
    def db_path(self, val: str | None) -> None:
        self._db_path = val
        self._initialized = False

    def _get_raw_conn(self) -> contextlib.AbstractContextManager[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.execute("PRAGMA busy_timeout = 5000")
        return contextlib.closing(conn)

    def _ensure_db(self) -> None:
        if not self._initialized:
            self._init_db()

    def _get_conn(self) -> contextlib.AbstractContextManager[sqlite3.Connection]:
        self._ensure_db()
        return self._get_raw_conn()

    def _init_db(self) -> None:
        with self._get_raw_conn() as conn:
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
                CREATE TABLE IF NOT EXISTS writes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL,
                    kind TEXT,
                    event_id TEXT,
                    prior_json TEXT,
                    undone INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS seen (
                    key TEXT PRIMARY KEY,
                    ts REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS timetable_overrides (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_date TEXT NOT NULL,
                    period INTEGER,
                    course_code TEXT NOT NULL,
                    course_name TEXT,
                    room TEXT,
                    status TEXT NOT NULL,
                    summary TEXT,
                    created REAL
                );
                """
            )

    def _compute_hash(self, chat_id: int | str, message_id: int | str, content: str = "") -> str:
        raw_key = f"{chat_id}:{message_id}:{content.strip()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def add_pending(self, event_json: str, chat_id: int = 0, msg_id: int = 0) -> int:
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO pending (event_json, status, created) VALUES (?, 'PENDING', ?)",
                (event_json, time.time()),
            )
            return cur.lastrowid or 0

    def get_pending(self, pid: int) -> tuple[str, str, float] | None:
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT event_json, status, created FROM pending WHERE id = ?", (pid,)
            )
            row = cur.fetchone()
            return (row[0], row[1], float(row[2])) if row else None

    def list_pending(self, limit: int = 20) -> list[dict]:
        with self._get_conn() as conn:
            query = (
                "SELECT id, event_json, status, created "
                "FROM pending WHERE status = 'PENDING' "
                "ORDER BY created DESC LIMIT ?"
            )
            cur = conn.execute(query, (limit,))
            rows = cur.fetchall()
            results = []
            for r in rows:
                try:
                    data = json.loads(r[1])
                    results.append(
                        {"id": r[0], "event": data, "status": r[2], "created": float(r[3])}
                    )
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
            return results

    def claim_pending(self, pid: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE pending SET status = 'CLAIMED' WHERE id = ? AND status = 'PENDING'", (pid,)
            )
            return cur.rowcount == 1

    def finish_pending(self, pid: int, status: str) -> None:
        with self._get_conn() as conn:
            conn.execute("UPDATE pending SET status = ? WHERE id = ?", (status, pid))

    def record_write(self, kind: str, event_id: str, prior_json: str) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO writes (ts, kind, event_id, prior_json) VALUES (?, ?, ?, ?)",
                (time.time(), kind, event_id, prior_json),
            )

    def last_write(self) -> tuple[int, str, str, str] | None:
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT id, kind, event_id, prior_json FROM writes "
                "WHERE undone = 0 ORDER BY ts DESC LIMIT 1"
            )
            row = cur.fetchone()
            return (int(row[0]), str(row[1]), str(row[2]), str(row[3])) if row else None

    def mark_undone(self, write_id: int) -> None:
        with self._get_conn() as conn:
            conn.execute("UPDATE writes SET undone = 1 WHERE id = ?", (write_id,))

    def is_duplicate(
        self,
        chat_id: int | str,
        message_id: int | str,
        content: str = "",
        ttl_seconds: float | None = None,
    ) -> bool:
        ttl = self.ttl_seconds if ttl_seconds is None else ttl_seconds
        msg_hash = self._compute_hash(chat_id, message_id, content)
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT ts FROM seen WHERE key = ?", (msg_hash,))
            row = cursor.fetchone()
            if row:
                if time.time() - row[0] < ttl:
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

    def record_override(
        self,
        target_date: str,
        period: int | None,
        course_code: str,
        course_name: str | None = None,
        room: str | None = None,
        status: str = "OVERRIDE",
        summary: str = "",
    ) -> int:
        now = time.time()
        with self._get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO timetable_overrides
                (target_date, period, course_code, course_name, room, status, summary, created)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    target_date,
                    period,
                    course_code,
                    course_name or "",
                    room or "",
                    status,
                    summary,
                    now,
                ),
            )
            return cur.lastrowid or 0

    def get_overrides(self, target_date: str) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.execute(
                """
                SELECT id, target_date, period, course_code, course_name, room, status, summary
                FROM timetable_overrides
                WHERE target_date = ?
                ORDER BY period ASC
                """,
                (target_date,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": row[0],
                    "target_date": row[1],
                    "period": row[2],
                    "course_code": row[3],
                    "course_name": row[4],
                    "room": row[5],
                    "status": row[6],
                    "summary": row[7],
                }
                for row in rows
            ]

    def delete_override(self, override_id: int) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM timetable_overrides WHERE id = ?", (override_id,))


deduplicator = MessageDeduplicator()
