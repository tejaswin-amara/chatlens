"""Parser for WhatsApp exported .txt chat files."""

import re
from datetime import datetime
from pathlib import Path

# Matches lines like:
#   12/31/20, 1:45 PM - Sender: text
#   31/12/2020, 13:45 - Sender: text
#   31.12.20, 13:45 - Sender: text
_LINE_RE = re.compile(
    r"^(\d{1,2}[/\.]\d{1,2}[/\.]\d{2,4}),?\s+"  # date
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)"  # time
    r"\s*[-–]\s*"  # separator
    r"(.+?):\s"  # sender
    r"(.*)",  # message start
    re.DOTALL,
)

_SYSTEM_MARKERS = {
    "messages and calls are end-to-end encrypted",
    "<media omitted>",
    "this message was deleted",
    "you deleted this message",
    "missed voice call",
    "missed video call",
}

# ponytail: brute-force tries multiple date formats instead of locale detection
_DATE_FORMATS = [
    "%d/%m/%Y, %I:%M %p",
    "%m/%d/%Y, %I:%M %p",
    "%d/%m/%y, %I:%M %p",
    "%m/%d/%y, %I:%M %p",
    "%d/%m/%Y, %H:%M",
    "%m/%d/%Y, %H:%M",
    "%d/%m/%y, %H:%M",
    "%m/%d/%y, %H:%M",
    "%d.%m.%y, %H:%M",
    "%d.%m.%y, %I:%M %p",
    "%d.%m.%Y, %H:%M",
    "%d.%m.%Y, %I:%M %p",
]


def _parse_datetime(date_str: str, time_str: str) -> str:
    """Try multiple date/time formats and return ISO string."""
    raw = f"{date_str}, {time_str}".strip()
    # Normalize whitespace around AM/PM
    raw = re.sub(r"\s+", " ", raw)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except ValueError:
            continue
    return raw  # fallback: return as-is


def parse_whatsapp_export(file_path: str) -> list[dict]:
    """Parse a WhatsApp exported .txt chat file."""
    path = Path(file_path)
    chat_name = path.stem
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    results: list[dict] = []
    current: dict | None = None

    for line in lines:
        m = _LINE_RE.match(line)
        if m:
            # Flush previous message
            if current and current["text"].strip():
                results.append(current)

            date_str, time_str, sender, text = m.groups()

            if any(marker in text.lower() for marker in _SYSTEM_MARKERS):
                current = None
                continue

            current = {
                "platform": "whatsapp",
                "chat_name": chat_name,
                "sender": sender.strip(),
                "timestamp": _parse_datetime(date_str, time_str),
                "text": text,
            }
        elif current is not None:
            # Continuation of multi-line message
            current["text"] += "\n" + line

    # Flush last message
    if current and current["text"].strip():
        results.append(current)

    return results
