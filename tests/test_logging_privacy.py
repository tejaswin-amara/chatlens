from src.utils.logging import _scrub_secrets, _sentry_before_send


def test_sentry_before_send():
    # bot token regex scrubbing
    event = {
        "logentry": {"message": "Called with bot1234:ABCDEF-xyz"},
        "exception": {"values": [{"value": "HTTP 401 bot123:abc_def"}]},
        "extra": {"msg_text": "Hello world", "message_text": "Hello again"},
    }

    result = _sentry_before_send(event, None)

    assert result["logentry"]["message"] == "Called with ***"
    assert result["exception"]["values"][0]["value"] == "HTTP 401 ***"
    assert "msg_text" not in result["extra"]
    assert "message_text" not in result["extra"]


def test_sentry_before_send_aiza():
    event = {
        "logentry": {"message": "Called with FxxxFAKE-abcdefghijklmnopqrstuvwx_yZ123"},
        "exception": {"values": [{"value": "HTTP 401 FxxxFAKE-abcdefghijklmnopqrstuvwx_yZ123"}]},
        "extra": {},
    }

    result = _sentry_before_send(event, None)
    assert result["logentry"]["message"] == "Called with ***"
    assert result["exception"]["values"][0]["value"] == "HTTP 401 ***"


def test_structlog_scrub_secrets():
    event_dict = {
        "event": "Using bot12345:1234567890-ABCDEF",
        "error": "Failed with FxxxFAKE-abcdefghijklmnopqrstuvwx_yZ123",
        "level": "info",
    }

    result = _scrub_secrets(None, None, event_dict)
    assert result["event"] == "Using ***"
    assert result["error"] == "Failed with ***"


def test_sentry_no_leak_of_message():
    event = {"extra": {"msg_text": "Private contents"}}
    result = _sentry_before_send(event, None)
    assert "msg_text" not in result.get("extra", {})


def test_structlog_no_side_effects_on_clean_logs():
    event_dict = {
        "event": "Routine operation complete",
        "level": "info",
        "extra_info": "Some generic text",
    }
    result = _scrub_secrets(None, None, event_dict)
    assert result["event"] == "Routine operation complete"


def test_forbidden_id_scrubbing_and_zero_disclosure():
    raw_aadhaar_space = "2345 6789 0123"
    raw_aadhaar_dash = "9876-5432-1098"
    raw_rrn = "950101-1234567"
    raw_mynumber = "1234 5678 9012"
    raw_phone_dash = "123-456-7890"
    raw_phone_solid = "9876543210"
    raw_phone_intl = "+91 98765 43210"

    event_dict = {
        "event": (
            f"Student with Aadhaar {raw_aadhaar_space}, RRN {raw_rrn}, phone {raw_phone_dash}"
        ),
        "metadata": {
            "aadhaar_alt": raw_aadhaar_dash,
            "jp_id": raw_mynumber,
            "contact": raw_phone_solid,
            "intl_phone": raw_phone_intl,
        },
    }

    result = _scrub_secrets(None, None, event_dict)

    # 1. Check placeholders
    assert "[Aadhaar Redacted]" in result["event"]
    assert "[RRN Redacted]" in result["event"]
    assert "[PHONE]" in result["event"]
    assert "[Aadhaar Redacted]" in result["metadata"]["aadhaar_alt"]
    assert "[MyNumber Redacted]" in result["metadata"]["jp_id"]
    assert "[PHONE]" in result["metadata"]["contact"]
    assert "[PHONE]" in result["metadata"]["intl_phone"]

    # 2. Strict Zero-Disclosure verification: zero raw digits in output
    for sensitive_id in [
        raw_aadhaar_space,
        raw_aadhaar_dash,
        raw_rrn,
        raw_mynumber,
        raw_phone_dash,
        raw_phone_solid,
        raw_phone_intl,
    ]:
        assert sensitive_id not in str(result)
        # Ensure digits sequence is not present
        digits_only = "".join(filter(str.isdigit, sensitive_id))
        assert digits_only not in str(result)


def test_phone_number_scrubbing_formats():
    event_dict = {
        "us_phone": "Call (123) 456-7890 immediately",
        "intl_phone": "Reach +1-123-456-7890 or +91 9876543210",
        "in_phone_split": "Emergency: 98765 43210 or 98765-43210",
    }
    result = _scrub_secrets(None, None, event_dict)
    assert result["us_phone"] == "Call [PHONE] immediately"
    assert result["intl_phone"] == "Reach [PHONE] or [PHONE]"
    assert result["in_phone_split"] == "Emergency: [PHONE] or [PHONE]"
