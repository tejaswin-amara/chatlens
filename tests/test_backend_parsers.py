"""Unit tests for ChatLens v2 WhatsApp and Telegram export parsers."""

import json
import sys
from pathlib import Path

backend_dir = str(Path(__file__).resolve().parent.parent / "chatlens-v2" / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from parsers.telegram import parse_telegram_export  # noqa: E402
from parsers.whatsapp import parse_whatsapp_export  # noqa: E402


def test_whatsapp_parser_basic(tmp_path: Path):
    chat_file = tmp_path / "study_group.txt"
    chat_file.write_text(
        "12/31/20, 1:45 PM - Messages and calls are end-to-end encrypted. "
        "No one outside of this chat.\n"
        "12/31/20, 1:46 PM - Alice: Hey everyone, welcome to the study group!\n"
        "12/31/20, 1:47 PM - Bob: Thanks Alice.\nHere are my notes for DSA:\n- Arrays\n- Trees\n"
        "12/31/20, 1:48 PM - Alice: <media omitted>\n"
        "12/31/20, 1:49 PM - Charlie: See you all tomorrow at HC-15C.\n",
        encoding="utf-8",
    )

    results = parse_whatsapp_export(str(chat_file))
    assert len(results) == 3

    assert results[0]["sender"] == "Alice"
    assert results[0]["text"] == "Hey everyone, welcome to the study group!"
    assert results[0]["platform"] == "whatsapp"
    assert results[0]["chat_name"] == "study_group"

    # Multi-line message
    assert results[1]["sender"] == "Bob"
    assert "Here are my notes for DSA:\n- Arrays\n- Trees" in results[1]["text"]

    assert results[2]["sender"] == "Charlie"
    assert "HC-15C" in results[2]["text"]


def test_whatsapp_parser_24h_format(tmp_path: Path):
    chat_file = tmp_path / "project_team.txt"
    chat_file.write_text(
        "31/12/2020, 14:15 - David: Let's meet at 3 PM.\n31.12.20, 14:16 - Eve: Sounds good.\n",
        encoding="utf-8",
    )

    results = parse_whatsapp_export(str(chat_file))
    assert len(results) == 2
    assert results[0]["sender"] == "David"
    assert results[1]["sender"] == "Eve"


def test_telegram_parser_single_chat(tmp_path: Path):
    data = {
        "name": "Machine Learning Discussion",
        "type": "public_supergroup",
        "id": 987654321,
        "messages": [
            {
                "id": 101,
                "type": "message",
                "date": "2026-10-15T10:00:00",
                "from": "Prof. Rao",
                "text": "Assignment 2 is posted.",
                "reply_to_message_id": None,
            },
            {
                "id": 102,
                "type": "service",
                "date": "2026-10-15T10:05:00",
                "action": "pin_message",
            },
            {
                "id": 103,
                "type": "message",
                "date": "2026-10-15T10:10:00",
                "from": "Student 1",
                "text": [
                    "Is it due on ",
                    {"type": "bold", "text": "Monday"},
                    "?",
                ],
                "reply_to_message_id": 101,
            },
        ],
    }

    json_file = tmp_path / "result.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")

    results = parse_telegram_export(str(json_file))
    assert len(results) == 2

    assert results[0]["sender"] == "Prof. Rao"
    assert results[0]["text"] == "Assignment 2 is posted."
    assert results[0]["chat_name"] == "Machine Learning Discussion"
    assert results[0]["reply_to"] is None

    # Flattened text parts
    assert results[1]["sender"] == "Student 1"
    assert results[1]["text"] == "Is it due on Monday?"
    assert results[1]["reply_to"] == "101"


def test_telegram_parser_full_account(tmp_path: Path):
    data = {
        "chats": {
            "about": "Full account export",
            "list": [
                {
                    "name": "OSSP Class",
                    "id": 111,
                    "type": "private_group",
                    "messages": [
                        {
                            "id": 1,
                            "type": "message",
                            "date": "2026-10-15T09:00:00",
                            "from": "Instructor",
                            "text": "Lab session at HC-15C today.",
                        }
                    ],
                },
                {
                    "name": "DSA Class",
                    "id": 222,
                    "type": "private_group",
                    "messages": [
                        {
                            "id": 2,
                            "type": "message",
                            "date": "2026-10-15T11:00:00",
                            "from": "TA",
                            "text": "Practice problem set uploaded.",
                        }
                    ],
                },
            ],
        }
    }

    json_file = tmp_path / "account_export.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")

    results = parse_telegram_export(str(json_file))
    assert len(results) == 2
    assert results[0]["chat_name"] == "OSSP Class"
    assert results[0]["text"] == "Lab session at HC-15C today."
    assert results[1]["chat_name"] == "DSA Class"
    assert results[1]["text"] == "Practice problem set uploaded."
