"""Telegram event handlers for commands, announcements, and multimodal media."""

import asyncio
import enum
import time
from datetime import timedelta

from telethon import TelegramClient, events

from src.config import settings
from src.parsing.ai_extractor import ai_extractor
from src.parsing.regex_parser import RegexParser
from src.parsing.schemas import ExtractedAcademicEvent
from src.timetable import (
    COURSE_INFO as COURSE_INFO,
)
from src.timetable import (
    PERIOD_TIMES as PERIOD_TIMES,
)
from src.timetable import (
    format_day_schedule,
)
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
        file_size = getattr(getattr(msg, "file", None), "size", None)
        if isinstance(file_size, (int, float)) and file_size > 5_000_000:
            logger.warning("Voice message exceeds 5MB limit", size=file_size)
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
        file_size = getattr(getattr(msg, "file", None), "size", None)
        if isinstance(file_size, (int, float)) and file_size > 5_000_000:
            logger.warning("Media message exceeds 5MB limit", size=file_size)
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
            import src.timetable as tt
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

            periods = tt.parse_periods(parsed_event.period or "")
            if not periods:
                deduplicator.record_override(
                    target_dt,
                    None,
                    parsed_event.course_code or "",
                    parsed_event.course_name or "",
                    parsed_event.room,
                    "OVERRIDE",
                    parsed_event.summary,
                )
            else:
                for p in periods:
                    deduplicator.record_override(
                        target_dt,
                        p,
                        parsed_event.course_code or "",
                        parsed_event.course_name or "",
                        parsed_event.room,
                        "OVERRIDE",
                        parsed_event.summary,
                    )
            details_list.append("Timetable Override Recorded")

        elif parsed_event.intent == "CLASS_CANCELLED":
            import src.timetable as tt
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

            periods = tt.parse_periods(parsed_event.period or "")
            if not periods:
                deduplicator.record_override(
                    target_dt,
                    None,
                    parsed_event.course_code or "",
                    parsed_event.course_name or "",
                    None,
                    "CANCELLED",
                    parsed_event.summary,
                )
            else:
                for p in periods:
                    deduplicator.record_override(
                        target_dt,
                        p,
                        parsed_event.course_code or "",
                        parsed_event.course_name or "",
                        None,
                        "CANCELLED",
                        parsed_event.summary,
                    )
            details_list.append("Class Cancellation Recorded")

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

    sender_id = getattr(sender, "id", None) or getattr(msg, "sender_id", 0) or 0
    is_owner = bool(settings.owner_chat_id and str(sender_id) == str(settings.owner_chat_id))

    from src.governance.audit import audit_logger
    from src.governance.guards import input_guard
    from src.governance.policy_engine import ActionTier, PolicyVerdict, policy_engine

    raw_date = getattr(msg, "date", None)
    msg_ts = raw_date.timestamp() if raw_date and hasattr(raw_date, "timestamp") else time.time()
    untrusted_input = input_guard.sanitize_and_wrap(
        channel_id=chat_id,
        sender_id=sender_id,
        text=msg_text,
        timestamp=msg_ts,
        is_owner=is_owner,
    )
    event_id = audit_logger.generate_event_id(
        chat_id, getattr(msg, "id", 0), untrusted_input.timestamp
    )

    if untrusted_input.quarantined:
        logger.warning(
            "untrusted_input_quarantined",
            chat_id=chat_id,
            msg_id=getattr(msg, "id", 0),
            reason=untrusted_input.quarantine_reason,
        )
        audit_logger.log_action(
            event_id=event_id,
            untrusted_input=untrusted_input,
            extracted_intent="INJECTION_BLOCKED",
            risk_tier=ActionTier.TIER_2_HIGH_RISK,
            policy_verdict=PolicyVerdict.QUARANTINED,
            approver_id="SYSTEM_AUTO",
            details=untrusted_input.quarantine_reason or "Prompt injection detected",
        )
        deduplicator.mark_processed(chat_id, msg.id, msg_text)
        if settings.bot_token and settings.owner_chat_id:
            alert = (
                f"🛡️ **Security Alert: Quarantined Prompt Injection**\n"
                f"• **Channel:** `{chat_name}` ({chat_id})\n"
                f"• **Sender:** `{sender_name}` ({sender_id})\n"
                f"• **Reason:** {untrusted_input.quarantine_reason}\n"
                f"• **Filtered Snippet:** `{untrusted_input.content[:100]}`"
            )
            await asyncio.to_thread(bot.send, alert)
        return

    if deduplicator.is_duplicate(chat_id, msg.id, msg_text):
        logger.debug("Skipping duplicate message", chat_id=chat_id, msg_id=msg.id)
        return

    parsed_event, source = await extract(client, msg)

    if parsed_event and parsed_event.summary:
        is_inj, inj_reason = input_guard.detect_injection(parsed_event.summary)
        if is_inj:
            logger.warning(
                "extracted_summary_injection_quarantined",
                reason=inj_reason,
                chat_id=chat_id,
                msg_id=getattr(msg, "id", 0),
            )
            return

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

        audit_logger.log_action(
            event_id=event_id,
            untrusted_input=untrusted_input,
            extracted_intent=parsed_event.intent,
            risk_tier=policy_engine.classify_action_tier(parsed_event.intent, source or "unknown"),
            policy_verdict=PolicyVerdict.REJECTED,
            approver_id="SYSTEM_AUTO",
            details="Dry run mode - external writes disabled",
        )

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

        audit_logger.log_action(
            event_id=event_id,
            untrusted_input=untrusted_input,
            extracted_intent=parsed_event.intent,
            risk_tier=policy_engine.classify_action_tier(parsed_event.intent, source or "unknown"),
            policy_verdict=PolicyVerdict.CONFIRMATION_PENDING,
            approver_id="SYSTEM_AUTO",
            details=f"Pending PID {pid}: {verdict.reason}",
        )

    else:  # Decision.AUTO
        execution_status, details_list = await apply_event(
            parsed_event,
            source_sender=f"{chat_name} ({sender_name})",
            message_text=msg_text or "[Multimodal Media]",
        )
        if not execution_status.startswith("FAILED"):
            deduplicator.mark_processed(chat_id, msg.id, msg_text)
            deduplicator.mark_processed("system", "evt", evt_dedupe_key)

        audit_logger.log_action(
            event_id=event_id,
            untrusted_input=untrusted_input,
            extracted_intent=parsed_event.intent,
            risk_tier=policy_engine.classify_action_tier(parsed_event.intent, source or "unknown"),
            policy_verdict=PolicyVerdict.ALLOWED,
            approver_id="SYSTEM_AUTO",
            details=f"Auto applied: {execution_status}",
        )

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
    if settings.owner_chat_id and (not sender_id or str(sender_id) != str(settings.owner_chat_id)):
        return

    cb_id = query.get("id")
    msg_id = query.get("message", {}).get("message_id")
    data = query.get("data", "")

    try:
        await asyncio.to_thread(bot.answer_callback, cb_id)
    except Exception as e:
        logger.debug("Failed to answer callback query", error=str(e))

    if data.startswith("cmd:"):
        cmd_name = data.split(":", 1)[1]
        synth_msg = {
            "chat": {"id": sender_id},
            "from": {"id": sender_id},
            "text": f"/{cmd_name}",
        }
        await handle_bot_command(synth_msg)
        return

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
        from src.governance.audit import audit_logger
        from src.governance.policy_engine import PolicyVerdict

        audit_logger.update_verdict(
            event_id=f"pending:{pid}",
            verdict=PolicyVerdict.REJECTED,
            approver_id=str(sender_id),
            details="Rejected by human owner via Telegram inline callback",
        )
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
            result_text = f"❌ Action failed: {parsed_event.intent}\nStatus: {execution_status}"
            await asyncio.to_thread(bot.edit, int(msg_id), result_text)
    else:
        deduplicator.finish_pending(pid, "APPROVED")
        from src.governance.audit import audit_logger
        from src.governance.policy_engine import PolicyVerdict

        audit_logger.update_verdict(
            event_id=f"pending:{pid}",
            verdict=PolicyVerdict.ALLOWED,
            approver_id=str(sender_id),
            details=f"Approved by human owner via Telegram inline callback | {execution_status}",
        )
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
    if settings.owner_chat_id and chat_id and str(chat_id) != str(settings.owner_chat_id):
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


_active_client: TelegramClient | None = None


async def handle_bot_command(msg: dict) -> None:
    from src.config import settings
    from src.notify.bot import bot

    chat_id = msg.get("chat", {}).get("id") or msg.get("from", {}).get("id")
    if settings.owner_chat_id and (not chat_id or str(chat_id) != str(settings.owner_chat_id)):
        return

    text = (msg.get("text") or "").strip()
    cmd = text.split()[0].lower().split("@")[0] if text else ""

    recognized_commands = (
        "/",
        "/start",
        "/help",
        "/today",
        "/tomorrow",
        "/timetable",
        "/schedule",
        "/briefing",
        "/digest",
        "/attendance",
        "/bunk",
        "/margins",
        "/deadlines",
        "/deadline",
        "/tasks",
        "/status",
        "/marks",
        "/cgpa",
        "/fee",
        "/quarantine",
        "/quarantined",
        "/quarantine_inspect",
        "/rescan",
        "/scan",
        "/undo",
        "/ask",
        "/exam",
        "/exams",
        "/viva",
    )
    if cmd.startswith("/") and cmd not in recognized_commands:
        import difflib

        fuzzy_candidates = tuple(c for c in recognized_commands if c not in ("/", "/undo", "/bunk"))
        close = difflib.get_close_matches(cmd, fuzzy_candidates, n=1, cutoff=0.75)
        if close:
            cmd = close[0]

    if cmd in ("/", "/start", "/help"):
        reply = (
            "👋 **ChatLens & SPARK PA Menu**\n\n"
            "Academic & Schedule Commands:\n"
            "• `/today` — Today's classes, rooms & status\n"
            "• `/tomorrow` — Tomorrow's schedule & upcoming classes\n"
            "• `/timetable` — Official weekly course timetable & rooms\n"
            "• `/briefing` — Generate today's academic briefing\n"
            "• `/attendance` — Live attendance & safe bunk margins\n"
            "• `/bunk` — Exact attendance bunk buffer calculator\n"
            "• `/deadlines` — Upcoming task deadlines & academic milestones\n"
            "• `/exam` — In-sem lab exams & project defence schedules\n"
            "• `/ask <question>` — Instant semantic answer (viva prep, Arduino code, rooms)\n"
            "• `/status` — Live daemon & chat monitoring status\n"
            "• `/marks` — In-sem internal marks & assessments\n"
            "• `/cgpa` — Official academic grades & transcript\n"
            "• `/fee` — Fee orders & payment receipts\n"
            "• `/quarantine` — View isolated prompt injection attempts\n"
            "• `/rescan` — Deep-scan course group messages & files (past 7 days)\n"
            "• `/undo` — Revert last applied calendar override\n"
            "• `/help` — Show all available options\n\n"
            "💬 *Tap any button below or ask a question directly!*"
        )
        await asyncio.to_thread(bot.send, reply)

    elif cmd == "/status":
        from src.utils import clock

        now_str = clock.now_ist().strftime("%Y-%m-%d %H:%M:%S IST")
        reply = (
            f"🟢 **ChatLens PA Status** ({now_str})\n\n"
            f"• **SPARK Mode**: `{settings.spark_mode}`\n"
            f"• **Telegram**: Active ({len(settings.allowed_chat_ids)} monitored course chats)\n"
            f"• **Gemini AI**: `{settings.gemini_model}` (Active & Connected)\n"
            f"• **KL ERP Bridge**: Configured (`{settings.erp_username}`)\n"
            f"• **Google Workspace**: Connected\n"
            f"• **Owner**: `{settings.owner_chat_id}`\n"
            f"• **Status**: 🚀 Live & Listening in Real-Time"
        )
        await asyncio.to_thread(bot.send, reply)

    elif cmd == "/today":
        from src.utils import clock

        today = clock.today_ist()
        now = clock.now_ist()
        schedule_text = format_day_schedule(today, now_dt=now)
        await asyncio.to_thread(bot.send, schedule_text)

    elif cmd == "/tomorrow":
        import datetime

        from src.utils import clock

        tomorrow = clock.today_ist() + datetime.timedelta(days=1)
        schedule_text = format_day_schedule(tomorrow, now_dt=None)
        await asyncio.to_thread(bot.send, schedule_text)

    elif cmd in ("/timetable", "/schedule"):
        from src.utils import clock

        today = clock.today_ist()
        now = clock.now_ist()
        schedule_text = format_day_schedule(today, now_dt=now)
        reply = (
            f"📅 **Official Academic Timetable (KLEF T04 - S-10)**\n\n"
            f"{schedule_text}\n\n"
            f"💡 *Use `/today` or `/tomorrow` for live classes or `/exam` for lab dates.*"
        )
        await asyncio.to_thread(bot.send, reply)

    elif cmd == "/attendance":
        from src.erp import klu_erp

        await asyncio.to_thread(bot.send, "⏳ Fetching live attendance from KL ERP...")
        records = await klu_erp.get_attendance()
        if not records:
            await asyncio.to_thread(
                bot.send,
                "⚠️ Could not retrieve attendance from KL ERP.\n"
                "Please verify `ERP_USERNAME` and `ERP_PASSWORD` in `.env` or check portal status.",
            )
        else:
            lines = ["📊 **Live Attendance Overview (KL ERP)**:\n"]
            critical = []
            for r in records:
                pct = r["percentage"]
                status_icon = "🟢" if pct >= 85.0 else ("🟡" if pct >= 75.0 else "🔴")
                name_short = r["course_name"] or r["course_code"]
                ltps_tag = f" [{r['ltps']}]" if r.get("ltps") else ""
                line = (
                    f"{status_icon} **{name_short}**{ltps_tag} (`{r['course_code']}`)\n"
                    f"   • Attended: {r['attended']}/{r['conducted']} ({pct}%)\n"
                )
                if r["safe_bunks"] > 0:
                    line += f"   • Margin: **{r['safe_bunks']} safe bunks** remaining\n"
                elif r["recovery_needed"] > 0:
                    line += f"   • ⚠️ Needs **{r['recovery_needed']} classes** to reach 85%\n"
                    critical.append(f"{name_short}{ltps_tag}")
                lines.append(line)

            if critical:
                lines.append(
                    f"\n⚠️ **Action Required**: {len(critical)} components below 85% distinction!"
                )

            await asyncio.to_thread(bot.send, "\n".join(lines))

    elif cmd == "/marks":
        from src.erp import klu_erp

        await asyncio.to_thread(bot.send, "⏳ Fetching internal assessment marks from KL ERP...")
        marks = await klu_erp.get_marks()
        if not marks:
            await asyncio.to_thread(
                bot.send,
                "⚠️ No internal marks found or ERP unavailable.\n"
                "Ensure `ERP_USERNAME` and `ERP_PASSWORD` are configured.",
            )
        else:
            lines = ["📝 **Internal Assessment Marks (KL ERP)**:\n"]
            for m in marks[:15]:
                lines.append(
                    f"• **{m['course_name'] or m['course_code']}** — {m['component']}: "
                    f"**{m['secured_marks']} / {m['max_marks']}** ({m['percentage']}%)"
                )
            await asyncio.to_thread(bot.send, "\n".join(lines))

    elif cmd == "/cgpa":
        from src.erp import klu_erp

        await asyncio.to_thread(
            bot.send, "⏳ Fetching official academic transcript & CGPA from KL ERP..."
        )
        records = await klu_erp.get_cgpa()
        if not records:
            await asyncio.to_thread(
                bot.send,
                "⚠️ No CGPA transcript found or ERP unavailable.\n"
                "Ensure `ERP_USERNAME` and `ERP_PASSWORD` are configured.",
            )
        else:
            lines = ["🎓 **Academic Grades & Transcript (KL ERP)**:\n"]
            for r in records[:18]:
                gp = r["grade_point"]
                lines.append(
                    f"• **{r['course_code']}** ({r['grade']}): {r['course_name']}\n"
                    f"   Grade Point: **{gp}** | Credits: {r['credits']} | Term: {r['semester']}"
                )
            await asyncio.to_thread(bot.send, "\n".join(lines))

    elif cmd == "/fee":
        from src.erp import klu_erp

        await asyncio.to_thread(bot.send, "⏳ Fetching fee order details from KL ERP...")
        fees = await klu_erp.get_fee_orders()
        if not fees:
            await asyncio.to_thread(bot.send, "⚠️ No fee records found or ERP unavailable.")
        else:
            lines = ["💳 **Fee Orders & Receipts (KL ERP)**:\n"]
            for f in fees[:10]:
                lines.append(
                    f"• **Order {f['order_id']}** ({f['term']}): {f['amount']} "
                    f"— `{f['status']}` ({f['date']})"
                )
            await asyncio.to_thread(bot.send, "\n".join(lines))

    elif cmd in ("/rescan", "/scan"):
        if _active_client:
            await asyncio.to_thread(
                bot.send, "🔄 Starting deep multimodal rescan of course groups (past 7 days)..."
            )
            count = await catch_up_chats(_active_client, days=7, full_rescan=True)
            await asyncio.to_thread(
                bot.send,
                f"✅ **Deep Rescan Complete**\n"
                f"• Messages & files processed: {count}\n"
                f"• Monitored chats: {len(settings.allowed_chat_ids)}\n"
                f"• Type `/today` to review your updated schedule.",
            )
        else:
            await asyncio.to_thread(bot.send, "⚠️ Telegram client not available for rescan.")

    elif cmd in ("/deadlines", "/deadline", "/tasks"):
        from src.academic_calendar import load_calendar
        from src.utils import clock
        from src.utils.deduplication import deduplicator

        today = clock.today_ist()
        cal = load_calendar()
        milestones_list = []
        if cal:
            for term, term_dates in cal.terms.items():
                for m_name, m_date in term_dates.items():
                    if m_date >= today:
                        milestones_list.append((m_date, f"{m_name} ({term})"))
        milestones_list.sort(key=lambda x: x[0])

        pending_items = deduplicator.list_pending(limit=5)

        lines = [f"⏰ **Upcoming Deadlines & Milestones** (as of {today.strftime('%d %b %Y')}):\n"]
        if not milestones_list and not pending_items:
            lines.append("🎉 No upcoming deadlines registered in calendar or task tracker.")
        else:
            if milestones_list:
                lines.append("📅 **Academic Calendar Milestones**:")
                for m_date, m_label in milestones_list[:6]:
                    days_left = (m_date - today).days
                    if days_left == 0:
                        day_str = "today!"
                    elif days_left > 0:
                        day_str = f"in {days_left} days"
                    else:
                        day_str = ""
                    lines.append(f"• **{m_label}**: `{m_date.strftime('%d %b %Y')}` ({day_str})")
            if pending_items:
                lines.append("\n📝 **Pending Tasks & Class Deadlines**:")
                for item in pending_items:
                    ev = item.get("event", {})
                    summary = ev.get("summary") or ev.get("description") or "Assignment / Task"
                    lines.append(f"• **{summary}** (Status: `{item.get('status')}`)")

        await asyncio.to_thread(bot.send, "\n".join(lines))

    elif cmd in ("/exam", "/exams", "/viva"):
        reply = (
            "📝 **ESD & IoT Lab Exams & Defence (Section S-10)**:\n\n"
            "• **Lab In-Sem Exam**: 15 Oct 2026, 10:00 AM – 11:40 AM (P3-P4)\n"
            "  - Room: `103` | Faculty: Dr. Dinesh Kumar\n\n"
            "• **Project Defence & Demonstration**: 16 Oct 2026, 10:00 AM – 11:40 AM (P3-P4)\n"
            "  - Room: `14D` | Faculty: Dr. Dinesh Kumar | Lab Tech: Ms. Swathi\n\n"
            "💡 *Tip: Use `/ask <question>` (e.g. `/ask thermistor viva`) to review prep!*"
        )
        await asyncio.to_thread(bot.send, reply)

    elif cmd == "/ask":
        query_text = text[len(cmd) :].strip()
        if not query_text:
            msg_hint = "ℹ️ Please specify your question: `/ask <your question>`"
            await asyncio.to_thread(bot.send, msg_hint)
        else:
            from src.knowledge.retriever import knowledge_retriever

            initial_res = await asyncio.to_thread(bot.send, "💭 *Thinking...*")
            msg_id = (
                initial_res.get("result", {}).get("message_id")
                if isinstance(initial_res, dict)
                else None
            )

            ask_chunks: list[str] = []
            last_edit_ts = time.time()
            try:
                for chunk_text in knowledge_retriever.answer_stream(query_text):
                    ask_chunks.append(chunk_text)
                    now_ts = time.time()
                    if msg_id and (now_ts - last_edit_ts >= 0.35):
                        current_str = "".join(ask_chunks)
                        await asyncio.to_thread(
                            bot.edit, msg_id, f"💡 **Academic Intel Answer**:\n\n{current_str}"
                        )
                        last_edit_ts = now_ts

                final_answer = "".join(ask_chunks).strip()
                if msg_id:
                    await asyncio.to_thread(
                        bot.edit, msg_id, f"💡 **Academic Intel Answer**:\n\n{final_answer}"
                    )
                else:
                    await asyncio.to_thread(
                        bot.send, f"💡 **Academic Intel Answer**:\n\n{final_answer}"
                    )
            except Exception as e:
                logger.warning("Streaming ask failed, falling back to static", error=str(e))
                answer_text = await asyncio.to_thread(knowledge_retriever.answer, query_text)
                if msg_id:
                    await asyncio.to_thread(
                        bot.edit, msg_id, f"💡 **Academic Intel Answer**:\n\n{answer_text}"
                    )
                else:
                    await asyncio.to_thread(
                        bot.send, f"💡 **Academic Intel Answer**:\n\n{answer_text}"
                    )

    elif cmd == "/undo":
        await handle_undo_command(msg)

    elif cmd in ("/bunk", "/margins"):
        import json

        from src.briefing import format_bunk_calculator
        from src.utils.deduplication import deduplicator

        cached_att = deduplicator.meta_get("erp_attendance_cache")
        records = None
        if cached_att:
            try:
                records = json.loads(cached_att)
            except Exception:
                records = None

        if records:
            att_rows = [
                {
                    "course": r.get("course_name") or r.get("course_code"),
                    "code": r.get("course_code", ""),
                    "attended": r.get("attended"),
                    "held": r.get("conducted"),
                }
                for r in records
            ]
            reply = format_bunk_calculator(att_rows)
            await asyncio.to_thread(bot.send, reply)
            from src.erp import klu_erp

            asyncio.create_task(klu_erp.get_attendance())
        else:
            from src.erp import klu_erp

            await asyncio.to_thread(
                bot.send, "⏳ Calculating attendance bunk margins from KL ERP..."
            )
            records = await klu_erp.get_attendance()
            if records:
                att_rows = [
                    {
                        "course": r.get("course_name") or r.get("course_code"),
                        "code": r.get("course_code", ""),
                        "attended": r.get("attended"),
                        "held": r.get("conducted"),
                    }
                    for r in records
                ]
                reply = format_bunk_calculator(att_rows)
                await asyncio.to_thread(bot.send, reply)
            else:
                await asyncio.to_thread(bot.send, "⚠️ Could not retrieve attendance from KL ERP.")

    elif cmd in ("/briefing", "/digest"):
        from src.briefing import build_briefing, fetch_briefing_inputs
        from src.utils import clock

        await asyncio.to_thread(bot.send, "⏳ Compiling today's academic briefing...")
        inputs = await fetch_briefing_inputs()
        text_briefing = build_briefing(clock.now_ist(), *inputs)
        await asyncio.to_thread(bot.send, text_briefing)

    elif cmd in ("/quarantine", "/quarantined"):
        from src.governance.audit import audit_logger
        from src.governance.policy_engine import PolicyVerdict

        records = audit_logger.get_audit_trail(limit=5, verdict=PolicyVerdict.QUARANTINED.value)
        if not records:
            await asyncio.to_thread(
                bot.send, "🛡️ **Quarantine Console**: Zero quarantined messages. All clear!"
            )
        else:
            lines = [f"🛡️ **Quarantine Console** ({len(records)} recent isolated events):\n"]
            for r in records:
                ev_short = r["event_id"][:8]
                ts_str = time.strftime("%d %b %H:%M", time.localtime(r["timestamp"]))
                lines.append(
                    f"• **ID `{ev_short}`** ({ts_str})\n"
                    f"  - Sender: `{r['sender_id']}` in Chat `{r['channel_id']}`\n"
                    f"  - Reason: {r['details']}\n"
                    f"  - Inspect: `/quarantine_inspect {r['event_id']}`"
                )
            await asyncio.to_thread(bot.send, "\n".join(lines))

    elif cmd.startswith("/quarantine_inspect"):
        from src.governance.audit import audit_logger

        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await asyncio.to_thread(bot.send, "ℹ️ Usage: `/quarantine_inspect <event_id>`")
        else:
            target_id = parts[1].strip()
            rec = None
            if len(target_id) < 64:
                all_rec = audit_logger.get_audit_trail(limit=50)
                for r in all_rec:
                    if r["event_id"].startswith(target_id):
                        rec = r
                        break
            else:
                rec = audit_logger.get_record(target_id)

            if not rec:
                await asyncio.to_thread(bot.send, f"⚠️ Quarantine record `{target_id}` not found.")
            else:
                ts_val = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rec["timestamp"]))
                info = (
                    f"🔍 **Quarantine Record Inspection**\n\n"
                    f"• **Event ID**: `{rec['event_id']}`\n"
                    f"• **Timestamp**: `{ts_val}`\n"
                    f"• **Trust Tier**: `{rec['source_trust_tier']}`\n"
                    f"• **Verdict**: `{rec['policy_verdict']}`\n"
                    f"• **Risk Tier**: `{rec['risk_tier']}`\n"
                    f"• **Channel**: `{rec['channel_id']}` | **Sender**: `{rec['sender_id']}`\n"
                    f"• **Details**: {rec['details']}\n"
                    f"• **Raw Fingerprint**: `{rec['raw_fingerprint']}`"
                )
                await asyncio.to_thread(bot.send, info)

    else:
        reply_sent = False
        if not text.startswith("/"):
            from src.knowledge.retriever import knowledge_retriever

            initial_res = await asyncio.to_thread(bot.send, "💭 *Thinking...*")
            msg_id = (
                initial_res.get("result", {}).get("message_id")
                if isinstance(initial_res, dict)
                else None
            )

            intel_chunks: list[str] = []
            intel_last_edit_ts = time.time()
            try:
                for chunk_text in knowledge_retriever.answer_stream(text):
                    intel_chunks.append(chunk_text)
                    intel_now_ts = time.time()
                    if msg_id and (intel_now_ts - intel_last_edit_ts >= 0.35):
                        await asyncio.to_thread(bot.edit, msg_id, f"💡 {''.join(intel_chunks)}")
                        intel_last_edit_ts = intel_now_ts

                final_answer = "".join(intel_chunks).strip()
                if (
                    final_answer
                    and "Information not provided" not in final_answer
                    and len(final_answer) > 5
                ):
                    if msg_id:
                        await asyncio.to_thread(bot.edit, msg_id, f"💡 {final_answer}")
                    else:
                        await asyncio.to_thread(bot.send, f"💡 {final_answer}")
                    reply_sent = True
            except Exception as e:
                logger.debug("Streaming intel answer failed", error=str(e))

        if not reply_sent and settings.gemini_api_key.get_secret_value():
            try:
                from google import genai

                client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
                prompt = (
                    "You are the helpful personal college assistant for Tejaswin Amara (KLEF).\n"
                    f"Answer this query concisely in 1-3 sentences:\n\n{text}"
                )
                initial_res = await asyncio.to_thread(bot.send, "💭 *Thinking...*")
                msg_id = (
                    initial_res.get("result", {}).get("message_id")
                    if isinstance(initial_res, dict)
                    else None
                )
                stream = client.models.generate_content_stream(
                    model=settings.gemini_model,
                    contents=prompt,
                )
                gemini_chunks: list[str] = []
                gemini_last_edit_ts = time.time()
                for chunk in stream:
                    if chunk.text:
                        gemini_chunks.append(chunk.text)
                        gemini_now_ts = time.time()
                        if msg_id and (gemini_now_ts - gemini_last_edit_ts >= 0.35):
                            await asyncio.to_thread(
                                bot.edit, msg_id, f"🤖 {''.join(gemini_chunks)}"
                            )
                            gemini_last_edit_ts = gemini_now_ts

                final_text = "".join(gemini_chunks).strip()
                if final_text:
                    if msg_id:
                        await asyncio.to_thread(bot.edit, msg_id, f"🤖 {final_text}")
                    else:
                        await asyncio.to_thread(bot.send, f"🤖 {final_text}")
                    reply_sent = True
            except Exception as e:
                logger.warning("Gemini command reply failed", error=str(e))

        if not reply_sent:
            await asyncio.to_thread(
                bot.send,
                f'🤖 Received: "{text}"\nUse `/help` for commands or `/today` for your schedule.',
            )


async def catch_up_chats(client: TelegramClient, days: int = 7, full_rescan: bool = False) -> int:
    from src.utils import clock

    total_scanned = 0
    cutoff = clock.now_ist() - timedelta(days=days)

    for chat_id in settings.allowed_chat_ids:
        try:
            last_id = deduplicator.get_chat_state(chat_id)
            if last_id is None and not full_rescan:
                messages = await client.get_messages(chat_id, limit=1)
                if messages:
                    deduplicator.update_chat_state(chat_id, messages[0].id)
                continue

            if last_id is None:
                messages = await client.get_messages(chat_id, limit=200)
                msgs_to_process = list(reversed(messages))
            else:
                messages = await client.get_messages(
                    chat_id, min_id=last_id, reverse=True, limit=200
                )
                msgs_to_process = list(messages)

            if len(messages) == 200:
                logger.warning("Catch-up truncated at 200 messages", chat_id=chat_id)

            for msg in msgs_to_process:
                is_out = getattr(msg, "out", False)
                if getattr(msg, "date", None) and msg.date >= cutoff and not is_out:
                    await process_message(client, chat_id, msg)
                    total_scanned += 1
                if hasattr(msg, "id"):
                    deduplicator.update_chat_state(chat_id, msg.id)

        except Exception as e:
            logger.warning("Failed to catch up chat", chat_id=chat_id, error=str(e))

    return total_scanned


def register_handlers(client: TelegramClient) -> None:
    global _active_client
    _active_client = client

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
