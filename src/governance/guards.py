"""Untrusted input guardrails enforcing Dual-Trust Boundary and anti-prompt injection.

Adopts Microsoft Agent Governance principles using Python standard library.
Treats all group chat messages, captions, and file content as UNTRUSTED_COMMUNITY.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass

# Deterministic Prompt Injection & Jailbreak Heuristics
INJECTION_PATTERNS = [
    re.compile(
        r"(?i)\b(?:ignore|disregard|forget|bypass)\s+(?:all\s+)?"
        r"(?:(?:previous|prior|above|system)\s+)*instructions?\b"
    ),
    re.compile(
        r"(?i)\b(?:system\s+override|admin\s+override|developer\s+mode|"
        r"dan\s+mode|jailbreak|root\s+access)\b"
    ),
    re.compile(
        r"(?i)\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+"
        r"(?:an?\s+)?(?:root|admin|unrestricted|god\s+mode|evil|malicious)\b"
    ),
    re.compile(
        r"(?i)\b(?:mark\s+(?:today|tomorrow)\s+as\s+holiday|declare\s+(?:an?\s+)?holiday|"
        r"cancel\s+all\s+classes|override\s+all\s+rooms)\b"
    ),
    re.compile(r"(?i)(?:<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\])"),
    re.compile(r"(?i)^\s*(?:system|assistant|admin)\s*:"),
    re.compile(r"(?i)\b(?:drop\s+table|delete\s+from|rm\s+-rf)\b"),
]

# Zero-Disclosure PII & Credential Scrubbing Patterns
PII_PATTERNS = [
    # Aadhaar / Indian National IDs (12 digits)
    (re.compile(r"\b[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}\b"), "[AADHAAR_REDACTED]"),
    # Student University Roll Numbers (e.g., 2520030286)
    (re.compile(r"\b2[0-9]{9}\b"), "[ROLL_NO_REDACTED]"),
    # Telegram Bot Tokens (e.g., 8691846900:AAFk...)
    (re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"), "[BOT_TOKEN_REDACTED]"),
    # Google API Keys (AIza... or AQ.Ab...)
    (re.compile(r"\bAIza[0-9A-Za-z-_]{35}\b"), "[API_KEY_REDACTED]"),
    (re.compile(r"\bAQ\.[A-Za-z0-9_-]{30,}\b"), "[API_KEY_REDACTED]"),
    # Phone numbers (E.164, 5+5 Indian format, 3-3-4 international, and 10-digit contiguous)
    (
        re.compile(
            r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?(?:\d{5}[-.\s]?\d{5}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\d{10})(?!\d)"
        ),
        "[PHONE_REDACTED]",
    ),
    # Email addresses
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[EMAIL_REDACTED]",
    ),
    # HTTP/HTTPS URLs
    (re.compile(r"https?://\S+"), "[URL_REDACTED]"),
]


@dataclass(frozen=True)
class UntrustedInput:
    """Immutable data boundary encapsulating untrusted input."""

    source_trust_tier: str  # "UNTRUSTED_COMMUNITY" or "TRUSTED_OWNER"
    channel_id: int | str
    sender_id: int | str | None
    content: str
    raw_content: str
    raw_fingerprint: str
    timestamp: float
    quarantined: bool = False
    quarantine_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "source_trust_tier": self.source_trust_tier,
            "channel_id": str(self.channel_id),
            "sender_id": str(self.sender_id or ""),
            "content": self.content,
            "raw_fingerprint": self.raw_fingerprint,
            "timestamp": self.timestamp,
            "quarantined": self.quarantined,
            "quarantine_reason": self.quarantine_reason,
        }


class InputGuard:
    """Anti-prompt injection and zero-disclosure PII sanitization engine."""

    @staticmethod
    def compute_fingerprint(text: str) -> str:
        """Compute SHA-256 fingerprint of the raw text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @classmethod
    def detect_injection(cls, text: str) -> tuple[bool, str | None]:
        """Detect prompt injection and adversarial manipulation attempts."""
        if not text:
            return False, None

        for pattern in INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                return True, f"Matched injection signature: '{match.group(0)[:40]}'"
        return False, None

    @classmethod
    def redact_pii(cls, text: str) -> str:
        """Scrub personal identifiable information and secrets with zero disclosure."""
        if not text:
            return ""

        sanitized = text
        for pattern, replacement in PII_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    @classmethod
    def sanitize_and_wrap(
        cls,
        channel_id: int | str,
        sender_id: int | str | None,
        text: str,
        timestamp: float | None = None,
        is_owner: bool = False,
    ) -> UntrustedInput:
        """Sanitize raw text, check injection guardrails, and seal in a trusted container."""
        ts = timestamp if timestamp is not None else time.time()
        raw_text = text or ""
        fingerprint = cls.compute_fingerprint(raw_text)

        # Owners bypass injection quarantine, but still get PII scrubbed for log safety
        trust_tier = "TRUSTED_OWNER" if is_owner else "UNTRUSTED_COMMUNITY"

        is_injected, reason = False, None
        if not is_owner:
            is_injected, reason = cls.detect_injection(raw_text)

        sanitized_content = cls.redact_pii(raw_text)

        return UntrustedInput(
            source_trust_tier=trust_tier,
            channel_id=channel_id,
            sender_id=sender_id,
            content=sanitized_content,
            raw_content=raw_text,
            raw_fingerprint=fingerprint,
            timestamp=ts,
            quarantined=is_injected,
            quarantine_reason=reason,
        )


input_guard = InputGuard()
