"""Main daemon lifecycle runner for ChatLens PA Bot background worker."""

import asyncio
import signal
import sys

from telethon import TelegramClient
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
    from src.config import settings
    if settings.spark_mode == "dry" or not settings.bot_token or not settings.owner_chat_id:
        return

    from src.ingestion.handlers import handle_bot_callback
    from src.notify.bot import bot

    offset = 0
    while True:
        try:
            updates = await asyncio.to_thread(bot.get_updates, offset, 30)
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                if "callback_query" in update:
                    await handle_bot_callback(update["callback_query"])
                elif "message" in update and "text" in update["message"]:
                    msg = update["message"]
                    if msg.get("chat", {}).get("id") == settings.owner_chat_id:
                        if msg["text"].strip().startswith("/undo"):
                            from src.ingestion.handlers import handle_undo_command
                            await handle_undo_command(msg)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("Bot polling error", error=str(e))
            await asyncio.sleep(5)


async def run_briefing() -> None:
    import sqlite3
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    from src.academic_calendar import load_calendar
    from src.briefing import build_briefing
    from src.config import settings
    from src.notify.bot import bot
    from src.workspace.calendar_sync import calendar_sync
    from src.workspace.sheets_logger import sheets_logger
    from src.workspace.tasks_sync import tasks_sync

    IST = ZoneInfo("Asia/Kolkata")

    def _is_sent_today(today_str: str) -> bool:
        try:
            with sqlite3.connect(settings.spark_db, isolation_level=None) as conn:
                row = conn.execute("SELECT value FROM meta WHERE key = 'briefing_last_date'").fetchone()
                if row and row[0] == today_str:
                    return True
        except Exception:
            pass
        return False

    def _mark_sent_today(today_str: str) -> None:
        try:
            with sqlite3.connect(settings.spark_db, isolation_level=None) as conn:
                conn.execute("INSERT INTO meta (key, value) VALUES ('briefing_last_date', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (today_str,))
        except Exception:
            pass

    while True:
        now = datetime.now(IST)
        target = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)

        sleep_seconds = (target - now).total_seconds()
        logger.info(f"Briefing scheduler sleeping for {sleep_seconds} seconds until 07:00 IST")

        try:
            await asyncio.sleep(sleep_seconds)
        except asyncio.CancelledError:
            break

        # Time to send!
        today_str = datetime.now(IST).strftime("%Y-%m-%d")
        if _is_sent_today(today_str):
            continue

        try:
            # Fetch data
            now_ist = datetime.now(IST)
            start_str = now_ist.strftime("%Y-%m-%d")
            end_str = (now_ist + timedelta(days=3)).strftime("%Y-%m-%d")

            cal_events = []
            try:
                service = calendar_sync.auth.get_calendar_service()
                time_min = now_ist.replace(hour=0, minute=0, second=0).isoformat()
                time_max = now_ist.replace(hour=23, minute=59, second=59).isoformat()
                events_result = service.events().list(
                    calendarId=calendar_sync.calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    timeZone="Asia/Kolkata",
                    singleEvents=True,
                    orderBy="startTime"
                ).execute()
                cal_events = events_result.get("items", [])
            except Exception as e:
                logger.warning("Briefing cal fetch failed", error=str(e))

            tasks = await asyncio.to_thread(tasks_sync.list_open_tasks, start_str, end_str)

            attendance_rows = []
            try:
                service = sheets_logger.auth.get_sheets_service()
                result = service.spreadsheets().values().get(
                    spreadsheetId=sheets_logger.sheet_id,
                    range="Attendance!A:C"
                ).execute()
                values = result.get("values", [])
                if len(values) > 1:
                    headers = [str(h).lower() for h in values[0]]
                    for row in values[1:]:
                        if len(row) >= 3:
                            row_dict = dict(zip(headers, row))
                            # Expecting course, attended, held
                            if "course" in row_dict and "attended" in row_dict and "held" in row_dict:
                                attendance_rows.append(row_dict)
            except Exception as e:
                logger.warning("Briefing sheets fetch failed", error=str(e))

            milestones = {}
            cal = load_calendar()
            if cal:
                # Get milestones from terms
                for term, dates in cal.terms.items():
                    for name, d in dates.items():
                        milestones[f"{term} {name}"] = d

            text = build_briefing(now_ist, cal_events, tasks, attendance_rows, milestones)

            await asyncio.to_thread(bot.send, text)
            _mark_sent_today(today_str)

        except Exception as e:
            logger.error("Failed to send briefing, will retry in 5 minutes", error=str(e))
            try:
                await asyncio.sleep(300)
                await asyncio.to_thread(bot.send, text)
                _mark_sent_today(today_str)
            except Exception as e2:
                logger.error("Briefing retry failed", error=str(e2))

async def run_heartbeat() -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from src.workspace.sheets_logger import sheets_logger

    IST = ZoneInfo("Asia/Kolkata")

    while True:
        try:
            await asyncio.sleep(900) # 15 minutes
            now_str = datetime.now(IST).isoformat()

            def do_heartbeat():
                service = sheets_logger.auth.get_sheets_service()
                try:
                    service.spreadsheets().values().update(
                        spreadsheetId=sheets_logger.sheet_id,
                        range="Status!A1",
                        valueInputOption="USER_ENTERED",
                        body={"values": [[now_str]]}
                    ).execute()
                except Exception as e:
                    # If tab doesn't exist, it throws an error like 'Unable to parse range'
                    if 'parse range' in str(e).lower() or 'not found' in str(e).lower():
                        # Create the tab
                        body = {
                            "requests": [{
                                "addSheet": {"properties": {"title": "Status"}}
                            }]
                        }
                        service.spreadsheets().batchUpdate(
                            spreadsheetId=sheets_logger.sheet_id,
                            body=body
                        ).execute()
                        # Retry
                        service.spreadsheets().values().update(
                            spreadsheetId=sheets_logger.sheet_id,
                            range="Status!A1",
                            valueInputOption="USER_ENTERED",
                            body={"values": [[now_str]]}
                        ).execute()
                    else:
                        raise e

            await asyncio.to_thread(do_heartbeat)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("Heartbeat failed", error=str(e))

async def run_daemon() -> None:
    configure_logging()
    logger.info("Starting ChatLens Enterprise PA Bot Daemon")

    try:
        settings.validate_required()
    except ValueError as e:
        logger.critical("Configuration validation failed", error=str(e))
        try:
            from src.notify.bot import bot
            bot.send(f"🛑 SPARK exiting: Config validation failed: {str(e)}")
        except Exception:
            pass
        sys.exit(2)

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
            await client.connect()
            await catch_up_chats(client)
            if not await client.is_user_authorized():
                logger.critical("Telethon session is unauthorized. Regenerate session using scripts/generate_session.py")
                try:
                    from src.notify.bot import bot
                    bot.send("🛑 SPARK exiting: Telethon session unauthorized")
                except Exception:
                    pass
                sys.exit(2)
            logger.info("ChatLens PA Bot is live and listening for events")
            if getattr(client, "_spark_startup_sent", False) is False:
                from src.timetable import load as load_tt
                tt = load_tt()
                tt_status = "loaded" if tt else "missing or sample"
                try:
                    from src.notify.bot import bot
                    await asyncio.to_thread(bot.send, f"🚀 SPARK started: mode={settings.spark_mode}, {len(settings.allowed_chat_ids)} chats, timetable {tt_status}")
                    client._spark_startup_sent = True
                except Exception:
                    await client.send_message("me", f"🚀 SPARK started: mode={settings.spark_mode}, {len(settings.allowed_chat_ids)} chats, timetable {tt_status}")
                    client._spark_startup_sent = True
            backoff = 2

            bot_poll_task = asyncio.create_task(bot_callback_poll())
            briefing_task = asyncio.create_task(run_briefing())
            heartbeat_task = asyncio.create_task(run_heartbeat())
            disconnected_task = asyncio.create_task(client.run_until_disconnected())
            stop_task = asyncio.create_task(stop_event.wait())

            done, pending = await asyncio.wait(
                [disconnected_task, stop_task, bot_poll_task, briefing_task, heartbeat_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            for task in done:
                task.result()

            if stop_event.is_set():
                break

        except FloodWaitError as e:
            logger.warning("Telegram FloodWaitError encountered", seconds=e.seconds)
            await asyncio.sleep(e.seconds)
        except (AuthKeyUnregisteredError, SessionRevokedError, SessionExpiredError, UserDeactivatedError, UserDeactivatedBanError) as e:
            logger.critical("Unrecoverable Telegram session error", error=str(e))
            try:
                from src.notify.bot import bot
                bot.send(f"🛑 SPARK exiting: Session error: {str(e)}")
            except Exception:
                pass
            sys.exit(2)
        except SystemExit:
            raise
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
