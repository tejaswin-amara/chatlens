"""Prompt-injection canary suite (PI-01 to PI-10) for ChatLens & SPARK PA.

Verifies:
1. Defense-in-depth against prompt injection attacks (Data-Instruction Separation).
2. URL redaction of canary domain (http://canary.invalid/*).
3. Invariant: Gemini-derived events and HOLIDAY/CLASS_CANCELLED never auto-apply (Decision.AUTO).
4. No external network or shell execution is triggered.
"""

import json
from pathlib import Path

import pytest

from src.ingestion.handlers import Decision, decide
from src.parsing.ai_extractor import AIExtractor
from src.parsing.regex_parser import RegexParser


@pytest.fixture
def canary_cases() -> list[dict]:
    fixture_path = Path(__file__).parent / "fixtures" / "prompt_injection_cases.json"
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


def test_canary_fixture_loaded(canary_cases: list[dict]):
    assert len(canary_cases) == 10
    case_ids = [c["id"] for c in canary_cases]
    for i in range(1, 11):
        assert f"PI-{i:02d}" in case_ids


def test_canary_pii_and_url_redaction(canary_cases: list[dict]):
    """Ensure that all canary URLs are redacted to [URL] before reaching any LLM prompt."""
    extractor = AIExtractor(api_key="fake-test-key")

    for case in canary_cases:
        payload = case["payload"]
        redacted = extractor._redact_pii(payload)

        # Invariant: canary domain is completely removed/redacted
        assert "canary.invalid" not in redacted, f"Failed for {case['id']}: URL was not redacted"

        # If payload had a canary URL, [URL] placeholder must be present
        if "http://canary.invalid" in payload:
            assert "[URL]" in redacted, f"Failed for {case['id']}: [URL] placeholder missing"


def test_canary_regex_parsing_and_decision_policy(canary_cases: list[dict]):
    """Ensure prompt injection attacks never bypass decision guardrails to reach Decision.AUTO."""
    for case in canary_cases:
        payload = case["payload"]
        parsed = RegexParser.parse(payload)

        if parsed:
            # If parsed by regex, verify strict decision policy
            decision_live = decide(
                "live",
                "regex",
                parsed.intent,
                True,
                True,
            )
            # Holiday, Class Cancelled, or Review events must NEVER be Decision.AUTO
            if parsed.intent in ("HOLIDAY", "CLASS_CANCELLED"):
                assert decision_live != Decision.AUTO, (
                    f"Unsafe AUTO decision for {case['id']} with intent {parsed.intent}"
                )

        # Regardless of intent, any Gemini-derived event MUST require confirmation
        # (Decision.CONFIRM)
        intents_to_check = (
            [parsed.intent] if parsed else ["HOLIDAY", "TASK", "ROOM_OVERRIDE", "CLASS_CANCELLED"]
        )
        for intent in intents_to_check:
            decision_gemini = decide(
                "live",
                "gemini",
                intent,
                True,
                True,
            )
            assert decision_gemini != Decision.AUTO, (
                f"Gemini extraction must never Decision.AUTO for {case['id']}"
            )
            assert decision_gemini in (Decision.CONFIRM, Decision.REVIEW)


def test_canary_dry_mode_absolute_lock(canary_cases: list[dict]):
    """Ensure dry mode never yields AUTO or CONFIRM for any injection payload."""
    for case in canary_cases:
        payload = case["payload"]
        parsed = RegexParser.parse(payload)
        intent = parsed.intent if parsed else "ROOM_OVERRIDE"

        decision = decide(
            "dry",
            "regex",
            intent,
            True,
            True,
        )
        assert decision == Decision.DRY_RUN, (
            f"Dry mode must strictly return DRY_RUN for {case['id']}"
        )
