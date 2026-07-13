"""Parser for Telegram Desktop JSON exports."""

import json
from pathlib import Path


def _flatten_text(text_field) -> str:
    """Flatten Telegram's text field (plain string or list of segments) to a single string."""
    if isinstance(text_field, str):
        return text_field
    if isinstance(text_field, list):
        parts = []
        for part in text_field:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get("text", ""))
        return "".join(parts)
    return ""


def _parse_message(msg: dict, chat_name: str) -> dict | None:
    """Convert a single Telegram message dict to our standard format."""
    if msg.get("type") != "message":
        return None
    text = _flatten_text(msg.get("text", ""))
    if not text.strip():
        return None
    return {
        "platform": "telegram",
        "chat_name": chat_name,
        "sender": msg.get("from", msg.get("actor", "Unknown")),
        "timestamp": msg.get("date", ""),
        "text": text,
        "reply_to": msg.get("reply_to_message_id"),
        "forwarded_from": msg.get("forwarded_from"),
    }


def parse_telegram_export(file_path: str) -> list[dict]:
    """Parse a Telegram Desktop JSON export file.

    Handles both full-account exports (chats.list[].messages[]) and
    single-chat exports (messages[] at root).
    """
    data = json.loads(Path(file_path).read_text(encoding="utf-8"))
    results: list[dict] = []

    if "chats" in data:
        # Full-account export
        for chat in data["chats"].get("list", []):
            chat_name = chat.get("name", chat.get("id", "Unknown"))
            for msg in chat.get("messages", []):
                parsed = _parse_message(msg, str(chat_name))
                if parsed:
                    results.append(parsed)
    elif "messages" in data:
        # Single-chat export
        chat_name = data.get("name", Path(file_path).stem)
        for msg in data["messages"]:
            parsed = _parse_message(msg, str(chat_name))
            if parsed:
                results.append(parsed)

    return results
