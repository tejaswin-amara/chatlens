"""ARQ worker entrypoint for background parsing tasks."""

from arq.connections import RedisSettings

from chatlens import config
from chatlens.parsers.telegram_live import fetch_telegram_chats
from chatlens.parsers.whatsapp import parse_whatsapp_export
from chatlens.storage import MessageStore


async def parse_whatsapp_export_job(ctx, job_id: str, path: str) -> dict:
    store = MessageStore()
    store.update_job_status(job_id, "running")
    try:
        messages = parse_whatsapp_export(path)
        inserted = store.ingest(messages)
        result = {"parsed": len(messages), "ingested": inserted}
        store.update_job_status(job_id, "completed", result=result)
        return result
    except Exception as exc:
        store.update_job_status(job_id, "failed", error=str(exc))
        raise


async def fetch_telegram_chats_job(ctx, job_id: str, chat_names: list[str] | None, limit: int) -> dict:
    store = MessageStore()
    store.update_job_status(job_id, "running")
    try:
        messages = fetch_telegram_chats(chat_names=chat_names, limit=limit)
        inserted = store.ingest(messages)
        result = {"fetched": len(messages), "ingested": inserted}
        store.update_job_status(job_id, "completed", result=result)
        return result
    except Exception as exc:
        store.update_job_status(job_id, "failed", error=str(exc))
        raise


class WorkerSettings:
    functions = [parse_whatsapp_export_job, fetch_telegram_chats_job]
    redis_settings = RedisSettings.from_dsn(config.REDIS_URL)
