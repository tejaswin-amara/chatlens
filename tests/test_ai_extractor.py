from unittest.mock import MagicMock, patch

import pytest

from src.parsing.ai_extractor import AIExtractor
from src.utils import clock


@pytest.fixture
def clean_db():
    from src.utils.db import get_connection
    from src.utils.deduplication import deduplicator

    deduplicator._init_db()
    with get_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS llm_budget (day TEXT PRIMARY KEY, calls INTEGER)")
        conn.execute("DELETE FROM llm_budget")


def test_ai_extractor_budget_exhaustion(clean_db):
    from src.config import settings

    extractor = AIExtractor()
    from src.utils.db import get_connection

    with get_connection() as conn:
        today_str = clock.today_ist().strftime("%Y-%m-%d")
        conn.execute(
            "INSERT INTO llm_budget (day, calls) VALUES (?, ?)",
            (today_str, settings.gemini_daily_budget),
        )

    with patch("src.notify.bot.bot.send"):
        res = extractor.extract_from_text("Test", None)
        assert res is None


def test_ai_extractor_day_rollover(clean_db):
    from src.config import settings

    extractor = AIExtractor()
    import datetime

    from src.utils.db import get_connection

    with get_connection() as conn:
        yesterday_str = (clock.today_ist() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        conn.execute(
            "INSERT INTO llm_budget (day, calls) VALUES (?, ?)",
            (yesterday_str, settings.gemini_daily_budget),
        )

    with patch("src.parsing.ai_extractor.AIExtractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.text = '{"intent": "TASK", "summary": "Test", "action_required": false}'
        mock_client.models.generate_content.return_value = mock_resp
        res = extractor.extract_from_text("Test", None)
        assert res is not None


def test_ai_extractor_retry_counts_toward_budget(clean_db):
    extractor = AIExtractor()
    with patch("src.parsing.ai_extractor.AIExtractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("Transient Error")

        with pytest.raises(Exception):
            extractor.extract_from_text("Test", None)

        from src.utils.db import get_connection

        with get_connection() as conn:
            today_str = clock.today_ist().strftime("%Y-%m-%d")
            row = conn.execute(
                "SELECT calls FROM llm_budget WHERE day = ?", (today_str,)
            ).fetchone()
            # It should have counted up on each attempt
            assert row[0] >= 2


def test_ai_extractor_redaction_cases(clean_db):
    extractor = AIExtractor()
    with patch("src.parsing.ai_extractor.AIExtractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.text = '{"intent": "TASK", "summary": "Test", "action_required": false}'
        mock_client.models.generate_content.return_value = mock_resp

        extractor.extract_from_text(
            "Call 123-456-7890 or 9876543210 and email test@example.com", None
        )

        call_args = mock_client.models.generate_content.call_args.kwargs["contents"]
        text_sent = str(call_args)
        assert "123-456-7890" not in text_sent
        assert "9876543210" not in text_sent
        assert "test@example.com" not in text_sent
        assert "[PHONE]" in text_sent
        assert "[EMAIL]" in text_sent


def test_ai_extractor_no_sampling_params(clean_db):
    extractor = AIExtractor()
    with patch("src.parsing.ai_extractor.AIExtractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.text = '{"intent": "TASK", "summary": "Test", "action_required": false}'
        mock_client.models.generate_content.return_value = mock_resp

        extractor.extract_from_text("Test", None)
        config = mock_client.models.generate_content.call_args.kwargs["config"]
        # Verify no temperature/top_k/top_p
        if not isinstance(config, dict):
            # pydantic/object style
            config = getattr(config, "model_dump", lambda: getattr(config, "__dict__", {}))()

        assert config.get("temperature") is None
        assert config.get("top_p") is None
        assert config.get("top_k") is None


def test_ai_extractor_clienterror_not_retried(clean_db):
    from google.genai import errors

    extractor = AIExtractor()
    with patch("src.parsing.ai_extractor.AIExtractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.models.generate_content.side_effect = errors.ClientError(
            "400 Bad Request", response_json={}
        )

        with pytest.raises(errors.ClientError):
            extractor.extract_from_text("Test", None)

        assert mock_client.models.generate_content.call_count == 1


def test_ai_extractor_media_gate(clean_db):
    extractor = AIExtractor()
    with patch("src.config.settings.spark_media", False):
        res = extractor.extract_from_media(b"123", "image/jpeg", None)
        assert res is None


def test_ai_extractor_empty_response(clean_db):
    extractor = AIExtractor()
    with patch("src.parsing.ai_extractor.AIExtractor._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.text = "{}"
        mock_client.models.generate_content.return_value = mock_resp
        res = extractor.extract_from_text("Test", None)
        assert res is None
