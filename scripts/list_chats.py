#!/usr/bin/env python3
import asyncio

from telethon import TelegramClient

from src.config import settings


async def main():
    client = TelegramClient(
        "chatlens_session",
        settings.telegram_api_id,
        settings.telegram_api_hash
    )
    if settings.telegram_session_string:
        from telethon.sessions import StringSession
        client = TelegramClient(
            StringSession(settings.telegram_session_string),
            settings.telegram_api_id,
            settings.telegram_api_hash
        )

    await client.start()
    async for dialog in client.iter_dialogs():
        print(f"{dialog.id}\t{dialog.name}")

if __name__ == "__main__":
    asyncio.run(main())
