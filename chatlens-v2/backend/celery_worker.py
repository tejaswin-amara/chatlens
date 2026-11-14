import asyncio
import hashlib
import inspect
import logging
import os
from typing import Any

from database import AsyncSessionLocal
from embeddings import generate_embeddings_batch as gen_batch
from models import Message
from parsers.telegram import parse_telegram_export
from parsers.whatsapp import parse_whatsapp_export
from sqlalchemy import select
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


def generate_embeddings_batch(
    texts: list[str],
    *,
    batch_size: int = 100,
    model: str = "text-embedding-004",
) -> list[list[float] | None]:
    """Generate vector embeddings for a list of texts via Google GenAI with batching."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return [None] * len(texts)
    try:
        client = genai.Client(api_key=api_key)
        return gen_batch(
            client,
            texts,
            task_type="RETRIEVAL_DOCUMENT",
            model=model,
            batch_size=batch_size,
        )
    except Exception as exc:
        logger.debug(f"Batch embedding failed: {exc}")
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

        # Batch embed all non-empty messages to enrich vector search without truncation
        # using Gemini text-embedding-004 batched up to 100 texts per request
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and genai is not None:
            try:
                client = genai.Client(api_key=api_key)
                embed_candidates = [
                    m for m in messages if isinstance(m.get("text"), str) and m["text"].strip()
                ]
                batch_size = 100
                for i in range(0, len(embed_candidates), batch_size):
                    chunk = embed_candidates[i : i + batch_size]
                    chunk_texts = [m["text"][:1000] for m in chunk]
                    chunk_embs = gen_batch(
                        client,
                        chunk_texts,
                        task_type="RETRIEVAL_DOCUMENT",
                        model="text-embedding-004",
                        batch_size=batch_size,
                    )
                    for m, emb in zip(chunk, chunk_embs, strict=False):
                        if emb is not None:
                            m["embedding"] = emb
            except Exception as exc:
                logger.debug(f"Batch embedding skipped: {exc}")

        is_sqlite = False
        bind = getattr(session, "bind", None)
        if bind is None and hasattr(session, "get_bind"):
            try:
                bind = session.get_bind()
            except Exception as exc:
                logger.debug(f"session.get_bind check failed: {exc}")
                bind = None
        if bind is not None and hasattr(bind, "dialect"):
            is_sqlite = getattr(bind.dialect, "name", "") == "sqlite"
        if not is_sqlite:
            try:
                from database import DATABASE_URL, engine

                if hasattr(engine, "dialect") and getattr(engine.dialect, "name", "") == "sqlite":
                    is_sqlite = True
                elif "sqlite" in str(DATABASE_URL).lower():
                    is_sqlite = True
            except Exception as exc:
                logger.debug(f"Dialect fallback check failed: {exc}")

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
            exec_stmt = session.execute(stmt)
            if inspect.isawaitable(exec_stmt):
                await exec_stmt
        commit_res = session.commit()
        if inspect.isawaitable(commit_res):
            await commit_res


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


def run_system_diagnostics_sync(
    use_ai: bool = False, auto_remediate: bool = False
) -> dict[str, Any]:
    """Execute system diagnostics and optional safe auto-remediations synchronously."""
    from diagnostics import DiagnosticsService

    service = DiagnosticsService()

    async def _run_with_db(session: Any) -> dict[str, Any]:
        report = await service.run_diagnostics(
            session=session, use_ai=use_ai, deep_consistency=True
        )
        if auto_remediate and report.get("root_causes"):
            results = []
            for rc in report.get("root_causes", []):
                action = rc.get("recommended_action")
                if action in {"REQUEUE_STALLED_PENDING", "PRUNE_STALE_OVERRIDES"}:
                    res = await service.execute_remediation(action=action, db=session)
                    results.append(res)
            report["auto_remediation_results"] = results
        return report

    async def _runner() -> dict[str, Any]:
        try:
            async with AsyncSessionLocal() as session:
                return await _run_with_db(session)
        except Exception:
            return await _run_with_db(None)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, _runner()).result()
    else:
        return asyncio.run(_runner())


@celery_app.task(bind=True)
def run_system_diagnostics_task(
    self: Any, use_ai: bool = False, auto_remediate: bool = False
) -> dict[str, Any]:
    """Celery background worker task for system diagnostics and auto-remediation."""
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Running system diagnostics"},
        )
    except Exception as exc:
        logger.debug(f"Task progress update failed: {exc}")
    return run_system_diagnostics_sync(use_ai=use_ai, auto_remediate=auto_remediate)


async def backfill_embeddings_sync(
    chat_id: str | None = None,
    batch_size: int = 100,
    limit: int = 1000,
) -> dict[str, Any]:
    """Asynchronously backfill vector embeddings for messages without embeddings."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return {
            "status": "skipped",
            "reason": "No GEMINI_API_KEY or genai library",
            "updated": 0,
            "total_candidates": 0,
        }

    client = genai.Client(api_key=api_key)
    updated_count = 0

    async with AsyncSessionLocal() as session:
        stmt = (
            select(Message)
            .where(Message.embedding.is_(None))
            .where(Message.text.isnot(None))
            .where(Message.text != "")
        )
        if chat_id:
            stmt = stmt.where(Message.chat_name == chat_id)
        stmt = stmt.order_by(Message.id.asc()).limit(limit)

        exec_res = session.execute(stmt)
        res = await exec_res if inspect.isawaitable(exec_res) else exec_res
        candidates = list(res.scalars().all())
        if not candidates:
            return {"status": "done", "updated": 0, "total_candidates": 0}

        for i in range(0, len(candidates), batch_size):
            chunk = candidates[i : i + batch_size]
            texts = [c.text[:1000] for c in chunk]
            embs = gen_batch(
                client,
                texts,
                task_type="RETRIEVAL_DOCUMENT",
                model="text-embedding-004",
                batch_size=batch_size,
            )
            for msg_item, emb in zip(chunk, embs, strict=False):
                if emb is not None:
                    msg_item.embedding = emb
                    updated_count += 1
            commit_res = session.commit()
            if inspect.isawaitable(commit_res):
                await commit_res

    return {"status": "done", "updated": updated_count, "total_candidates": len(candidates)}


def run_backfill_embeddings_sync(
    chat_id: str | None = None,
    batch_size: int = 100,
    limit: int = 1000,
) -> dict[str, Any]:
    """Synchronous executor for backfill_embeddings_sync."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                asyncio.run,
                backfill_embeddings_sync(chat_id=chat_id, batch_size=batch_size, limit=limit),
            ).result()
    else:
        return asyncio.run(
            backfill_embeddings_sync(chat_id=chat_id, batch_size=batch_size, limit=limit)
        )


@celery_app.task(bind=True)
def backfill_embeddings_task(
    self: Any,
    chat_id: str | None = None,
    batch_size: int = 100,
    limit: int = 1000,
) -> dict[str, Any]:
    """Celery background worker task for backfilling missing message vector embeddings."""
    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Backfilling embeddings", "chat_id": chat_id},
        )
    except Exception as exc:
        logger.debug(f"Task progress update failed: {exc}")
    return run_backfill_embeddings_sync(chat_id=chat_id, batch_size=batch_size, limit=limit)
