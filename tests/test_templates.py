"""Unit tests for the centralized ChatLens Message Template Engine and Markdown safety."""

from datetime import date, datetime

from src.formatting.markdown_safety import extract_and_clean_urls, sanitize_markdown
from src.formatting.templates import (
    attribute_course,
    calculate_urgency,
    get_standard_navigation_buttons,
    group_and_consolidate_notices,
    render_attendance_card,
    render_deadlines_card,
    render_proactive_reminder,
    render_status_card,
)


def test_attribute_course_known_and_heuristics():
    # Direct match
    assert attribute_course("ML")[0] == "ML"
    assert attribute_course(course_code="25SC2107E")[0] == "ML"
    assert attribute_course("DSA")[0] == "DSA"
    assert attribute_course(course_code="25CS2103E")[0] == "DSA"

    # Text heuristics match
    assert attribute_course(text="Upload your moocs certificates")[0] == "ML"
    assert attribute_course(text="Mandatory assessment on codetantra")[0] == "DSA"
    assert attribute_course(text="Complete your arduino breadboard circuit")[0] == "ESD"
    assert attribute_course(text="SQL foreign key constraint error")[0] == "DBSE"
    assert attribute_course(text="Linux system call fork and exec")[0] == "OSSP"

    # Fallback
    key, name, code, emoji = attribute_course(text="General university administrative notice")
    assert key == "GENERAL"
    assert emoji == "📌"


def test_calculate_urgency_relative_dates():
    today = date(2026, 10, 25)

    # Overdue
    badge, prio = calculate_urgency("2026-10-24", today)
    assert prio == 0
    assert "Overdue" in badge

    # Due Today
    badge, prio = calculate_urgency("2026-10-25", today)
    assert prio == 1
    assert "Due Today" in badge

    # Due Tomorrow
    badge, prio = calculate_urgency("2026-10-26", today)
    assert prio == 2
    assert "Due Tomorrow" in badge

    # Due in future days
    badge, prio = calculate_urgency("2026-10-30", today)
    assert prio == 3
    assert "in 5 days" in badge

    # Undated
    badge, prio = calculate_urgency(None, today)
    assert prio == 4
    assert "Action Item" in badge


def test_extract_and_clean_urls_sanitization():
    # Broken markdown brackets from ingestion
    raw = (
        "All the students, upload your moocs certification in the below drive link: "
        "[https://drive.google.com/drive/folders/1Z_wxxutVD6lPUckEkTEDPZ4FxR_b8-yh]("
    )
    cleaned, links = extract_and_clean_urls(raw)
    assert len(links) == 1
    assert links[0][0] == "Google Drive Folder"
    assert "drive.google.com" in links[0][1]
    assert "🔗 [Google Drive Folder]" in cleaned
    assert not cleaned.endswith("](")


def test_sanitize_markdown_balances_tokens():
    # Unbalanced backtick
    assert sanitize_markdown("Code `test without close").endswith("`")

    # Unbalanced bold
    assert sanitize_markdown("**Bold text without close").endswith("**")

    # Already balanced
    balanced = "• **Course**: `25CS2103E`"
    assert sanitize_markdown(balanced) == balanced


def test_group_and_consolidate_fragmented_notices():
    today = date(2026, 10, 25)
    fragmented_items = [
        {
            "id": 6,
            "chat_id": -5464066653,
            "event": {
                "summary": "Upload your moocs certificates at the earliest",
                "course_name": None,
                "target_date": None,
            },
        },
        {
            "id": 5,
            "chat_id": -5464066653,
            "event": {
                "summary": "donot modify the certificates and upload",
                "course_name": None,
                "target_date": None,
            },
        },
        {
            "id": 3,
            "chat_id": -5464066653,
            "event": {
                "summary": "Submit immediately as today is the last date",
                "course_name": None,
                "target_date": "2026-10-24",
            },
        },
        {
            "id": 2,
            "chat_id": -5464066653,
            "event": {
                "summary": (
                    "All the students, upload your moocs certification in the below drive link: "
                    "https://drive.google.com/drive/folders/1Z_wxxutVD6lPUckEkTEDPZ4FxR_b8-yh"
                ),
                "course_name": None,
                "target_date": None,
            },
        },
        {
            "id": 1,
            "event": {
                "summary": "Mandatory coding assessment for DSA in Codetantra from 8 PM to 9 PM.",
                "course_name": "DSA",
                "course_code": "25CS2103E",
                "target_date": "2026-10-24",
                "period": "8:00 PM - 9:00 PM",
            },
        },
    ]

    cards = group_and_consolidate_notices(fragmented_items, today)

    # 4 ML fragmented notices should be consolidated into 1 card, 1 DSA card -> 2 cards total
    assert len(cards) == 2

    # Verify ML card attributes
    ml_card = next(c for c in cards if c["course_name"] == "Machine Learning")
    assert ml_card["emoji"] == "🧠"
    assert ml_card["course_code"] == "25SC2107E"
    assert len(ml_card["links"]) == 1
    assert "Google Drive Folder" in ml_card["links"][0][0]
    assert "Overdue" in ml_card["badge"]


def test_render_deadlines_card_layout():
    today = date(2026, 10, 25)
    milestones = [
        (date(2026, 11, 15), "Lab In-Sem Examinations (T04)"),
        (date(2026, 12, 5), "Last Instruction Day (T04)"),
    ]
    pending = [
        {
            "id": 1,
            "event": {
                "course_name": "DSA",
                "course_code": "25CS2103E",
                "summary": "Coding assessment in Codetantra",
                "target_date": "2026-10-25",
                "period": "8:00 PM - 9:00 PM",
            },
        }
    ]

    rendered = render_deadlines_card(today, milestones, pending)

    assert "⏰ **Upcoming Deadlines & Milestones**" in rendered
    assert "Sunday, 25 Oct 2026" in rendered
    assert "💻 **Data Structures & Algorithms-3** (`25CS2103E`)" in rendered
    assert "🚨 Due Today!" in rendered
    assert "🏛️ **University Academic Milestones**:" in rendered
    assert "Lab In-Sem Examinations" in rendered


def test_render_status_card():
    now_dt = datetime(2026, 10, 25, 10, 30, 0)
    card = render_status_card(
        now_dt=now_dt,
        spark_mode="confirm",
        chat_count=10,
        model_name="gemini-3.5-flash-lite",
        erp_user="2520090104",
        owner_chat_id=7246876230,
    )
    assert "🟢 **ChatLens PA Status**" in card
    assert "confirm" in card
    assert "10 monitored course channels" in card
    assert "gemini-3.5-flash-lite" in card


def test_render_attendance_card():
    now_dt = datetime(2026, 10, 25, 10, 30, 0)
    records = [
        {
            "course_name": "Machine Learning",
            "course_code": "25SC2107E",
            "percentage": 91.0,
            "attended": 19,
            "held": 21,
            "safe_bunks": 1,
        },
        {
            "course_name": "Embedded System Design & IoT",
            "course_code": "25EC2206E",
            "percentage": 82.0,
            "attended": 23,
            "held": 28,
            "safe_bunks": 0,
        },
    ]
    card = render_attendance_card(records, now_dt)
    assert "📊 **Live Academic Attendance & Bunk Margins**" in card
    assert "🟢 Safe" in card
    assert "🟡 Borderline" in card


def test_render_proactive_reminder():
    reminder = render_proactive_reminder(
        course_name="Machine Learning",
        course_code="25SC2107E",
        period="Today 2:00 PM",
        summary="Submit MOOCS certificate to https://drive.google.com/drive/folders/abc",
    )
    assert "⏰ **Upcoming Academic Reminder!**" in reminder
    assert "Machine Learning (`25SC2107E`)" in reminder
    assert "🔗 [Google Drive Folder]" in reminder


def test_get_standard_navigation_buttons():
    buttons = get_standard_navigation_buttons()
    assert len(buttons) == 2
    assert buttons[0][0]["callback_data"] == "cmd:today"
    assert buttons[0][1]["callback_data"] == "cmd:attendance"
    assert buttons[1][0]["callback_data"] == "cmd:deadlines"
    assert buttons[1][1]["callback_data"] == "cmd:status"


def test_sanitize_markdown_escapes_underscores_outside_code():
    # Plain course code with underscore
    assert sanitize_markdown("Course CS_101 notice") == "Course CS\\_101 notice"

    # Inline code span with underscore must NOT be escaped
    assert sanitize_markdown("Variable `test_var` value") == "Variable `test_var` value"

    # Multi-line code block must NOT be escaped
    code_block = "```\ndef foo_bar():\n    return 42\n```"
    assert sanitize_markdown(code_block) == code_block

    # Link label with underscore escaped, but URL destination preserved
    link_md = "Click [My_Drive](https://drive.google.com/folder_id) now"
    expected = "Click [My\\_Drive](https://drive.google.com/folder_id) now"
    assert sanitize_markdown(link_md) == expected

    # Already escaped underscore should not be double escaped
    assert sanitize_markdown("Already CS\\_101") == "Already CS\\_101"


def test_templates_event_receipt_and_review():
    from src.formatting.templates import (
        render_calendar_conflict,
        render_circuit_breaker_alert,
        render_event_receipt,
        render_review_notice,
        render_security_quarantine_alert,
    )
    from src.parsing.schemas import ExtractedAcademicEvent

    event = ExtractedAcademicEvent(
        intent="ROOM_OVERRIDE",
        course_name="Machine Learning",
        course_code="25SC2107E",
        room="C-321",
        target_date="2026-11-05",
        summary="Class shifted to C-321",
    )

    # Dry run receipt
    dry_receipt = render_event_receipt(event, is_dry_run=True)
    assert "[DRY RUN] Event Processed:" in dry_receipt
    assert "DRY\\_RUN (Would execute)" in dry_receipt
    assert "`ROOM_OVERRIDE`" in dry_receipt

    # Auto applied receipt
    auto_receipt = render_event_receipt(
        event, execution_status="SUCCESS", details_list=["Room updated"], is_dry_run=False
    )
    assert "✅ **Action applied:**" in auto_receipt
    assert "SUCCESS (Room updated)" in auto_receipt

    # Review notice (confirmation)
    confirm_notice = render_review_notice(event, reason="Out of schedule", is_confirmation=True)
    assert "🔔 **Review needed for ROOM\\_OVERRIDE**" in confirm_notice
    assert "Tap Apply to execute" in confirm_notice

    # Review notice (needs review)
    review_notice = render_review_notice(event, reason="Out of schedule", is_confirmation=False)
    assert "Review needed for ROOM\\_OVERRIDE" in review_notice

    # Calendar conflict
    conflict = render_calendar_conflict("mid-term", "2026-09-20", "2026-09-22")
    assert "⚠️ **Calendar Conflict**" in conflict
    assert "Message date: 2026-09-20" in conflict
    assert "Calendar date: 2026-09-22" in conflict

    # Circuit breaker alert
    cb_alert = render_circuit_breaker_alert()
    assert "🚨 **Circuit Breaker Tripped**" in cb_alert

    # Security alert
    sec_alert = render_security_quarantine_alert("Main", 123, "Eve", 456, "Injection", "ignore all")
    assert "🛡️ **Security Alert: Quarantined Prompt Injection**" in sec_alert


def test_academic_calendar_loading_and_milestones():
    from src.academic_calendar import get_milestone_date, load_calendar

    cal = load_calendar()
    assert cal is not None
    assert "T04" in cal.terms
    assert "T05" in cal.terms

    lab_exam_date = get_milestone_date("lab exam", date(2026, 10, 1), cal)
    assert lab_exam_date == date(2026, 10, 15)

    fee_date = get_milestone_date("fee", date(2026, 8, 1), cal)
    assert fee_date == date(2026, 8, 10)
