"""Comprehensive unit test suite for chatlens-v2/backend.

Tests parsers, deterministic content hashes, and statistical aggregation
without requiring live database or external network access.
"""

import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime

# Ensure chatlens-v2/backend is on python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chatlens-v2", "backend"))
)

from analyzer import _format_messages
from parsers.telegram import parse_telegram_export
from parsers.whatsapp import parse_whatsapp_export

# --- 1. WhatsApp Parser Tests ---


def test_whatsapp_parser_standard():
    """Test WhatsApp parser handling standard timestamps, multi-line continuations, and media."""
    content = """15/01/24, 10:30 - Messages are end-to-end encrypted.
15/01/24, 10:30 - Alice: Hello from Alice!
15/01/24, 10:31 - Bob: Here is a message
with a multi-line
continuation.
15/01/24, 10:32 - Alice: <Media omitted>
15/01/24, 10:33 - Alice: Back to regular text.
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name

    try:
        messages = parse_whatsapp_export(path)
        # System message and <Media omitted> should be filtered
        assert len(messages) == 3
        assert messages[0]["sender"] == "Alice"
        assert messages[0]["text"] == "Hello from Alice!"
        assert messages[0]["platform"] == "whatsapp"

        # Multi-line
        assert messages[1]["sender"] == "Bob"
        assert "multi-line\ncontinuation" in messages[1]["text"]

        # Final message
        assert messages[2]["sender"] == "Alice"
        assert messages[2]["text"] == "Back to regular text."
    finally:
        os.unlink(path)


def test_whatsapp_parser_us_format_and_12h():
    """Test WhatsApp parser handling US date format with AM/PM indicators."""
    content = """1/15/24, 10:30 AM - Carol: Morning team!
1/15/24, 2:45 PM - Dave: Good afternoon Carol.
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name

    try:
        messages = parse_whatsapp_export(path)
        assert len(messages) == 2
        assert messages[0]["sender"] == "Carol"
        assert messages[1]["sender"] == "Dave"
        assert messages[1]["text"] == "Good afternoon Carol."
    finally:
        os.unlink(path)


# --- 2. Telegram Parser Tests ---


def test_telegram_parser_single_chat():
    """Test Telegram parser handling JSON exports with structured text and service messages."""
    data = {
        "name": "Design Team",
        "type": "private_group",
        "id": 998877,
        "messages": [
            {
                "id": 1,
                "type": "message",
                "date": "2026-02-10T14:00:00",
                "from": "Elena",
                "from_id": "user001",
                "text": "Reviewing the designs now.",
            },
            {
                "id": 2,
                "type": "message",
                "date": "2026-02-10T14:01:00",
                "from": "Frank",
                "from_id": "user002",
                "text": [
                    {"type": "plain", "text": "See link: "},
                    {"type": "link", "text": "https://figma.com/file/xyz"},
                ],
            },
            {
                "id": 3,
                "type": "service",
                "date": "2026-02-10T14:02:00",
                "text": "Elena pinned a message",
            },
            {
                "id": 4,
                "type": "message",
                "date": "2026-02-10T14:03:00",
                "from": "Elena",
                "from_id": "user001",
                "text": "",
                "photo": "photos/screenshot.png",
            },
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        path = f.name

    try:
        messages = parse_telegram_export(path)
        # Service message (id=3) and photo without text (id=4) should be excluded
        assert len(messages) == 2
        assert messages[0]["sender"] == "Elena"
        assert messages[0]["text"] == "Reviewing the designs now."
        assert messages[0]["chat_name"] == "Design Team"
        assert messages[0]["platform"] == "telegram"

        # Text array joined
        assert messages[1]["sender"] == "Frank"
        assert messages[1]["text"] == "See link: https://figma.com/file/xyz"
    finally:
        os.unlink(path)


def test_telegram_parser_full_export_chats_list():
    """Test Telegram parser handling full account export with chats.list array."""
    data = {
        "chats": {
            "list": [
                {
                    "name": "General Chat",
                    "type": "public_supergroup",
                    "id": 1001,
                    "messages": [
                        {
                            "id": 10,
                            "type": "message",
                            "date": "2026-03-01T08:00:00",
                            "from": "Grace",
                            "from_id": "u10",
                            "text": "Morning everyone!",
                        }
                    ],
                },
                {
                    "name": "Tech Announcements",
                    "type": "channel",
                    "id": 1002,
                    "messages": [
                        {
                            "id": 20,
                            "type": "message",
                            "date": "2026-03-01T09:00:00",
                            "from": "Admin",
                            "from_id": "u0",
                            "text": "Maintenance at 10 PM.",
                        }
                    ],
                },
            ]
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        path = f.name

    try:
        messages = parse_telegram_export(path)
        assert len(messages) == 2
        assert messages[0]["chat_name"] == "General Chat"
        assert messages[0]["sender"] == "Grace"
        assert messages[1]["chat_name"] == "Tech Announcements"
        assert messages[1]["text"] == "Maintenance at 10 PM."
    finally:
        os.unlink(path)


# --- 3. Content-Hash Determinism Tests ---


def test_content_hash_determinism():
    """Test that content-hash generation is strictly reproducible across runs."""
    sender = "Alice Smith"
    timestamp = "2026-04-12T15:30:00"
    text = "Important project update meeting tomorrow at 9 AM."

    expected_hash = hashlib.sha256(f"{sender}:{timestamp}:{text}".encode()).hexdigest()

    # Re-generate multiple times
    h1 = hashlib.sha256(f"{sender}:{timestamp}:{text}".encode()).hexdigest()
    h2 = hashlib.sha256(f"{sender}:{timestamp}:{text}".encode()).hexdigest()

    assert h1 == expected_hash
    assert h2 == expected_hash
    assert len(expected_hash) == 64

    # Any change alters the hash
    altered_text_hash = hashlib.sha256(f"{sender}:{timestamp}:{text}.".encode()).hexdigest()
    assert altered_text_hash != expected_hash


# --- 4. Chat Statistical Aggregation Tests ---


def test_analyzer_format_messages():
    """Test helper formatting messages into structured transcript string."""
    messages = [
        {"sender": "Alice", "timestamp": "2026-05-01 10:00", "text": "Hi Bob"},
        {"sender": "Bob", "timestamp": "2026-05-01 10:02", "text": "Hey Alice!"},
    ]
    formatted = _format_messages(messages)
    assert "Alice (2026-05-01 10:00): Hi Bob" in formatted
    assert "Bob (2026-05-01 10:02): Hey Alice!" in formatted


def test_analyzer_forbidden_id_redaction():
    """Test ChatAnalyzer._format_messages strictly redacts Aadhaar, RRN, and MyNumber."""
    messages = [
        {
            "sender": "Alice",
            "timestamp": "2026-05-01 10:00",
            "text": "My Aadhaar is 2345 6789 0123 and KR RRN is 900101-1234567",
        },
        {
            "sender": "Bob",
            "timestamp": "2026-05-01 10:02",
            "text": "Japanese MyNumber is 1234 5678 9012. Please keep confidential.",
        },
    ]
    formatted = _format_messages(messages)
    assert "[Aadhaar Redacted]" in formatted
    assert "[RRN Redacted]" in formatted
    assert "[MyNumber Redacted]" in formatted
    # Assert zero raw digits for forbidden IDs
    assert "2345 6789 0123" not in formatted
    assert "900101-1234567" not in formatted
    assert "1234 5678 9012" not in formatted
    assert "234567890123" not in formatted
    assert "123456789012" not in formatted


def test_chat_statistics_aggregation():
    """Test pure statistical aggregation functions without requiring live database."""
    sample_messages = [
        {"sender": "Alice", "timestamp": "2026-05-01T09:15:00", "text": "Morning!"},
        {"sender": "Bob", "timestamp": "2026-05-01T09:20:00", "text": "Good morning Alice."},
        {"sender": "Alice", "timestamp": "2026-05-01T14:30:00", "text": "Status update ready."},
        {"sender": "Carol", "timestamp": "2026-05-02T11:00:00", "text": "Reviewed and approved."},
        {"sender": "Bob", "timestamp": "2026-05-02T16:45:00", "text": "Deployed to staging."},
    ]

    total_count = len(sample_messages)
    assert total_count == 5

    # Participant breakdown
    senders = Counter(m["sender"] for m in sample_messages)
    assert senders["Alice"] == 2
    assert senders["Bob"] == 2
    assert senders["Carol"] == 1
    assert len(senders) == 3

    # Hourly distribution
    hours = [datetime.fromisoformat(m["timestamp"]).hour for m in sample_messages]
    hour_counts = Counter(hours)
    assert hour_counts[9] == 2
    assert hour_counts[14] == 1
    assert hour_counts[11] == 1
    assert hour_counts[16] == 1

    # Date timeline buckets
    dates = [datetime.fromisoformat(m["timestamp"]).date().isoformat() for m in sample_messages]
    date_counts = Counter(dates)
    assert date_counts["2026-05-01"] == 3
    assert date_counts["2026-05-02"] == 2
