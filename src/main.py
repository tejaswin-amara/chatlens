"""Main daemon lifecycle runner for ChatLens PA Bot background worker."""

import asyncio
import contextlib
import signal
import sys

from telethon.errors import (
    AuthKeyUnregisteredError,
    FloodWaitError,
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
    if not settings.bot_token or not settings.owner_chat_id:
        return

    import asyncio

    from src.ingestion.handlers import (
        handle_bot_callback,
        handle_bot_command,
        handle_undo_command,
    )
    from src.notify.bot import bot
    from src.utils.deduplication import deduplicator

    await asyncio.to_thread(bot.delete_webhook)
    await asyncio.to_thread(bot.set_my_commands)
    await asyncio.to_thread(bot.set_my_commands, scope={"type": "all_private_chats"})
    if settings.owner_chat_id:
        with contextlib.suppress(Exception):
            await asyncio.to_thread(
                bot.set_my_commands,
                scope={"type": "chat", "chat_id": int(str(settings.owner_chat_id))},
            )

    saved_offset = deduplicator.meta_get("telegram_bot_update_offset")
    offset = int(saved_offset) if saved_offset and saved_offset.isdigit() else 0
    logger.info("Bot callback polling started", initial_offset=offset)

    while True:
        try:
            try:
                updates = await asyncio.wait_for(
                    asyncio.to_thread(bot.get_updates, offset, 1),
                    timeout=35.0,
                )
            except TimeoutError:
                logger.debug("get_updates poll timed out, cycling loop")
                continue

            if updates and "result" in updates:
                for up in updates["result"]:
                    update_id = up.get("update_id", offset)
                    offset = max(offset, update_id + 1)
                    deduplicator.meta_set("telegram_bot_update_offset", str(offset))

                    if "callback_query" in up:
                        cb = up["callback_query"]
                        logger.info(
                            "Bot callback query received",
                            cb_id=cb.get("id"),
                            data=cb.get("data"),
                            sender_id=cb.get("from", {}).get("id"),
                        )
                        try:
                            await handle_bot_callback(cb)
                        except Exception as cb_err:
                            logger.error(
                                "Bot callback execution error",
                                error=str(cb_err),
                                exc_info=True,
                            )
                            cb_id = cb.get("id")
                            if cb_id:
                                try:
                                    await asyncio.to_thread(
                                        bot.answer_callback,
                                        cb_id,
                                        text="⚠️ Action failed.",
                                    )
                                except Exception as ack_err:
                                    logger.debug(
                                        "Failed to acknowledge callback", error=str(ack_err)
                                    )
                    elif "message" in up:
                        m = up["message"]
                        text = (m.get("text") or "").strip()
                        sender_id = m.get("from", {}).get("id") or m.get("chat", {}).get("id")
                        if settings.owner_chat_id and str(sender_id) != str(settings.owner_chat_id):
                            continue
                        cmd_name = text.split()[0] if text else "empty"
                        logger.info("Bot command received", sender_id=sender_id, cmd=cmd_name)
                        try:
                            if text.startswith("/undo"):
                                await handle_undo_command(m)
                            else:
                                await handle_bot_command(m)
                        except Exception as cmd_err:
                            logger.error(
                                "Bot command execution error",
                                cmd=cmd_name,
                                error=str(cmd_err),
                                exc_info=True,
                            )
                            if sender_id:
                                try:
                                    err_name = type(cmd_err).__name__
                                    await asyncio.to_thread(
                                        bot.send,
                                        f"⚠️ Could not execute `{cmd_name}`: {err_name}",
                                        chat_id=sender_id,
                                    )
                                except Exception as send_err:
                                    logger.debug(
                                        "Failed to send error notification", error=str(send_err)
                                    )
            await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Bot callback polling error", error=str(e))
            await asyncio.sleep(1)


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
        sleep_sec = max(1.0, (target - now).total_seconds())
        await asyncio.sleep(sleep_sec)

        today_str = clock.today_ist().strftime("%Y-%m-%d")
        if _is_sent_today(today_str):
            continue

        max_retries = 3
        backoff_sec = 300
        for retry in range(max_retries):
            try:
                inputs = await fetch_briefing_inputs()
                text = build_briefing(clock.now_ist(), *inputs)
                for attempt in range(2):
                    try:
                        await asyncio.to_thread(bot.send, text)
                        _mark_sent_today(today_str)
                        await asyncio.to_thread(deduplicator.prune_expired)
                        logger.info("Daily briefing dispatched and database pruned")
                        break
                    except Exception as send_err:
                        if attempt == 1:
                            raise send_err
                        await asyncio.sleep(5)
                break
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Failed to build or send briefing", error=str(e), retry=retry)
                if retry < max_retries - 1:
                    await asyncio.sleep(backoff_sec)


async def run_heartbeat() -> None:
    import asyncio
    import time

    from src.utils import clock
    from src.utils.deduplication import deduplicator

    last_sheets_sync = 0.0

    while True:
        try:
            # 1. Local SQLite heartbeat: update every 60s so healthcheck verifies responsiveness
            deduplicator.meta_set("last_heartbeat", str(clock.now_ist().timestamp()))
            logger.debug("Local heartbeat logged")

            # 2. External Google Sheets heartbeat: Periodic (900s), isolated from local heartbeat
            now_ts = time.time()
            if now_ts - last_sheets_sync >= 900:
                try:
                    from src.workspace.sheets_logger import sheets_logger

                    await asyncio.to_thread(sheets_logger.log_heartbeat)
                    last_sheets_sync = now_ts
                except Exception as sheets_err:
                    logger.warning("Failed to log Google Sheets heartbeat", error=str(sheets_err))

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Failed to record heartbeat", error=str(e))
        await asyncio.sleep(60)


async def run_reminders() -> None:
    """Proactively check for upcoming same-day academic deadlines and assessments every 60s."""
    import asyncio

    from src.notify.bot import bot
    from src.utils import clock
    from src.utils.deduplication import deduplicator

    while True:
        try:
            today_str = clock.today_ist().strftime("%Y-%m-%d")
            now = clock.now_ist()

            for item in deduplicator.list_pending(limit=None):
                try:
                    ev = item.get("event", {})
                    if isinstance(ev, dict) and "event" in ev:
                        ev = ev["event"]

                    t_date = (ev.get("target_date") or "").split("T")[0]
                    if t_date == today_str:
                        item_id = item.get("id")
                        meta_key = f"reminded:pending:{item_id}:{today_str}"
                        if not deduplicator.meta_get(meta_key):
                            c_name = (
                                ev.get("course_name") or ev.get("course_code") or "Academic Notice"
                            )
                            period = ev.get("period") or "Today"
                            summary = ev.get("summary") or "Assessment / Deadline"
                            intent = ev.get("intent", "NOTICE")

                            from src.formatting.templates import render_proactive_reminder

                            text = render_proactive_reminder(
                                course_name=c_name,
                                course_code=ev.get("course_code"),
                                period=period,
                                summary=summary,
                                intent=intent,
                            )
                            if settings.bot_token and settings.owner_chat_id:
                                await asyncio.to_thread(bot.send, text)
                            deduplicator.meta_set(meta_key, str(now.timestamp()))
                            logger.info(
                                "Proactive reminder dispatched", item_id=item_id, course=c_name
                            )
                except Exception as item_err:
                    logger.warning(
                        "Failed processing reminder item",
                        item_id=item.get("id"),
                        error=str(item_err),
                    )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.debug("Reminder check cycle error", error=str(e))

        await asyncio.sleep(60)


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


async def _watch_stop_file(stop_event: asyncio.Event) -> None:
    import asyncio
    from pathlib import Path

    stop_file = Path("logs/spark_daemon.stop")
    while not stop_event.is_set():
        exists = await asyncio.to_thread(stop_file.exists)
        if exists:
            logger.info("Graceful shutdown stop file detected. Halting daemon...")
            stop_event.set()
            with contextlib.suppress(OSError):
                await asyncio.to_thread(stop_file.unlink)
            break
        await asyncio.sleep(0.5)


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
        except (NotImplementedError, AttributeError):
            try:
                signal.signal(sig, lambda *_: _signal_handler())
            except (ValueError, OSError, AttributeError):
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

    from src.erp.sync import run_erp_sync
    from src.telemetry.emitter import emitter
    from src.utils.deduplication import deduplicator

    emitter.start()
    deduplicator.prune_expired()

    jobs = [
        asyncio.create_task(supervise("briefing", run_briefing, stop_event)),
        asyncio.create_task(supervise("heartbeat", run_heartbeat, stop_event)),
        asyncio.create_task(supervise("reminders", run_reminders, stop_event)),
        asyncio.create_task(supervise("erp_sync", lambda: run_erp_sync(stop_event), stop_event)),
        asyncio.create_task(
            supervise("stop_file", lambda: _watch_stop_file(stop_event), stop_event)
        ),
    ]
    if settings.bot_token and settings.owner_chat_id:
        jobs.append(asyncio.create_task(supervise("bot_poll", bot_callback_poll, stop_event)))

    startup_sent = False
    backoff = BACKOFF_START
    consecutive_connection_failures = 0
    try:
        while not stop_event.is_set():
            try:
                logger.info("Connecting Telethon StringSession client...")
                await client.connect()

                if not await client.is_user_authorized():
                    logger.critical("Telethon session is unauthorized.")
                    return 2

                consecutive_connection_failures = 0

                if not startup_sent:
                    from src.timetable import load as load_timetable
                    from src.utils import clock
                    from src.utils.deduplication import deduplicator

                    now_ts = clock.now_ist().timestamp()
                    last_notify = deduplicator.meta_get("last_startup_notify_ts")
                    should_notify = True
                    if last_notify:
                        try:
                            debounce_window = getattr(settings, "startup_debounce_seconds", 900)
                            if not isinstance(debounce_window, (int, float)) or hasattr(
                                debounce_window, "assert_called"
                            ):
                                debounce_sec = 900.0
                            else:
                                debounce_sec = float(debounce_window)

                            if now_ts - float(last_notify) < debounce_sec:
                                should_notify = False
                                logger.info(
                                    "Startup notification suppressed (debounced within 900s)",
                                    elapsed_s=now_ts - float(last_notify),
                                )
                        except ValueError:
                            pass

                    loaded_tt = load_timetable()
                    tt_status = (
                        "loaded"
                        if (
                            getattr(loaded_tt, "path", None)
                            and not getattr(loaded_tt, "sample", True)
                        )
                        else "missing/sample"
                    )
                    msg = (
                        f"🚀 SPARK started: mode={settings.spark_mode}, "
                        f"{len(settings.allowed_chat_ids)} chats, timetable {tt_status}"
                    )
                    if should_notify and settings.bot_token and settings.owner_chat_id:
                        from src.notify.bot import bot

                        try:
                            await asyncio.to_thread(bot.send, msg, buttons=[])
                            deduplicator.meta_set("last_startup_notify_ts", str(now_ts))
                        except Exception as err:
                            logger.warning("Failed to send startup notification", error=str(err))
                    startup_sent = True

                asyncio.create_task(catch_up_chats(client))
                backoff = BACKOFF_START
                logger.info("ChatLens PA Bot is live and listening for events")

                await _listen(client, stop_event)

                if not stop_event.is_set():
                    logger.warning("Telegram client disconnected cleanly. Reconnecting...")
                    if hasattr(client, "disconnect"):
                        with contextlib.suppress(Exception):
                            res = client.disconnect()
                            if asyncio.iscoroutine(res):
                                await res
                    await _sleep_or_stop(stop_event, backoff)
                    backoff = min(backoff * 2, BACKOFF_MAX)
            except FloodWaitError as e:
                logger.warning("FloodWait encountered during connect", seconds=e.seconds)
                await _sleep_or_stop(stop_event, e.seconds)
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
                if hasattr(client, "disconnect"):
                    with contextlib.suppress(Exception):
                        res = client.disconnect()
                        if asyncio.iscoroutine(res):
                            await res
                consecutive_connection_failures += 1
                if consecutive_connection_failures % 30 == 0:
                    logger.warning(
                        "Telegram network unreachable; continuing retry loop...",
                        failures=consecutive_connection_failures,
                    )
                await _sleep_or_stop(stop_event, backoff)
                backoff = min(backoff * 2, BACKOFF_MAX)

        return 0
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Daemon interrupted by user/signal. Exiting cleanly.")
        stop_event.set()
        return 0
    finally:
        stop_event.set()
        await emitter.stop()
        for j in jobs:
            j.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
        if client and hasattr(client, "is_connected"):
            is_conn = (
                client.is_connected() if callable(client.is_connected) else client.is_connected
            )
            if is_conn and hasattr(client, "disconnect"):
                res = client.disconnect()
                if asyncio.iscoroutine(res):
                    await res


def main() -> None:
    import asyncio

    try:
        code = asyncio.run(run_daemon())
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Daemon interrupted via signal. Exiting cleanly.")
        code = 0
    except Exception as e:
        logger.critical("Fatal daemon crash", error=str(e), exc_info=True)
        code = 1
    sys.exit(code)


if __name__ == "__main__":
    main()
