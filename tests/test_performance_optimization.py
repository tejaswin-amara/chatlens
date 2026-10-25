"""Tests for performance optimization: L1 timetable cache, SIMD retrieval, and streaming."""

from __future__ import annotations

import asyncio
import json
import os
import time
from unittest.mock import MagicMock

import numpy as np
import pytest

import src.timetable as tt
from src.config import settings
from src.ingestion.handlers import handle_bot_command
from src.knowledge.retriever import ContiguousVectorBuffer, KnowledgeRetriever
from src.notify.bot import bot
from src.utils.db import get_connection
from src.utils.deduplication import deduplicator


def test_timetable_l1_cache_hit_and_invalidation(tmp_path) -> None:
    """Test that timetable is cached in memory by mtime and invalidates on edit."""
    toml_path = tmp_path / "test_tt.toml"
    content_v1 = """
[meta]
term = "T01"
valid_from = 2026-08-01
valid_to = 2026-12-31
sample = false

[[slot]]
day = "Mon"
period = 1
course = "DSA"
room = "H-001"
faculty = "Prof. X"
"""
    toml_path.write_text(content_v1, encoding="utf-8")
    path_str = str(toml_path)

    tt.clear_cache()

    # First load - cache miss
    tt1 = tt.load(path_str)
    assert tt1 is not None
    assert tt1.meta.term == "T01"
    assert len(tt1.slots) == 1
    assert tt1.slots[0].course == "DSA"

    # Second load - cache hit (same object or cached structure)
    tt2 = tt.load(path_str)
    assert tt2 is not None
    assert tt2.meta.term == "T01"

    # Invalidate by modifying file content and touching mtime
    time.sleep(0.05)
    content_v2 = content_v1.replace('term = "T01"', 'term = "T02"')
    toml_path.write_text(content_v2, encoding="utf-8")
    os.utime(path_str, (time.time() + 1, time.time() + 1))

    # Third load - must detect new mtime and reload
    tt3 = tt.load(path_str)
    assert tt3 is not None
    assert tt3.meta.term == "T02"


def test_deterministic_slash_commands(monkeypatch) -> None:
    """Verify standard slash commands (/today, /tomorrow, /timetable, /status) execute cleanly."""
    sent: list[str] = []
    monkeypatch.setattr(bot, "send", lambda text, **kw: sent.append(text))
    owner_id = settings.owner_chat_id or 12345

    # 1. /status
    asyncio.run(
        handle_bot_command({"chat": {"id": owner_id}, "from": {"id": owner_id}, "text": "/status"})
    )
    assert len(sent) == 1
    assert "ChatLens PA Status" in sent[-1]

    # 2. /today
    asyncio.run(
        handle_bot_command({"chat": {"id": owner_id}, "from": {"id": owner_id}, "text": "/today"})
    )
    assert len(sent) == 2
    has_today = any(k in sent[-1] for k in ("S-10", "scheduled classes", "Regular instruction"))
    assert has_today

    # 3. /tomorrow
    asyncio.run(
        handle_bot_command(
            {"chat": {"id": owner_id}, "from": {"id": owner_id}, "text": "/tomorrow"}
        )
    )
    assert len(sent) == 3

    # 4. /timetable
    asyncio.run(
        handle_bot_command(
            {"chat": {"id": owner_id}, "from": {"id": owner_id}, "text": "/timetable"}
        )
    )
    assert len(sent) == 4
    assert "Official Academic Timetable" in sent[-1]


def test_bunk_command_fast_path_from_cache(monkeypatch) -> None:
    """Verify /bunk uses cached attendance for deterministic sub-millisecond execution."""
    sample_records = [
        {
            "course_name": "Data Structures",
            "course_code": "25CS2103E",
            "attended": 30,
            "conducted": 32,
            "percentage": 93.75,
            "safe_bunks": 4,
            "recovery_needed": 0,
        }
    ]
    deduplicator.meta_set("erp_attendance_cache", json.dumps(sample_records))

    sent: list[str] = []
    monkeypatch.setattr(bot, "send", lambda text, **kw: sent.append(text))
    from src.erp import klu_erp

    async def mock_get_att() -> list[dict]:
        return sample_records

    monkeypatch.setattr(klu_erp, "get_attendance", mock_get_att)
    owner_id = settings.owner_chat_id or 12345

    # Warmup
    asyncio.run(
        handle_bot_command({"chat": {"id": owner_id}, "from": {"id": owner_id}, "text": "/bunk"})
    )
    sent.clear()

    t0 = time.perf_counter()
    asyncio.run(
        handle_bot_command({"chat": {"id": owner_id}, "from": {"id": owner_id}, "text": "/bunk"})
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert len(sent) == 1
    assert "Attendance & Bunk Margin Calculator" in sent[0]
    assert "Data Structures" in sent[0]
    assert elapsed_ms < 100.0  # Under 100ms in test environment


def test_contiguous_vector_buffer_search() -> None:
    """Verify ContiguousVectorBuffer computes cosine similarities and top-K min-heap."""
    buf = ContiguousVectorBuffer(dim=8)
    vectors = np.array(
        [
            [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
    buf.set_vectors(vectors)

    query = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
    top_results = buf.search_top_k(query, k=2)

    assert len(top_results) == 2
    # The exact match at index 0 must have score ~1.0
    assert top_results[0][1] == 0
    assert pytest.approx(top_results[0][0], rel=1e-3) == 1.0
    # The partial match at index 3 must be second
    assert top_results[1][1] == 3


def test_sqlite_pragmas_and_concurrent_writes(tmp_path) -> None:
    """Verify SQLite connection optimization pragmas and concurrent write safety."""
    test_db = str(tmp_path / "perf_test.db")
    with get_connection(test_db) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS writes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL,
                kind TEXT,
                event_id TEXT,
                prior_json TEXT
            )
            """
        )
        cur = conn.cursor()
        cur.execute("PRAGMA synchronous;")
        sync_mode = cur.fetchone()[0]
        # NORMAL synchronous is 1
        assert sync_mode in (1, "NORMAL")

    # Concurrent writes test
    import concurrent.futures

    errors: list[Exception] = []

    def write_worker(wid: int) -> None:
        for i in range(10):
            try:
                with get_connection(test_db) as c:
                    c.execute(
                        "INSERT INTO writes (ts, kind, event_id, prior_json) VALUES (?, ?, ?, ?)",
                        (time.time(), "test", f"ev_{wid}_{i}", "{}"),
                    )
            except Exception as e:
                errors.append(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(write_worker, i) for i in range(8)]
        concurrent.futures.wait(futures)

    assert len(errors) == 0


def test_knowledge_retriever_answer_stream() -> None:
    """Verify streaming token chunk generator from knowledge_retriever."""
    kr = KnowledgeRetriever()
    kr.chunks = ["EXAM: Lab Exam 15 Oct in Room 103"]

    class MockChunk:
        def __init__(self, text: str) -> None:
            self.text = text

    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = [
        MockChunk("Room"),
        MockChunk(" 103"),
        MockChunk(" for"),
        MockChunk(" exam"),
    ]
    kr._client = mock_client

    chunks = list(kr.answer_stream("Where is the exam?"))
    assert len(chunks) == 4
    assert "".join(chunks) == "Room 103 for exam"
