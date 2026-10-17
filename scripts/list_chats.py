#!/usr/bin/env python3
import asyncio

from telethon import TelegramClient

from src.config import settings


async def main():
    api_hash = settings.telegram_api_hash.get_secret_value()
    session_str = settings.telegram_session_string.get_secret_value()

    if session_str:
        from telethon.sessions import StringSession

        client = TelegramClient(
            StringSession(session_str),
            settings.telegram_api_id,
            api_hash,
        )
    else:
        client = TelegramClient("chatlens_session", settings.telegram_api_id, api_hash)

    await client.start()
    async for dialog in client.iter_dialogs():
        print(f"{dialog.id}\t{dialog.name}")


if __name__ == "__main__":
    asyncio.run(main())
