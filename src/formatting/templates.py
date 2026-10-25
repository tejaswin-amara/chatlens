"""Centralized Message Template Engine for ChatLens Enterprise PA."""

import re
from datetime import date, datetime
from typing import Any

from src.formatting.markdown_safety import extract_and_clean_urls, sanitize_markdown

COURSE_METADATA: dict[str, dict[str, str]] = {
    "ML": {
        "name": "Machine Learning",
        "code": "25SC2107E",
        "emoji": "🧠",
        "keywords": (
            r"\b(ml|machine learning|moocs?|certificates?|certification|lakshmi|prasanna)\b"
        ),
    },
    "DSA": {
        "name": "Data Structures & Algorithms-3",
        "code": "25CS2103E",
        "emoji": "💻",
        "keywords": r"\b(dsa|data structures|codetantra|chandusha|assessment)\b",
    },
    "OSSP": {
        "name": "Operating Systems & Systems Programming",
        "code": "25CS2104E",
        "emoji": "⚙️",
        "keywords": r"\b(ossp|operating systems|unix|linux|kernel)\b",
    },
    "ESD": {
        "name": "Embedded System Design & IoT",
        "code": "25EC2206E",
        "emoji": "📡",
        "keywords": r"\b(esd|ebsd|iot|embedded|arduino|dinesh)\b",
    },
    "DBSE": {
        "name": "Database Systems Engineering",
        "code": "25CS1302E",
        "emoji": "🗄️",
        "keywords": r"\b(dbse|database|sql|normalization|schema)\b",
    },
    "JAPANESE": {
        "name": "Japanese Language Proficiency-2",
        "code": "25FL2112E",
        "emoji": "🌐",
        "keywords": r"\b(japanese|jpn|flp|flp-2)\b",
    },
}

CHAT_TO_COURSE: dict[int, str] = {
    -5464066653: "ML",
    -5309899409: "DSA",
    -4997701423: "ESD",
    -1003408628464: "GLBCP",
    -1003956754765: "MENTEES",
    -1003844611672: "DSA",
}


def attribute_course(
    course_name: str | None = None,
    course_code: str | None = None,
    text: str = "",
    chat_id: int | None = None,
) -> tuple[str, str, str, str]:
    """Identify canonical course key, full title, official code, and semantic emoji."""
    # 1. Direct match by provided course_name or code
    combined = f"{course_name or ''} {course_code or ''}".upper()
    for key, meta in COURSE_METADATA.items():
        if (
            key in combined
            or meta["code"].upper() in combined
            or meta["name"].upper() in combined
        ):
            return key, meta["name"], meta["code"], meta["emoji"]

    # 2. Text heuristics match
    text_lower = text.lower()
    for key, meta in COURSE_METADATA.items():
        if re.search(meta["keywords"], text_lower):
            return key, meta["name"], meta["code"], meta["emoji"]

    # 3. Chat ID mapping fallback
    if chat_id and chat_id in CHAT_TO_COURSE:
        ck = CHAT_TO_COURSE[chat_id]
        if ck in COURSE_METADATA:
            meta = COURSE_METADATA[ck]
            return ck, meta["name"], meta["code"], meta["emoji"]

    return "GENERAL", "Academic Notice", "", "📌"


def calculate_urgency(
    target_date_str: str | None, today_date: date
) -> tuple[str, int]:
    """Calculate human-readable badge and sort priority weight.

    Priority:
    0: Overdue
    1: Due Today
    2: Due Tomorrow
    3: Due in X days
    4: Action Required (undated)
    5: Information / Past Completed
    """
    if not target_date_str:
        return "📌 Action Item", 4

    try:
        t_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return "📌 Action Item", 4

    days_diff = (t_date - today_date).days

    if days_diff < 0:
        return f"⚠️ Overdue (Due: {t_date.strftime('%d %b')})", 0
    if days_diff == 0:
        return "🚨 Due Today!", 1
    if days_diff == 1:
        return f"⏳ Due Tomorrow ({t_date.strftime('%d %b')})", 2
    return f"⏳ Due in {days_diff} days ({t_date.strftime('%d %b')})", 3


def group_and_consolidate_notices(
    items: list[dict[str, Any]], today_date: date
) -> list[dict[str, Any]]:
    """Group related and fragmentary notices by course and topic."""
    grouped: dict[str, dict[str, Any]] = {}

    for item in items:
        ev = item.get("event", {})
        if isinstance(ev, dict) and "event" in ev:
            ev = ev["event"]

        chat_id = item.get("chat_id") or ev.get("chat_id")
        summary = ev.get("summary") or ev.get("description") or ""
        cleaned_text, links = extract_and_clean_urls(summary)
        low_text = cleaned_text.lower()

        c_key, c_name, c_code, c_emoji = attribute_course(
            ev.get("course_name"), ev.get("course_code"), cleaned_text, chat_id=chat_id
        )

        t_date_str = ev.get("target_date")
        badge, priority = calculate_urgency(t_date_str, today_date)

        # Build group key based on course + broad topic
        if any(w in low_text for w in ("mooc", "certif")):
            topic_key = "ML_MOOCS"
            topic_title = "MOOCS Certification Submission"
            if c_key == "GENERAL":
                c_name = COURSE_METADATA["ML"]["name"]
                c_code = COURSE_METADATA["ML"]["code"]
                c_emoji = COURSE_METADATA["ML"]["emoji"]
        elif c_key == "ML" and any(w in low_text for w in ("submit", "last date", "deadline")):
            topic_key = "ML_MOOCS"
            topic_title = "MOOCS Certification Submission"
        elif any(w in low_text for w in ("assessment", "codetantra")):
            topic_key = "DSA_ASSESSMENT"
            topic_title = "Coding Assessment (CodeTantra)"
            if c_key == "GENERAL":
                c_name = COURSE_METADATA["DSA"]["name"]
                c_code = COURSE_METADATA["DSA"]["code"]
                c_emoji = COURSE_METADATA["DSA"]["emoji"]
        elif "exam" in low_text:
            topic_key = f"{c_key}_EXAM"
            topic_title = "In-Sem Exam Schedule"
        else:
            topic_key = f"{c_key}_{ev.get('summary', '')[:20]}"
            topic_title = ev.get("summary", "Course Assignment")

        if topic_key not in grouped:
            grouped[topic_key] = {
                "course_name": c_name,
                "course_code": c_code,
                "emoji": c_emoji,
                "topic_title": topic_title,
                "badge": badge,
                "priority": priority,
                "target_date": t_date_str,
                "period": ev.get("period"),
                "links": list(links),
                "notes": set(),
            }
        else:
            # Update priority/badge if this item is more urgent
            if priority < grouped[topic_key]["priority"]:
                grouped[topic_key]["priority"] = priority
                grouped[topic_key]["badge"] = badge
                grouped[topic_key]["target_date"] = t_date_str
            for l_item in links:
                if l_item not in grouped[topic_key]["links"]:
                    grouped[topic_key]["links"].append(l_item)

        # Distill concise instruction note if informative
        s_clean = re.sub(r"🔗\s*\[.*?\]\(.*?\)", "", cleaned_text).strip()
        s_clean = s_clean.replace("All the students,", "").replace("Dear students,", "").strip()
        if len(s_clean) > 8 and not s_clean.lower().startswith("submit immediately as today"):
            grouped[topic_key]["notes"].add(s_clean)

    cards = list(grouped.values())
    cards.sort(key=lambda x: x["priority"])
    return cards


def render_deadlines_card(
    today_date: date,
    milestones: list[tuple[date, str]],
    pending_items: list[dict[str, Any]],
) -> str:
    """Render executive-grade deadlines and academic intel card."""
    lines: list[str] = [
        f"⏰ **Upcoming Deadlines & Milestones** (as of {today_date.strftime('%d %b %Y')}):",
        f"📅 *{today_date.strftime('%A, %d %b %Y')}*",
        "",
    ]

    cards = group_and_consolidate_notices(pending_items, today_date)

    if cards:
        lines.append("📋 **Active Course Tasks & Announcements**:")
        for c in cards:
            c_header = f"• {c['emoji']} **{c['course_name']}**"
            if c["course_code"]:
                c_header += f" (`{c['course_code']}`)"
            lines.append(c_header)

            lines.append(f"  └ 📄 **{c['topic_title']}**")
            lines.append(f"     • **Status**: {c['badge']}")
            if c.get("period"):
                lines.append(f"     • **Time Window**: `{c['period']}`")

            if c["links"]:
                for label, url in c["links"][:2]:
                    lines.append(f"     • **Portal**: 🔗 [{label}]({url})")

            if c["notes"]:
                # Display the most descriptive note
                clean_note = sorted(c["notes"], key=len, reverse=True)[0]
                if clean_note:
                    lines.append(f"     • **Guidance**: {clean_note}")
            lines.append("")
    else:
        lines.append("🎉 *No pending tasks or notices registered from course chats.*")
        lines.append("")

    if milestones:
        lines.append("🏛️ **University Academic Milestones**:")
        for m_date, m_label in milestones[:5]:
            days_left = (m_date - today_date).days
            if days_left == 0:
                day_str = "today!"
            elif days_left > 0:
                day_str = f"in {days_left} days"
            else:
                day_str = "past"
            lines.append(f"• **{m_label}**: `{m_date.strftime('%d %b %Y')}` ({day_str})")
        lines.append("")

    lines.append("💡 *Tip: Tap `/today` for live classes or `/attendance` for safe bunk margins.*")
    return sanitize_markdown("\n".join(lines))


def render_day_schedule(
    target_date: date,
    slots: list[Any],
    active_deadlines: list[dict[str, Any]] | None = None,
    is_today: bool = True,
    term: str = "T04",
    section: str = "S-10",
) -> str:
    """Render structured academic schedule with live progression badges."""
    day_label = "Today" if is_today else "Tomorrow"
    date_str = target_date.strftime("%a, %d %b %Y")

    lines: list[str] = [
        f"📅 **Academic Schedule for {day_label} ({date_str})**",
        f"🕒 *Term {term} • Section {section}*",
        "",
    ]

    if not slots:
        lines.append(
            f"🎉 *No scheduled classes for {day_label.lower()} ({date_str}). Enjoy your break!*"
        )
    else:
        for s in slots:
            p_time = getattr(s, "period_time", f"Period {getattr(s, 'period', 1)}")
            c_name = getattr(s, "course_name", getattr(s, "course", "Course"))
            c_code = getattr(s, "course_code", "")
            room = getattr(s, "room", "TBD")
            faculty = getattr(s, "faculty", "Faculty")
            c_type = getattr(s, "type", "Class")
            status_icon = getattr(s, "status_icon", "⬡")

            code_tag = f" (`{c_code}`)" if c_code else ""
            lines.append(f"• **{p_time}** (P{getattr(s, 'period', 1)})")
            lines.append(f"  └ {status_icon} **{c_name}**{code_tag}")
            lines.append(f"     • Room: `{room}` | Faculty: {faculty} | Type: {c_type}")
            lines.append("")

    if active_deadlines:
        lines.append("🚨 **Active Deadlines & Assessments Today**:")
        for ev in active_deadlines:
            c_name = ev.get("course_name") or ev.get("course_code") or "Academic Notice"
            period = f" [{ev.get('period')}]" if ev.get("period") else ""
            summary = ev.get("summary") or "Assessment / Task"
            lines.append(f"• ⏰{period} **{c_name}**: {summary}")
        lines.append("")

    lines.append("💡 *Tip: Use `/tomorrow` for upcoming classes or `/exam` for lab exam dates.*")
    return sanitize_markdown("\n".join(lines))


def render_status_card(
    now_dt: datetime,
    spark_mode: str,
    chat_count: int,
    model_name: str,
    erp_user: str,
    owner_chat_id: int | str,
) -> str:
    """Render executive PA daemon status card."""
    now_str = now_dt.strftime("%A, %d %b %Y • %H:%M:%S IST")
    lines = [
        "🟢 **ChatLens PA Status**",
        f"🕒 *{now_str}*",
        "",
        f"• **SPARK Mode**: `{spark_mode}` (Safe Write Guard active)",
        f"• **Telegram**: Active ({chat_count} monitored course channels)",
        f"• **Gemini AI**: `{model_name}` (Connected & Streaming)",
        f"• **KL ERP Bridge**: Configured (`{erp_user}`)",
        "• **Google Workspace**: Calendar & Tasks Connected",
        f"• **Owner**: `{owner_chat_id}`",
        "• **Status**: 🚀 Live & Listening in Real-Time",
        "",
        "🚀 *All background daemons, listeners, and reminder loops are fully operational.*",
    ]
    return sanitize_markdown("\n".join(lines))


def render_attendance_card(records: list[dict[str, Any]], now_dt: datetime) -> str:
    """Render attendance summary card with exact bunk margins."""
    lines = [
        "📊 **Live Academic Attendance & Bunk Margins**",
        f"🕒 *Source: KL ERP System (as of {now_dt.strftime('%d %b %Y')})*",
        "",
    ]

    for r in records:
        c_name = r.get("course_name") or r.get("course") or "Course"
        c_code = r.get("course_code") or r.get("code") or ""
        pct = float(r.get("percentage") or 0.0)
        attended = r.get("attended", 0)
        held = r.get("held") or r.get("conducted", 0)
        bunks = r.get("safe_bunks", 0)

        if pct >= 85.0:
            badge = "🟢 Safe"
            buffer_desc = f"**{bunks} classes** can be safely missed"
        elif pct >= 80.0:
            badge = "🟡 Borderline"
            buffer_desc = f"**{bunks} classes** (Must attend next sessions)"
        else:
            badge = "🔴 Danger"
            buffer_desc = "**0 classes** (Attendance recovery required)"

        code_str = f" (`{c_code}`)" if c_code else ""
        lines.append(f"• **{c_name}**{code_str}")
        lines.append(f"  └ Current: **{pct:.1f}%** ({attended}/{held} attended) • {badge}")
        lines.append(f"     • Bunk Buffer: {buffer_desc}")
        lines.append("")

    lines.append("💡 *Target threshold is 85.0%. Courses below 85% risk attendance condonation.*")
    return sanitize_markdown("\n".join(lines))


def render_proactive_reminder(
    course_name: str,
    course_code: str | None,
    period: str,
    summary: str,
    intent: str = "EXAM_DEADLINE",
) -> str:
    """Render immediate proactive reminder card."""
    code_str = f" (`{course_code}`)" if course_code else ""
    cleaned_summary, links = extract_and_clean_urls(summary)

    lines = [
        "⏰ **Upcoming Academic Reminder!**",
        "",
        f"• **Course**: {course_name}{code_str}",
        f"• **Scheduled Window**: {period}",
        f"• **Notice**: {cleaned_summary}",
    ]
    if links:
        for label, url in links[:2]:
            lines.append(f"• **Link**: 🔗 [{label}]({url})")

    lines.append("")
    lines.append(f"🚀 *Action Required: {intent} active today. Please prepare in advance!*")
    return sanitize_markdown("\n".join(lines))


def get_standard_navigation_buttons() -> list[list[dict[str, str]]]:
    """Return standard 2x2 inline navigation keyboard."""
    return [
        [
            {"text": "📅 Today", "callback_data": "cmd:today"},
            {"text": "📊 Attendance", "callback_data": "cmd:attendance"},
        ],
        [
            {"text": "⏰ Deadlines", "callback_data": "cmd:deadlines"},
            {"text": "🟢 Status", "callback_data": "cmd:status"},
        ],
    ]
