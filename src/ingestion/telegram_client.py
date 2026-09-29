"""Headless Telethon client initialization using StringSession."""

from telethon import TelegramClient
from telethon.sessions import StringSession

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def create_telegram_client() -> TelegramClient:
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be configured.")

    if not settings.telegram_session_string:
        raise ValueError("TELEGRAM_SESSION_STRING must be configured for headless operation.")

    logger.info("Initializing headless Telethon StringSession client")
    session = StringSession(settings.telegram_session_string)
    client = TelegramClient(session, settings.telegram_api_id, settings.telegram_api_hash)
    return client
