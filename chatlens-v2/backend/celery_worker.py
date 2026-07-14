import os
import asyncio
from celery import Celery
from parsers.whatsapp import parse_whatsapp_export
from parsers.telegram import parse_telegram_export
from database import AsyncSessionLocal
from models import Message

redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery_app = Celery("chatlens", broker=redis_url)

async def save_messages(messages: list[dict]):
    if not messages:
        return
    async with AsyncSessionLocal() as session:
        # bulk insert
        db_messages = [Message(**msg) for msg in messages]
        session.add_all(db_messages)
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
