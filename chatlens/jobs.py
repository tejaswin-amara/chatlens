"""Helpers to enqueue background parsing jobs via ARQ/Redis."""

import asyncio

from arq import create_pool
from arq.connections import RedisSettings

from chatlens import config
from chatlens.storage import MessageStore

TASK_PARSE_WHATSAPP = "parse_whatsapp_export_job"
TASK_FETCH_TELEGRAM = "fetch_telegram_chats_job"


async def _enqueue(task_name: str, payload: dict, *args) -> str:
    store = MessageStore()
    job_id = store.create_job(task_name=task_name, payload=payload)
    redis = await create_pool(RedisSettings.from_dsn(config.REDIS_URL))
    try:
        await redis.enqueue_job(task_name, job_id, *args)
    except Exception as exc:
        store.update_job_status(job_id, "failed", error=str(exc))
        raise
    finally:
        await redis.aclose()
    return job_id


async def enqueue_parse_whatsapp_export(path: str) -> str:
    return await _enqueue(TASK_PARSE_WHATSAPP, {"path": path}, path)


async def enqueue_fetch_telegram_chats(chat_names: list[str] | None, limit: int) -> str:
    payload = {"chat_names": chat_names, "limit": limit}
    return await _enqueue(TASK_FETCH_TELEGRAM, payload, chat_names, limit)


def enqueue_parse_whatsapp_export_sync(path: str) -> str:
    return asyncio.run(enqueue_parse_whatsapp_export(path))


def enqueue_fetch_telegram_chats_sync(chat_names: list[str] | None, limit: int) -> str:
    return asyncio.run(enqueue_fetch_telegram_chats(chat_names, limit))
