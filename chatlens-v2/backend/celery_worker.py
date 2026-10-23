import asyncio
import hashlib
import logging
import os
from typing import Any

from database import AsyncSessionLocal
from embeddings import generate_embedding
from models import Message
from parsers.telegram import parse_telegram_export
from parsers.whatsapp import parse_whatsapp_export
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

try:
    from google import genai
except ImportError:
    genai = None  # type: ignore

try:
    from celery import Celery

    redis_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL", "redis://localhost:6379/0")
    backend_url = os.getenv("CELERY_RESULT_BACKEND") or redis_url
    celery_app = Celery("chatlens", broker=redis_url, backend=backend_url)
except ImportError:

    class DummyCelery:
        def task(self, *args: Any, **kwargs: Any) -> Any:
            def decorator(fn: Any) -> Any:
                fn.delay = fn
                return fn

            return decorator

    celery_app = DummyCelery()  # type: ignore

logger = logging.getLogger(__name__)


def generate_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    """Generate vector embeddings for a list of texts via Google GenAI."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return [None] * len(texts)
    try:
        client = genai.Client(api_key=api_key)
        return [
            generate_embedding(
                client,
                t,
                task_type="RETRIEVAL_DOCUMENT",
                model="gemini-embedding-001",
            )
            for t in texts
        ]
    except Exception:
        return [None] * len(texts)


async def save_messages(messages: list[dict[str, Any]]) -> None:
    """Save imported messages with content hash deduplication and embeddings."""
    if not messages:
        return
    async with AsyncSessionLocal() as session:
        for msg in messages:
            msg_str = (
                f"{msg.get('platform', '')}|{msg.get('chat_name', '')}|"
                f"{msg.get('sender', '')}|{msg.get('timestamp', '')}|{msg.get('text', '')}"
            )
            msg["content_hash"] = hashlib.sha256(msg_str.encode("utf-8")).hexdigest()

        # Batch embed up to first 200 non-empty messages to enrich vector search
        # without hitting API quota
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and genai is not None:
            try:
                client = genai.Client(api_key=api_key)
                embed_candidates = [m for m in messages[:200] if m.get("text", "").strip()]
                for m in embed_candidates:
                    emb = generate_embedding(
                        client,
                        m["text"][:500],
                        task_type="RETRIEVAL_DOCUMENT",
                        model="gemini-embedding-001",
                    )
                    if emb is not None:
                        m["embedding"] = emb
            except Exception as exc:
                logger.debug(f"Batch embedding skipped: {exc}")

        bind = session.bind or getattr(session, "_bind", None)
        is_sqlite = False
        if bind is not None and hasattr(bind, "dialect"):
            is_sqlite = bind.dialect.name == "sqlite"

        chunk_size = 1000
        for i in range(0, len(messages), chunk_size):
            chunk = messages[i : i + chunk_size]
            stmt: Any
            if is_sqlite:
                stmt = (
                    sqlite_insert(Message)
                    .values(chunk)
                    .on_conflict_do_nothing(index_elements=["content_hash"])
                )
            else:
                stmt = (
                    pg_insert(Message)
                    .values(chunk)
                    .on_conflict_do_nothing(index_elements=["content_hash"])
                )
            await session.execute(stmt)
        await session.commit()


def parse_and_save_sync(file_path: str, platform: str) -> dict[str, Any]:
    """Synchronous parsing and DB commit fallback when Celery/Redis is not running."""
    try:
        messages: list[dict[str, Any]] = []
        import tempfile
        import zipfile
        from pathlib import Path

        if zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, "r") as z:
                # Security check: verify no path traversal
                for info in z.infolist():
                    if os.path.isabs(info.filename) or ".." in Path(info.filename).parts:
                        return {"status": "error", "error": "Zip contains unsafe path traversal"}

                namelist = [
                    n
                    for n in z.namelist()
                    if not n.startswith("__MACOSX")
                    and (n.lower().endswith(".txt") or n.lower().endswith(".json"))
                ]
                if not namelist:
                    return {"status": "done", "count": 0}

                with tempfile.TemporaryDirectory() as tmpdir:
                    for n in namelist:
                        extracted = z.extract(n, path=tmpdir)
                        if n.lower().endswith(".json"):
                            messages.extend(parse_telegram_export(extracted))
                        else:
                            messages.extend(parse_whatsapp_export(extracted))
        elif platform == "whatsapp":
            messages = parse_whatsapp_export(file_path)
        elif platform == "telegram":
            messages = parse_telegram_export(file_path)

        if messages:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(asyncio.run, save_messages(messages)).result()
            else:
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
def parse_file_task(self: Any, file_path: str, platform: str) -> dict[str, Any]:
    """Celery background worker task for chat parsing."""
    try:
        self.update_state(
            state="PROGRESS", meta={"current": 0, "total": 0, "status": "Parsing file"}
        )
    except Exception as exc:
        logger.debug(f"Task progress update failed: {exc}")
    return parse_and_save_sync(file_path, platform)
