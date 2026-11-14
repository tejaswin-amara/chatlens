"""Autonomous Academic ERP Sync Agent for ChatLens & SPARK.

Periodically crawls KLU ERP for active term records (Y25 T05),
detects attendance/marks/seating deltas, updates cache in spark.db,
and alerts OWNER_CHAT_ID via Telegram.
"""

import asyncio
import json
import math
from datetime import date, datetime, time, timedelta
from typing import Any

from src.config import settings
from src.erp.client import klu_erp
from src.erp.scrapers import compute_remaining_classes
from src.formatting.markdown_safety import sanitize_markdown
from src.timetable import T05_COURSE_METADATA
from src.utils import clock
from src.utils.deduplication import deduplicator
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Daytime Keep-Alive parameters:
# 15 minutes (900s) during active academic hours 07:00–18:00 IST
KEEP_ALIVE_INTERVAL_SECONDS: float = 15 * 60.0


def is_daytime_academic_hours(now: datetime) -> bool:
    """Check if current time is within daytime academic hours (Mon-Sat 07:00–18:00 IST)."""
    if now.tzinfo is None:
        raise ValueError("now must be a timezone-aware datetime")
    # Mon=0, ..., Sat=5; Sun=6 (skip Sunday)
    if now.weekday() == 6:
        return False
    start_t = time(7, 0)
    end_t = time(18, 0)
    return start_t <= now.time() <= end_t


async def erp_keep_alive_ping() -> bool:
    """Ping KLU ERP /index.php with current session cookies to maintain an active PHP session."""
    if not settings.erp_username or not settings.erp_password.get_secret_value():
        logger.debug("ERP credentials unconfigured; skipping keep-alive ping")
        return False

    index_url = f"{klu_erp.base_url}/index.php"
    try:
        if not klu_erp._cookies:
            logger.info("No cached ERP session for keep-alive. Performing initial login...")
            return await klu_erp.login()

        async with klu_erp._get_http_client() as client:
            res = await client.get(index_url)
            if klu_erp._is_session_expired(res):
                logger.info("ERP session expired during keep-alive ping. Re-authenticating...")
                return await klu_erp.login()

            logger.debug("ERP keep-alive ping successful", status_code=res.status_code)
            deduplicator.meta_set("last_erp_keep_alive_ts", str(clock.now_ist().timestamp()))
            return True
    except Exception as e:
        logger.warning("ERP keep-alive ping encountered error", error=str(e))
        return False


async def run_erp_keep_alive(stop_event: asyncio.Event | None = None) -> None:
    """Daytime keep-alive loop pinging /index.php every 15 minutes (07:00–18:00 IST)."""
    if stop_event is None:
        stop_event = asyncio.Event()

    logger.info(
        "Academic ERP keep-alive worker started (Schedule: Mon-Sat 07:00-18:00 IST, 15m interval)"
    )

    while not stop_event.is_set():
        now = clock.now_ist()
        if is_daytime_academic_hours(now):
            try:
                await erp_keep_alive_ping()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("Error during ERP keep-alive ping", error=str(e))

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=KEEP_ALIVE_INTERVAL_SECONDS)
            break
        except TimeoutError:
            pass
        except asyncio.CancelledError:
            raise


# Scheduled crawl trigger times (Mon–Sat in IST):
# 07:15 AM (Morning briefing pre-check)
# 01:15 PM (Mid-day post-lunch refresh)
# 05:15 PM & 05:30 PM (Evening wrap-up)
SYNC_SCHEDULE_TIMES: list[tuple[int, int]] = [
    (7, 15),
    (13, 15),
    (17, 15),
    (17, 30),
]


def next_sync_run(now: datetime) -> datetime:
    """Calculate the next scheduled sync execution time in IST (Mon-Sat)."""
    if now.tzinfo is None:
        raise ValueError("now must be a timezone-aware datetime")

    current_date = now.date()

    # Search up to 7 days ahead to find the next valid scheduled slot
    for day_offset in range(8):
        candidate_date = current_date + timedelta(days=day_offset)
        # Mon=0, ..., Sat=5; Sun=6 (skip Sunday)
        if candidate_date.weekday() == 6:
            continue

        for hour, minute in SYNC_SCHEDULE_TIMES:
            slot_dt = datetime.combine(candidate_date, time(hour, minute), tzinfo=clock.IST)
            if slot_dt > now:
                return slot_dt

    # Fallback: next day 07:15 AM
    fallback = now.replace(hour=7, minute=15, second=0, microsecond=0) + timedelta(days=1)
    return fallback


def enrich_course_record(
    record: dict[str, Any],
    ref_date: date | None = None,
    last_instruction_day: date | None = None,
) -> dict[str, Any]:
    """Enrich scraped attendance record with Cluster 4 curriculum metadata."""
    code = record.get("course_code", "").strip()
    name = record.get("course_name", "").strip()
    enriched = dict(record)

    # Search Cluster 4 metadata for matching course code
    meta = next((m for m in T05_COURSE_METADATA.values() if m.code == code), None)
    if meta:
        if not enriched.get("course_name") or enriched["course_name"] == code:
            enriched["course_name"] = meta.name
        enriched["category"] = meta.category
        enriched["credits"] = meta.credits
        if not enriched.get("section"):
            enriched["section"] = meta.section
        if meta.faculty:
            enriched["faculty"] = meta.faculty

    # Compute both 75% floor and 85% distinction margins
    attended = enriched.get("attended", 0)
    conducted = enriched.get("conducted", 0)

    if conducted > 0:
        enriched["safe_bunks_75"] = (
            max(0, math.floor((100 * attended - 75 * conducted) / 75))
            if 100 * attended >= 75 * conducted
            else 0
        )
        enriched["safe_bunks_85"] = (
            max(0, math.floor((100 * attended - 85 * conducted) / 85))
            if 100 * attended >= 85 * conducted
            else 0
        )
        enriched["recovery_needed"] = (
            max(0, math.ceil((85 * conducted - 100 * attended) / 15))
            if 100 * attended < 85 * conducted
            else 0
        )
        enriched["recovery_needed_75"] = (
            max(0, math.ceil((75 * conducted - 100 * attended) / 25))
            if 100 * attended < 75 * conducted
            else 0
        )
    else:
        enriched["safe_bunks_75"] = 0
        enriched["safe_bunks_85"] = 0
        enriched["recovery_needed"] = 0
        enriched["recovery_needed_75"] = 0

    # Remaining classes and hard detention lockout calculation
    if "remaining_classes" not in enriched or enriched["remaining_classes"] is None:
        enriched["remaining_classes"] = compute_remaining_classes(
            course_code=code,
            course_name=name,
            ref_date=ref_date,
            last_instruction_day=last_instruction_day,
        )

    rem_classes = enriched.get("remaining_classes")
    rec_85 = enriched.get("recovery_needed", 0)
    rec_75 = enriched.get("recovery_needed_75", 0)

    # Flag hard detention when required recovery exceeds remaining classes
    hard_detention = bool(
        rem_classes is not None
        and ((rec_85 > 0 and rec_85 > rem_classes) or (rec_75 > 0 and rec_75 > rem_classes))
    )
    enriched["hard_detention"] = hard_detention
    enriched["detention_lockout"] = hard_detention

    return enriched


def format_attendance_delta_alert(deltas: list[dict[str, Any]], now_dt: datetime) -> str:
    """Format structured markdown alert for detected attendance changes."""
    date_str = now_dt.strftime("%d %b %Y, %I:%M %p")
    lines: list[str] = [
        "📊 **Attendance Update Detected (KL ERP — Y25 T05)**",
        f"🕒 *Crawl Timestamp: {date_str} IST*",
        "",
    ]

    for d in deltas:
        c_name = d.get("course_name") or d.get("course_code") or "Course"
        c_code = d.get("course_code", "")
        ltps = f" [{d['ltps']}]" if d.get("ltps") else ""
        attended = d.get("attended", 0)
        conducted = d.get("conducted", 0)
        pct = d.get("percentage", 0.0)

        diff_str = d.get("diff_summary", "")
        safe_85 = d.get("safe_bunks_85", 0)
        safe_75 = d.get("safe_bunks_75", 0)
        recovery = d.get("recovery_needed", 0)
        hard_detention = d.get("hard_detention", False)
        rem_classes = d.get("remaining_classes")

        lines.append(f"• **{c_name}**{ltps} (`{c_code}`)")
        lines.append(f"  └ Attended: **{attended}/{conducted}** ({pct:.1f}%) | Delta: {diff_str}")

        if hard_detention:
            rem_str = f"{rem_classes}" if rem_classes is not None else "0"
            lines.append(
                f"  └ 🚨 **HARD DETENTION LOCKOUT**: Requires **{recovery} classes** for 85%, "
                f"but only **{rem_str} classes** remain in term!"
            )
        elif recovery > 0:
            lines.append(f"  └ ⚠️ Recovery: Needs **{recovery} consecutive classes** to reach 85%")
        else:
            lines.append(
                f"  └ Margin: **{safe_85} safe bunks** (≥85%) | **{safe_75} safe bunks** (≥75%)"
            )
        lines.append("")

    lines.append(
        "💡 *Target distinction threshold is 85.0%. "
        "Type `/attendance` or `/bunk` for full overview.*"
    )
    return sanitize_markdown("\n".join(lines))


class AcademicERPSyncAgent:
    """Autonomous synchronization engine for KLU ERP."""

    def __init__(
        self,
        academic_year: str = "29",
        semester_id: str = "2",
        term_label: str = "Y25 T05",
    ) -> None:
        self.academic_year = academic_year
        self.semester_id = semester_id
        self.term_label = term_label

    async def sync_once(self, send_alerts: bool = True) -> dict[str, Any]:
        """Execute a single sync pass, detect deltas, update cache, and dispatch alerts."""
        if not settings.erp_username or not settings.erp_password.get_secret_value():
            logger.warning("ERP credentials unconfigured; skipping ERP sync pass")
            return {"success": False, "reason": "Unconfigured ERP credentials"}

        logger.info(
            "Starting scheduled ERP sync pass",
            academic_year=self.academic_year,
            semester_id=self.semester_id,
            term=self.term_label,
        )

        now_dt = clock.now_ist()
        sync_result: dict[str, Any] = {
            "success": True,
            "timestamp": now_dt.isoformat(),
            "attendance_deltas": 0,
            "marks_deltas": 0,
            "seating_deltas": 0,
        }

        # 1. Attendance Scraping & Delta Detection
        try:
            raw_records = await klu_erp.get_attendance(
                academic_year=self.academic_year, semester_id=self.semester_id
            )
            if raw_records:
                records = [enrich_course_record(r) for r in raw_records]
                deltas = self._detect_attendance_deltas(records)
                sync_result["attendance_deltas"] = len(deltas)

                # Persist updated cache and sync timestamp
                deduplicator.meta_set("erp_attendance_cache", json.dumps(records))
                deduplicator.meta_set("last_attendance_sync_ts", str(now_dt.timestamp()))

                if deltas:
                    try:
                        deduplicator.add_outbox_event(
                            event_type="erp.attendance_update",
                            payload={
                                "timestamp": now_dt.isoformat(),
                                "term": self.term_label,
                                "academic_year": self.academic_year,
                                "semester_id": self.semester_id,
                                "deltas_count": len(deltas),
                                "deltas": deltas,
                            },
                        )
                        logger.info("Emitted erp.attendance_update outbox event", count=len(deltas))
                    except Exception as outbox_err:
                        logger.warning(
                            "Failed to emit attendance outbox event", error=str(outbox_err)
                        )

                    if send_alerts:
                        alert_text = format_attendance_delta_alert(deltas, now_dt)
                        await self._dispatch_alert(alert_text)
                        logger.info(
                            "Attendance deltas dispatched to owner",
                            count=len(deltas),
                        )
        except Exception as att_err:
            logger.warning("Attendance sync cycle failed", error=str(att_err))
            sync_result["attendance_error"] = str(att_err)

        # 400ms rate-limit spacing between sequential ERP requests
        await asyncio.sleep(0.4)

        # 2. Internal Marks Scraping & Delta Detection
        try:
            marks = await klu_erp.get_marks(
                academic_year=self.academic_year, semester_id=self.semester_id
            )
            if marks:
                marks_deltas = self._detect_marks_deltas(marks)
                sync_result["marks_deltas"] = len(marks_deltas)
                if marks_deltas:
                    try:
                        deduplicator.add_outbox_event(
                            event_type="erp.marks_update",
                            payload={
                                "timestamp": now_dt.isoformat(),
                                "term": self.term_label,
                                "academic_year": self.academic_year,
                                "semester_id": self.semester_id,
                                "deltas_count": len(marks_deltas),
                                "deltas": marks_deltas,
                            },
                        )
                        logger.info(
                            "Emitted erp.marks_update outbox event", count=len(marks_deltas)
                        )
                    except Exception as outbox_err:
                        logger.warning("Failed to emit marks outbox event", error=str(outbox_err))

                    if send_alerts:
                        alert_text = self._format_marks_delta_alert(marks_deltas, now_dt)
                        await self._dispatch_alert(alert_text)
                        logger.info("Internal marks deltas dispatched", count=len(marks_deltas))
        except Exception as marks_err:
            logger.warning("Marks sync cycle failed", error=str(marks_err))
            sync_result["marks_error"] = str(marks_err)

        # 400ms rate-limit spacing between sequential ERP requests
        await asyncio.sleep(0.4)

        # 3. Exam Seating Allocations Check
        try:
            seating = await klu_erp.get_exam_seating()
            if seating:
                seating_deltas = self._detect_seating_deltas(seating)
                sync_result["seating_deltas"] = len(seating_deltas)
                if seating_deltas and send_alerts:
                    alert_text = self._format_seating_delta_alert(seating_deltas, now_dt)
                    await self._dispatch_alert(alert_text)
                    logger.info("Exam seating deltas dispatched", count=len(seating_deltas))
        except Exception as seat_err:
            logger.warning("Exam seating sync cycle failed", error=str(seat_err))
            sync_result["seating_error"] = str(seat_err)

        deduplicator.meta_set("last_erp_sync_summary", json.dumps(sync_result))
        return sync_result

    def _detect_attendance_deltas(
        self, current_records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Compare scraped records against cached baseline to find deltas."""
        cached_raw = deduplicator.meta_get("erp_attendance_cache")
        if not cached_raw:
            # Baseline initialization — no deltas on initial empty cache
            logger.info("Baseline attendance cache populated", count=len(current_records))
            return []

        try:
            cached_list = json.loads(cached_raw)
            cached_map = {f"{r.get('course_code')}:{r.get('ltps', '')}": r for r in cached_list}
        except Exception:
            return []

        deltas: list[dict[str, Any]] = []
        for curr in current_records:
            key = f"{curr.get('course_code')}:{curr.get('ltps', '')}"
            prev = cached_map.get(key)
            if not prev:
                # Newly added component
                delta_item = dict(curr)
                delta_item["diff_summary"] = "🆕 **New course component registered**"
                deltas.append(delta_item)
                continue

            prev_cond = prev.get("conducted", 0)
            curr_cond = curr.get("conducted", 0)
            prev_att = prev.get("attended", 0)
            curr_att = curr.get("attended", 0)
            prev_pct = prev.get("percentage", 0.0)
            curr_pct = curr.get("percentage", 0.0)

            if curr_cond != prev_cond or curr_att != prev_att or curr_pct != prev_pct:
                att_diff = curr_att - prev_att
                cond_diff = curr_cond - prev_cond

                if att_diff > 0 and cond_diff > 0 and att_diff == cond_diff:
                    diff_str = f"🟢 **+{att_diff} class{'es' if att_diff > 1 else ''} attended**"
                elif att_diff == 0 and cond_diff > 0:
                    diff_str = f"🔴 **+{cond_diff} absence{'s' if cond_diff > 1 else ''} recorded**"
                elif att_diff > 0 and cond_diff > att_diff:
                    abs_diff = cond_diff - att_diff
                    diff_str = f"🟡 **+{att_diff} attended, +{abs_diff} absent**"
                else:
                    pct_change = curr_pct - prev_pct
                    diff_str = f"📈 **Percentage updated ({pct_change:+.1f}%)**"

                delta_item = dict(curr)
                delta_item["diff_summary"] = diff_str
                deltas.append(delta_item)

        return deltas

    def _detect_marks_deltas(self, current_marks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cached_raw = deduplicator.meta_get("erp_marks_cache")
        if not cached_raw:
            return []
        try:
            cached_list = json.loads(cached_raw)
            cached_keys = {
                f"{m.get('course_code')}:{m.get('component')}:{m.get('secured_marks')}"
                for m in cached_list
            }
        except Exception:
            return []

        new_marks = []
        for m in current_marks:
            key = f"{m.get('course_code')}:{m.get('component')}:{m.get('secured_marks')}"
            if key not in cached_keys:
                new_marks.append(m)
        return new_marks

    def _detect_seating_deltas(self, current_seating: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cached_raw = deduplicator.meta_get("erp_exam_seating_cache")
        if not cached_raw:
            deduplicator.meta_set("erp_exam_seating_cache", json.dumps(current_seating))
            return current_seating if current_seating else []
        try:
            cached_list = json.loads(cached_raw)
            cached_keys = {
                f"{s.get('course_code')}:{s.get('exam_date')}:{s.get('room_no')}"
                for s in cached_list
            }
        except Exception:
            return []

        new_seats = []
        for s in current_seating:
            key = f"{s.get('course_code')}:{s.get('exam_date')}:{s.get('room_no')}"
            if key not in cached_keys:
                new_seats.append(s)

        if new_seats:
            deduplicator.meta_set("erp_exam_seating_cache", json.dumps(current_seating))
        return new_seats

    def _format_marks_delta_alert(self, marks: list[dict[str, Any]], now_dt: datetime) -> str:
        lines = [
            "📝 **Internal Assessment Marks Update (KL ERP — Y25 T05)**",
            f"🕒 *Crawl Timestamp: {now_dt.strftime('%d %b %Y, %I:%M %p')} IST*",
            "",
        ]
        for m in marks:
            c_name = m.get("course_name") or m.get("course_code") or "Course"
            lines.append(f"• **{c_name}** (`{m.get('course_code', '')}`)")
            score_str = f"Score: **{m.get('secured_marks')} / {m.get('max_marks')}**"
            pct_str = f"({m.get('percentage', 0.0)}%)"
            comp_name = m.get("component", "Assessment")
            score_part = f"{score_str} {pct_str}"
            lines.append(f"  └ Component: **{comp_name}** — {score_part}")
            lines.append("")
        return sanitize_markdown("\n".join(lines))

    def _format_seating_delta_alert(self, seating: list[dict[str, Any]], now_dt: datetime) -> str:
        lines = [
            "🏛️ **Exam Seating Allotment Published (KL ERP)**",
            f"🕒 *Crawl Timestamp: {now_dt.strftime('%d %b %Y, %I:%M %p')} IST*",
            "",
        ]
        for s in seating:
            c_code = s.get("course_code", "")
            lines.append(f"• **{c_code}** — Date: `{s.get('exam_date', 'TBD')}`")
            lines.append(
                f"  └ Room: **{s.get('room_no', 'TBD')}** | Slot: {s.get('exam_slot', 'TBD')} "
                f"| Type: {s.get('exam_type', 'Exam')}"
            )
            lines.append("")
        return sanitize_markdown("\n".join(lines))

    async def _dispatch_alert(self, text: str) -> None:
        """Strictly dispatches alert to OWNER_CHAT_ID (never to public chats)."""
        if not settings.bot_token or not settings.owner_chat_id:
            logger.info("Bot credentials missing; alert logged locally", length=len(text))
            return
        from src.notify.bot import bot

        try:
            await asyncio.to_thread(bot.send, text, chat_id=settings.owner_chat_id)
        except Exception as e:
            logger.error("Failed to dispatch ERP delta alert to owner", error=str(e))


erp_sync_agent = AcademicERPSyncAgent()


async def run_erp_sync(stop_event: asyncio.Event | None = None) -> None:
    """Supervised worker loop for scheduled academic ERP sync and keep-alive."""
    if stop_event is None:
        stop_event = asyncio.Event()
    logger.info(
        "Academic ERP sync scheduler started",
        schedule="Mon-Sat 07:15, 13:15, 17:15, 17:30 IST",
        keep_alive="15m",
    )

    keep_alive_task = asyncio.create_task(run_erp_keep_alive(stop_event))

    try:
        while not stop_event.is_set():
            now = clock.now_ist()
            target = next_sync_run(now)
            sleep_sec = max(1.0, (target - now).total_seconds())

            logger.debug(
                "ERP sync sleeping until next scheduled run",
                next_run=target.isoformat(),
                sleep_seconds=round(sleep_sec, 1),
            )

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=sleep_sec)
                break
            except TimeoutError:
                pass
            except asyncio.CancelledError:
                raise

            if stop_event.is_set():
                break

            # Execute scheduled crawl
            try:
                await erp_sync_agent.sync_once(send_alerts=True)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(
                    "Unhandled error during scheduled ERP sync",
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(60.0)
    finally:
        keep_alive_task.cancel()
        try:
            await keep_alive_task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("ERP keep-alive task cleanup error", error=str(e))
