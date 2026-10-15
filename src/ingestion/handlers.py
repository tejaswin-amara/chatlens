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


def _get_sender_name(sender: object) -> str:
    if not sender:
        return "Unknown"
    first = getattr(sender, "first_name", "") or ""
    last = getattr(sender, "last_name", "") or ""
    name = f"{first} {last}".strip()
    return name or getattr(sender, "title", "") or getattr(sender, "username", "") or "Unknown"


async def apply_event(
    parsed_event: ExtractedAcademicEvent,
    source_sender: str = "callback",
    message_text: str = "",
) -> tuple[str, list[str]]:
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

                                conflict_msg = (
                                    f"⚠️ **Calendar Conflict**\n"
                                    f"Found conflict for {milestone_match}.\n"
                                    f"Message date: {msg_dt}\n"
                                    f"Calendar date: {cal_date}"
                                )
                                await asyncio.to_thread(bot.send, conflict_msg)
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

    from src.workspace.sheets_logger import sheets_logger

    try:
        await asyncio.to_thread(
            sheets_logger.append_audit_log,
            source_sender,
            message_text or parsed_event.summary,
            parsed_event.intent,
            execution_status,
            ", ".join(details_list) or (parsed_event.course_name or ""),
        )
    except Exception as e:
        logger.debug("Failed to append audit log in apply_event", error=str(e))

    return execution_status, details_list


async def process_message(client: TelegramClient, chat_id: int, msg) -> None:
    if not msg:
        return

    import hashlib
    import json
    import time

    import src.timetable as tt
    from src.notify.bot import bot
    from src.parsing.regex_parser import RegexParser
    from src.workspace.sheets_logger import sheets_logger

    start_time = time.time()
    msg_text = msg.text or ""

    chat_name = "Unknown"
    sender_name = "Unknown"
    try:
        chat = await msg.get_chat() if hasattr(msg, "get_chat") else getattr(msg, "chat", None)
        chat_name = getattr(chat, "title", None) or getattr(chat, "username", None) or str(chat_id)
    except Exception:
        chat_name = str(chat_id)

    try:
        sender = (
            await msg.get_sender() if hasattr(msg, "get_sender") else getattr(msg, "sender", None)
        )
        sender_name = _get_sender_name(sender)
    except Exception:
        sender_name = "Unknown"

    if deduplicator.is_duplicate(chat_id, msg.id, msg_text):
        logger.debug("Skipping duplicate message", chat_id=chat_id, msg_id=msg.id)
        return

    parsed_event, source = await extract(client, msg)

    if not parsed_event or parsed_event.intent == "UNKNOWN":
        if settings.spark_mode != "dry":
            deduplicator.mark_processed(chat_id, msg.id, msg_text)
        return

    # Canonicalize course
    c_name, c_code = RegexParser.canonical_course(
        parsed_event.course_name, parsed_event.course_code
    )
    parsed_event.course_name = c_name
    parsed_event.course_code = c_code

    # Event Fingerprint Deduplication (24h TTL)
    evt_key = (
        f"{parsed_event.intent}:{parsed_event.course_code}:{parsed_event.room}:"
        f"{parsed_event.target_date}:{parsed_event.period}"
    )
    if parsed_event.intent in ("TASK", "EXAM_DEADLINE"):
        evt_key += f":{parsed_event.summary}"

    evt_hash = hashlib.sha256(evt_key.encode("utf-8")).hexdigest()
    evt_dedupe_key = f"evt:{evt_hash}"

    if deduplicator.is_duplicate("system", "evt", evt_dedupe_key, ttl_seconds=86400):
        try:
            await asyncio.to_thread(
                sheets_logger.append_audit_log,
                f"{chat_name} ({sender_name})",
                msg_text or "[Multimodal Media]",
                parsed_event.intent,
                "DUPLICATE_EVENT",
                f"Fingerprint: {evt_hash[:8]}",
            )
        except Exception as e:
            logger.debug("Audit log failed for duplicate event", error=str(e))
        return

    timetable = tt.load()
    timetable_ready = timetable is not None and not timetable.meta.sample
    verdict = tt.validate(parsed_event, timetable)

    decision = decide(
        settings.spark_mode, source or "unknown", parsed_event.intent, verdict.ok, timetable_ready
    )

    if decision == Decision.DRY_RUN:
        execution_status = "DRY_RUN"
        details_list = ["Would execute"]
        try:
            await asyncio.to_thread(
                sheets_logger.append_audit_log,
                f"{chat_name} ({sender_name})",
                msg_text or "[Multimodal Media]",
                parsed_event.intent,
                execution_status,
                ", ".join(details_list),
            )
        except Exception as e:
            logger.debug("Audit log failed for dry run", error=str(e))

        receipt = (
            f"🔍 **[DRY RUN] Event Processed:** `{parsed_event.intent}`\n"
            f"• **Course:** {parsed_event.course_name} ({parsed_event.course_code or 'N/A'})\n"
            f"• **Room:** {parsed_event.room or 'N/A'}\n"
            f"• **Target Date:** {parsed_event.target_date or 'N/A'}\n"
            f"• **Summary:** {parsed_event.summary}\n"
            f"• **Status:** DRY_RUN (Would execute)\n"
        )
        if settings.bot_token and settings.owner_chat_id:
            try:
                await asyncio.to_thread(bot.send, receipt)
            except Exception as e:
                logger.debug("Failed to send bot receipt", error=str(e))
        elif hasattr(client, "send_message"):
            try:
                await client.send_message("me", receipt)
            except Exception as e:
                logger.debug("Failed to send client receipt", error=str(e))

    elif decision == Decision.REVIEW:
        execution_status = "NEEDS_REVIEW"
        details_list = [f"Validation failed: {verdict.reason}"]
        text = (
            f"Review needed for {parsed_event.intent}\n"
            f"{parsed_event.summary}\n"
            f"Reason: {verdict.reason}"
        )
        if settings.bot_token and settings.owner_chat_id:
            await asyncio.to_thread(bot.send, text, buttons=None)

        deduplicator.mark_processed(chat_id, msg.id, msg_text)
        try:
            await asyncio.to_thread(
                sheets_logger.append_audit_log,
                f"{chat_name} ({sender_name})",
                msg_text or "[Multimodal Media]",
                parsed_event.intent,
                execution_status,
                verdict.reason or "",
            )
        except Exception as e:
            logger.debug("Audit log failed for review", error=str(e))

    elif decision == Decision.CONFIRM:
        execution_status = "PENDING_CONFIRMATION"
        details_list = ["Awaiting owner"]
        wrapper = {"event": parsed_event.model_dump(), "source": source}
        pid = deduplicator.add_pending(json.dumps(wrapper))

        text = (
            f"Review needed for {parsed_event.intent}\n"
            f"{parsed_event.summary}\n"
            f"Reason: {verdict.reason}"
        )
        buttons = [
            {"text": "✅ Apply", "callback_data": f"ok:{pid}"},
            {"text": "❌ Ignore", "callback_data": f"no:{pid}"},
        ]
        if settings.bot_token and settings.owner_chat_id:
            await asyncio.to_thread(bot.send, text, buttons=buttons)

        deduplicator.mark_processed(chat_id, msg.id, msg_text)
        deduplicator.mark_processed("system", "evt", evt_dedupe_key)
        try:
            await asyncio.to_thread(
                sheets_logger.append_audit_log,
                f"{chat_name} ({sender_name})",
                msg_text or "[Multimodal Media]",
                parsed_event.intent,
                "PENDING_CONFIRMATION",
                f"Pending PID {pid}",
            )
        except Exception as e:
            logger.debug("Audit log failed for pending confirmation", error=str(e))

    else:  # Decision.AUTO
        execution_status, details_list = await apply_event(
            parsed_event,
            source_sender=f"{chat_name} ({sender_name})",
            message_text=msg_text or "[Multimodal Media]",
        )
        if not execution_status.startswith("FAILED"):
            deduplicator.mark_processed(chat_id, msg.id, msg_text)
            deduplicator.mark_processed("system", "evt", evt_dedupe_key)

        receipt = (
            f"✅ **Action applied:** `{parsed_event.intent}`\n"
            f"• **Course:** {parsed_event.course_name} ({parsed_event.course_code or 'N/A'})\n"
            f"• **Room:** {parsed_event.room or 'N/A'}\n"
            f"• **Target Date:** {parsed_event.target_date or 'N/A'}\n"
            f"• **Summary:** {parsed_event.summary}\n"
            f"• **Status:** {execution_status} ({', '.join(details_list) or 'Logged'})\n"
        )
        if settings.bot_token and settings.owner_chat_id:
            try:
                await asyncio.to_thread(bot.send, receipt)
            except Exception as e:
                logger.debug("Failed to send bot receipt", error=str(e))
        elif hasattr(client, "send_message"):
            try:
                await client.send_message("me", receipt)
            except Exception as e:
                logger.debug("Failed to send client receipt", error=str(e))

    latency_ms = int((time.time() - start_time) * 1000)
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


async def handle_bot_callback(query: dict) -> None:
    import json
    import time

    from src.config import settings
    from src.notify.bot import bot

    sender_id = query.get("from", {}).get("id")
    if settings.owner_chat_id and sender_id != settings.owner_chat_id:
        return

    cb_id = query.get("id")
    msg_id = query.get("message", {}).get("message_id")
    data = query.get("data", "")

    try:
        await asyncio.to_thread(bot.answer_callback, cb_id)
    except Exception as e:
        logger.debug("Failed to answer callback query", error=str(e))

    if not data.startswith("ok:") and not data.startswith("no:"):
        return

    action, pid_str = data.split(":")
    pid = int(pid_str)

    row = deduplicator.get_pending(pid)
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
        deduplicator.finish_pending(pid, "IGNORED")
        if msg_id:
            await asyncio.to_thread(bot.edit, int(msg_id), "❌ Action ignored.")
        return

    if not deduplicator.claim_pending(pid):
        if msg_id:
            await asyncio.to_thread(bot.edit, int(msg_id), "⚠️ This request was already handled.")
        return

    wrapper = json.loads(event_json)
    event_dict = wrapper["event"]
    parsed_event = ExtractedAcademicEvent(**event_dict)

    execution_status, details_list = await apply_event(
        parsed_event,
        source_sender="Owner (Bot Callback)",
        message_text=parsed_event.summary,
    )

    if execution_status.startswith("FAILED"):
        deduplicator.finish_pending(pid, "FAILED")
        if msg_id:
            result_text = (
                f"❌ Action failed: {parsed_event.intent}\n"
                f"Status: {execution_status}"
            )
            await asyncio.to_thread(bot.edit, int(msg_id), result_text)
    else:
        deduplicator.finish_pending(pid, "APPROVED")
        if msg_id:
            result_text = (
                f"✅ Action applied: {parsed_event.intent}\n"
                f"Status: {execution_status}\nDetails: {', '.join(details_list)}"
            )
            await asyncio.to_thread(bot.edit, int(msg_id), result_text)


async def handle_undo_command(msg: dict) -> None:
    import json
    from typing import Any

    from src.config import settings
    from src.notify.bot import bot
    from src.workspace.calendar_sync import calendar_sync
    from src.workspace.tasks_sync import tasks_sync

    chat_id = msg.get("chat", {}).get("id") or msg.get("from", {}).get("id")
    if settings.owner_chat_id and chat_id and chat_id != settings.owner_chat_id:
        return

    last = deduplicator.last_write()
    if not last:
        await asyncio.to_thread(bot.send, "⚠️ Nothing to undo.")
        return

    w_id, kind, event_id, prior_json_str = last
    prior = json.loads(prior_json_str)

    try:
        if kind == "patch":
            ext_props = prior.get("extendedProperties")
            if ext_props is None:
                ext_props = {"private": {"spark_override": None}}
            patch_body: dict[str, Any] = {
                "location": prior.get("location") or None,
                "reminders": prior.get("reminders") or {"useDefault": True},
                "extendedProperties": ext_props,
            }
            if "summary" in prior:
                patch_body["summary"] = prior["summary"]

            service = calendar_sync.auth.get_calendar_service()
            await asyncio.to_thread(
                service.events()
                .patch(calendarId=calendar_sync.calendar_id, eventId=event_id, body=patch_body)
                .execute
            )
            deduplicator.mark_undone(w_id)
            await asyncio.to_thread(bot.send, f"✅ Undid patch on event `{event_id}`.")

        elif kind == "insert":
            if prior.get("source") == "calendar":
                service = calendar_sync.auth.get_calendar_service()
                await asyncio.to_thread(
                    service.events()
                    .delete(calendarId=calendar_sync.calendar_id, eventId=event_id)
                    .execute
                )
                deduplicator.mark_undone(w_id)
                await asyncio.to_thread(bot.send, "✅ Deleted created calendar event.")
            elif prior.get("source") == "tasks":
                service = tasks_sync.auth.get_tasks_service()
                await asyncio.to_thread(
                    service.tasks().delete(tasklist="@default", task=event_id).execute
                )
                deduplicator.mark_undone(w_id)
                await asyncio.to_thread(bot.send, "✅ Deleted created task.")
            else:
                deduplicator.mark_undone(w_id)
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
