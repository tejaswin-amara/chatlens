"""Tests for KnowledgeRetriever and Turbovec semantic indexing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.knowledge.retriever import KnowledgeRetriever

try:
    import turbovec
except ImportError:
    turbovec = None


def test_retriever_load_chunks():
    """Verify chunks are loaded from academic intelligence fixture."""
    retriever = KnowledgeRetriever()
    assert len(retriever.chunks) > 0
    # Should include both exams and lab experiments
    has_exam = any("EXAM / DEFENCE SCHEDULE" in c for c in retriever.chunks)
    has_lab = any("LAB EXPERIMENT" in c for c in retriever.chunks)
    assert has_exam
    assert has_lab


def test_retriever_lexical_search():
    """Verify lexical token matching with course code expansion and keyword scoring."""
    retriever = KnowledgeRetriever()

    # Search for ESD
    res_esd = retriever.search("esd lab in-sem", top_k=2)
    assert len(res_esd) > 0
    assert any("25EC2206E" in r or "ESD" in r for r in res_esd)

    # Search for Viva Questions
    res_viva = retriever.search("thermistor viva", top_k=2)
    assert len(res_viva) > 0
    assert any("LAB EXPERIMENT" in r or "Viva" in r for r in res_viva)


@pytest.mark.skipif(turbovec is None, reason="turbovec not installed")
def test_retriever_turbovec_cache_persistence_roundtrip(tmp_path):
    """Verify Turbovec index can be built, saved to .tv cache, and reloaded."""
    cache_file = tmp_path / "test_intel.tv"
    retriever = KnowledgeRetriever(cache_path=cache_file)
    assert retriever.index is None

    # Manually create dummy embeddings
    n_chunks = len(retriever.chunks)
    dim = 3072
    dummy_vectors = np.ones((n_chunks, dim), dtype=np.float32)

    # Build Turbovec index
    retriever.index = turbovec.TurboQuantIndex(dim=dim, bit_width=4)
    retriever.index.add(dummy_vectors)
    retriever.index.sync(str(cache_file))

    assert cache_file.exists()

    # Now reload in a new retriever instance
    new_retriever = KnowledgeRetriever(cache_path=cache_file)
    assert new_retriever.index is not None
    assert len(new_retriever.index) == n_chunks


def test_retriever_answer_generation():
    """Verify answer generation with mock Gemini client."""
    retriever = KnowledgeRetriever()

    mock_resp = MagicMock()
    mock_resp.text = "The ESD In-Sem exam is in Room 103."

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch.object(retriever, "_get_client", return_value=mock_client):
        ans = retriever.answer("Where is the ESD exam?")
        assert "ESD In-Sem exam is in Room 103" in ans
