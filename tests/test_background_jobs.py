"""Self-check tests for background job status + worker tasks."""

import asyncio
import os
import tempfile
from unittest.mock import patch

from chatlens.storage import MessageStore


def test_job_status_lifecycle():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store = MessageStore(db_path=db_path)
        job_id = store.create_job("parse_whatsapp_export_job", {"path": "/tmp/chat.txt"})
        queued = store.get_job(job_id)
        assert queued is not None
        assert queued["status"] == "queued"
        assert queued["payload"]["path"] == "/tmp/chat.txt"

        store.update_job_status(job_id, "running")
        running = store.get_job(job_id)
        assert running["status"] == "running"

        store.update_job_status(job_id, "completed", result={"parsed": 3, "ingested": 2})
        completed = store.get_job(job_id)
        assert completed["status"] == "completed"
        assert completed["result"] == {"parsed": 3, "ingested": 2}
        print("✓ test_job_status_lifecycle passed")
    finally:
        os.unlink(db_path)


def test_parse_whatsapp_job_updates_status():
    from chatlens.worker import parse_whatsapp_export_job

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store = MessageStore(db_path=db_path)
        job_id = store.create_job("parse_whatsapp_export_job", {"path": "/tmp/chat.txt"})

        with patch("chatlens.worker.MessageStore", side_effect=lambda: MessageStore(db_path=db_path)):
            with patch("chatlens.worker.parse_whatsapp_export", return_value=[
                {
                    "platform": "whatsapp",
                    "chat_name": "A",
                    "sender": "Alice",
                    "timestamp": "2024-01-15T10:30:00",
                    "text": "Hello",
                }
            ]):
                asyncio.run(parse_whatsapp_export_job({}, job_id, "/tmp/chat.txt"))

        job = store.get_job(job_id)
        assert job["status"] == "completed"
        assert job["result"] == {"parsed": 1, "ingested": 1}
        print("✓ test_parse_whatsapp_job_updates_status passed")
    finally:
        os.unlink(db_path)


def test_fetch_telegram_job_failure_updates_status():
    from chatlens.worker import fetch_telegram_chats_job

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store = MessageStore(db_path=db_path)
        job_id = store.create_job("fetch_telegram_chats_job", {"chat_names": None, "limit": 10})

        with patch("chatlens.worker.MessageStore", side_effect=lambda: MessageStore(db_path=db_path)):
            with patch("chatlens.worker.fetch_telegram_chats", side_effect=ValueError("telegram auth missing")):
                try:
                    asyncio.run(fetch_telegram_chats_job({}, job_id, None, 10))
                    raise AssertionError("Expected fetch_telegram_chats_job to raise ValueError")
                except ValueError:
                    pass

        job = store.get_job(job_id)
        assert job["status"] == "failed"
        assert "telegram auth missing" in (job["error"] or "")
        print("✓ test_fetch_telegram_job_failure_updates_status passed")
    finally:
        os.unlink(db_path)


if __name__ == "__main__":
    test_job_status_lifecycle()
    test_parse_whatsapp_job_updates_status()
    test_fetch_telegram_job_failure_updates_status()
    print("\nAll background job tests passed ✓")
