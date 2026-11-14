"""Hash-based deduplication cache to prevent re-processing identical messages."""

import contextlib
import hashlib
import json
import re
import sqlite3
import time
from typing import Any

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
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA journal_size_limit = 67108864;")
        conn.execute("PRAGMA cache_size = -32000;")
        conn.execute("PRAGMA temp_store = MEMORY;")
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
                CREATE TABLE IF NOT EXISTS llm_budget (
                    day TEXT PRIMARY KEY,
                    calls INTEGER
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
                CREATE INDEX IF NOT EXISTS idx_pending_status_created
                    ON pending (status, created);
                CREATE INDEX IF NOT EXISTS idx_writes_undone_ts
                    ON writes (undone, ts);
                CREATE INDEX IF NOT EXISTS idx_overrides_date_period
                    ON timetable_overrides (target_date, period);

                CREATE TABLE IF NOT EXISTS chatlens_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    processed INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_outbox_processed_ts
                    ON chatlens_outbox (processed, ts);

                CREATE TABLE IF NOT EXISTS chatlens_inbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    command TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING'
                );
                CREATE INDEX IF NOT EXISTS idx_inbox_status_ts
                    ON chatlens_inbox (status, ts);

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    chat_name TEXT,
                    message_id INTEGER NOT NULL,
                    sender_name TEXT,
                    text TEXT NOT NULL,
                    date TEXT NOT NULL,
                    ts REAL NOT NULL,
                    UNIQUE(chat_id, message_id)
                );
                CREATE INDEX IF NOT EXISTS idx_chat_messages_ts
                    ON chat_messages (ts);
                CREATE INDEX IF NOT EXISTS idx_chat_messages_chat
                    ON chat_messages (chat_id);

                CREATE TABLE IF NOT EXISTS knowledge_docs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    title TEXT,
                    text TEXT NOT NULL,
                    source TEXT NOT NULL,
                    ts REAL NOT NULL,
                    UNIQUE(filename, chunk_index)
                );
                CREATE INDEX IF NOT EXISTS idx_knowledge_docs_source
                    ON knowledge_docs (source);
                """
            )
            self._initialized = True

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

    def list_pending(self, limit: int | None = 20) -> list[dict]:
        with self._get_conn() as conn:
            if limit is not None and limit > 0:
                query = (
                    "SELECT id, event_json, status, created "
                    "FROM pending WHERE status = 'PENDING' "
                    "ORDER BY created DESC LIMIT ?"
                )
                cur = conn.execute(query, (limit,))
            else:
                query = (
                    "SELECT id, event_json, status, created "
                    "FROM pending WHERE status = 'PENDING' "
                    "ORDER BY created DESC"
                )
                cur = conn.execute(query)
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

    def prune_expired(self, max_age_seconds: float | None = None) -> int:
        """Prune expired seen hashes and old processed outbox/inbox events."""
        ttl = self.ttl_seconds if max_age_seconds is None else max_age_seconds
        cutoff = time.time() - ttl
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM seen WHERE ts < ?", (cutoff,))
            pruned_seen = cursor.rowcount
            month_ago = time.time() - (86400 * 30)
            conn.execute(
                "DELETE FROM chatlens_outbox WHERE processed = 1 AND ts < ?",
                (month_ago,),
            )
            conn.execute(
                "DELETE FROM chatlens_inbox WHERE status IN ('PROCESSED', 'REJECTED') AND ts < ?",
                (month_ago,),
            )
            return pruned_seen

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

    def get_llm_calls(self, day: str) -> int:
        with self._get_conn() as conn:
            row = conn.execute("SELECT calls FROM llm_budget WHERE day = ?", (day,)).fetchone()
            return int(row[0]) if row else 0

    def increment_llm_calls(self, day: str) -> int:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO llm_budget (day, calls) VALUES (?, 1)
                ON CONFLICT(day) DO UPDATE SET calls = calls + 1
                """,
                (day,),
            )
            row = conn.execute("SELECT calls FROM llm_budget WHERE day = ?", (day,)).fetchone()
            return int(row[0]) if row else 1

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

    def add_outbox_event(self, event_type: str, payload: dict) -> int:
        now = time.time()
        payload_str = json.dumps(payload, default=str)
        with self._get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO chatlens_outbox (ts, event_type, payload_json, processed)
                VALUES (?, ?, ?, 0)
                """,
                (now, event_type, payload_str),
            )
            return cur.lastrowid or 0

    def poll_inbox_commands(self, limit: int = 20) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT id, ts, command, payload_json, status FROM chatlens_inbox "
                "WHERE status = 'PENDING' ORDER BY ts ASC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                try:
                    p_data = json.loads(r[3])
                except (json.JSONDecodeError, TypeError):
                    p_data = {}
                results.append(
                    {
                        "id": int(r[0]),
                        "ts": float(r[1]),
                        "command": str(r[2]),
                        "payload": p_data,
                        "status": str(r[4]),
                    }
                )
            return results

    def mark_inbox_processed(self, command_id: int, status: str = "PROCESSED") -> None:
        with self._get_conn() as conn:
            conn.execute("UPDATE chatlens_inbox SET status = ? WHERE id = ?", (status, command_id))

    def mark_outbox_processed(self, event_id: int) -> None:
        with self._get_conn() as conn:
            conn.execute("UPDATE chatlens_outbox SET processed = 1 WHERE id = ?", (event_id,))

    def store_chat_message(
        self,
        chat_id: int | str,
        chat_name: str,
        message_id: int | str,
        sender_name: str,
        text: str,
        date: str = "",
        ts: float | None = None,
    ) -> bool:
        if not text or not str(text).strip():
            return False
        now_ts = time.time() if ts is None else float(ts)
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO chat_messages "
                "(chat_id, chat_name, message_id, sender_name, text, date, ts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(chat_id, message_id) DO UPDATE SET "
                "text=excluded.text, sender_name=excluded.sender_name, "
                "date=excluded.date, ts=excluded.ts",
                (
                    int(chat_id),
                    chat_name,
                    int(message_id),
                    sender_name,
                    str(text).strip(),
                    date,
                    now_ts,
                ),
            )
            return True

    def search_chat_messages(self, query: str, limit: int = 3) -> list[dict]:
        words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 2]
        if not words:
            return []
        conditions = ["text LIKE ?" for _ in words]
        sql = (
            "SELECT chat_id, chat_name, message_id, sender_name, text, date, ts "
            f"FROM chat_messages WHERE {' OR '.join(conditions)} ORDER BY ts DESC LIMIT ?"
        )
        params = [f"%{w}%" for w in words] + [limit * 3]
        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()

        scored: list[tuple[float, dict]] = []
        q_lower = query.lower()
        for r in rows:
            t = str(r[4])
            t_lower = t.lower()
            score = sum(3 for w in words if w in t_lower)
            if q_lower in t_lower:
                score += 10
            c_name = r[1] or str(r[0])
            d_val = r[5] or time.strftime("%Y-%m-%d", time.localtime(r[6]))
            scored.append(
                (
                    score,
                    {
                        "chat_id": r[0],
                        "chat_name": c_name,
                        "message_id": r[2],
                        "sender_name": r[3],
                        "text": t,
                        "date": d_val,
                        "source": f"[Chat: {c_name}, {d_val}]",
                    },
                )
            )
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def store_knowledge_doc(
        self,
        filename: str,
        chunk_index: int,
        title: str,
        text: str,
        source: str = "",
        ts: float | None = None,
    ) -> bool:
        if not text or not str(text).strip():
            return False
        now_ts = time.time() if ts is None else float(ts)
        src = source or f"[Doc: {filename}]"
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO knowledge_docs (filename, chunk_index, title, text, source, ts) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(filename, chunk_index) DO UPDATE SET "
                "title=excluded.title, text=excluded.text, source=excluded.source, ts=excluded.ts",
                (filename, chunk_index, title, str(text).strip(), src, now_ts),
            )
            return True

    def search_knowledge_docs(self, query: str, limit: int = 3) -> list[dict]:
        words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 2]
        if not words:
            return []
        conditions = ["(text LIKE ? OR title LIKE ?)" for _ in words]
        sql = (
            f"SELECT filename, chunk_index, title, text, source, ts FROM knowledge_docs "
            f"WHERE {' OR '.join(conditions)} LIMIT ?"
        )
        params: list[Any] = []
        for w in words:
            params.extend([f"%{w}%", f"%{w}%"])
        params.append(limit * 3)

        with self._get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()

        scored: list[tuple[float, dict]] = []
        q_lower = query.lower()
        for r in rows:
            t = str(r[3])
            t_lower = t.lower()
            title = str(r[2] or "")
            score = sum(3 for w in words if w in t_lower or w in title.lower())
            if q_lower in t_lower:
                score += 10
            scored.append(
                (
                    score,
                    {
                        "filename": r[0],
                        "chunk_index": r[1],
                        "title": r[2],
                        "text": t,
                        "source": r[4] or f"[Doc: {r[0]}]",
                    },
                )
            )
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def list_recent_chat_notices(self, limit: int = 5) -> list[dict]:
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT chat_name, sender_name, text, date, ts FROM chat_messages "
                "ORDER BY ts DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
            return [
                {
                    "chat_name": r[0],
                    "sender_name": r[1],
                    "text": r[2],
                    "date": r[3],
                    "source": f"[Chat: {r[0]}, {r[3]}]",
                }
                for r in rows
            ]

    def list_outbox_events(self, limit: int = 20, unprocessed_only: bool = True) -> list[dict]:
        with self._get_conn() as conn:
            if unprocessed_only:
                cur = conn.execute(
                    "SELECT id, ts, event_type, payload_json, processed FROM chatlens_outbox "
                    "WHERE processed = 0 ORDER BY ts ASC LIMIT ?",
                    (limit,),
                )
            else:
                cur = conn.execute(
                    "SELECT id, ts, event_type, payload_json, processed FROM chatlens_outbox "
                    "ORDER BY ts DESC LIMIT ?",
                    (limit,),
                )
            rows = cur.fetchall()
            results = []
            for r in rows:
                try:
                    p_data = json.loads(r[3])
                except (json.JSONDecodeError, TypeError):
                    p_data = {}
                results.append(
                    {
                        "id": int(r[0]),
                        "ts": float(r[1]),
                        "event_type": str(r[2]),
                        "payload": p_data,
                        "processed": int(r[4]),
                    }
                )
            return results


deduplicator = MessageDeduplicator()
