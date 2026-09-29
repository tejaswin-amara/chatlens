"""Google Calendar Adapter for timetable room overrides and holiday event syncing."""

from datetime import datetime, timedelta
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.utils.logging import get_logger
from src.workspace.auth import workspace_auth

logger = get_logger(__name__)


class CalendarSync:
    def __init__(self, calendar_id: str | None = None, auth_adapter: Any = None) -> None:
        self.calendar_id = calendar_id or settings.google_calendar_id
        self.auth = auth_adapter or workspace_auth

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
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
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = events_result.get("items", [])

        search_terms = [t.upper() for t in (course_code, course_name) if t]
        matched_event = None

        if search_terms:
            for item in items:
                summary = item.get("summary", "").upper()
                description = item.get("description", "").upper()
                text_to_search = f"{summary} {description}"
                if any(term in text_to_search for term in search_terms):
                    matched_event = item
                    break

        reminders_override = {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 10}],
        }

        if matched_event:
            event_id = matched_event["id"]
            patch_body = {
                "location": f"Room {new_room}",
                "reminders": reminders_override,
            }
            updated = (
                service.events()
                .patch(calendarId=self.calendar_id, eventId=event_id, body=patch_body)
                .execute()
            )
            logger.info(
                "Updated calendar class room",
                event_id=event_id,
                room=new_room,
                target_date=target_date,
            )
            return updated

        event_body = {
            "summary": f"[{course_code or course_name or 'Class'}] Room: {new_room}",
            "location": f"Room {new_room}",
            "description": f"Room update for period {period or 'scheduled'}",
            "start": {"dateTime": f"{target_date}T09:00:00Z"},
            "end": {"dateTime": f"{target_date}T10:00:00Z"},
            "reminders": reminders_override,
        }
        created = service.events().insert(calendarId=self.calendar_id, body=event_body).execute()
        logger.info("Inserted new calendar class event", room=new_room, target_date=target_date)
        return created

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def create_holiday_event(self, reason: str, target_date: str) -> dict[str, Any]:
        service = self.auth.get_calendar_service()

        dt = datetime.strptime(target_date, "%Y-%m-%d")
        next_day = (dt + timedelta(days=1)).strftime("%Y-%m-%d")

        event_body = {
            "summary": f"University Holiday: {reason}",
            "description": f"Official Holiday Circular: {reason}",
            "start": {"date": target_date},
            "end": {"date": next_day},
            "reminders": {"useDefault": False, "overrides": []},
            "transparency": "transparent",
        }

        created = service.events().insert(calendarId=self.calendar_id, body=event_body).execute()
        logger.info("Created university holiday event", reason=reason, target_date=target_date)
        return created


calendar_sync = CalendarSync()
