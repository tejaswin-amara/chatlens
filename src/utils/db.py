import contextlib
import sqlite3

from src.config import settings


def get_connection(db_path: str | None = None):
    conn = sqlite3.connect(db_path or settings.spark_db, isolation_level=None)
    conn.execute("PRAGMA busy_timeout = 5000")
    return contextlib.closing(conn)


def record_write(kind: str, event_id: str, prior_json: str) -> None:
    import time

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO writes (ts, kind, event_id, prior_json) VALUES (?, ?, ?, ?)",
            (time.time(), kind, event_id, prior_json),
        )
