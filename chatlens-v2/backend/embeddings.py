"""Embeddings generation utility for ChatLens v2 semantic search."""

from typing import Any


def generate_embedding(
    client: Any,
    text: str,
    *,
    task_type: str = "RETRIEVAL_DOCUMENT",
    model: str = "text-embedding-004",
) -> list[float] | None:
    """Generate a vector embedding for a single text using Google GenAI client.

    Returns a list of float values if successful, or None if client is missing or call fails.
    """
    if client is None or not text or not text.strip():
        return None

    try:
        config_dict = {"task_type": task_type} if task_type else None
        result = client.models.embed_content(
            model=model,
            contents=text,
            config=config_dict,
        )
        if hasattr(result, "embeddings") and result.embeddings:
            vals = result.embeddings[0].values
            return [float(v) for v in vals] if vals is not None else None
    except Exception:
        return None

    return None


def generate_embeddings_batch(
    client: Any,
    texts: list[str],
    *,
    task_type: str = "RETRIEVAL_DOCUMENT",
    model: str = "text-embedding-004",
    batch_size: int = 100,
) -> list[list[float] | None]:
    """Generate vector embeddings for a batch of texts safely.

    Batches up to 100 texts per API call into Gemini text-embedding-004,
    with fallback to per-item embedding if the batch call fails.
    """
    if client is None or not texts:
        return [None] * len(texts)

    all_results: list[list[float] | None] = []
    config_dict = {"task_type": task_type} if task_type else None

    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        chunk_results: list[list[float] | None] = [None] * len(chunk)

        # Identify non-empty candidates in chunk
        valid_indices = [idx for idx, t in enumerate(chunk) if t and t.strip()]
        if not valid_indices:
            all_results.extend(chunk_results)
            continue

        valid_texts = [chunk[idx] for idx in valid_indices]

        try:
            # Attempt multi-content batch request (up to 100 texts in one request)
            res = client.models.embed_content(
                model=model,
                contents=valid_texts,
                config=config_dict,
            )
            if hasattr(res, "embeddings") and res.embeddings:
                for sub_idx, emb in enumerate(res.embeddings):
                    orig_idx = valid_indices[sub_idx]
                    vals = getattr(emb, "values", None)
                    if vals is not None:
                        chunk_results[orig_idx] = [float(v) for v in vals]
            else:
                # If embeddings attribute is missing or empty, trigger per-item fallback
                raise ValueError("No embeddings returned in batch response")
        except Exception:
            # Fallback to item-by-item processing for this chunk
            for orig_idx in valid_indices:
                chunk_results[orig_idx] = generate_embedding(
                    client,
                    chunk[orig_idx],
                    task_type=task_type,
                    model=model,
                )

        all_results.extend(chunk_results)

    return all_results
