from datetime import date, datetime, timedelta


def classes_can_skip(a: int, h: int, floor: int) -> int:
    return max(0, (100 * a - floor * h) // floor)


def classes_needed(a: int, h: int, floor: int) -> int:
    import math

    if floor == 100:
        return 0
    return max(0, math.ceil((floor * h - 100 * a) / (100 - floor)))


def format_bunk_calculator(attendance_rows: list[dict]) -> str:
    """Format an interactive bunk buffer and attendance recovery calculator."""
    if not attendance_rows:
        return "⚠️ No attendance records available from KL ERP or Sheets."

    lines = ["📊 **KL ERP Attendance & Bunk Margin Calculator**:\n"]
    for row in attendance_rows:
        course = row.get("course", "Unknown")
        code = row.get("code") or ""
        label = f"{course} ({code})" if code else course
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

        pct = (a / h) * 100
        filled = min(10, max(0, int(pct / 10)))
        bar = "█" * filled + "░" * (10 - filled)

        # 75% margin (University Detention Floor)
        if pct >= 75:
            safe_75 = classes_can_skip(a, h, 75)
            status_75 = f"🟢 Safe bunks (≥75%): **{safe_75}**"
        else:
            need_75 = classes_needed(a, h, 75)
            status_75 = f"🔴 Attend next: **{need_75}** classes consecutively"

        # 85% margin (Academic Distinction Benchmark)
        if pct >= 85:
            safe_85 = classes_can_skip(a, h, 85)
            status_85 = f"Safe bunks (≥85%): **{safe_85}**"
        else:
            need_85 = classes_needed(a, h, 85)
            status_85 = f"Need for 85%: **{need_85}**"

        lines.append(f"• **{label}**: `[{bar}]` **{pct:.1f}%** ({a}/{h})")
        lines.append(f"  └ {status_75} | {status_85}")

    return "\n".join(lines)


def simulate_bunk_impact(records: list[dict], course_query: str, skip_count: int = 1) -> str:
    """Calculate projected attendance percentage, safe bunk buffer, and detention breaches."""
    if not records:
        return "⚠️ No attendance records available for simulation."

    query = (course_query or "").strip().upper()
    if not query:
        return "⚠️ Please specify a course code or name to simulate (e.g. `/bunk CIS 2`)."

    matched: dict | None = None

    for r in records:
        c_code = str(r.get("course_code") or r.get("code") or "").upper()
        c_name = str(r.get("course_name") or r.get("course") or "").upper()
        if query == c_code or query == c_name:
            matched = r
            break
        if query in c_code or query in c_name:
            matched = r
            break

    if not matched:
        from src.parsing.regex_parser import COURSES

        for canon, aliases in COURSES.items():
            if query == canon or any(query == a for a in aliases):
                for r in records:
                    c_code = str(r.get("course_code") or r.get("code") or "").upper()
                    c_name = str(r.get("course_name") or r.get("course") or "").upper()
                    if canon in c_name or any(a in c_name for a in aliases):
                        matched = r
                        break
            if matched:
                break

    if not matched:
        return f"⚠️ Course '{course_query}' not found in attendance records."

    c_name = matched.get("course_name") or matched.get("course") or course_query
    c_code = matched.get("course_code") or matched.get("code") or ""
    label = f"{c_name} (`{c_code}`)" if c_code else str(c_name)

    a_val = matched.get("attended")
    h_val = matched.get("held") or matched.get("conducted")
    if a_val is None or h_val is None:
        return f"⚠️ Attendance numbers missing for {label}."
    try:
        a = int(a_val)
        h = int(h_val)
    except (ValueError, TypeError):
        return f"⚠️ Invalid attendance figures recorded for {label}."

    if h <= 0 or a > h:
        return f"⚠️ Cannot simulate bunk impact: conducted classes count ({h}) is invalid."

    pct_curr = (a / h) * 100.0
    proj_h = h + skip_count
    proj_pct = (a / proj_h) * 100.0

    curr_safe_75 = classes_can_skip(a, h, 75)
    proj_safe_75 = classes_can_skip(a, proj_h, 75)
    curr_need_75 = classes_needed(a, h, 75)
    proj_need_75 = classes_needed(a, proj_h, 75)

    proj_safe_85 = classes_can_skip(a, proj_h, 85)
    proj_need_85 = classes_needed(a, proj_h, 85)

    if pct_curr >= 75.0 and proj_pct < 75.0:
        status_line = (
            f"🚨 **CRITICAL DETENTION THRESHOLD BREACH!**\n"
            f"  └ Attendance plummets below 75% floor to **{proj_pct:.1f}%**!\n"
            f"  └ Recovery: Requires attending next **{proj_need_75}** classes consecutively."
        )
    elif proj_pct < 75.0:
        status_line = (
            f"🔴 **DETENTION RISK ESCALATION**\n"
            f"  └ Already below 75% ({pct_curr:.1f}%). Projected: **{proj_pct:.1f}%**.\n"
            f"  └ Recovery increases from {curr_need_75} to **{proj_need_75}** consecutive classes."
        )
    elif proj_pct < 85.0 and pct_curr >= 85.0:
        status_line = (
            f"🟡 **Distinction Target Compromised**\n"
            f"  └ Safe for 75% ({proj_pct:.1f}% ≥ 75%, {proj_safe_75} bunks left), "
            f"but falls below 85% benchmark (need {proj_need_85} classes to restore)."
        )
    else:
        status_line = (
            f"🟢 **Safe Bunk Confirmed**\n"
            f"  └ Projected attendance remains at **{proj_pct:.1f}%** (≥75% floor).\n"
            f"  └ Remaining safe bunks (≥75%): **{proj_safe_75}** | (≥85%): **{proj_safe_85}**."
        )

    buffer_75_str = (
        f"{curr_safe_75} safe bunks ➔ **{proj_safe_75} safe bunks**"
        if proj_pct >= 75.0
        else f"Requires **{proj_need_75}** classes recovery (was {curr_need_75})"
    )

    unit = "classes" if skip_count > 1 else "class"
    lines = [
        f"🔮 **Attendance Bunk Simulation ({skip_count} {unit})**:\n",
        f"• **Course**: **{label}**",
        f"• **Current Attendance**: **{pct_curr:.1f}%** ({a}/{h})",
        f"• **Projected Attendance**: **{proj_pct:.1f}%** ({a}/{proj_h})",
        f"• **75% Detention Floor**: {buffer_75_str}",
        f"• **Assessment**: {status_line}",
    ]
    return "\n".join(lines)


def detect_high_stakes_classes(today_date: date, records: list[dict]) -> list[dict]:
    """Detect courses scheduled today where a single absence breaches 75% detention floor."""
    if not records:
        return []

    try:
        from src.timetable import get_effective_slots

        slots = get_effective_slots(today_date)
    except Exception:
        slots = []

    if not slots:
        return []

    high_stakes: list[dict] = []
    seen: set[str] = set()

    for s in slots:
        c_code = getattr(s, "course_code", "") or getattr(s, "code", "") or ""
        c_name = getattr(s, "course_name", "") or getattr(s, "course", "") or ""
        key = (c_code or c_name).upper()
        if not key or key in seen:
            continue

        matched_rec = None
        for r in records:
            r_code = str(r.get("course_code") or r.get("code") or "").upper()
            r_name = str(r.get("course_name") or r.get("course") or "").upper()
            if key == r_code or key == r_name or key in r_name or r_code in key:
                matched_rec = r
                break

        if not matched_rec:
            continue

        a_val = matched_rec.get("attended")
        h_val = matched_rec.get("held") or matched_rec.get("conducted")
        if a_val is None or h_val is None:
            continue
        try:
            a = int(a_val)
            h = int(h_val)
        except (ValueError, TypeError):
            continue

        if h <= 0 or a > h:
            continue

        pct = (a / h) * 100.0
        proj_miss_pct = (a / (h + 1)) * 100.0

        if (75.0 <= pct <= 78.0) or (pct >= 75.0 and proj_miss_pct < 75.0):
            seen.add(key)
            high_stakes.append(
                {
                    "course": (
                        matched_rec.get("course_name") or matched_rec.get("course") or c_name
                    ),
                    "code": matched_rec.get("course_code") or matched_rec.get("code") or c_code,
                    "current_pct": round(pct, 1),
                    "projected_pct": round(proj_miss_pct, 1),
                    "attended": a,
                    "held": h,
                    "period": getattr(s, "period", None),
                    "room": getattr(s, "room", None),
                    "danger": True,
                }
            )

    return high_stakes


def next_run(now: datetime) -> datetime:
    if now.tzinfo is None:
        raise ValueError("now must be a timezone-aware datetime")
    run_today = now.replace(hour=7, minute=15, second=0, microsecond=0)
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
                except (ValueError, TypeError):
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
                except (ValueError, TypeError):
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

        high_stakes = detect_high_stakes_classes(now.date(), attendance_rows)
        if high_stakes:
            lines.append("")
            lines.append("🚨 **High-Stakes Classes Today (75% Detention Risk)**:")
            for hs in high_stakes:
                p_info = f" [P{hs['period']}]" if hs.get("period") else ""
                r_info = f" in {hs['room']}" if hs.get("room") else ""
                lines.append(
                    f"  • **{hs['course']}**{p_info}{r_info}: {hs['current_pct']}% "
                    f"➔ drops to {hs['projected_pct']}% if missed! (Zero absence tolerance)"
                )

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
    from datetime import timedelta

    from src.academic_calendar import load_calendar
    from src.utils import clock
    from src.workspace.calendar_sync import calendar_sync
    from src.workspace.sheets_logger import sheets_logger
    from src.workspace.tasks_sync import tasks_sync

    now = clock.now_ist()
    start_str = now.strftime("%Y-%m-%d")
    end_str = (now + timedelta(days=3)).strftime("%Y-%m-%d")
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
            timeZone="Asia/Kolkata",
        )
        .execute
    )
    tasks_task = asyncio.to_thread(tasks_sync.list_open_tasks, start_str, end_str)
    sheets_task = asyncio.to_thread(sheets_logger.get_attendance)

    cal_res, tasks_res, att_res = await asyncio.gather(
        cal_task, tasks_task, sheets_task, return_exceptions=True
    )

    calendar_events = cal_res.get("items", []) if not isinstance(cal_res, Exception) else []
    tasks = tasks_res if not isinstance(tasks_res, Exception) else []
    attendance_rows = att_res if not isinstance(att_res, Exception) else []

    cal = load_calendar()
    milestones = (
        {f"{term} {name}": d for term, dates in cal.terms.items() for name, d in dates.items()}
        if cal
        else {}
    )

    return calendar_events, tasks, attendance_rows, milestones
