"""Main daemon lifecycle runner for ChatLens PA Bot background worker."""

import asyncio
import signal
import sys

from telethon import TelegramClient
from telethon.errors import FloodWaitError

from src.config import settings
from src.ingestion.handlers import register_handlers
from src.ingestion.telegram_client import create_telegram_client
from src.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def run_daemon() -> None:
    configure_logging()
    logger.info("Starting ChatLens Enterprise PA Bot Daemon")

    try:
        settings.validate_required()
    except ValueError as e:
        logger.critical("Configuration validation failed", error=str(e))
        sys.exit(1)

    client: TelegramClient = create_telegram_client()
    register_handlers(client)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Shutdown signal received (SIGINT/SIGTERM). Stopping daemon...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    backoff = 2
    while not stop_event.is_set():
        try:
            logger.info("Connecting Telethon StringSession client...")
            await client.start()
            logger.info("ChatLens PA Bot is live and listening for events")
            backoff = 2

            disconnected_task = asyncio.create_task(client.run_until_disconnected())
            stop_task = asyncio.create_task(stop_event.wait())

            done, pending = await asyncio.wait(
                [disconnected_task, stop_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            if stop_event.is_set():
                break

        except FloodWaitError as e:
            logger.warning("Telegram FloodWaitError encountered", seconds=e.seconds)
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error("Daemon execution error encountered", error=str(e), backoff_s=backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

    logger.info("Disconnecting Telethon client...")
    if client.is_connected():
        await client.disconnect()
    logger.info("ChatLens PA Bot Daemon stopped cleanly.")


def main() -> None:
    try:
        asyncio.run(run_daemon())
    except KeyboardInterrupt:
        logger.info("Daemon interrupted by user.")


if __name__ == "__main__":
    main()
