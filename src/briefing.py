from datetime import date, datetime


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
            if ratio < 0.85:
                attend = max(0, -((100*a - 85*h) // 15))
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
