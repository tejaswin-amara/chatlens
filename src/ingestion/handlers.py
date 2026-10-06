"""Telegram event handlers for commands, announcements, and multimodal media."""

import asyncio
import enum
from datetime import timedelta

from telethon import TelegramClient, events

from src.config import settings
from src.parsing.ai_extractor import ai_extractor
from src.parsing.regex_parser import RegexParser
from src.parsing.schemas import ExtractedAcademicEvent
from src.utils.deduplication import deduplicator
from src.utils.logging import get_logger
from src.workspace.calendar_sync import calendar_sync
from src.workspace.tasks_sync import tasks_sync

logger = get_logger(__name__)


class Decision(enum.Enum):
    DRY_RUN = "DRY_RUN"
    REVIEW = "REVIEW"
    CONFIRM = "CONFIRM"
    AUTO = "AUTO"


def decide(
    mode: str, source: str, event_intent: str, verdict: bool, timetable_ready: bool
) -> Decision:
    if mode == "dry":
        return Decision.DRY_RUN

    if not verdict:
        return Decision.REVIEW

    if mode == "live":
        if not timetable_ready and event_intent == "ROOM_OVERRIDE":
            return Decision.CONFIRM
        if source == "regex" and event_intent in ("ROOM_OVERRIDE", "TASK", "EXAM_DEADLINE"):
            return Decision.AUTO
        return Decision.CONFIRM

    return Decision.CONFIRM


async def extract(client: TelegramClient, msg) -> tuple[ExtractedAcademicEvent | None, str | None]:
    msg_text = msg.text or ""
    parsed_event: ExtractedAcademicEvent | None = None
    source = None

    if msg.voice or (msg.document and "audio" in getattr(msg.document, "mime_type", "")):
        source = "gemini"
        source = "gemini"
        if msg.file and msg.file.size and msg.file.size > 5_000_000:
            logger.warning("Voice message exceeds 5MB limit", size=msg.file.size)
        else:
            try:
                media_bytes = await client.download_media(msg, file=bytes)
                if media_bytes:
                    parsed_event = await asyncio.to_thread(
                        ai_extractor.extract_from_voice, media_bytes, msg.date
                    )
            except Exception as e:
                logger.error("Failed voice extraction", error=str(e))

    elif msg.photo or (msg.document and "pdf" in getattr(msg.document, "mime_type", "")):
        source = "gemini"
        source = "gemini"
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
                        mime_type,
                        msg.date,
                    )
            except Exception as e:
                logger.error("Failed media vision extraction", error=str(e))

    elif msg_text.strip():
        parsed_event = RegexParser.parse(msg_text, msg.date)
        if parsed_event:
            source = "regex"
        else:
            source = "gemini"
            try:
                parsed_event = await asyncio.to_thread(
                    ai_extractor.extract_from_text, msg_text, msg.date
                )
            except Exception as e:
                logger.error("Failed AI text extraction", error=str(e))

    return parsed_event, source


async def apply_event(parsed_event: ExtractedAcademicEvent) -> tuple[str, list[str]]:
    details_list = []
    execution_status = "SUCCESS"
    try:
        if parsed_event.intent == "ROOM_OVERRIDE" and parsed_event.room:
            from src.utils import clock

            target_dt = parsed_event.target_date or str(clock.today_ist())
            await asyncio.to_thread(
                calendar_sync.update_class_room,
                parsed_event.course_name,
                parsed_event.course_code,
                parsed_event.room,
                target_dt,
                parsed_event.period,
            )
            details_list.append("Google Calendar Patched")

        elif parsed_event.intent == "CLASS_CANCELLED":
            from src.utils import clock

            target_dt = parsed_event.target_date or str(clock.today_ist())
            await asyncio.to_thread(
                calendar_sync.cancel_class,
                parsed_event.course_name,
                parsed_event.course_code,
                target_dt,
                parsed_event.period,
            )
            details_list.append("Google Calendar Class Cancelled")

        elif parsed_event.intent == "HOLIDAY":
            from src.utils import clock

            target_dt = parsed_event.target_date or str(clock.today_ist())
            await asyncio.to_thread(
                calendar_sync.create_holiday_event,
                parsed_event.summary,
                target_dt,
            )
            details_list.append("Google Calendar Holiday Inserted")

        elif parsed_event.intent in ("EXAM_DEADLINE", "TASK") or parsed_event.action_required:
            conflict_found = False
            if parsed_event.target_date:
                import re

                milestone_pattern = re.compile(
                    r"(fee|re-check|last instruction|detention|mid-term|lab exam|sem-end)",
                    re.IGNORECASE,
                )
                if milestone_pattern.search(parsed_event.summary):
                    from src.academic_calendar import get_milestone_date, load_calendar

                    cal = load_calendar()
                    if cal:
                        match = milestone_pattern.search(parsed_event.summary)
                        if match:
                            milestone_match = match.group(1).lower()
                            from datetime import datetime

                            msg_dt = datetime.strptime(parsed_event.target_date, "%Y-%m-%d").date()
                            cal_date = get_milestone_date(milestone_match, msg_dt, cal)
                            if cal_date and cal_date != msg_dt:
                                conflict_found = True
                                execution_status = "CALENDAR_CONFLICT"
                                details_list.append(
                                    f"Conflict: Msg date {msg_dt}, Cal date {cal_date}"
                                )
                                from src.notify.bot import bot

                                await asyncio.to_thread(
                                    bot.send,
                                    f"⚠️ **Calendar Conflict**\nFound conflict for {milestone_match}.\nMessage date: {msg_dt}\nCalendar date: {cal_date}",
                                )
                    else:
                        logger.warning("Calendar file missing, skipping guard")

            if not conflict_found:
                await asyncio.to_thread(
                    tasks_sync.create_task,
                    parsed_event.summary,
                    None,
                    parsed_event.target_date,
                    parsed_event.course_code,
                )
                details_list.append("Google Task Created")

    except Exception as e:
        execution_status = f"FAILED: {e}"
        logger.error("Workspace sync error", error=str(e))

    # Write audit log for the operation

    from src.workspace.sheets_logger import sheets_logger

    try:
        await asyncio.to_thread(
            sheets_logger.append_audit_log,
            "callback",
            "",
            parsed_event.intent,
            execution_status,
            parsed_event.course_name or "",
        )
    except Exception:
        pass

    return execution_status, details_list


async def process_message(client: TelegramClient, chat_id: int, msg) -> None:
    if not msg:
        return

    msg_text = msg.text or ""

    if deduplicator.is_duplicate(chat_id, msg.id, msg_text):
        logger.debug("Skipping duplicate message", chat_id=chat_id, msg_id=msg.id)
        return

    parsed_event, source = await extract(client, msg)

    if not parsed_event or parsed_event.intent == "UNKNOWN":
        deduplicator.mark_processed(chat_id, msg.id, msg_text)
        return

    import src.timetable as tt

    timetable = tt.load()
    timetable_ready = timetable is not None and not timetable.meta.sample
    verdict = tt.validate(parsed_event, timetable)

    decision = decide(
        settings.spark_mode, source or "unknown", parsed_event.intent, verdict.ok, timetable_ready
    )

    deduplicator.mark_processed(chat_id, msg.id, msg_text)

    if decision == Decision.DRY_RUN:
        execution_status = "DRY_RUN"
        details_list = ["Would execute"]
    elif decision == Decision.REVIEW:
        execution_status = "NEEDS_REVIEW"
        details_list = ["Awaiting owner"]
    elif decision == Decision.CONFIRM:
        execution_status = "PENDING_CONFIRMATION"
        details_list = ["Awaiting owner"]
    else:
        execution_status, details_list = await apply_event(parsed_event)

    if decision in (Decision.REVIEW, Decision.CONFIRM) and settings.spark_mode != "dry":
        import json

        wrapper = {"event": parsed_event.model_dump(), "source": source}
        pid = deduplicator.add_pending(json.dumps(wrapper))

        text = f"Review needed for {parsed_event.intent}\n{parsed_event.summary}\nReason: {verdict.reason}"
        if decision == Decision.CONFIRM:
            buttons = [
                {"text": "✅ Apply", "callback_data": f"ok:{pid}"},
                {"text": "❌ Ignore", "callback_data": f"no:{pid}"},
            ]
        else:
            buttons = []

        from src.notify.bot import bot

        await asyncio.to_thread(bot.send, text, buttons)
        return

    if decision == Decision.AUTO:
        receipt = (
            f"✅ **Action applied:** `{parsed_event.intent}`\n"
            f"• **Course:** {parsed_event.course_name} ({parsed_event.course_code or 'N/A'})\n"
            f"• **Room:** {parsed_event.room or 'N/A'}\n"
            f"• **Target Date:** {parsed_event.target_date or 'N/A'}\n"
            f"• **Summary:** {parsed_event.summary}\n"
            f"• **Status:** {execution_status} ({', '.join(details_list) or 'Logged'})\n"
        )
        from src.notify.bot import bot

        await asyncio.to_thread(bot.send, receipt)


async def handle_bot_callback(query: dict) -> None:
    import json

    from src.config import settings
    from src.notify.bot import bot
    from src.utils.db import get_connection  # type: ignore

    sender_id = query.get("from", {}).get("id")
    if sender_id and sender_id != settings.owner_chat_id:
        return

    sender_id = query.get("from", {}).get("id")
    from src.config import settings

    if sender_id and settings.owner_chat_id and sender_id != settings.owner_chat_id:
        return

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

    with get_connection() as conn:
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
        import time

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

        cursor = conn.execute(
            "UPDATE pending SET status = 'APPROVED' WHERE id = ? AND status = 'PENDING'", (pid,)
        )
        if cursor.rowcount != 1:
            return

    wrapper = json.loads(event_json)
    event_dict = wrapper["event"]
    parsed_event = ExtractedAcademicEvent(**event_dict)

    execution_status, details_list = await apply_event(parsed_event)

    if msg_id:
        result_text = (
            f"✅ Action applied: {parsed_event.intent}\n"
            f"Status: {execution_status}\nDetails: {', '.join(details_list)}"
        )
        await asyncio.to_thread(bot.edit, int(msg_id), result_text)


async def handle_undo_command(msg: dict) -> None:
    import json

    from src.notify.bot import bot
    from src.utils.db import get_connection  # type: ignore
    from src.workspace.calendar_sync import calendar_sync
    from src.workspace.tasks_sync import tasks_sync

    with get_connection() as conn:
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
                    "extendedProperties": prior.get("extendedProperties") or None,
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


async def catch_up_chats(client: TelegramClient) -> None:
    for chat_id in settings.allowed_chat_ids:
        try:
            last_id = deduplicator.get_chat_state(chat_id)
            if last_id is None:
                messages = await client.get_messages(chat_id, limit=1)
                if messages:
                    deduplicator.update_chat_state(chat_id, messages[0].id)
                continue

            from src.utils import clock

            cutoff = clock.now_ist() - timedelta(days=7)
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
