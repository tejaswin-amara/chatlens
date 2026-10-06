from datetime import date, datetime, timedelta


def classes_can_skip(a: int, h: int, floor: int) -> int:
    return max(0, (100 * a - floor * h) // floor)


def classes_needed(a: int, h: int, floor: int) -> int:
    import math

    if floor == 100:
        return 0
    return max(0, math.ceil((floor * h - 100 * a) / (100 - floor)))


def next_run(now: datetime) -> datetime:
    # return the next 07:00 occurrence
    run_today = now.replace(hour=7, minute=0, second=0, microsecond=0)
    if now >= run_today:
        return run_today + timedelta(days=1)
    return run_today


def build_briefing(
    now: datetime,
    calendar_events: list[dict],
    tasks: list[dict],
    attendance_rows: list[dict],
    milestones: dict[str, date],
) -> str:
    lines = []

    # a) today's Calendar events
    lines.append(f"📅 **Today's Classes ({now.strftime('%d %b')})**")
    if not calendar_events:
        lines.append("  No classes today")
    else:
        for ev in calendar_events:
            title = ev.get("summary", "Class")
            loc = ev.get("location", "N/A")
            start = ev.get("start", {}).get("dateTime", "")
            time_str = "All day"
            if start:
                try:
                    dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    time_str = dt.strftime("%I:%M %p")
                except Exception:
                    pass

            override_marker = ""
            ext = ev.get("extendedProperties", {}).get("private", {})
            if ext.get("spark_override") == "1":
                override_marker = " 🔁"

            lines.append(f"  • {time_str}: {title} [{loc}]{override_marker}")

    # b) Google Tasks due within 3 days
    if tasks:
        lines.append("")
        lines.append("📝 **Upcoming Tasks**")
        for task in tasks:
            title = task.get("title", "Task")
            due_str = task.get("due", "")
            urgent_marker = ""
            if due_str:
                try:
                    due_dt = datetime.fromisoformat(due_str.replace("Z", "+00:00")).date()
                    if (due_dt - now.date()).days <= 3:
                        urgent_marker = " [URGENT]"
                except Exception:
                    pass
            lines.append(f"  • {title}{urgent_marker}")

    # c) Attendance
    if attendance_rows:
        lines.append("")
        lines.append("📊 **Attendance Alerts**")
        alert_count = 0
        for row in attendance_rows:
            course = row.get("course", "Unknown")
            a_val = row.get("attended")
            h_val = row.get("held")

            if a_val is None or h_val is None:
                continue
            try:
                a = int(a_val)
                h = int(h_val)
            except ValueError:
                continue

            if h <= 0 or a > h:
                continue

            ratio = a / h if h > 0 else 0
            # We use float division just for the condition, exact needed with integer math
            if ratio < 0.85:
                attend = classes_needed(a, h, 85)
                alert_count += 1
                flag = "🔴 <75%" if ratio < 0.75 else "🟡 <85%"
                lines.append(f"  {flag} {course}: {a}/{h} (Need {attend} more)")
            else:
                # Not alerting if okay, only flagging below 85%
                pass

        if alert_count == 0:
            lines.append("  All courses above 85%")

    # d) Academic dates
    if milestones:
        lines.append("")
        lines.append("🎓 **Academic Milestones (Next 7 Days)**")
        count = 0
        for name, m_date in milestones.items():
            diff = (m_date - now.date()).days
            if 0 <= diff <= 7:
                lines.append(f"  • {name}: {m_date.strftime('%d %b')}")
                count += 1
        if count == 0:
            lines.pop()
            lines.pop()

    full_text = "\n".join(lines)
    if len(full_text) > 3500:
        return full_text[:3499] + "…"
    return full_text


async def fetch_briefing_inputs():
    import asyncio

    from src.academic_calendar import load_calendar
    from src.utils import clock
    from src.workspace.calendar_sync import calendar_sync
    from src.workspace.sheets_logger import sheets_logger
    from src.workspace.tasks_sync import tasks_sync

    now = clock.now_ist()
    time_min = now.replace(hour=0, minute=0, second=0).isoformat()
    time_max = now.replace(hour=23, minute=59, second=59).isoformat()

    cal_task = asyncio.to_thread(
        calendar_sync.auth.get_calendar_service()
        .events()
        .list(
            calendarId=calendar_sync.calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute
    )
    tasks_task = asyncio.to_thread(
        tasks_sync.auth.get_tasks_service()
        .tasks()
        .list(tasklist="@default", showCompleted=False, showHidden=False)
        .execute
    )
    sheets_task = asyncio.to_thread(sheets_logger.get_attendance)

    cal_res, tasks_res, att_res = await asyncio.gather(
        cal_task, tasks_task, sheets_task, return_exceptions=True
    )

    calendar_events = cal_res.get("items", []) if not isinstance(cal_res, Exception) else []
    tasks = tasks_res.get("items", []) if not isinstance(tasks_res, Exception) else []
    attendance_rows = att_res if not isinstance(att_res, Exception) else []

    cal = load_calendar()
    milestones = cal.milestones if cal else {}

    return calendar_events, tasks, attendance_rows, milestones
