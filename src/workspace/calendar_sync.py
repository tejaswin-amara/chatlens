"""Google Calendar Adapter for timetable room overrides and holiday event syncing."""

from datetime import datetime, timedelta
from typing import Any

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config import settings
from src.utils import clock
from src.utils.logging import get_logger
from src.workspace.auth import workspace_auth

logger = get_logger(__name__)


class CalendarSync:
    def __init__(self, calendar_id: str | None = None, auth_adapter: Any = None) -> None:
        self.calendar_id = calendar_id or settings.google_calendar_id
        self.auth = auth_adapter or workspace_auth

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(lambda e: not isinstance(e, LookupError)),
    )
    def update_class_room(
        self,
        course_name: str | None,
        course_code: str | None,
        new_room: str,
        target_date: str,
        period: str | None = None,
    ) -> dict[str, Any]:
        service = self.auth.get_calendar_service()

        dt = datetime.strptime(target_date, "%Y-%m-%d")
        time_min = dt.replace(hour=0, minute=0, second=0).isoformat() + "Z"
        time_max = dt.replace(hour=23, minute=59, second=59).isoformat() + "Z"

        events_result = (
            service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                timeZone="Asia/Kolkata",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = events_result.get("items", [])

        search_terms = [t.upper() for t in (course_code, course_name) if t]
        matched_events = []

        period_start = None
        period_end = None
        if period:
            import re

            m = re.search(r"P(\d+)", period)
            m_end = re.search(r"-P(\d+)", period)
            if m:
                p_start = int(m.group(1))
                p_end = int(m_end.group(1)) if m_end else p_start

                period_map = {
                    1: ("08:10", "09:00"),
                    2: ("09:00", "09:50"),
                    3: ("10:00", "10:50"),
                    4: ("10:50", "11:40"),
                    5: ("11:50", "12:40"),
                    7: ("13:20", "14:10"),
                    8: ("14:20", "15:10"),
                    9: ("15:10", "16:00"),
                }

                if p_start in period_map and p_end in period_map:
                    start_str = period_map[p_start][0]
                    end_str = period_map[p_end][1]
                    period_start = datetime.strptime(
                        f"{target_date} {start_str}", "%Y-%m-%d %H:%M"
                    ) - timedelta(minutes=1)
                    period_end = datetime.strptime(
                        f"{target_date} {end_str}", "%Y-%m-%d %H:%M"
                    ) + timedelta(minutes=1)
                elif "14:20" in period:
                    period_start = datetime.strptime(
                        f"{target_date} 14:20", "%Y-%m-%d %H:%M"
                    ) - timedelta(minutes=1)
                    period_end = datetime.strptime(
                        f"{target_date} 15:10", "%Y-%m-%d %H:%M"
                    ) + timedelta(minutes=1)

        if search_terms:
            for item in items:
                summary = item.get("summary", "").upper()
                description = item.get("description", "").upper()
                text_to_search = f"{summary} {description}"
                if any(term in text_to_search for term in search_terms):
                    if period_start and period_end:
                        start_time_str = item.get("start", {}).get("dateTime")
                        if start_time_str:
                            start_time = (
                                datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                                .astimezone(clock.IST)
                                .replace(tzinfo=None)
                            )
                            if period_start <= start_time <= period_end:
                                matched_events.append(item)
                    else:
                        matched_events.append(item)

        if len(matched_events) == 0:
            raise LookupError(
                f"No events found matching course {course_code or course_name} and period {period}"
            )
        elif len(matched_events) > 1:
            raise LookupError(
                f"Multiple events found matching course {course_code or course_name} "
                f"and period {period}"
            )

        matched_event = matched_events[0]

        reminders_override = {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 10}],
        }

        prior_state = {
            "location": matched_event.get("location"),
            "reminders": matched_event.get("reminders"),
            "extendedProperties": matched_event.get("extendedProperties"),
        }

        event_id = matched_event["id"]
        current_location = matched_event.get("location", "")
        if current_location == f"Room {new_room}":
            return matched_event

        patch_body = {
            "location": f"Room {new_room}",
            "reminders": reminders_override,
            "extendedProperties": {"private": {"spark_override": "1"}},
        }
        updated = (
            service.events()
            .patch(calendarId=self.calendar_id, eventId=event_id, body=patch_body)
            .execute()
        )

        import json
        import time

        from src.utils.db import get_connection

        with get_connection() as conn:
            conn.execute(
                "INSERT INTO writes (ts, kind, event_id, prior_json) VALUES (?, ?, ?, ?)",
                (time.time(), "patch", event_id, json.dumps(prior_state)),
            )
        logger.info(
            "Updated calendar class room",
            event_id=event_id,
            room=new_room,
            target_date=target_date,
        )
        return updated

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(lambda e: not isinstance(e, LookupError)),
    )
    def create_holiday_event(self, reason: str, target_date: str) -> dict[str, Any]:
        service = self.auth.get_calendar_service()

        dt = datetime.strptime(target_date, "%Y-%m-%d")
        next_day = (dt + timedelta(days=1)).strftime("%Y-%m-%d")

        time_min = dt.isoformat() + "Z"
        time_max = (dt + timedelta(days=1)).isoformat() + "Z"

        existing = (
            service.events()
            .list(
                calendarId=self.calendar_id, timeMin=time_min, timeMax=time_max, singleEvents=True
            )
            .execute()
        )

        expected_summary = f"University Holiday: {reason}"
        for item in existing.get("items", []):
            if item.get("summary") == expected_summary:
                return item

        event_body = {
            "summary": expected_summary,
            "description": f"Official Holiday Circular: {reason}",
            "start": {"date": target_date},
            "end": {"date": next_day},
            "reminders": {"useDefault": False, "overrides": []},
            "transparency": "transparent",
        }

        created = service.events().insert(calendarId=self.calendar_id, body=event_body).execute()
        import json
        import time

        from src.utils.db import get_connection

        with get_connection() as conn:
            conn.execute(
                "INSERT INTO writes (ts, kind, event_id, prior_json) VALUES (?, ?, ?, ?)",
                (
                    time.time(),
                    "insert",
                    created["id"],
                    json.dumps({"action": "delete", "source": "calendar"}),
                ),
            )
        logger.info("Created university holiday event", reason=reason, target_date=target_date)
        return created

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(lambda e: not isinstance(e, LookupError)),
    )
    def cancel_class(
        self,
        course_name: str | None,
        course_code: str | None,
        target_date: str,
        period: str | None = None,
    ) -> dict[str, Any]:
        service = self.auth.get_calendar_service()

        dt = datetime.strptime(target_date, "%Y-%m-%d")
        time_min = dt.replace(hour=0, minute=0, second=0).isoformat() + "Z"
        time_max = dt.replace(hour=23, minute=59, second=59).isoformat() + "Z"

        events_result = (
            service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                timeZone="Asia/Kolkata",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = events_result.get("items", [])

        search_terms = [t.upper() for t in (course_code, course_name) if t]
        matched_events = []

        period_start = None
        period_end = None
        if period:
            import re

            m = re.search(r"P(\d+)", period)
            m_end = re.search(r"-P(\d+)", period)
            if m:
                p_start = int(m.group(1))
                p_end = int(m_end.group(1)) if m_end else p_start

                period_map = {
                    1: ("08:10", "09:00"),
                    2: ("09:00", "09:50"),
                    3: ("10:00", "10:50"),
                    4: ("10:50", "11:40"),
                    5: ("11:50", "12:40"),
                    7: ("13:20", "14:10"),
                    8: ("14:20", "15:10"),
                    9: ("15:10", "16:00"),
                }

                if p_start in period_map and p_end in period_map:
                    start_str = period_map[p_start][0]
                    end_str = period_map[p_end][1]
                    period_start = datetime.strptime(
                        f"{target_date} {start_str}", "%Y-%m-%d %H:%M"
                    ) - timedelta(minutes=1)
                    period_end = datetime.strptime(
                        f"{target_date} {end_str}", "%Y-%m-%d %H:%M"
                    ) + timedelta(minutes=1)

        if search_terms:
            for item in items:
                summary = item.get("summary", "").upper()
                description = item.get("description", "").upper()
                text_to_search = f"{summary} {description}"
                if any(term in text_to_search for term in search_terms):
                    if period_start and period_end:
                        start_time_str = item.get("start", {}).get("dateTime")
                        if start_time_str:
                            start_time = (
                                datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                                .astimezone(clock.IST)
                                .replace(tzinfo=None)
                            )
                            if period_start <= start_time <= period_end:
                                matched_events.append(item)
                    else:
                        matched_events.append(item)

        if len(matched_events) == 0:
            raise LookupError(
                f"No events found matching course {course_code or course_name} and period {period}"
            )
        elif len(matched_events) > 1:
            raise LookupError(
                f"Multiple events found matching course {course_code or course_name} "
                f"and period {period}"
            )

        matched_event = matched_events[0]

        current_summary = matched_event.get("summary", "")
        if current_summary.startswith("CANCELLED: "):
            return matched_event

        patch_body = {
            "summary": f"CANCELLED: {current_summary}",
            "extendedProperties": {"private": {"spark_override": "1"}},
        }

        prior_state = {"summary": current_summary}

        updated = (
            service.events()
            .patch(calendarId=self.calendar_id, eventId=matched_event["id"], body=patch_body)
            .execute()
        )

        import json
        import time

        from src.utils.db import get_connection

        with get_connection() as conn:
            conn.execute(
                "INSERT INTO writes (ts, kind, event_id, prior_json) VALUES (?, ?, ?, ?)",
                (time.time(), "patch", matched_event["id"], json.dumps(prior_state)),
            )

        return updated


calendar_sync = CalendarSync()
