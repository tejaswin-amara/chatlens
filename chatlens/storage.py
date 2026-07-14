"""SQLite-backed message store with FTS5 full-text search."""

import hashlib
import json
import sqlite3

from chatlens import config


class MessageStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or config.DB_PATH
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
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

    def ingest(self, messages: list[dict]) -> int:
        """Bulk insert messages, skipping duplicates. Returns count of inserted rows."""
        inserted = 0
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
                inserted += 1
            except sqlite3.IntegrityError:
                continue  # duplicate
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

    def get_all_messages(self, limit: int = 2000) -> list[dict]:
        """Retrieve recent messages across all chats for global summarization."""
        rows = self._conn.execute(
            "SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

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

    def get_chat_stats(self, chat_name: str) -> dict:
        """Calculate quantitative and 'Spotify Wrapped' stats for a specific chat."""
        # 1. Basic Stats
        total_msgs = self._conn.execute(
            "SELECT COUNT(*) FROM messages WHERE chat_name = ?", (chat_name,)
        ).fetchone()[0]

        top_senders = self._conn.execute(
            "SELECT sender, COUNT(*) as count FROM messages WHERE chat_name = ? GROUP BY sender ORDER BY count DESC LIMIT 5",
            (chat_name,)
        ).fetchall()

        rows = self._conn.execute(
            "SELECT sender, timestamp, text FROM messages WHERE chat_name = ? ORDER BY timestamp ASC", (chat_name,)
        ).fetchall()

        stats = {
            "total_messages": total_msgs,
            "total_words": 0,
            "top_senders": [{"name": r["sender"], "count": r["count"]} for r in top_senders],
            "awards": {},
            "activity_by_hour": {i: 0 for i in range(24)},
            "activity_by_day": {i: 0 for i in range(7)}
        }
        
        if not rows:
            return stats

        from datetime import datetime

        sender_stats = {}
        last_timestamp = None
        last_sender = None
        
        for r in rows:
            sender = r["sender"]
            text = r["text"] or ""
            ts_str = r["timestamp"]
            
            words = len(text.split())
            stats["total_words"] += words
            
            if sender not in sender_stats:
                sender_stats[sender] = {"messages": 0, "words": 0, "monologue_max_length": 0, "response_times": [], "starters": 0}
                
            sender_stats[sender]["messages"] += 1
            sender_stats[sender]["words"] += words
            sender_stats[sender]["monologue_max_length"] = max(sender_stats[sender]["monologue_max_length"], len(text))
            
            try:
                # Basic ISO parsing
                clean_ts = ts_str.replace("Z", "+00:00")
                dt = datetime.fromisoformat(clean_ts)
                stats["activity_by_hour"][dt.hour] += 1
                stats["activity_by_day"][dt.weekday()] += 1
                
                if last_timestamp and sender != last_sender:
                    diff = (dt - last_timestamp).total_seconds()
                    if diff > 28800: # 8 hours
                        sender_stats[sender]["starters"] += 1
                    else:
                        sender_stats[sender]["response_times"].append(diff)
                        
                last_timestamp = dt
                last_sender = sender
            except Exception:
                pass

        if sender_stats:
            top_talker = max(sender_stats.keys(), key=lambda s: sender_stats[s]["messages"])
            stats["awards"]["🗣️ Top Talker"] = f"{top_talker} ({sender_stats[top_talker]['messages']} msgs)"
            
            if len(sender_stats) > 1:
                observer = min(sender_stats.keys(), key=lambda s: sender_stats[s]["messages"])
                stats["awards"]["👀 The Observer"] = f"{observer} (only {sender_stats[observer]['messages']} msgs)"
                
            monologuer = max(sender_stats.keys(), key=lambda s: sender_stats[s]["monologue_max_length"])
            stats["awards"]["📜 The Monologuer"] = f"{monologuer} ({sender_stats[monologuer]['monologue_max_length']} chars in one msg)"
            
            icebreaker = max(sender_stats.keys(), key=lambda s: sender_stats[s]["starters"])
            if sender_stats[icebreaker]["starters"] > 0:
                stats["awards"]["🧊 The Icebreaker"] = f"{icebreaker} ({sender_stats[icebreaker]['starters']} times)"
                
            valid_speeders = {s: sum(sender_stats[s]["response_times"])/len(sender_stats[s]["response_times"]) 
                              for s in sender_stats if len(sender_stats[s]["response_times"]) >= 5}
            if valid_speeders:
                speed_demon = min(valid_speeders.keys(), key=lambda s: valid_speeders[s])
                stats["awards"]["⚡ Speed Demon"] = f"{speed_demon} (~{int(valid_speeders[speed_demon])}s avg reply)"

        return stats

    def close(self):
        self._conn.close()
