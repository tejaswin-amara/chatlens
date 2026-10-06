"""Live Telegram message fetcher via Telethon."""

import asyncio
from datetime import datetime

from telethon import TelegramClient
from telethon.tl.types import User

from chatlens import config

SESSION_NAME = "chatlens_session"


def _sender_name(sender) -> str:
    if sender is None:
        return "Unknown"
    if isinstance(sender, User):
        parts = [sender.first_name or "", sender.last_name or ""]
        return " ".join(p for p in parts if p) or sender.username or "Unknown"
    return getattr(sender, "title", None) or getattr(sender, "username", None) or "Unknown"


def _get_client() -> TelegramClient:
    api_id = config.TELEGRAM_API_ID
    api_hash = config.TELEGRAM_API_HASH
    if not api_id or not api_hash:
        raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env")
    return TelegramClient(SESSION_NAME, int(api_id), api_hash)


async def send_code(phone: str) -> str:
    """Send login code to phone, return phone_code_hash."""
    client = _get_client()
    await client.connect()
    if await client.is_user_authorized():
        await client.disconnect()
        return "ALREADY_AUTHORIZED"
    sent = await client.send_code_request(phone)
    await client.disconnect()
    return sent.phone_code_hash


async def verify_code(phone: str, code: str, phone_code_hash: str) -> bool:
    """Verify code and save session."""
    client = _get_client()
    await client.connect()
    try:
        if await client.is_user_authorized():
            return True
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        return True
    except Exception as e:
        raise ValueError(f"Failed to verify code: {e}")
    finally:
        await client.disconnect()


async def _fetch(chat_names: list[str] | None, limit: int) -> list[dict]:
    client = _get_client()
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        raise PermissionError("Not authorized. Please login first.")

    results: list[dict] = []
    try:
        dialogs = await client.get_dialogs()
        targets = dialogs
        if chat_names:
            name_set = {n.lower() for n in chat_names}
            targets = [d for d in dialogs if d.name.lower() in name_set]

        for dialog in targets:
            async for msg in client.iter_messages(dialog, limit=limit):
                if not msg.text:
                    continue
                sender = await msg.get_sender() if msg.sender_id else None
                results.append(
                    {
                        "platform": "telegram",
                        "chat_name": dialog.name or str(dialog.id),
                        "sender": _sender_name(sender),
                        "timestamp": msg.date.isoformat()
                        if isinstance(msg.date, datetime)
                        else str(msg.date),
                        "text": msg.text,
                        "reply_to": msg.reply_to_msg_id if msg.reply_to else None,
                        "forwarded_from": (
                            msg.forward.from_name or str(msg.forward.from_id)
                            if msg.forward
                            else None
                        ),
                    }
                )
    finally:
        await client.disconnect()

    return results


def fetch_telegram_chats(chat_names: list[str] | None = None, limit: int = 1000) -> list[dict]:
    """Fetch messages from Telegram chats via live API.

    Sync wrapper around the async Telethon client.
    """
    # ponytail: uses asyncio.run; breaks if called inside an existing event loop.
    # Upgrade path: accept an optional loop param or use nest_asyncio.
    return asyncio.run(_fetch(chat_names, limit))


def send_telegram_code_sync(phone: str) -> str:
    return asyncio.run(send_code(phone))


def verify_telegram_code_sync(phone: str, code: str, phone_code_hash: str) -> bool:
    return asyncio.run(verify_code(phone, code, phone_code_hash))
