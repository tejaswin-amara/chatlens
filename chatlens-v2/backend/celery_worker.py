import asyncio
import hashlib
import os

try:
    from google import genai
except ImportError:
    genai = None  # type: ignore

try:
    from celery import Celery

    redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    celery_app = Celery("chatlens", broker=redis_url)
except ImportError:

    class DummyCelery:
        def task(self, *args, **kwargs):
            def decorator(fn):
                fn.delay = fn
                return fn

            return decorator

    celery_app = DummyCelery()


def generate_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    """Generate 768-dim embeddings via Google GenAI for a list of texts."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return [None] * len(texts)
    try:
        client = genai.Client(api_key=api_key)
        res = client.models.embed_content(
            model="text-embedding-004",
            contents=texts,
        )
        if hasattr(res, "embeddings") and res.embeddings:
            return [e.values for e in res.embeddings]
    except Exception:
        pass
    return [None] * len(texts)


async def save_messages(messages: list[dict]):
    if not messages:
        return
    async with AsyncSessionLocal() as session:
        for msg in messages:
            msg_str = (
                f"{msg.get('platform', '')}|{msg.get('chat_name', '')}|"
                f"{msg.get('sender', '')}|{msg.get('timestamp', '')}|{msg.get('text', '')}"
            )
            msg["content_hash"] = hashlib.sha256(msg_str.encode("utf-8")).hexdigest()

        # Batch embed up to first 200 non-empty messages to enrich vector search without hitting quota
        embed_candidates = [m for m in messages[:200] if m.get("text", "").strip()]
        if embed_candidates:
            texts = [m["text"][:500] for m in embed_candidates]
            embeddings = generate_embeddings_batch(texts)
            for m, emb in zip(embed_candidates, embeddings, strict=False):
                if emb is not None:
                    m["embedding"] = emb

        chunk_size = 1000
        for i in range(0, len(messages), chunk_size):
            chunk = messages[i : i + chunk_size]
            stmt = (
                insert(Message)
                .values(chunk)
                .on_conflict_do_nothing(index_elements=["content_hash"])
            )
            await session.execute(stmt)
        await session.commit()


def parse_and_save_sync(file_path: str, platform: str) -> dict:
    """Synchronous parsing and DB commit fallback when Celery/Redis is not running."""
    try:
        messages = []
        if platform == "whatsapp":
            messages = parse_whatsapp_export(file_path)
        elif platform == "telegram":
            messages = parse_telegram_export(file_path)

        if messages:
            asyncio.run(save_messages(messages))

        return {"status": "done", "count": len(messages)}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass


@celery_app.task(bind=True)
def parse_file_task(self, file_path: str, platform: str):
    """Celery background worker task for chat parsing."""
    try:
        self.update_state(
            state="PROGRESS", meta={"current": 0, "total": 0, "status": "Parsing file"}
        )
    except Exception:
        pass
    return parse_and_save_sync(file_path, platform)
