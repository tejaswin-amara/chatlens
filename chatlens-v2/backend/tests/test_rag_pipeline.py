"""Unit tests for Phase 3 RAG & Embedding Scale:
- Batch Gemini text-embedding-004 generation
- Full conversation indexing in save_messages (no [:200] truncation)
- backfill_embeddings_task Celery task
- Reciprocal Rank Fusion (RRF)
- Context window expansion ([M - 2, M + 2])
- Hybrid retrieval with semantic + lexical search
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend root is in sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from celery_worker import (  # noqa: E402
    backfill_embeddings_sync,
    save_messages,
)
from celery_worker import (  # noqa: E402
    generate_embeddings_batch as worker_batch,
)
from core.ai import (  # noqa: E402
    expand_context_window,
    hybrid_retrieve_messages,
    reciprocal_rank_fusion,
)
from embeddings import (  # noqa: E402
    generate_embeddings_batch as embeddings_batch,
)
from models import Base, Message  # noqa: E402


@pytest.fixture
def sqlite_session_factory():
    """In-memory SQLite synchronous session factory fixture."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    sm = sessionmaker(bind=test_engine)
    yield sm
    Base.metadata.drop_all(test_engine)


def test_celery_worker_batch_wrapper():
    """Verify worker_batch returns None list when client is unavailable."""
    assert worker_batch(["text 1", "text 2"]) == [None, None]


def test_reciprocal_rank_fusion_scoring():
    """Verify RRF formula correctly scores and ranks candidate IDs across multiple lists."""
    # List 1: [1, 2, 3] -> ranks 1, 2, 3
    # List 2: [2, 3, 4] -> ranks 1, 2, 3
    dense_ids = [1, 2, 3]
    sparse_ids = [2, 3, 4]

    fused = reciprocal_rank_fusion(dense_ids, sparse_ids, k=60)
    # Item 2 has rank 2 in dense (1/62) and rank 1 in sparse (1/61) => highest score
    assert fused[0] == 2
    # Item 3 has rank 3 in dense (1/63) and rank 2 in sparse (1/62) => second highest
    assert fused[1] == 3
    # Items 1 and 4:
    # 1: 1/61 (dense rank 1) = ~0.016393
    # 4: 1/63 (sparse rank 3) = ~0.015873
    assert fused[2] == 1
    assert fused[3] == 4


def test_reciprocal_rank_fusion_edge_cases():
    """Verify RRF behavior with empty lists or single list input."""
    assert reciprocal_rank_fusion([], []) == []
    assert reciprocal_rank_fusion([10, 20], None) == [10, 20]
    assert reciprocal_rank_fusion([[100], [200, 100]], k=60) == [100, 200]


def test_expand_context_window(sqlite_session_factory):
    """Verify expand_context_window fetches [M - 2, M + 2] around hit IDs chronologically."""
    with sqlite_session_factory() as session:
        for i in range(1, 11):
            session.add(
                Message(
                    id=i,
                    platform="telegram",
                    chat_name="StudyGroup",
                    sender=f"User{i}",
                    timestamp=f"2026-11-14T10:0{i:02d}:00",
                    text=f"Message content {i}",
                    content_hash=f"hash_{i}",
                )
            )
        session.commit()

        # Context around hit M=5 with window=2 should return IDs 3, 4, 5, 6, 7
        import asyncio

        res = asyncio.run(
            expand_context_window(session, hit_ids=[5], chat_name="StudyGroup", window_size=2)
        )
        res_ids = [m.id for m in res]
        assert res_ids == [3, 4, 5, 6, 7]

        # Overlapping hits M=5 and M=6 should return IDs 3, 4, 5, 6, 7, 8 deduplicated
        res_overlap = asyncio.run(
            expand_context_window(session, hit_ids=[5, 6], chat_name="StudyGroup", window_size=2)
        )
        overlap_ids = [m.id for m in res_overlap]
        assert overlap_ids == [3, 4, 5, 6, 7, 8]

        # Edge hit M=1 should clamp to positive IDs [1, 2, 3]
        res_start = asyncio.run(
            expand_context_window(session, hit_ids=[1], chat_name="StudyGroup", window_size=2)
        )
        start_ids = [m.id for m in res_start]
        assert start_ids == [1, 2, 3]


def test_embeddings_batch_size_and_model():
    """Verify generate_embeddings_batch chunks requests up to 100 texts with text-embedding-004."""
    mock_client = MagicMock()

    class MockEmbedding:
        def __init__(self, val: float):
            self.values = [val] * 768

    class MockResponse:
        def __init__(self, count: int, base: float):
            self.embeddings = [MockEmbedding(base + i) for i in range(count)]

    # 150 texts should produce 2 calls: one with 100 texts, one with 50 texts
    texts = [f"Sample message text {i}" for i in range(150)]

    def side_effect(model, contents, config=None):
        assert model == "text-embedding-004"
        assert config == {"task_type": "RETRIEVAL_DOCUMENT"}
        return MockResponse(len(contents), 0.1)

    mock_client.models.embed_content.side_effect = side_effect

    res = embeddings_batch(mock_client, texts, batch_size=100)
    assert len(res) == 150
    assert mock_client.models.embed_content.call_count == 2
    assert all(r is not None and len(r) == 768 for r in res)


def test_embeddings_batch_fallback_on_error():
    """Verify generate_embeddings_batch falls back gracefully if batch call raises."""
    mock_client = MagicMock()

    class MockSingle:
        embeddings = [MagicMock(values=[0.5] * 768)]

    # Fail on batch (list of texts), succeed on single text
    def side_effect(model, contents, config=None):
        if isinstance(contents, list):
            raise RuntimeError("Batch unsupported by endpoint")
        return MockSingle()

    mock_client.models.embed_content.side_effect = side_effect

    texts = ["Msg 1", "Msg 2"]
    res = embeddings_batch(mock_client, texts, batch_size=100)
    assert len(res) == 2
    assert all(r is not None and len(r) == 768 for r in res)


def test_save_messages_full_indexing_no_truncation():
    """Verify save_messages processes messages beyond 200 without [:200] slicing."""
    messages = [
        {
            "platform": "telegram",
            "chat_name": "FullChat",
            "sender": f"User{i}",
            "timestamp": f"2026-11-14T12:{i % 60:02d}:00",
            "text": f"Valid text content {i}",
        }
        for i in range(250)
    ]

    mock_genai = MagicMock()
    mock_client = MagicMock()

    class MockEmbedding:
        values = [0.1] * 768

    class MockResponse:
        def __init__(self, count: int):
            self.embeddings = [MockEmbedding() for _ in range(count)]

    mock_client.models.embed_content.side_effect = lambda model, contents, config=None: (
        MockResponse(len(contents))
    )
    mock_genai.Client.return_value = mock_client

    import asyncio

    # Patch AsyncSessionLocal to commit into a mock session
    mock_session = MagicMock()
    mock_session.execute = MagicMock(return_value=None)
    mock_session.commit = MagicMock(return_value=None)

    class DummyContext:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with (
        patch("celery_worker.AsyncSessionLocal", return_value=DummyContext()),
        patch("celery_worker.genai", mock_genai),
        patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}),
    ):
        asyncio.run(save_messages(messages))

        # Verify all 250 messages received embeddings (previously truncated at 200)
        assert len(messages) == 250
        embedded_count = sum(1 for m in messages if "embedding" in m and m["embedding"] is not None)
        assert embedded_count == 250


def test_backfill_embeddings_sync(sqlite_session_factory):
    """Verify backfill_embeddings_sync finds unembedded messages and commits in batches."""
    with sqlite_session_factory() as session:
        for i in range(1, 15):
            session.add(
                Message(
                    id=i,
                    platform="telegram",
                    chat_name="UnembeddedChat",
                    sender="Student",
                    timestamp=f"2026-11-14T09:{i:02d}:00",
                    text=f"Lecture notes {i}",
                    content_hash=f"unemb_{i}",
                    embedding=None,
                )
            )
        session.commit()

        mock_genai = MagicMock()
        mock_client = MagicMock()

        class MockEmbedding:
            values = [0.42] * 768

        class MockResponse:
            def __init__(self, count: int):
                self.embeddings = [MockEmbedding() for _ in range(count)]

        mock_client.models.embed_content.side_effect = lambda model, contents, config=None: (
            MockResponse(len(contents))
        )
        mock_genai.Client.return_value = mock_client

        class DummyContext:
            async def __aenter__(self):
                return session

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        import asyncio

        with (
            patch("celery_worker.AsyncSessionLocal", return_value=DummyContext()),
            patch("celery_worker.genai", mock_genai),
            patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}),
        ):
            report = asyncio.run(
                backfill_embeddings_sync(chat_id="UnembeddedChat", batch_size=5, limit=50)
            )
            assert report["status"] == "done"
            assert report["updated"] == 14
            assert report["total_candidates"] == 14

            # Verify messages in DB now have embeddings
            res = session.execute(select(Message).where(Message.chat_name == "UnembeddedChat"))
            all_msgs = list(res.scalars().all())
            assert len(all_msgs) == 14
            assert all(m.embedding is not None for m in all_msgs)


def test_hybrid_retrieve_messages_with_window_expansion(sqlite_session_factory):
    """Verify hybrid_retrieve_messages combines sparse/dense results with [M-2, M+2] context."""
    with sqlite_session_factory() as session:
        for i in range(1, 11):
            session.add(
                Message(
                    id=i,
                    platform="telegram",
                    chat_name="ExamGroup",
                    sender="Professor",
                    timestamp=f"2026-11-14T08:{i:02d}:00",
                    text="Important announcement: Midterm exam schedule released"
                    if i == 5
                    else f"Discussion message {i}",
                    content_hash=f"exam_{i}",
                )
            )
        session.commit()

        import asyncio

        # Search for "Midterm exam" which matches message id=5
        results = asyncio.run(
            hybrid_retrieve_messages(
                db=session,
                chat_name="ExamGroup",
                query_text="Midterm exam",
                query_embedding=None,
                limit=10,
                window_size=2,
                expand_window=True,
            )
        )

        res_ids = [m.id for m in results]
        # Should return context window [3, 4, 5, 6, 7] around hit M=5
        assert 5 in res_ids
        assert res_ids == [3, 4, 5, 6, 7]
