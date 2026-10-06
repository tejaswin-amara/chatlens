import pytest

from src.config import Settings


def test_settings_valid():
    s = Settings(
        TELEGRAM_API_ID=123,
        TELEGRAM_API_HASH="SECRET_HASH_VALUE",
        TELEGRAM_SESSION_STRING="SECRET_SESSION_VALUE",
        GOOGLE_CREDENTIALS_BASE64="b64",
        GEMINI_API_KEY="SECRET_GEMINI_KEY",
        SPARK_MODE="dry",
        SPARK_CHAT_IDS="1,2, 3",
    )
    s.validate_required()
    assert s.allowed_chat_ids == [1, 2, 3]

    # Repr doesn't leak secrets
    r = repr(s)
    assert "SECRET_HASH_VALUE" not in r
    assert "SECRET_SESSION_VALUE" not in r

    # Str doesn't leak secrets
    st = str(s)
    assert "SECRET_HASH_VALUE" not in st
    assert "SECRET_GEMINI_KEY" not in st

    # Model dump doesn't leak secrets
    d = s.model_dump()
    assert d["telegram_api_hash"].get_secret_value() == "SECRET_HASH_VALUE"


def test_settings_invalid_chat_ids():
    s = Settings(
        TELEGRAM_API_ID=123,
        TELEGRAM_API_HASH="hash",
        TELEGRAM_SESSION_STRING="session",
        GOOGLE_CREDENTIALS_BASE64="b64",
        GEMINI_API_KEY="gemini",
        SPARK_MODE="dry",
        SPARK_CHAT_IDS="",
    )
    with pytest.raises(ValueError, match="cannot be empty"):
        s.validate_required()


def test_settings_invalid_mode():
    s = Settings(
        TELEGRAM_API_ID=123,
        TELEGRAM_API_HASH="hash",
        TELEGRAM_SESSION_STRING="session",
        GOOGLE_CREDENTIALS_BASE64="b64",
        GEMINI_API_KEY="gemini",
        SPARK_MODE="invalid",
        SPARK_CHAT_IDS="1",
    )
    with pytest.raises(ValueError, match="SPARK_MODE must be dry, confirm, or live"):
        s.validate_required()


def test_settings_missing_live_confirm():
    s = Settings(
        TELEGRAM_API_ID=123,
        TELEGRAM_API_HASH="hash",
        TELEGRAM_SESSION_STRING="session",
        GOOGLE_CREDENTIALS_BASE64="b64",
        GEMINI_API_KEY="gemini",
        SPARK_MODE="live",
        SPARK_CHAT_IDS="1",
    )
    with pytest.raises(ValueError, match="BOT_TOKEN"):
        s.validate_required()
