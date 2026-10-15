"""Unit tests for ChatLens v2 API endpoints and SPARK status bridge."""

import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

backend_dir = str(Path(__file__).resolve().parent.parent / "chatlens-v2" / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import main  # noqa: E402


@pytest.mark.asyncio
async def test_spark_status_offline(tmp_path: Path):
    non_existent = str(tmp_path / "missing_spark.db")
    with patch.dict(os.environ, {"SPARK_DB": non_existent, "SPARK_MODE": "dry"}):
        status = await main.get_spark_status()
        assert status["status"] == "offline"
        assert status["mode"] == "dry"
        assert status["seen_messages"] == 0
        assert status["pending"] == []
        assert status["writes"] == []


@pytest.mark.asyncio
async def test_spark_status_online(tmp_path: Path):
    db_file = tmp_path / "test_spark.db"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()

    cur.execute("CREATE TABLE seen (key TEXT PRIMARY KEY, ts REAL);")
    cur.execute("INSERT INTO seen VALUES ('key1', 100.0), ('key2', 200.0);")

    cur.execute(
        "CREATE TABLE pending (id INTEGER PRIMARY KEY, ts REAL, status TEXT, event_json TEXT);"
    )
    cur.execute(
        "INSERT INTO pending VALUES (1, 100.0, 'PENDING', '{\"kind\": \"ROOM_OVERRIDE\"}');"
    )

    cur.execute(
        "CREATE TABLE writes (id INTEGER PRIMARY KEY, ts REAL, kind TEXT, "
        "event_id TEXT, prior_json TEXT, undone INTEGER);"
    )
    cur.execute("INSERT INTO writes VALUES (1, 100.0, 'ROOM_OVERRIDE', 'evt_1', '{}', 0);")
    conn.commit()
    conn.close()

    with patch.dict(os.environ, {"SPARK_DB": str(db_file), "SPARK_MODE": "confirm"}):
        status = await main.get_spark_status()
        assert status["status"] == "online"
        assert status["mode"] == "confirm"
        assert status["seen_messages"] == 2
        assert len(status["pending"]) == 1
        assert status["pending"][0]["status"] == "PENDING"
        assert len(status["writes"]) == 1
        assert status["writes"][0]["kind"] == "ROOM_OVERRIDE"
        assert status["writes"][0]["undone"] is False


@pytest.mark.asyncio
async def test_get_task_status():
    mock_res = MagicMock()
    mock_res.ready.return_value = True
    mock_res.result = {"status": "done", "count": 42}

    with patch("celery.result.AsyncResult", return_value=mock_res):
        res = await main.get_task_status("test-task-123")
        assert res["status"] == "SUCCESS"
        assert res["count"] == 42


def test_message_to_dict():
    msg = MagicMock()
    msg.id = 1
    msg.platform = "whatsapp"
    msg.chat_name = "DSA"
    msg.sender = "Alice"
    msg.timestamp = "2026-10-15T10:00:00"
    msg.text = "Hello world"
    msg.reply_to = None
    msg.forwarded_from = None

    d = main.message_to_dict(msg)
    assert d["id"] == 1
    assert d["chat_name"] == "DSA"
    assert d["text"] == "Hello world"
