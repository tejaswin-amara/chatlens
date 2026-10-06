"""Main daemon lifecycle runner for ChatLens PA Bot background worker."""

import asyncio
import signal
import sys

from telethon.errors import (
    AuthKeyUnregisteredError,
    SessionExpiredError,
    SessionRevokedError,
    UserDeactivatedBanError,
    UserDeactivatedError,
)

from src.config import settings
from src.ingestion.handlers import catch_up_chats, register_handlers
from src.ingestion.telegram_client import create_telegram_client
from src.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def bot_callback_poll() -> None:
    import asyncio

    from src.ingestion.handlers import handle_bot_callback, handle_undo_command
    from src.notify.bot import bot

    offset = 0
    while True:
        try:
            updates = await asyncio.to_thread(bot.get_updates, offset)
            if updates and "result" in updates:
                for up in updates["result"]:
                    update_id = up.get("update_id", offset)
                    offset = max(offset, update_id + 1)

                    if "callback_query" in up:
                        await handle_bot_callback(up["callback_query"])
                    elif "message" in up and up["message"].get("text") == "/undo":
                        await handle_undo_command(up["message"])
            await asyncio.sleep(2)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Bot callback polling error", error=str(e))
            await asyncio.sleep(5)


async def run_briefing() -> None:
    import asyncio

    from src.briefing import build_briefing, fetch_briefing_inputs, next_run
    from src.notify.bot import bot
    from src.utils import clock
    from src.utils.deduplication import deduplicator

    def _is_sent_today(today_str: str) -> bool:
        return deduplicator.meta_get("briefing_last_date") == today_str

    def _mark_sent_today(today_str: str) -> None:
        deduplicator.meta_set("briefing_last_date", today_str)

    while True:
        now = clock.now_ist()
        target = next_run(now)
        await asyncio.sleep((target - now).total_seconds())

        today_str = clock.today_ist().strftime("%Y-%m-%d")
        if _is_sent_today(today_str):
            continue

        try:
            inputs = await fetch_briefing_inputs()
            text = build_briefing(clock.now_ist(), *inputs)
            for attempt in range(2):
                try:
                    await asyncio.to_thread(bot.send, text)
                    _mark_sent_today(today_str)
                    logger.info("Daily briefing dispatched")
                    break
                except Exception as send_err:
                    if attempt == 1:
                        raise send_err
                    await asyncio.sleep(5)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Failed to build or send briefing", error=str(e))


async def run_heartbeat() -> None:
    import asyncio

    from src.utils import clock
    from src.utils.deduplication import deduplicator

    while True:
        try:
            from src.workspace.sheets_logger import sheets_logger

            await asyncio.to_thread(sheets_logger.log_heartbeat)
            deduplicator.meta_set("last_heartbeat", str(clock.now_ist().timestamp()))
            logger.debug("Heartbeat logged")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Failed to log heartbeat", error=str(e))
        await asyncio.sleep(900)


BACKOFF_START, BACKOFF_MAX = 2.0, 60.0


async def _sleep_or_stop(stop: asyncio.Event, seconds: float) -> None:
    import asyncio
    import contextlib

    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=seconds)


async def _listen(client, stop: asyncio.Event) -> None:
    import asyncio

    listen = asyncio.create_task(client.run_until_disconnected())
    waiter = asyncio.create_task(stop.wait())
    try:
        done, _ = await asyncio.wait({listen, waiter}, return_when=asyncio.FIRST_COMPLETED)
        if listen in done:
            listen.result()
    finally:
        for t in (listen, waiter):
            t.cancel()
        await asyncio.gather(listen, waiter, return_exceptions=True)


async def supervise(name: str, job, stop: asyncio.Event) -> None:
    import asyncio

    backoff = BACKOFF_START
    while not stop.is_set():
        try:
            await job()
            return
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Background job crashed", job=name, error=str(e), backoff_s=backoff)
            await _sleep_or_stop(stop, backoff)
            backoff = min(backoff * 2, BACKOFF_MAX)


def _install_signal_handlers(loop, stop_event: asyncio.Event) -> None:
    def _signal_handler() -> None:
        logger.info("Shutdown signal received (SIGINT/SIGTERM). Stopping daemon...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass


async def run_daemon(*, client=None, stop_event=None, handle_signals=True) -> int:
    import asyncio

    configure_logging()
    logger.info("Starting ChatLens Enterprise PA Bot Daemon")

    try:
        settings.validate_required()
    except ValueError as e:
        logger.critical("Configuration validation failed", error=str(e))
        return 2

    if client is None:
        client = create_telegram_client()

    loop = asyncio.get_running_loop()
    if stop_event is None:
        stop_event = asyncio.Event()

    if handle_signals:
        _install_signal_handlers(loop, stop_event)

    register_handlers(client)

    jobs = [
        asyncio.create_task(supervise("briefing", run_briefing, stop_event)),
        asyncio.create_task(supervise("heartbeat", run_heartbeat, stop_event)),
    ]
    if settings.spark_mode != "dry":
        jobs.append(asyncio.create_task(supervise("bot_poll", bot_callback_poll, stop_event)))

    backoff = BACKOFF_START
    while not stop_event.is_set():
        try:
            logger.info("Connecting Telethon StringSession client...")
            await client.connect()

            if not await client.is_user_authorized():
                logger.critical("Telethon session is unauthorized.")
                return 2

            await catch_up_chats(client)
            logger.info("ChatLens PA Bot is live and listening for events")

            await _listen(client, stop_event)

            if not stop_event.is_set():
                logger.warning("Telegram client disconnected cleanly. Reconnecting...")
                await _sleep_or_stop(stop_event, backoff)
                backoff = min(backoff * 2, BACKOFF_MAX)
        except AuthKeyUnregisteredError:
            logger.critical("Unrecoverable AuthKeyUnregisteredError")
            return 2
        except SessionRevokedError:
            logger.critical("Unrecoverable SessionRevokedError")
            return 2
        except SessionExpiredError:
            logger.critical("Unrecoverable SessionExpiredError")
            return 2
        except UserDeactivatedError:
            logger.critical("Unrecoverable UserDeactivatedError")
            return 2
        except UserDeactivatedBanError:
            logger.critical("Unrecoverable UserDeactivatedBanError")
            return 2
        except Exception as e:
            logger.error("Transient error in connection loop", error=str(e))
            await _sleep_or_stop(stop_event, backoff)
            backoff = min(backoff * 2, BACKOFF_MAX)

    stop_event.set()
    for j in jobs:
        j.cancel()
    await asyncio.gather(*jobs, return_exceptions=True)
    return 0


def main() -> None:
    import asyncio

    code = asyncio.run(run_daemon())
    sys.exit(code)
