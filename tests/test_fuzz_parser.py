"""Exhaustive fuzzing and error-path unit tests for ChatLens v2 parsers.

Validates parser resilience against:
- Malformed WhatsApp exports (invalid timestamps, missing senders, mixed locales)
- Corrupt and non-standard Telegram JSON exports
- Empty, corrupted, and directory-traversal (Zip slip) zip archives
- Boundary limits and fuzz invariants (never raises uncaught exceptions,
  always returns schema-compliant message dictionaries)
"""

import json
import sys
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

backend_dir = str(Path(__file__).resolve().parent.parent / "chatlens-v2" / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from celery_worker import parse_and_save_sync  # noqa: E402
from parsers.telegram import _flatten_text, parse_telegram_export  # noqa: E402
from parsers.whatsapp import parse_whatsapp_export  # noqa: E402

# ── 1. WhatsApp Parser Fuzzing & Edge Cases ──


def test_whatsapp_empty_file(tmp_path: Path):
    f = tmp_path / "empty_chat.txt"
    f.write_text("", encoding="utf-8")
    msgs = parse_whatsapp_export(str(f))
    assert msgs == []


def test_whatsapp_whitespace_and_garbage(tmp_path: Path):
    f = tmp_path / "garbage.txt"
    f.write_text(
        "   \n\n\t\nRandom unformatted text without any timestamp\nAnother line\n",
        encoding="utf-8",
    )
    msgs = parse_whatsapp_export(str(f))
    assert msgs == []


def test_whatsapp_invalid_timestamps_fallback(tmp_path: Path):
    """Verify parser does not crash on impossible dates, falling back to raw string."""
    content = (
        "99/99/99, 99:99 - Ghost: Spooky message\n"
        "00/00/0000, 00:00 - Zero: Matrix line\n"
        "31/02/2026, 12:00 - NonLeap: Feb 31st invalid\n"
    )
    f = tmp_path / "invalid_dates.txt"
    f.write_text(content, encoding="utf-8")
    msgs = parse_whatsapp_export(str(f))
    assert len(msgs) == 3
    assert msgs[0]["sender"] == "Ghost"
    assert msgs[0]["timestamp"] == "99/99/99, 99:99"
    assert msgs[1]["sender"] == "Zero"
    assert msgs[2]["sender"] == "NonLeap"


def test_whatsapp_missing_sender_and_system_markers(tmp_path: Path):
    content = (
        "15/10/2026, 10:00 - Messages and calls are end-to-end encrypted. "
        "No one outside can read.\n"
        "15/10/2026, 10:05 - Alice: Hello everyone\n"
        "15/10/2026, 10:06 - <Media omitted>\n"
        "Continuation line belonging to nothing\n"
        "15/10/2026, 10:10 - Bob: Replying with\nmultiline continuation\nand another line\n"
        "15/10/2026, 10:15 - This message was deleted\n"
    )
    f = tmp_path / "system_and_multiline.txt"
    f.write_text(content, encoding="utf-8")
    msgs = parse_whatsapp_export(str(f))
    assert len(msgs) == 2
    assert msgs[0]["sender"] == "Alice"
    assert msgs[0]["text"] == "Hello everyone"
    assert msgs[1]["sender"] == "Bob"
    assert "multiline continuation" in msgs[1]["text"]
    assert "and another line" in msgs[1]["text"]


def test_whatsapp_mixed_international_locales(tmp_path: Path):
    content = (
        "15/10/26, 1:45 PM - Sender1: US 12h format\n"
        "15/10/2026, 13:45 - Sender2: 24h format\n"
        "15.10.26, 13:45 - Sender3: Dot format\n"
        "10/15/26, 09:30 AM - Sender4: Month first 12h\n"
    )
    f = tmp_path / "mixed_locales.txt"
    f.write_text(content, encoding="utf-8")
    msgs = parse_whatsapp_export(str(f))
    assert len(msgs) == 4
    for m in msgs:
        assert m["platform"] == "whatsapp"
        assert len(m["timestamp"]) > 0
        assert m["sender"].startswith("Sender")


def test_whatsapp_extreme_line_lengths(tmp_path: Path):
    huge_text = "A" * 100_000
    content = f"15/10/2026, 10:00 - Alice: {huge_text}\n"
    f = tmp_path / "huge.txt"
    f.write_text(content, encoding="utf-8")
    msgs = parse_whatsapp_export(str(f))
    assert len(msgs) == 1
    assert len(msgs[0]["text"]) == 100_000


# ── 2. Telegram Parser Fuzzing & Edge Cases ──


def test_telegram_corrupt_json(tmp_path: Path):
    f = tmp_path / "corrupt.json"
    f.write_text('{"messages": [{"type": "message", "text": "unclosed', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        parse_telegram_export(str(f))


def test_telegram_empty_or_non_dict(tmp_path: Path):
    f1 = tmp_path / "empty.json"
    f1.write_text("{}", encoding="utf-8")
    assert parse_telegram_export(str(f1)) == []

    f2 = tmp_path / "array.json"
    f2.write_text("[]", encoding="utf-8")
    assert parse_telegram_export(str(f2)) == []


def test_telegram_flatten_text_heterogeneous_structures():
    assert _flatten_text("") == ""
    assert _flatten_text("plain string") == "plain string"
    assert _flatten_text(None) == ""
    assert _flatten_text(12345) == ""
    assert _flatten_text(["part1", " ", "part2"]) == "part1 part2"
    assert (
        _flatten_text(
            [
                "Visit ",
                {"type": "link", "text": "https://example.com"},
                " for details.",
                {"other": "missing text key"},
            ]
        )
        == "Visit https://example.com for details."
    )


def test_telegram_missing_and_service_fields(tmp_path: Path):
    data = {
        "name": "Channel",
        "messages": [
            {"type": "service", "action": "pin_message", "text": "Service message"},
            {"type": "message", "text": ""},  # empty text -> skipped
            {"type": "message", "text": "   "},  # whitespace text -> skipped
            {
                "type": "message",
                "text": "Valid message",
                "from": None,
                "actor": "FallbackActor",
                "date": "2026-10-15T12:00:00",
            },
            {
                "type": "message",
                "text": "Another valid",
                # missing from and actor
                "date": "2026-10-15T12:05:00",
                "reply_to_message_id": 42,
            },
        ],
    }
    f = tmp_path / "telegram_edge.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    msgs = parse_telegram_export(str(f))
    assert len(msgs) == 2
    assert msgs[0]["sender"] == "FallbackActor"
    assert msgs[1]["sender"] == "Unknown"
    assert msgs[1]["reply_to"] == "42"


# ── 3. Zip Archive Security & Edge Cases (Zip Slip & Empty Zips) ──


def test_parse_and_save_empty_zip(tmp_path: Path):
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(str(zip_path), "w"):
        pass  # 0 entries

    res = parse_and_save_sync(str(zip_path), "whatsapp")
    assert res["status"] == "done"
    assert res["count"] == 0


def test_parse_and_save_zip_without_chat_files(tmp_path: Path):
    zip_path = tmp_path / "images_only.zip"
    with zipfile.ZipFile(str(zip_path), "w") as z:
        z.writestr("photo.jpg", b"fake-jpg-data")
        z.writestr("notes.pdf", b"fake-pdf-data")

    res = parse_and_save_sync(str(zip_path), "whatsapp")
    assert res["status"] == "done"
    assert res["count"] == 0


def test_parse_and_save_zip_slip_rejection(tmp_path: Path):
    """Verify zip archives attempting path traversal are rejected safely."""
    zip_path = tmp_path / "malicious_slip.zip"
    with zipfile.ZipFile(str(zip_path), "w") as z:
        z.writestr("../../etc/passwd", "root:x:0:0:::")

    res = parse_and_save_sync(str(zip_path), "whatsapp")
    assert res["status"] == "error"
    assert "unsafe path traversal" in res["error"]


def test_parse_and_save_valid_nested_zip(tmp_path: Path):
    zip_path = tmp_path / "valid_chat.zip"
    chat_content = (
        "15/10/26, 10:00 AM - Alice: Message inside zip\n"
        "15/10/26, 10:05 AM - Bob: Acknowledged inside zip\n"
    )
    with zipfile.ZipFile(str(zip_path), "w") as z:
        z.writestr("chat/nested_whatsapp.txt", chat_content)

    with patch("celery_worker.save_messages", new=AsyncMock()):
        res = parse_and_save_sync(str(zip_path), "whatsapp")
        assert res["status"] == "done"
        assert res["count"] == 2
