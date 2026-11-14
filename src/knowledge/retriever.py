"""In-process semantic knowledge retriever powered by TurboVec and Gemini Embeddings.

Indexes academic intelligence, exam schedules, and lab viva preparation.
Uses TurboQuant 4-bit vector quantization for low-memory in-process search.
"""

from __future__ import annotations

import heapq
import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

import numpy as np

try:
    import turbovec  # type: ignore[import-untyped]
except ImportError:
    turbovec = None  # type: ignore

from google import genai

from src.config import settings
from src.knowledge.document_loader import document_loader
from src.utils.deduplication import deduplicator
from src.utils.logging import get_logger
from src.utils.redaction import redact_pii

logger = get_logger(__name__)

INTEL_PATH = Path("data/academic_intelligence.json")
INDEX_CACHE_PATH = Path("data/intel_index.tv")
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 3072


class ContiguousVectorBuffer:
    """Contiguous SIMD-friendly vector buffer with precomputed norms and top-k min-heap."""

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self.dim = dim
        self.vectors: np.ndarray = np.empty((0, dim), dtype=np.float32)
        self.norms: np.ndarray = np.empty((0, 1), dtype=np.float32)
        self.unit_vectors: np.ndarray = np.empty((0, dim), dtype=np.float32)

    def set_vectors(self, vectors: np.ndarray) -> None:
        if len(vectors) == 0:
            return
        self.vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.norms = np.ascontiguousarray(norms, dtype=np.float32)
        self.unit_vectors = np.ascontiguousarray(self.vectors / self.norms, dtype=np.float32)

    def search_top_k(self, query_vec: np.ndarray, k: int = 3) -> list[tuple[float, int]]:
        """Cosine similarity with precomputed norms and early-exit top-K min-heap."""
        if len(self.unit_vectors) == 0:
            return []
        q = np.ascontiguousarray(query_vec, dtype=np.float32).reshape(-1)
        q_norm = np.linalg.norm(q)
        if q_norm > 0:
            q = q / q_norm

        # SIMD dot product via OpenBLAS/MKL matrix-vector multiply
        scores = self.unit_vectors @ q

        if len(scores) <= k:
            return sorted([(float(scores[i]), i) for i in range(len(scores))], reverse=True)

        # Min-heap of size K for early-exit top-K pruning
        top_k_heap: list[tuple[float, int]] = []
        for i in range(k):
            top_k_heap.append((float(scores[i]), i))
        heapq.heapify(top_k_heap)

        for i in range(k, len(scores)):
            s = float(scores[i])
            if s > top_k_heap[0][0]:
                heapq.heapreplace(top_k_heap, (s, i))

        return sorted(top_k_heap, key=lambda x: x[0], reverse=True)


def _build_rag_prompt(context: str, safe_query: str) -> str:
    """Build the strict QUOTA-CONSERVE prompt for grounded RAG answers."""
    instructions = [
        "You are ChatLens Assistant, an intelligent academic personal assistant",
        "operating in strict QUOTA-CONSERVE mode.",
        "Instructions:",
        "1. Answer user questions directly, accurately, and naturally based strictly on the",
        "   provided context.",
        "2. If the answer is missing from the context, output exactly:",
        "   'Not found in your chats/documents.' Do not speculate.",
        "3. Skip pleasantries, greetings, and filler words. Maximum 2 to 3 sentences",
        "   or a compact bullet list.",
        "4. Use bold text for key entities (dates, course codes, rooms, names, deadlines).",
        "5. Append the exact source citation in brackets at the end:",
        "   [Chat: <Name>, <Date>] or [Doc: <Filename>].",
    ]
    return "\n".join(instructions) + f"\n\nContext:\n{context}\n\nUser Question: {safe_query}"


class KnowledgeRetriever:
    """In-process semantic knowledge engine using TurboVec and Gemini."""

    def __init__(self, cache_path: Path | None = None) -> None:
        self.chunks: list[str] = []
        self.index: Any = None
        self.vector_buffer = ContiguousVectorBuffer(dim=EMBEDDING_DIM)
        self._client: genai.Client | None = None
        self.cache_path = cache_path or INDEX_CACHE_PATH
        self._load_chunks()
        try:
            document_loader.index_all()
        except Exception as e:
            logger.debug(f"Document loader auto-index failed: {e}")
        self._load_cached_index()

    def _load_cached_index(self) -> None:
        """Attempt to load an existing Turbovec index from disk cache."""
        if turbovec is not None and self.cache_path.exists():
            try:
                self.index = turbovec.TurboQuantIndex.load(str(self.cache_path))
                if hasattr(self.index, "prepare"):
                    self.index.prepare()
                logger.info("Loaded cached TurboVec index", path=str(self.cache_path))
            except Exception as e:
                logger.warning("Failed to load cached TurboVec index", error=str(e))

    def _get_client(self) -> genai.Client | None:
        if not self._client:
            api_key = (
                settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None
            )
            if api_key:
                self._client = genai.Client(api_key=api_key)
        return self._client

    def _load_chunks(self) -> None:
        """Parse structured academic intelligence into searchable document chunks."""
        self.chunks.clear()
        if not INTEL_PATH.exists():
            return

        try:
            with open(INTEL_PATH, encoding="utf-8") as f:
                data = json.load(f)

            # 1. Exams and Defences
            for exam in data.get("exams", []):
                chunk = (
                    f"EXAM / DEFENCE SCHEDULE:\n"
                    f"Course: {exam.get('course')} ({exam.get('course_code')})\n"
                    f"Section: {exam.get('section')}\n"
                    f"Event: {exam.get('event')}\n"
                    f"Date: {exam.get('date')} Time: {exam.get('time')}\n"
                    f"Room: {exam.get('room')} Faculty: {exam.get('faculty')}\n"
                    f"Lab Technician: {exam.get('lab_technician') or 'None'}"
                )
                self.chunks.append(chunk)

            # 2. Lab Experiments & Viva Questions
            for exp in data.get("lab_experiments", []):
                viva_str = "\n".join(f"  - Viva: {q}" for q in exp.get("viva_questions", []))
                chunk = (
                    f"LAB EXPERIMENT {exp.get('id')}: {exp.get('title')}\n"
                    f"Task: {exp.get('task')}\n"
                    f"Viva Questions & Answers:\n{viva_str}"
                )
                self.chunks.append(chunk)
        except Exception as e:
            logger.warning("Failed to load academic intelligence chunks", error=str(e))

    def build_index(self) -> bool:
        """Build the in-memory TurboQuant 4-bit quantized vector index."""
        if not self.chunks or turbovec is None:
            return False

        client = self._get_client()
        if not client:
            return False

        try:
            embeddings_list = []
            for chunk in self.chunks:
                res = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=chunk,
                )
                if res.embeddings and len(res.embeddings) > 0 and res.embeddings[0].values:
                    embeddings_list.append(res.embeddings[0].values)

            if not embeddings_list:
                return False

            vectors = np.ascontiguousarray(embeddings_list, dtype=np.float32)
            self.vector_buffer.set_vectors(vectors)
            self.index = turbovec.TurboQuantIndex(dim=EMBEDDING_DIM, bit_width=4)
            self.index.add(vectors)
            if hasattr(self.index, "prepare"):
                self.index.prepare()
            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                self.index.sync(str(self.cache_path))
                logger.info("Persisted TurboVec index", path=str(self.cache_path))
            except Exception as e:
                logger.debug("Could not persist TurboVec index to disk", error=str(e))
            logger.info("Built TurboVec knowledge index", chunks=len(self.chunks))
            return True
        except Exception as e:
            logger.warning("Failed to build TurboVec index", error=str(e))
            return False

    def search(self, query: str, top_k: int = 3) -> list[str]:
        """Perform semantic search using TurboVec; falls back to lexical keyword matching."""
        if not self.chunks:
            return []

        # Try TurboVec vector search if index is ready
        if self.index is not None:
            client = self._get_client()
            if client:
                try:
                    res = client.models.embed_content(
                        model=EMBEDDING_MODEL,
                        contents=query,
                    )
                    if not res.embeddings or not res.embeddings[0].values:
                        return []
                    q_vec = np.ascontiguousarray([res.embeddings[0].values], dtype=np.float32)
                    _, indices = self.index.search(q_vec, k=min(top_k, len(self.chunks)))
                    matched = [
                        self.chunks[idx] for idx in indices[0] if 0 <= idx < len(self.chunks)
                    ]
                    if matched:
                        return matched
                except Exception as e:
                    logger.debug(
                        "TurboVec search error, falling back to keywords",
                        error=str(e),
                    )

        # Lexical fallback: word overlap with regex tokenization and min-heap top-K pruning
        import re

        raw_tokens = re.findall(r"\w+", query.lower())
        tokens = set(raw_tokens)
        if "s10" in tokens:
            tokens.add("s-10")
        if "s8" in tokens:
            tokens.add("s-8")
        if "dsa" in tokens or "dsa3" in tokens:
            tokens.update({"dsa", "dsa3", "25cs2103e"})
        if "ossp" in tokens:
            tokens.update({"ossp", "25cs2104e"})
        if "ml" in tokens:
            tokens.update({"ml", "25sc2107e"})
        if "esd" in tokens:
            tokens.update({"esd", "25ec2206e"})
        if "dbse" in tokens:
            tokens.update({"dbse", "25cs1302e"})
        if "japanese" in tokens:
            tokens.update({"japanese", "25fl2112e"})

        scored = []
        for chunk in self.chunks:
            chunk_lower = chunk.lower()
            # Score each matching token; give extra weight to exact sequence or keyword matches
            score = sum(2 if token in chunk_lower else 0 for token in tokens if len(token) > 2)
            if "project defence" in query.lower() and "project defence" in chunk_lower:
                score += 10
            if "lab in-sem" in query.lower() and "lab in-sem" in chunk_lower:
                score += 10
            if score > 0:
                scored.append((score, chunk))

        if not scored:
            return self.chunks[:top_k]

        # Early-exit top-K pruning with min-heap O(N log K)
        top_items = heapq.nlargest(top_k, scored, key=lambda x: x[0])
        return [c for _, c in top_items]

    def hybrid_retrieve_knowledge(self, query: str, top_k: int = 3) -> list[dict[str, str]]:
        """Unified hybrid search over document chunks and chat history."""
        results: list[dict[str, str]] = []
        seen_texts: set[str] = set()

        # 1. Search SQLite knowledge_docs
        try:
            doc_hits = deduplicator.search_knowledge_docs(query, limit=top_k)
            for d in doc_hits:
                txt = d.get("text", "").strip()
                if txt and txt not in seen_texts:
                    seen_texts.add(txt)
                    results.append({"text": txt, "source": d.get("source", "[Doc: unknown]")})
        except Exception as e:
            logger.debug(f"SQLite knowledge docs search error: {e}")

        # 2. Search SQLite chat_messages
        try:
            chat_hits = deduplicator.search_chat_messages(query, limit=top_k)
            for c in chat_hits:
                txt = c.get("text", "").strip()
                if txt and txt not in seen_texts:
                    seen_texts.add(txt)
                    results.append({"text": txt, "source": c.get("source", "[Chat: historical]")})
        except Exception as e:
            logger.debug(f"SQLite chat search error: {e}")

        # 3. Fallback to in-memory chunks
        if len(results) < top_k:
            mem_hits = self.search(query, top_k=top_k)
            for m in mem_hits:
                if m not in seen_texts:
                    seen_texts.add(m)
                    results.append({"text": m, "source": "[Doc: academic_intelligence.json]"})

        return results[:top_k]

    def answer_stream(self, query: str) -> Generator[str, None, None]:
        """Generate a streaming response via Gemini Interactions API for low TTFT."""
        safe_query = redact_pii(query)
        hits = self.hybrid_retrieve_knowledge(safe_query, top_k=3)
        if not hits:
            yield "Not found in your chats/documents."
            return

        context_blocks = [f"{h['text']}\nSource: {h['source']}" for h in hits]
        context = "\n\n---\n\n".join(context_blocks)

        client = self._get_client()
        if not client:
            yield f"{hits[0]['text']} {hits[0]['source']}"
            return

        prompt = _build_rag_prompt(context, safe_query)

        try:
            stream = client.models.generate_content_stream(
                model=settings.gemini_model,
                contents=prompt,
            )
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error("Failed to generate streaming answer from retriever", error=str(e))
            yield f"{hits[0]['text']} {hits[0]['source']}"

    def answer(self, query: str) -> str:
        """Generate a concise, grounded answer using Gemini and retrieved knowledge."""
        safe_query = redact_pii(query)
        hits = self.hybrid_retrieve_knowledge(safe_query, top_k=3)
        if not hits:
            return "Not found in your chats/documents."

        context_blocks = [f"{h['text']}\nSource: {h['source']}" for h in hits]
        context = "\n\n---\n\n".join(context_blocks)

        client = self._get_client()
        if not client:
            return f"**{hits[0]['text'].splitlines()[0]}** {hits[0]['source']}"

        prompt = _build_rag_prompt(context, safe_query)

        try:
            resp = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
            )
            return resp.text.strip() if resp.text else f"{hits[0]['text']} {hits[0]['source']}"
        except Exception as e:
            logger.error("Failed to generate answer from retriever", error=str(e))
            return f"{hits[0]['text']} {hits[0]['source']}"


knowledge_retriever = KnowledgeRetriever()
