"""Deterministic PII redaction module conforming to [R-BAN-4]."""

from __future__ import annotations

import re

# Deterministic patterns conforming to [R-BAN-4]
_TOKEN_PATTERNS = [
    re.compile(r"\b(?:bot)?\d{8,12}:[A-Za-z0-9_-]{20,45}\b"),  # Telegram Bot Token
    re.compile(r"\bAIza[0-9A-Za-z\-_]{30,40}\b"),  # Google API key
    re.compile(r"\bAQ\.[A-Za-z0-9_-]{25,}\b"),  # Gemini API key
    re.compile(r"(?:Bearer\s+|token=)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE),
]

_ID_PATTERNS = [
    re.compile(r"\b2\d{9}\b"),  # Student roll number (e.g. 2520090104)
    re.compile(r"\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b"),  # Aadhaar
    re.compile(r"\b\d{6}[\s\-]?[1-8]\d{6}\b"),  # RRN
    re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),  # MyNumber
]

_PHONE_PATTERNS = [
    re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b"),  # Indian 10-digit mobile
    re.compile(r"\b\+?[1-9]\d{0,2}[\-\s]?\(?\d{2,4}\)?[\-\s]?\d{3,4}[\-\s]?\d{3,4}\b"),
]


def redact_pii(text: str) -> str:
    """Deterministically redact PII from text replacing with [PHONE], [ID], [TOKEN]."""
    if not text:
        return ""

    redacted = text
    for pattern in _TOKEN_PATTERNS:
        redacted = pattern.sub("[TOKEN]", redacted)

    for pattern in _ID_PATTERNS:
        redacted = pattern.sub("[ID]", redacted)

    for pattern in _PHONE_PATTERNS:
        redacted = pattern.sub("[PHONE]", redacted)

    return redacted
