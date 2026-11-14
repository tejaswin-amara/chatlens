"""Core AI retrieval algorithms and hybrid search services for ChatLens v2.

Implements:
1. Reciprocal Rank Fusion (RRF) combining dense vector search (pgvector) and sparse
   lexical search (PostgreSQL tsvector / full-text search).
2. Context Window Expansion ([M - 2, M + 2]) preserving chronological conversation context.
3. Fallback compatibility across PostgreSQL/pgvector and SQLite test environments.
"""

import inspect
import logging
import math
import re
from typing import Any

from models import Message
from sqlalchemy import func, or_, select

logger = logging.getLogger(__name__)


def _escape_like(text: str) -> str:
    """Escape special LIKE pattern characters (% and _) for SQL queries."""
    return text.replace("%", "\\%").replace("_", "\\_")


def _to_int_id(val: Any) -> int | None:
    """Extract integer ID from integer, Row, tuple, or string."""
    if val is None:
        return None
    if hasattr(val, "__getitem__") and not isinstance(val, (str, bytes)):
        try:
            return int(val[0])
        except (IndexError, TypeError, ValueError):
            pass
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def reciprocal_rank_fusion(
    dense_or_lists: list[Any] | list[list[Any]],
    sparse_ids: list[Any] | None = None,
    k: int = 60,
) -> list[int]:
    """Combine ranked lists of candidate IDs using Reciprocal Rank Fusion (RRF).

    Formula:
        RRF_score(d) = sum_{L in lists} ( 1 / (k + rank_L(d)) )
    where rank_L starts at 1.

    Args:
        dense_or_lists: Either a single list of dense candidate IDs or a list of ranked lists.
        sparse_ids: Optional second list of sparse candidate IDs if two lists are passed directly.
        k: Smoothing constant (default 60, as established by Cormack et al.).

    Returns:
        Deduplicated list of candidate IDs ordered by descending RRF score.
    """
    ranked_lists: list[list[int]] = []
    if sparse_ids is not None:
        if isinstance(dense_or_lists, list):
            dense_clean = [_to_int_id(x) for x in dense_or_lists]
            ranked_lists.append([x for x in dense_clean if x is not None])
        sparse_clean = [_to_int_id(x) for x in sparse_ids]
        ranked_lists.append([x for x in sparse_clean if x is not None])
    elif isinstance(dense_or_lists, list) and dense_or_lists:
        if isinstance(dense_or_lists[0], list):
            for sub in dense_or_lists:
                sub_clean = [_to_int_id(x) for x in sub]  # type: ignore
                ranked_lists.append([x for x in sub_clean if x is not None])
        else:
            single_clean = [_to_int_id(x) for x in dense_or_lists]
            ranked_lists.append([x for x in single_clean if x is not None])

    scores: dict[int, float] = {}
    for r_list in ranked_lists:
        for rank_idx, item_id in enumerate(r_list, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + (1.0 / (k + rank_idx))

    # Sort descending by RRF score; tie-break deterministically by ID ascending
    sorted_items = sorted(scores.items(), key=lambda entry: (-entry[1], entry[0]))
    return [item[0] for item in sorted_items]


async def expand_context_window(
    db: Any,
    hit_ids: list[Any],
    chat_name: str | None = None,
    window_size: int = 2,
) -> list[Message]:
    """Expand retrieved message hits with surrounding chronological context [M - 2, M + 2].

    Args:
        db: SQLAlchemy AsyncSession or sync Session.
        hit_ids: Sequence of retrieved message IDs.
        chat_name: Optional chat_name boundary filter.
        window_size: Number of messages before and after each hit (default 2 for [M-2, M+2]).

    Returns:
        Chronologically ordered messages containing both hits and their context window.
    """
    clean_hits = [_to_int_id(x) for x in hit_ids]
    valid_hits = [x for x in clean_hits if x is not None and x > 0]
    if not valid_hits:
        return []

    target_ids = {
        cid
        for m_id in valid_hits
        for cid in range(m_id - window_size, m_id + window_size + 1)
        if cid > 0
    }
    if not target_ids:
        return []

    stmt = select(Message).where(Message.id.in_(target_ids))
    if chat_name:
        stmt = stmt.where(Message.chat_name == chat_name)
    stmt = stmt.order_by(Message.timestamp.asc(), Message.id.asc())

    exec_res = db.execute(stmt)
    result = await exec_res if inspect.isawaitable(exec_res) else exec_res
    return list(result.scalars().all())


def _cosine_distance(v1: list[float], v2: list[float]) -> float:
    """Compute cosine distance between two float vectors (1.0 - cosine_similarity)."""
    if len(v1) != len(v2) or not v1:
        return 1.0
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 1.0
    sim = dot / (norm1 * norm2)
    return max(0.0, 1.0 - sim)


async def hybrid_retrieve_messages(
    db: Any,
    chat_name: str | None = None,
    query_text: str | None = None,
    query_embedding: list[float] | None = None,
    limit: int = 50,
    window_size: int = 2,
    expand_window: bool = True,
    k: int = 60,
) -> list[Message]:
    """Retrieve relevant messages using Hybrid RRF (dense pgvector + sparse tsvector)
    with [M - 2, M + 2] context window expansion.

    Args:
        db: Database session (AsyncSession or Session).
        chat_name: Optional chat filter.
        query_text: Natural language user question / query string.
        query_embedding: Dense embedding vector for query_text.
        limit: Max top hits to retrieve before context expansion.
        window_size: Window delta for expansion (default 2).
        expand_window: Whether to expand [M-2, M+2] around retrieved hits.
        k: RRF smoothing constant.

    Returns:
        List of relevant Message objects ordered chronologically.
    """
    bind = getattr(db, "bind", None)
    if bind is None and hasattr(db, "get_bind"):
        try:
            bind = db.get_bind()
        except Exception:
            bind = None

    is_postgres = False
    if bind is not None and hasattr(bind, "dialect"):
        is_postgres = getattr(bind.dialect, "name", "") == "postgresql"

    dense_ids: list[int] = []
    sparse_ids: list[int] = []

    # 1. Dense Semantic Retrieval
    if query_embedding is not None:
        try:
            if is_postgres:
                dense_pg_stmt: Any = select(Message.id).where(Message.embedding.isnot(None))
                if chat_name:
                    dense_pg_stmt = dense_pg_stmt.where(Message.chat_name == chat_name)
                dense_pg_stmt = dense_pg_stmt.order_by(
                    Message.embedding.cosine_distance(query_embedding).asc()
                ).limit(limit)
                exec_dense = db.execute(dense_pg_stmt)
                res_dense = await exec_dense if inspect.isawaitable(exec_dense) else exec_dense
                d_ids: list[int] = []
                for r in res_dense.all():
                    val = _to_int_id(r)
                    if val is not None:
                        d_ids.append(val)
                dense_ids = d_ids
            else:
                # In-memory / SQLite fallback: fetch messages and compute cosine distance
                dense_fallback_stmt: Any = select(Message.id, Message.embedding).where(
                    Message.embedding.isnot(None)
                )
                if chat_name:
                    dense_fallback_stmt = dense_fallback_stmt.where(Message.chat_name == chat_name)
                exec_dense = db.execute(dense_fallback_stmt)
                res_dense = await exec_dense if inspect.isawaitable(exec_dense) else exec_dense
                candidates = res_dense.all()
                scored_candidates: list[tuple[int, float]] = []
                for row in candidates:
                    cid = _to_int_id(row[0])
                    emb = row[1]
                    if cid is not None and emb is not None:
                        emb_vals = (
                            emb if isinstance(emb, list) else getattr(emb, "tolist", lambda: [])()
                        )
                        dist = _cosine_distance(query_embedding, emb_vals)
                        scored_candidates.append((cid, dist))
                scored_candidates.sort(key=lambda x: x[1])
                dense_ids = [c[0] for c in scored_candidates[:limit]]
        except Exception as exc:
            logger.debug(f"Dense vector retrieval failed: {exc}")

    # 2. Sparse Lexical Retrieval
    if query_text and query_text.strip():
        clean_text = query_text.strip()
        try:
            if is_postgres:
                ts_vec = func.to_tsvector("english", Message.text)
                ts_q = func.plainto_tsquery("english", clean_text)
                sparse_pg_stmt: Any = select(Message.id).where(ts_vec.op("@@")(ts_q))
                if chat_name:
                    sparse_pg_stmt = sparse_pg_stmt.where(Message.chat_name == chat_name)
                sparse_pg_stmt = sparse_pg_stmt.order_by(
                    func.ts_rank_cd(ts_vec, ts_q).desc()
                ).limit(limit)
                exec_sparse = db.execute(sparse_pg_stmt)
                res_sparse = await exec_sparse if inspect.isawaitable(exec_sparse) else exec_sparse
                s_ids: list[int] = []
                for r in res_sparse.all():
                    val = _to_int_id(r)
                    if val is not None:
                        s_ids.append(val)
                sparse_ids = s_ids
            else:
                # SQLite / non-PostgreSQL lexical fallback
                words = [w for w in re.findall(r"\w+", clean_text) if len(w) > 1]
                sparse_fallback_stmt: Any = select(Message.id).where(Message.text.isnot(None))
                if chat_name:
                    sparse_fallback_stmt = sparse_fallback_stmt.where(
                        Message.chat_name == chat_name
                    )
                if words:
                    conditions = [Message.text.ilike(f"%{_escape_like(w)}%") for w in words[:6]]
                    sparse_fallback_stmt = sparse_fallback_stmt.where(or_(*conditions))
                sparse_fallback_stmt = sparse_fallback_stmt.order_by(
                    Message.timestamp.desc(), Message.id.desc()
                ).limit(limit)
                exec_sparse = db.execute(sparse_fallback_stmt)
                res_sparse = await exec_sparse if inspect.isawaitable(exec_sparse) else exec_sparse
                s_ids2: list[int] = []
                for r in res_sparse.all():
                    val = _to_int_id(r)
                    if val is not None:
                        s_ids2.append(val)
                sparse_ids = s_ids2
        except Exception as exc:
            logger.debug(f"Sparse lexical retrieval failed: {exc}")

    # 3. Reciprocal Rank Fusion (RRF)
    fused_ids: list[int] = []
    if dense_ids or sparse_ids:
        fused_ids = reciprocal_rank_fusion(dense_ids, sparse_ids, k=k)

    # 4. Fallback if no dense/sparse hits found
    if not fused_ids:
        fallback_stmt: Any = select(Message.id)
        if chat_name:
            fallback_stmt = fallback_stmt.where(Message.chat_name == chat_name)
        fallback_stmt = fallback_stmt.order_by(Message.timestamp.desc(), Message.id.desc()).limit(
            limit
        )
        exec_fb = db.execute(fallback_stmt)
        res_fb = await exec_fb if inspect.isawaitable(exec_fb) else exec_fb
        fb_ids: list[int] = []
        for r in res_fb.all():
            val = _to_int_id(r)
            if val is not None:
                fb_ids.append(val)
        fused_ids = fb_ids

    top_ids = fused_ids[:limit]
    if not top_ids:
        return []

    # 5. Context Window Expansion ([M-2, M+2]) or Direct Message Fetch
    if expand_window:
        expanded_messages = await expand_context_window(
            db, top_ids, chat_name=chat_name, window_size=window_size
        )
        if expanded_messages:
            return expanded_messages

    # Direct fetch without window expansion
    fetch_stmt = select(Message).where(Message.id.in_(top_ids))
    if chat_name:
        fetch_stmt = fetch_stmt.where(Message.chat_name == chat_name)
    fetch_stmt = fetch_stmt.order_by(Message.timestamp.asc(), Message.id.asc())
    exec_fetch = db.execute(fetch_stmt)
    res_fetch = await exec_fetch if inspect.isawaitable(exec_fetch) else exec_fetch
    return list(res_fetch.scalars().all())
