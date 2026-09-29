"""Unit tests for Tier-2 Multimodal Gemini AI Extractor."""

from unittest.mock import MagicMock, patch

from src.parsing.ai_extractor import AIExtractor
from src.parsing.schemas import ExtractedAcademicEvent


@patch("src.parsing.ai_extractor.genai.Client")
def test_ai_extractor_from_text(mock_client_cls: MagicMock) -> None:
    mock_parsed_event = ExtractedAcademicEvent(
        intent="ROOM_OVERRIDE",
        course_name="ML",
        course_code="25CS2103E",
        room="HC-15C",
        target_date="2026-03-30",
        period="P3-P4",
        summary="Room for ML updated to HC-15C",
        action_required=False,
    )

    mock_response = MagicMock()
    mock_response.parsed = mock_parsed_event
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    extractor = AIExtractor(api_key="fake-key-123")
    result = extractor.extract_from_text("ML class has been shifted to room HC-15C today.")

    assert result.intent == "ROOM_OVERRIDE"
    assert result.course_name == "ML"
    assert result.room == "HC-15C"


@patch("src.parsing.ai_extractor.genai.Client")
def test_ai_extractor_from_voice(mock_client_cls: MagicMock) -> None:
    mock_parsed_event = ExtractedAcademicEvent(
        intent="TASK",
        course_name="OSSP",
        course_code="25CS2102",
        room=None,
        target_date="2026-04-05",
        period=None,
        summary="Voice memo: Submit OSSP assignment by Sunday.",
        action_required=True,
    )

    mock_response = MagicMock()
    mock_response.parsed = mock_parsed_event
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    extractor = AIExtractor(api_key="fake-key-123")
    fake_audio = b"\x00\x01\x02\x03"
    result = extractor.extract_from_voice(fake_audio)

    assert result.intent == "TASK"
    assert result.course_name == "OSSP"
    assert result.action_required is True


@patch("src.parsing.ai_extractor.genai.Client")
def test_ai_extractor_from_media(mock_client_cls: MagicMock) -> None:
    mock_parsed_event = ExtractedAcademicEvent(
        intent="HOLIDAY",
        course_name=None,
        course_code=None,
        room=None,
        target_date="2026-04-01",
        period=None,
        summary="University Notice: Holiday declared for April Fools' Day.",
        action_required=False,
    )

    mock_response = MagicMock()
    mock_response.parsed = mock_parsed_event
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    extractor = AIExtractor(api_key="fake-key-123")
    fake_image = b"\xff\xd8\xff\xe0"
    result = extractor.extract_from_media(fake_image)

    assert result.intent == "HOLIDAY"
    assert result.target_date == "2026-04-01"
