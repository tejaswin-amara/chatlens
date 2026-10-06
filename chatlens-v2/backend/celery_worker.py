import asyncio
import os

from celery import Celery
from database import AsyncSessionLocal
from models import Message
from parsers.telegram import parse_telegram_export
from parsers.whatsapp import parse_whatsapp_export

redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery_app = Celery("chatlens", broker=redis_url)


async def save_messages(messages: list[dict]):
    if not messages:
        return
    async with AsyncSessionLocal() as session:
        import hashlib

        from sqlalchemy.dialects.postgresql import insert

        for msg in messages:
            msg_str = f"{msg.get('platform', '')}|{msg.get('chat_name', '')}|{msg.get('sender', '')}|{msg.get('timestamp', '')}|{msg.get('text', '')}"
            msg["content_hash"] = hashlib.sha256(msg_str.encode("utf-8")).hexdigest()

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


@celery_app.task
def parse_file_task(file_path: str, platform: str):
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
