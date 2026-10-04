"""Telegram event handlers for commands, announcements, and multimodal media."""

import asyncio
import time
from datetime import datetime, timedelta

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import User

from src.config import settings
from src.parsing.ai_extractor import ai_extractor
from src.parsing.regex_parser import RegexParser
from src.parsing.schemas import ExtractedAcademicEvent
from src.utils.deduplication import deduplicator
from src.utils.logging import get_logger
from src.workspace.calendar_sync import calendar_sync
from src.workspace.sheets_logger import sheets_logger
from src.workspace.tasks_sync import tasks_sync

logger = get_logger(__name__)


def _get_sender_name(sender) -> str:
    if sender is None:
        return "Unknown"
    if isinstance(sender, User):
        parts = [sender.first_name or "", sender.last_name or ""]
        name = " ".join(p for p in parts if p).strip()
        return name or sender.username or str(sender.id)
    return getattr(sender, "title", None) or getattr(sender, "username", None) or "Unknown"


async def process_message(client: TelegramClient, chat_id: int, msg) -> None:
    if not msg:
        return

    chat = await msg.get_chat()
    chat_name = getattr(chat, "title", None) or getattr(chat, "username", None) or str(chat_id)
    sender = await msg.get_sender()
    sender_name = _get_sender_name(sender)
    msg_text = msg.text or ""

    if deduplicator.is_duplicate(chat_id, msg.id, msg_text):
        logger.debug("Skipping duplicate message", chat_id=chat_id, msg_id=msg.id)
        return

    deduplicator.mark_processed(chat_id, msg.id, msg_text)
    start_time = time.time()

    parsed_event: ExtractedAcademicEvent | None = None
    media_bytes: bytes | None = None

    if msg.voice or (msg.document and "audio" in getattr(msg.document, "mime_type", "")):
        if msg.file and msg.file.size and msg.file.size > 5_000_000:
            logger.warning("Voice message exceeds 5MB limit", size=msg.file.size)
        else:
            try:
                media_bytes = await client.download_media(msg, file=bytes)
                if media_bytes:
                    parsed_event = await asyncio.to_thread(
                        ai_extractor.extract_from_voice, media_bytes, message_date=msg.date
                    )

            except Exception as e:
                logger.error("Failed voice extraction", error=str(e))

    elif msg.photo or (msg.document and "pdf" in getattr(msg.document, "mime_type", "")):
        if msg.file and msg.file.size and msg.file.size > 5_000_000:
            logger.warning("Media message exceeds 5MB limit", size=msg.file.size)
        else:
            try:
                is_pdf = msg.document and "pdf" in getattr(msg.document, "mime_type", "")
                mime_type = "application/pdf" if is_pdf else "image/jpeg"
                media_bytes = await client.download_media(msg, file=bytes)
                if media_bytes:
                    parsed_event = await asyncio.to_thread(
                        ai_extractor.extract_from_media,
                        media_bytes,
                        mime_type=mime_type,
                        message_date=msg.date,
                    )

            except Exception as e:
                logger.error("Failed media vision extraction", error=str(e))

    elif msg_text.strip():
        source = None
        parsed_event = RegexParser.parse(msg_text, msg.date)
        if parsed_event:
            source = "regex"
        else:
            try:
                parsed_event = await asyncio.to_thread(
                    ai_extractor.extract_from_text, msg_text, msg.date
                )
                if parsed_event:
                    source = "gemini"
            except Exception as e:
                logger.error("Failed AI text extraction", error=str(e))

    if not parsed_event or parsed_event.intent == "UNKNOWN":
        return

    execution_status = "SUCCESS"
    details_list: list[str] = []

    # apply canonical course
    c_name, c_code = RegexParser.canonical_course(
        parsed_event.course_name, parsed_event.course_code
    )
    parsed_event.course_name = c_name
    parsed_event.course_code = c_code

    # Event dedupe
    if parsed_event:
        import hashlib
        evt_key = (f"{parsed_event.intent}:{parsed_event.course_code}:"
                   f"{parsed_event.room}:{parsed_event.target_date}:{parsed_event.period}")
        if parsed_event.intent in ("TASK", "EXAM_DEADLINE"):
            evt_key += f":{parsed_event.summary}"

        evt_hash = hashlib.sha256(evt_key.encode("utf-8")).hexdigest()
        evt_dedupe_key = f"evt:{evt_hash}"

        if deduplicator.is_duplicate("system", "evt", evt_dedupe_key):
            try:
                await asyncio.to_thread(
                    sheets_logger.append_audit_log,
                    source_sender=f"{chat_name} ({sender_name})",
                    message_text=msg_text or "[Multimodal Media]",
                    intent=parsed_event.intent,
                    execution_status="DUPLICATE_EVENT",
                    extra_details="Skipped write due to 7-day dedupe",
                )
            except Exception:
                pass
            return

        deduplicator.mark_processed("system", "evt", evt_dedupe_key)

    try:
        from src.timetable import load as load_tt
        from src.timetable import validate as validate_tt
        tt = load_tt()
        verdict = validate_tt(parsed_event, tt)

        needs_confirm = False
        if not verdict.ok:
            execution_status = "NEEDS_REVIEW"
            details_list.append(f"Validation failed: {verdict.reason}")
            needs_confirm = True
        elif settings.spark_mode == "confirm":
            needs_confirm = True
        elif settings.spark_mode == "live":
            if (
                source == "gemini"
                or parsed_event.intent == "HOLIDAY"
                or parsed_event.intent == "CLASS_CANCELLED"
            ):
                needs_confirm = True

        if settings.spark_mode == "dry":
            execution_status = "DRY_RUN"
            details_list.append("No workspace calls made")
        elif needs_confirm:
            import json
            import sqlite3
            event_dict = parsed_event.model_dump()
            wrapper = {"source": source, "event": event_dict}

            with sqlite3.connect(settings.spark_db, isolation_level=None) as conn:
                cursor = conn.execute(
                    "INSERT INTO pending (created, chat_id, msg_id, event_json, status) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (time.time(), chat_id, msg.id, json.dumps(wrapper), "PENDING")
                )
                pending_id = cursor.lastrowid

            from src.notify.bot import bot
            msg_text_fmt = (
                f"🔔 **Action Required:**\n- **Intent:** {parsed_event.intent}\n"
                f"- **Summary:** {parsed_event.summary}\n- **Validation:** {verdict.reason}"
            )
            buttons = [
                {"text": "✅ Apply", "callback_data": f"ok:{pending_id}"},
                {"text": "❌ Ignore", "callback_data": f"no:{pending_id}"}
            ]
            await asyncio.to_thread(bot.send, msg_text_fmt, buttons)
            execution_status = "PENDING_CONFIRMATION"
            details_list.append("Awaiting owner confirmation")
        else:
            if parsed_event.intent == "ROOM_OVERRIDE" and parsed_event.room:
                target_dt = parsed_event.target_date or datetime.now().strftime("%Y-%m-%d")
                await asyncio.to_thread(
                    calendar_sync.update_class_room,
                    course_name=parsed_event.course_name,
                    course_code=parsed_event.course_code,
                    new_room=parsed_event.room,
                    target_date=target_dt,
                    period=parsed_event.period,
                )
                details_list.append("Google Calendar Patched")

            elif parsed_event.intent == "CLASS_CANCELLED":
                target_dt = parsed_event.target_date or datetime.now().strftime("%Y-%m-%d")
                await asyncio.to_thread(
                    calendar_sync.cancel_class,
                    course_name=parsed_event.course_name,
                    course_code=parsed_event.course_code,
                    target_date=target_dt,
                    period=parsed_event.period,
                )
                details_list.append("Google Calendar Class Cancelled")

            elif parsed_event.intent == "HOLIDAY":
                target_dt = parsed_event.target_date or datetime.now().strftime("%Y-%m-%d")
                # Summary is truncated by regex parser up to 100 chars,
                # but here we can just use the parsed_event.summary
                await asyncio.to_thread(
                    calendar_sync.create_holiday_event,
                    reason=parsed_event.summary,
                    target_date=target_dt,
                )
                details_list.append("Google Calendar Holiday Inserted")

            elif parsed_event.intent in ("EXAM_DEADLINE", "TASK") or parsed_event.action_required:
                await asyncio.to_thread(
                    tasks_sync.create_task,
                    title=parsed_event.summary,
                    due_date=parsed_event.target_date,
                    course_code=parsed_event.course_code,
                )
                details_list.append("Google Task Created")

    except LookupError as e:
        execution_status = f"NO_MATCH: {e}"
        logger.warning("Lookup error in workspace sync", error=str(e))
    except Exception as e:
        execution_status = f"FAILED: {e}"
        logger.error("Workspace sync error", error=str(e))

    latency_ms = int((time.time() - start_time) * 1000)

    try:
        await asyncio.to_thread(
            sheets_logger.append_audit_log,
            source_sender=f"{chat_name} ({sender_name})",
            message_text=msg_text or "[Multimodal Media]",
            intent=parsed_event.intent,
            execution_status=execution_status,
            extra_details=", ".join(details_list),
        )
    except Exception as e:
        logger.error("Failed to append audit log", error=str(e))

    logger.info(
        "Processed message event",
        chat_id=chat_id,
        msg_id=msg.id,
        intent=parsed_event.intent,
        status=execution_status,
        latency_ms=latency_ms,
    )
    logger.debug(
        "Processed message details",
        chat_title=chat_name,
        sender_name=sender_name,
        text=msg_text,
    )

    try:
        c_name = parsed_event.course_name or "N/A"
        c_code = parsed_event.course_code or "N/A"
        course_str = f"{c_name} ({c_code})"
        dry_label = " (DRY RUN)" if settings.spark_mode == "dry" else ""
        receipt = (
            f"🤖 **ChatLens PA Sync Receipt{dry_label}**\n"
            f"• **Intent:** `{parsed_event.intent}`\n"
            f"• **Course:** {course_str}\n"
            f"• **Room:** {parsed_event.room or 'N/A'}\n"
            f"• **Target Date:** {parsed_event.target_date or 'N/A'}\n"
            f"• **Summary:** {parsed_event.summary}\n"
            f"• **Status:** {execution_status} ({', '.join(details_list) or 'Logged'})\n"
        )
        try:
            await client.send_message("me", receipt)
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
            await client.send_message("me", receipt)
    except Exception as e:
        logger.warning("Could not dispatch receipt to 'me'", error=str(e))

async def catch_up_chats(client: TelegramClient) -> None:
    for chat_id in settings.allowed_chat_ids:
        try:
            last_id = deduplicator.get_chat_state(chat_id)
            if last_id is None:
                messages = await client.get_messages(chat_id, limit=1)
                if messages:
                    deduplicator.update_chat_state(chat_id, messages[0].id)
                continue

            # Fetch messages newer than last_id
            cutoff = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(days=7)
            messages = await client.get_messages(chat_id, min_id=last_id, reverse=True, limit=200)
            if len(messages) == 200:
                logger.warning("Catch-up truncated at 200 messages", chat_id=chat_id)

            for msg in messages:
                if msg.date and msg.date >= cutoff and not msg.out:
                    await process_message(client, chat_id, msg)
                deduplicator.update_chat_state(chat_id, msg.id)

        except Exception as e:
            logger.warning("Failed to catch up chat", chat_id=chat_id, error=str(e))

def register_handlers(client: TelegramClient) -> None:
    @client.on(events.NewMessage(pattern=r"^(?:/task|todo:)\s+(.+)", chats="me", outgoing=True))
    async def handle_task_command(event: events.NewMessage.Event) -> None:
        task_text = event.pattern_match.group(1)
        if not task_text:
            await event.respond("⚠️ Usage: `/task <description of task>`")
            return

        try:
            created = await asyncio.to_thread(tasks_sync.create_task, title=task_text)
            task_id = created.get("id", "N/A")
            await event.respond(f"✅ **Task Created:** {task_text}\nTask ID: `{task_id}`")
        except Exception as e:
            await event.respond(f"❌ Failed to create task: {e}")

    @client.on(events.NewMessage(chats=settings.allowed_chat_ids))
    @client.on(events.MessageEdited(chats=settings.allowed_chat_ids))
    async def handle_incoming_message(event: events.NewMessage.Event) -> None:
        if event.out or not event.message:
            return
        if event.message.text and event.message.text.startswith("/"):
            return

        await process_message(client, event.chat_id, event.message)
        deduplicator.update_chat_state(event.chat_id, event.message.id)

async def handle_bot_callback(query: dict) -> None:
    import json
    import sqlite3

    from src.config import settings
    from src.notify.bot import bot

    cb_id = query.get("id")
    msg_id = query.get("message", {}).get("message_id")
    data = query.get("data", "")

    try:
        await asyncio.to_thread(bot.answer_callback, cb_id)
    except Exception:
        pass

    if not data.startswith("ok:") and not data.startswith("no:"):
        return

    action, pid_str = data.split(":")
    pid = int(pid_str)

    with sqlite3.connect(settings.spark_db, isolation_level=None) as conn:
        cursor = conn.execute(
            "SELECT event_json, status, created FROM pending WHERE id = ?", (pid,)
        )
        row = cursor.fetchone()
        if not row:
            if msg_id:
                await asyncio.to_thread(
                    bot.edit, int(msg_id), "⚠️ This request has expired or was not found."
                )
            return

        event_json, status, created = row
        if time.time() - created > 86400:
            if msg_id:
                await asyncio.to_thread(bot.edit, int(msg_id), "⚠️ This request has expired.")
            return

        if status != "PENDING":
            if msg_id:
                await asyncio.to_thread(
                    bot.edit, int(msg_id), f"⚠️ This request was already handled ({status})."
                )
            return

        if action == "no":
            conn.execute("UPDATE pending SET status = 'IGNORED' WHERE id = ?", (pid,))
            if msg_id:
                await asyncio.to_thread(bot.edit, int(msg_id), "❌ Action ignored.")
            return

        conn.execute("UPDATE pending SET status = 'APPROVED' WHERE id = ?", (pid,))

    # Execute the action
    wrapper = json.loads(event_json)
    event_dict = wrapper["event"]
    parsed_event = ExtractedAcademicEvent(**event_dict)

    execution_status = "SUCCESS"
    details_list = []
    try:
        if parsed_event.intent == "ROOM_OVERRIDE" and parsed_event.room:
            target_dt = parsed_event.target_date or datetime.now().strftime("%Y-%m-%d")
            await asyncio.to_thread(
                calendar_sync.update_class_room,
                course_name=parsed_event.course_name,
                course_code=parsed_event.course_code,
                new_room=parsed_event.room,
                target_date=target_dt,
                period=parsed_event.period,
            )
            details_list.append("Google Calendar Patched")

        elif parsed_event.intent == "CLASS_CANCELLED":
            target_dt = parsed_event.target_date or datetime.now().strftime("%Y-%m-%d")
            await asyncio.to_thread(
                calendar_sync.cancel_class,
                course_name=parsed_event.course_name,
                course_code=parsed_event.course_code,
                target_date=target_dt,
                period=parsed_event.period,
            )
            details_list.append("Google Calendar Class Cancelled")

        elif parsed_event.intent == "HOLIDAY":
            target_dt = parsed_event.target_date or datetime.now().strftime("%Y-%m-%d")
            await asyncio.to_thread(
                calendar_sync.create_holiday_event,
                reason=parsed_event.summary,
                target_date=target_dt,
            )
            details_list.append("Google Calendar Holiday Inserted")

        elif parsed_event.intent in ("EXAM_DEADLINE", "TASK") or parsed_event.action_required:
            await asyncio.to_thread(
                tasks_sync.create_task,
                title=parsed_event.summary,
                due_date=parsed_event.target_date,
                course_code=parsed_event.course_code,
            )
            details_list.append("Google Task Created")

    except Exception as e:
        execution_status = f"FAILED: {e}"
        logger.error("Workspace sync error from callback", error=str(e))

    if msg_id:
        result_text = (
            f"✅ Action applied: {parsed_event.intent}\n"
            f"Status: {execution_status}\nDetails: {', '.join(details_list)}"
        )
        await asyncio.to_thread(bot.edit, int(msg_id), result_text)

async def handle_undo_command(msg: dict) -> None:
    import json
    import sqlite3

    from src.config import settings
    from src.notify.bot import bot
    from src.workspace.calendar_sync import calendar_sync
    from src.workspace.tasks_sync import tasks_sync

    with sqlite3.connect(settings.spark_db, isolation_level=None) as conn:
        cursor = conn.execute(
            "SELECT id, kind, event_id, prior_json FROM writes "
            "WHERE undone = 0 ORDER BY ts DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if not row:
            await asyncio.to_thread(bot.send, "⚠️ Nothing to undo.")
            return

        w_id, kind, event_id, prior_json_str = row
        prior = json.loads(prior_json_str)

        try:
            if kind == "patch":
                # Restore previous location and reminders
                patch_body = {
                    "location": prior.get("location") or None,
                    "reminders": prior.get("reminders") or {"useDefault": True},
                    "extendedProperties": prior.get("extendedProperties") or None
                }
                # Also restore summary if it was cancelled
                if "summary" in prior:
                    patch_body["summary"] = prior["summary"]

                service = calendar_sync.auth.get_calendar_service()
                service.events().patch(
                    calendarId=calendar_sync.calendar_id, eventId=event_id, body=patch_body
                ).execute()
                await asyncio.to_thread(bot.send, f"✅ Undid patch on event `{event_id}`.")

            elif kind == "insert":
                if prior.get("source") == "calendar":
                    service = calendar_sync.auth.get_calendar_service()
                    service.events().delete(
                        calendarId=calendar_sync.calendar_id, eventId=event_id
                    ).execute()
                    await asyncio.to_thread(bot.send, "✅ Deleted created calendar event.")
                elif prior.get("source") == "tasks":
                    service = tasks_sync.auth.get_tasks_service()
                    service.tasks().delete(tasklist="@default", task=event_id).execute()
                    await asyncio.to_thread(bot.send, "✅ Deleted created task.")

            conn.execute("UPDATE writes SET undone = 1 WHERE id = ?", (w_id,))
        except Exception as e:
            await asyncio.to_thread(bot.send, f"❌ Undo failed: {e}")
