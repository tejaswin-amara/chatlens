"""Live Telegram message fetcher via Telethon."""

import asyncio
import logging
import os
import sys
from datetime import datetime

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import User

try:
    from telethon.errors import (
        AuthKeyDuplicatedError,
        AuthKeyUnregisteredError,
        FloodWaitError,
        SessionExpiredError,
        SessionRevokedError,
    )
except ImportError:

    class AuthKeyDuplicatedError(Exception):  # type: ignore[no-redef]
        pass

    class AuthKeyUnregisteredError(Exception):  # type: ignore[no-redef]
        pass

    class SessionExpiredError(Exception):  # type: ignore[no-redef]
        pass

    class SessionRevokedError(Exception):  # type: ignore[no-redef]
        pass

    class FloodWaitError(Exception):  # type: ignore[no-redef]
        pass


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

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
    session_str = getattr(config, "TELEGRAM_SESSION_STRING", None) or os.getenv(
        "TELEGRAM_SESSION_STRING"
    )
    session = StringSession(session_str) if session_str else SESSION_NAME
    client = TelegramClient(session, int(api_id), api_hash)
    client.flood_sleep_threshold = 0  # Do not sleep, raise FloodWaitError immediately
    return client


async def check_status() -> bool:
    try:
        client = _get_client()
        await client.connect()
        auth = await client.is_user_authorized()
        await client.disconnect()
        return bool(auth)
    except (AuthKeyDuplicatedError, SessionRevokedError, SessionExpiredError) as exc:
        logger.warning(f"Telegram live session conflict or invalidation: {exc}")
        return False
    except Exception as exc:
        if "AuthKeyDuplicated" in type(exc).__name__:
            logger.warning(f"Session collision with active daemon session: {exc}")
            return False
        logger.debug(f"Telegram check_status warning: {exc}")
        return False


async def send_code(phone: str) -> str:
    """Send login code to phone, return phone_code_hash."""
    client = _get_client()
    try:
        await client.connect()
    except (AuthKeyDuplicatedError, SessionRevokedError, SessionExpiredError) as exc:
        logger.warning(f"Session collision on send_code: {exc}")
        raise ValueError("Telegram session collision with active daemon session") from exc
    except Exception as exc:
        if "AuthKeyDuplicated" in type(exc).__name__:
            logger.warning(f"Session collision on send_code: {exc}")
            raise ValueError("Telegram session collision with active daemon session") from exc
        raise

    try:
        if await client.is_user_authorized():
            await client.disconnect()
            return "ALREADY_AUTHORIZED"
        sent = await client.send_code_request(phone)
        await client.disconnect()
        return sent.phone_code_hash
    except Exception:
        await client.disconnect()
        raise


async def verify_code(phone: str, code: str, phone_code_hash: str) -> bool:
    """Verify code and save session."""
    client = _get_client()
    try:
        await client.connect()
    except (AuthKeyDuplicatedError, SessionRevokedError, SessionExpiredError) as exc:
        logger.warning(f"Session collision on verify_code: {exc}")
        return False
    except Exception as exc:
        if "AuthKeyDuplicated" in type(exc).__name__:
            logger.warning(f"Session collision on verify_code: {exc}")
            return False
        raise

    try:
        if await client.is_user_authorized():
            return True
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        return True
    except (AuthKeyDuplicatedError, SessionRevokedError, SessionExpiredError) as exc:
        logger.warning(f"Session collision during sign_in: {exc}")
        return False
    except Exception as e:
        if "AuthKeyDuplicated" in type(e).__name__:
            logger.warning(f"Session collision during sign_in: {e}")
            return False
        raise ValueError(f"Failed to verify code: {e}") from e
    finally:
        try:
            await client.disconnect()
        except Exception as exc:
            logger.debug(f"Client disconnect warning: {exc}")


async def _fetch(chat_names: list[str] | None, limit: int) -> list[dict]:
    try:
        client = _get_client()
    except Exception as exc:
        logger.warning(f"Telegram client setup failed: {exc}")
        return []

    try:
        await client.connect()
    except (AuthKeyDuplicatedError, SessionRevokedError, SessionExpiredError) as exc:
        logger.warning(f"Telegram live connection collision with active daemon: {exc}")
        return []
    except Exception as exc:
        if "AuthKeyDuplicated" in type(exc).__name__:
            logger.warning(f"Session collision detected on connect: {exc}")
            return []
        logger.error(f"Failed to connect to Telegram live: {exc}")
        return []

    results: list[dict] = []
    try:
        try:
            authorized = await client.is_user_authorized()
        except (AuthKeyDuplicatedError, SessionRevokedError, SessionExpiredError) as exc:
            logger.warning(f"Telegram auth check collision with active daemon: {exc}")
            return []
        except Exception as exc:
            if "AuthKeyDuplicated" in type(exc).__name__:
                logger.warning(f"Session collision detected on auth check: {exc}")
                return []
            raise

        if not authorized:
            raise PermissionError("Not authorized. Please login first.")

        dialogs = await client.get_dialogs()
        targets = dialogs
        if chat_names:
            name_set = {n.lower() for n in chat_names}
            targets = [d for d in dialogs if d.name.lower() in name_set]
        else:
            # Respect SPARK_CHAT_IDS if configured
            spark_chat_ids_raw = os.getenv("SPARK_CHAT_IDS", "")
            allowlisted_ids: set[int] = set()
            if spark_chat_ids_raw:
                for token in spark_chat_ids_raw.replace(";", ",").split(","):
                    token_str = token.strip()
                    if token_str:
                        try:
                            allowlisted_ids.add(int(token_str))
                        except ValueError:
                            pass
            if allowlisted_ids:
                targets = [d for d in dialogs if getattr(d, "id", None) in allowlisted_ids]
            else:
                targets = targets[:5]

        for dialog in targets:
            try:
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
                            "reply_to": str(msg.reply_to_msg_id)
                            if msg.reply_to and msg.reply_to_msg_id
                            else None,
                            "forwarded_from": (
                                msg.forward.from_name or str(msg.forward.from_id)
                                if msg.forward
                                else None
                            ),
                        }
                    )
            except (AuthKeyDuplicatedError, SessionRevokedError) as exc:
                logger.warning(
                    f"Session collision while reading dialog {getattr(dialog, 'name', '')}: {exc}"
                )
                break
            except Exception as e:
                if "AuthKeyDuplicated" in type(e).__name__:
                    logger.warning(
                        "Session collision detected during message iteration, stopping gracefully."
                    )
                    break
                logger.error(f"Error fetching dialog {getattr(dialog, 'name', '')}: {e}")
                if "FloodWait" in type(e).__name__:
                    logger.warning("Hit rate limit, stopping sync early.")
                    break
    except (AuthKeyDuplicatedError, SessionRevokedError) as exc:
        logger.warning(f"Session collision encountered during live fetch: {exc}")
        return []
    except Exception as exc:
        if "AuthKeyDuplicated" in type(exc).__name__:
            logger.warning("Session collision detected during live fetch.")
            return []
        raise
    finally:
        try:
            await client.disconnect()
        except Exception as exc:
            logger.debug(f"Client disconnect warning: {exc}")

    return results


def fetch_telegram_chats(chat_names: list[str] | None = None, limit: int = 1000) -> list[dict]:
    """Fetch messages from Telegram chats via live API.

    Sync wrapper around the async Telethon client. Runs safely within existing event loops.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, _fetch(chat_names, limit)).result()
    return asyncio.run(_fetch(chat_names, limit))


def send_telegram_code_sync(phone: str) -> str:
    return asyncio.run(send_code(phone))


def verify_telegram_code_sync(phone: str, code: str, phone_code_hash: str) -> bool:
    return asyncio.run(verify_code(phone, code, phone_code_hash))
