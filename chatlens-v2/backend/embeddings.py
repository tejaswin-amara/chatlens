"""Embeddings generation utility for ChatLens v2 semantic search."""

from typing import Any


def generate_embedding(
    client: Any,
    text: str,
    *,
    task_type: str = "RETRIEVAL_DOCUMENT",
    model: str = "gemini-embedding-001",
) -> list[float] | None:
    """Generate a vector embedding for a single text using Google GenAI client.

    Returns a list of float values if successful, or None if client is missing or call fails.
    """
    if client is None or not text or not text.strip():
        return None

    try:
        result = client.models.embed_content(
            model=model,
            contents=text,
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
    model: str = "gemini-embedding-001",
) -> list[list[float] | None]:
    """Generate vector embeddings for a batch of texts safely."""
    if client is None or not texts:
        return [None] * len(texts)

    results: list[list[float] | None] = []
    for text in texts:
        results.append(generate_embedding(client, text, model=model))
    return results
