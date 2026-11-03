"""Adversarial challenge and empirical stress-test suite for SPARK PA fixes.

Covers:
1. Markdown safety and underscore escaping edge cases (code spans, URLs, malformed markup).
2. SPARK_MEDIA zero-byte download invariants and routing.
3. Proactive reminders date boundary conditions (today vs tomorrow vs yesterday vs None).
4. Timetable horizon extension and academic calendar milestone guards.
"""

import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.formatting.markdown_safety import (
    escape_markdown_underscores,
    extract_and_clean_urls,
    sanitize_markdown,
)
from src.timetable import get_effective_slots, load, validate
from src.utils import clock

# ============================================================================
# Vector 1: Markdown Formatting & Safety Stress Testing
# ============================================================================


class TestMarkdownUnderscoreEscaping:
    """Stress-test escape_markdown_underscores against hostile formatting patterns."""

    def test_plain_text_multiple_underscores(self):
        text = "course_code_is_25CS2103E_and_room_is_H006"
        escaped = escape_markdown_underscores(text)
        assert escaped == r"course\_code\_is\_25CS2103E\_and\_room\_is\_H006"

    def test_consecutive_underscores_prevent_italic_breakage(self):
        text = "__init__ and ___triple___ and ____quad____"
        escaped = escape_markdown_underscores(text)
        assert r"\_\_init\_\_" in escaped
        assert r"\_\_\_triple\_\_\_" in escaped
        assert r"\_\_\_\_quad\_\_\_\_" in escaped

    def test_pre_escaped_underscores_are_not_double_escaped(self):
        text = r"already\_escaped and unescaped_text"
        escaped = escape_markdown_underscores(text)
        assert escaped == r"already\_escaped and unescaped\_text"
        assert r"\\" not in escaped

    def test_inline_code_spans_preserve_underscores(self):
        text = "Run `import os_helper` and execute `python -m src.test_runner` in terminal."
        escaped = escape_markdown_underscores(text)
        assert "`import os_helper`" in escaped
        assert "`python -m src.test_runner`" in escaped
        assert r"os\_helper" not in escaped

    def test_code_blocks_preserve_underscores(self):
        text = (
            "Review the code below:\n"
            "```python\n"
            "def handle_academic_event(event_id, user_token):\n"
            "    my_var_name = 100\n"
            "    return my_var_name\n"
            "```\n"
            "End of notice."
        )
        escaped = escape_markdown_underscores(text)
        assert "def handle_academic_event(event_id, user_token):" in escaped
        assert "my_var_name = 100" in escaped
        assert r"handle\_academic\_event" not in escaped

    def test_markdown_links_escape_label_preserve_url_underscores(self):
        text = (
            "Check [Course_Materials_T04]"
            "(https://drive.google.com/drive_folders/folder_abc_123?auth_user=0) "
            "and [Form_Registration](https://forms.gle/form_xyz_789)"
        )
        escaped = escape_markdown_underscores(text)
        # Label must be escaped so Telegram doesn't interpret it as italic
        assert r"[Course\_Materials\_T04]" in escaped
        assert r"[Form\_Registration]" in escaped
        # URL targets must NOT be escaped, otherwise URLs break with %5C
        assert "(https://drive.google.com/drive_folders/folder_abc_123?auth_user=0)" in escaped
        assert "(https://forms.gle/form_xyz_789)" in escaped

    def test_complex_mixed_formatting_tokens(self):
        text = (
            "Notice: Course_A is rescheduled.\n"
            "• Use `helper_func_v2` for submission.\n"
            "• See [Drive_Link](https://drive.google.com/doc_id_999).\n"
            "• Do not modify test_file_final.py!"
        )
        escaped = escape_markdown_underscores(text)
        assert r"Course\_A" in escaped
        assert "`helper_func_v2`" in escaped
        assert r"[Drive\_Link](https://drive.google.com/doc_id_999)" in escaped
        assert r"test\_file\_final.py" in escaped

    def test_empty_or_no_underscore_passthrough(self):
        assert escape_markdown_underscores("") == ""
        assert escape_markdown_underscores("Hello world 123!") == "Hello world 123!"


class TestMarkdownSanitizationAndUrls:
    """Stress-test sanitize_markdown and extract_and_clean_urls with malformed markup."""

    def test_unbalanced_backticks_balanced(self):
        assert sanitize_markdown("Code `var_name").endswith("`")
        assert sanitize_markdown("Normal `code` text") == "Normal `code` text"

    def test_unbalanced_bold_tokens_balanced(self):
        assert sanitize_markdown("**Important notice").endswith("**")
        assert sanitize_markdown("• **Course**: `25CS2103E`") == "• **Course**: `25CS2103E`"

    def test_broken_markdown_bracket_in_url_sanitized(self):
        raw = "Notice here [https://drive.google.com/folders/folder_id_123]("
        cleaned, links = extract_and_clean_urls(raw)
        assert len(links) == 1
        assert links[0][0] == "Google Drive Folder"
        assert not cleaned.endswith("](")
        assert "🔗 [Google Drive Folder]" in cleaned

    def test_bot_send_markdown_sanitization_integration(self):
        from src.notify.bot import BotClient

        client = BotClient()
        client._retry = MagicMock(return_value={"ok": True, "result": {"message_id": 123}})

        with patch("src.notify.bot.settings") as s:
            s.owner_chat_id = 999
            # Send message with unescaped underscores in Markdown
            client.send("Notice for course_code_test", parse_mode="Markdown")

            call_args = client._retry.call_args[0]
            assert call_args[0] == "sendMessage"
            sent_data = call_args[1]
            assert sent_data["parse_mode"] == "Markdown"
            assert r"course\_code\_test" in sent_data["text"]

    def test_bot_send_markdown_fallback_on_400_error(self):
        from src.notify.bot import BotClient, BotError

        client = BotClient()
        # First call raises 400 Bad Request, second call (retry) succeeds
        client._retry = MagicMock(
            side_effect=[
                BotError("Telegram 400 Bad Request: can't parse entities"),
                {"ok": True, "result": {"message_id": 124}},
            ]
        )

        with patch("src.notify.bot.settings") as s:
            s.owner_chat_id = 999
            res = client.send("Problematic *markup _text", parse_mode="Markdown")
            assert res["ok"] is True
            assert client._retry.call_count == 2
            # Second call must omit parse_mode
            retry_data = client._retry.call_args_list[1][0][1]
            assert "parse_mode" not in retry_data


# ============================================================================
# Vector 2: SPARK_MEDIA Invariant & Zero-Byte Download Testing
# ============================================================================


class TestSparkMediaHandling:
    """Stress-test media processing when SPARK_MEDIA is disabled."""

    @pytest.mark.asyncio
    async def test_voice_note_no_text_zero_download(self):
        from src.config import settings
        from src.ingestion.handlers import extract

        settings.spark_media = False
        client = MagicMock()
        client.download_media = AsyncMock()

        msg = MagicMock()
        msg.text = None
        msg.voice = True
        msg.photo = False
        msg.document = None

        event, source = await extract(client, msg)
        assert event is None
        assert source is None
        client.download_media.assert_not_called()

    @pytest.mark.asyncio
    async def test_audio_document_zero_download(self):
        from src.config import settings
        from src.ingestion.handlers import extract

        settings.spark_media = False
        client = MagicMock()
        client.download_media = AsyncMock()

        doc = MagicMock()
        doc.mime_type = "audio/ogg"
        msg = MagicMock()
        msg.text = ""
        msg.voice = False
        msg.photo = False
        msg.document = doc

        event, source = await extract(client, msg)
        assert event is None
        assert source is None
        client.download_media.assert_not_called()

    @pytest.mark.asyncio
    async def test_pdf_document_no_text_zero_download(self):
        from src.config import settings
        from src.ingestion.handlers import extract

        settings.spark_media = False
        client = MagicMock()
        client.download_media = AsyncMock()

        doc = MagicMock()
        doc.mime_type = "application/pdf"
        msg = MagicMock()
        msg.text = None
        msg.voice = False
        msg.photo = False
        msg.document = doc

        event, source = await extract(client, msg)
        assert event is None
        assert source is None
        client.download_media.assert_not_called()

    @pytest.mark.asyncio
    async def test_pdf_document_with_non_matching_caption_zero_download(self):
        from src.config import settings
        from src.ingestion.handlers import extract

        settings.spark_media = False
        client = MagicMock()
        client.download_media = AsyncMock()

        doc = MagicMock()
        doc.mime_type = "application/pdf"
        msg = MagicMock()
        msg.text = "Here is the syllabus document for all students."
        msg.date = datetime(2026, 9, 1, 10, 0, 0)
        msg.voice = False
        msg.photo = False
        msg.document = doc

        with patch("src.ingestion.handlers.ai_extractor") as mock_ai:
            event, source = await extract(client, msg)
            assert event is None
            assert source is None
            client.download_media.assert_not_called()
            mock_ai.extract_from_text.assert_not_called()
            mock_ai.extract_from_media.assert_not_called()

    @pytest.mark.asyncio
    async def test_photo_with_regex_caption_zero_download(self):
        from src.config import settings
        from src.ingestion.handlers import extract

        settings.spark_media = False
        client = MagicMock()
        client.download_media = AsyncMock()

        msg = MagicMock()
        msg.text = "DSA class shifted to H006"
        msg.date = datetime(2026, 9, 15, 9, 0, 0)
        msg.voice = False
        msg.photo = True
        msg.document = None

        event, source = await extract(client, msg)
        assert event is not None
        assert source == "regex"
        assert event.intent == "ROOM_OVERRIDE"
        assert event.room == "H006"
        client.download_media.assert_not_called()

    @pytest.mark.asyncio
    async def test_photo_without_regex_match_zero_download_no_ai_fallback(self):
        from src.config import settings
        from src.ingestion.handlers import extract

        settings.spark_media = False
        client = MagicMock()
        client.download_media = AsyncMock()

        msg = MagicMock()
        msg.text = "Photo of campus bulletin board"
        msg.date = datetime(2026, 9, 15, 9, 0, 0)
        msg.voice = False
        msg.photo = True
        msg.document = None

        with patch("src.ingestion.handlers.ai_extractor") as mock_ai:
            event, source = await extract(client, msg)
            assert event is None
            assert source is None
            client.download_media.assert_not_called()
            mock_ai.extract_from_text.assert_not_called()
            mock_ai.extract_from_media.assert_not_called()


# ============================================================================
# Vector 3: Proactive Reminders Boundary Testing
# ============================================================================


class TestProactiveRemindersBoundaries:
    """Stress-test run_reminders date filtering and deduplication boundaries."""

    @pytest.mark.asyncio
    async def test_reminders_trigger_only_for_today(self):
        from src.main import run_reminders

        today_dt = clock.today_ist()
        today_str = today_dt.strftime("%Y-%m-%d")
        tomorrow_str = (today_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_str = (today_dt - timedelta(days=1)).strftime("%Y-%m-%d")

        pending_items = [
            # Item 1: Due Tomorrow -> MUST NOT TRIGGER
            {
                "id": 101,
                "event": {
                    "summary": "Tomorrow Assignment",
                    "course_name": "ML",
                    "target_date": tomorrow_str,
                },
                "status": "PENDING",
            },
            # Item 2: Due Yesterday -> MUST NOT TRIGGER
            {
                "id": 102,
                "event": {
                    "summary": "Yesterday Assignment",
                    "course_name": "DSA",
                    "target_date": yesterday_str,
                },
                "status": "PENDING",
            },
            # Item 3: Undated Pending Item -> MUST NOT TRIGGER
            {
                "id": 103,
                "event": {
                    "summary": "Undated Backlog Item",
                    "course_name": "DBSE",
                    "target_date": None,
                },
                "status": "PENDING",
            },
            # Item 4: Due Today -> MUST TRIGGER
            {
                "id": 104,
                "event": {
                    "summary": "Today Lab Exam",
                    "course_name": "OSSP",
                    "target_date": today_str,
                },
                "status": "PENDING",
            },
        ]

        with (
            patch("src.utils.deduplication.deduplicator.list_pending", return_value=pending_items),
            patch("src.utils.deduplication.deduplicator.meta_get", return_value=None),
            patch("src.utils.deduplication.deduplicator.meta_set") as mock_meta_set,
            patch("src.notify.bot.bot.send") as mock_bot_send,
            patch("asyncio.sleep", side_effect=asyncio.CancelledError),
        ):
            with pytest.raises(asyncio.CancelledError):
                await run_reminders()

            # Only item 104 must have triggered a send
            assert mock_bot_send.call_count == 1
            sent_text = mock_bot_send.call_args[0][0]
            assert "Today Lab Exam" in sent_text
            assert "OSSP" in sent_text
            assert "Tomorrow Assignment" not in sent_text
            assert "Undated Backlog Item" not in sent_text

            # meta_set called for item 104
            mock_meta_set.assert_called_once()
            meta_key_arg = mock_meta_set.call_args[0][0]
            assert meta_key_arg == f"reminded:pending:104:{today_str}"

    @pytest.mark.asyncio
    async def test_reminders_debounced_if_already_sent_today(self):
        from src.main import run_reminders

        today_str = clock.today_ist().strftime("%Y-%m-%d")
        pending_items = [
            {
                "id": 201,
                "event": {
                    "summary": "Already Reminded Exam",
                    "course_name": "ESD",
                    "target_date": today_str,
                },
                "status": "PENDING",
            }
        ]

        with (
            patch("src.utils.deduplication.deduplicator.list_pending", return_value=pending_items),
            patch("src.utils.deduplication.deduplicator.meta_get", return_value="1792850000"),
            patch("src.notify.bot.bot.send") as mock_bot_send,
            patch("asyncio.sleep", side_effect=asyncio.CancelledError),
        ):
            with pytest.raises(asyncio.CancelledError):
                await run_reminders()

            mock_bot_send.assert_not_called()


# ============================================================================
# Vector 4: Timetable Horizon & Academic Calendar Horizon Testing
# ============================================================================


class TestTimetableHorizonAndAcademicCalendar:
    """Stress-test timetable validity horizon and calendar milestone guards."""

    def test_timetable_horizon_extension_validity(self):
        tt = load("data/timetable_T04.toml")
        assert tt is not None
        assert tt.meta.term == "T04"
        # Confirm valid_to is extended to 2026-12-15
        assert tt.meta.valid_from <= date(2026, 7, 15)
        assert tt.meta.valid_to >= date(2026, 12, 15)

    def test_date_lookups_across_horizon_boundary(self):
        from src.parsing.regex_parser import ExtractedAcademicEvent

        tt = load("data/timetable_T04.toml")
        assert tt is not None

        # 2026-11-01 (Sunday - last day of old horizon, valid in term)
        ev_nov1 = ExtractedAcademicEvent(
            intent="ROOM_OVERRIDE",
            summary="DSA room change to H006",
            course_name="DSA",
            room="H006",
            target_date="2026-11-01",
            period="P1",
        )
        verdict_nov1 = validate(ev_nov1, tt)
        assert verdict_nov1.reason != "OUTSIDE_TERM"

        # 2026-11-02 (Monday - day that previously failed with OUTSIDE_TERM)
        ev_nov2 = ExtractedAcademicEvent(
            intent="ROOM_OVERRIDE",
            summary="DSA room change to H006",
            course_name="DSA",
            room="H006",
            target_date="2026-11-02",
            period="P1",
        )
        verdict_nov2 = validate(ev_nov2, tt)
        assert verdict_nov2.reason != "OUTSIDE_TERM"

        # 2026-12-01 (Tuesday - valid in extended horizon)
        ev_dec1 = ExtractedAcademicEvent(
            intent="ROOM_OVERRIDE",
            summary="DSA room change to H006",
            course_name="DSA",
            room="H006",
            target_date="2026-12-01",
            period="P1",
        )
        verdict_dec1 = validate(ev_dec1, tt)
        assert verdict_dec1.reason != "OUTSIDE_TERM"

        # 2026-12-16 (Beyond term horizon -> MUST be OUTSIDE_TERM)
        ev_dec16 = ExtractedAcademicEvent(
            intent="ROOM_OVERRIDE",
            summary="DSA room change to H006",
            course_name="DSA",
            room="H006",
            target_date="2026-12-16",
            period="P1",
        )
        verdict_dec16 = validate(ev_dec16, tt)
        assert verdict_dec16.reason == "OUTSIDE_TERM"

        # 2026-07-01 (Before term horizon -> MUST be OUTSIDE_TERM)
        ev_jul1 = ExtractedAcademicEvent(
            intent="ROOM_OVERRIDE",
            summary="DSA room change to H006",
            course_name="DSA",
            room="H006",
            target_date="2026-07-01",
            period="P1",
        )
        verdict_jul1 = validate(ev_jul1, tt)
        assert verdict_jul1.reason == "OUTSIDE_TERM"

    def test_effective_slots_retrieval_in_november(self):
        # 2026-11-02 is a Monday
        slots = get_effective_slots("2026-11-02")
        assert len(slots) > 0
        assert all(s.day == "Mon" for s in slots)

    def test_academic_calendar_milestone_guards_and_conflict_detection(self):
        from src.academic_calendar import get_milestone_date, load_calendar

        cal = load_calendar()
        assert cal is not None
        assert "T04" in cal.terms

        # Verify milestone queries
        lab_exam_dt = get_milestone_date("lab exam", date(2026, 10, 1), cal)
        assert lab_exam_dt == date(2026, 10, 12)

        sem_end_dt = get_milestone_date("sem-end", date(2026, 10, 1), cal)
        assert sem_end_dt == date(2026, 10, 26)
        # Window-aware match when date falls within official examination period
        assert get_milestone_date("sem-end", date(2026, 11, 1), cal) == date(2026, 11, 1)

        detention_dt = get_milestone_date("detention", date(2026, 11, 1), cal)
        assert detention_dt == date(2026, 10, 16)
