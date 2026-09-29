"""Telegram event handlers for commands, announcements, and multimodal media."""

import asyncio
import time
from datetime import datetime, timedelta

from telethon import TelegramClient, events
from telethon.tl.types import User

from src.parsing.ai_extractor import ai_extractor
from src.parsing.regex_parser import RegexParser
from src.parsing.schemas import ExtractedAcademicEvent
from src.utils.deduplication import deduplicator
from src.utils.logging import get_logger
from src.workspace.calendar_sync import calendar_sync
from src.workspace.keep_sync import keep_sync
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


def register_handlers(client: TelegramClient) -> None:
    @client.on(events.NewMessage(pattern=r"^/today", outgoing=True))
    async def handle_today_command(event: events.NewMessage.Event) -> None:
        today_str = datetime.now().strftime("%Y-%m-%d")
        response_text = (
            f"📅 **Today's PA Snapshot ({today_str})**\n\n"
            "• **Upcoming Classes:**\n"
            "  - P1-P2 (09:00 AM): DSA [Room H-005]\n"
            "  - P3-P4 (11:00 AM): ML [Room HC-15C]\n\n"
            "• **Pending Action Items:**\n"
            "  - [25CS2103E] Lab Record Submission (Due 11:59 PM)\n"
        )
        await event.respond(response_text)

    @client.on(events.NewMessage(pattern=r"^/next", outgoing=True))
    async def handle_next_command(event: events.NewMessage.Event) -> None:
        now = datetime.now()
        next_time_str = (now + timedelta(minutes=35)).strftime("%I:%M %p")
        response_text = (
            "⏳ **Next Class Notice**\n\n"
            "• **Course:** Machine Learning (`25CS2103E`)\n"
            "• **Room:** `HC-15C`\n"
            f"• **Time:** {next_time_str} (in 35 mins)\n"
            "• **Faculty:** Dr. A. Sharma\n"
        )
        await event.respond(response_text)

    @client.on(events.NewMessage(pattern=r"^/task(?:\s+(.+))?", outgoing=True))
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

    @client.on(events.NewMessage())
    async def handle_incoming_message(event: events.NewMessage.Event) -> None:
        msg = event.message
        if not msg:
            return

        # Early return for outgoing messages to prevent receipt re-ingestion
        if event.out:
            return

        # Ignore command triggers
        if msg.text and msg.text.startswith("/"):
            return

        chat = await event.get_chat()
        chat_id = event.chat_id
        chat_name = getattr(chat, "title", None) or getattr(chat, "username", None) or str(chat_id)
        sender = await event.get_sender()
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
            try:
                media_bytes = await client.download_media(msg, file=bytes)
                if media_bytes:
                    parsed_event = await asyncio.to_thread(
                        ai_extractor.extract_from_voice, media_bytes, message_date=msg.date
                    )
            except Exception as e:
                logger.error("Failed voice extraction", error=str(e))

        elif msg.photo or (msg.document and "pdf" in getattr(msg.document, "mime_type", "")):
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
            parsed_event = RegexParser.parse(msg_text, msg.date)
            if not parsed_event:
                try:
                    parsed_event = await asyncio.to_thread(
                        ai_extractor.extract_from_text, msg_text, msg.date
                    )
                except Exception as e:
                    logger.error("Failed AI text extraction", error=str(e))

        if not parsed_event or parsed_event.intent == "UNKNOWN":
            return

        execution_status = "SUCCESS"
        details_list: list[str] = []

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

                keep_text = (
                    f"Updated Room: {parsed_event.room} for "
                    f"{parsed_event.course_name or 'Class'} ({parsed_event.period or 'Today'})"
                )
                await asyncio.to_thread(
                    keep_sync.update_live_timetable_note, today_timetable_text=keep_text
                )
                details_list.append("Google Keep Updated")

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
            logger.error("Workspace sync error", error=str(e))

        latency_ms = int((time.time() - start_time) * 1000)

        await asyncio.to_thread(
            sheets_logger.append_audit_log,
            source_sender=f"{chat_name} ({sender_name})",
            message_text=msg_text or "[Multimodal Media]",
            intent=parsed_event.intent,
            execution_status=execution_status,
            extra_details=", ".join(details_list),
        )

        logger.info(
            "Processed message event",
            source_chat=chat_name,
            event_type=parsed_event.intent,
            latency_ms=latency_ms,
        )

        try:
            c_name = parsed_event.course_name or "N/A"
            c_code = parsed_event.course_code or "N/A"
            course_str = f"{c_name} ({c_code})"
            receipt = (
                "🤖 **ChatLens PA Sync Receipt**\n"
                f"• **Intent:** `{parsed_event.intent}`\n"
                f"• **Course:** {course_str}\n"
                f"• **Room:** {parsed_event.room or 'N/A'}\n"
                f"• **Target Date:** {parsed_event.target_date or 'N/A'}\n"
                f"• **Summary:** {parsed_event.summary}\n"
                f"• **Status:** {execution_status} ({', '.join(details_list) or 'Logged'})\n"
            )
            await client.send_message("me", receipt)
        except Exception as e:
            logger.warning("Could not dispatch receipt to 'me'", error=str(e))
