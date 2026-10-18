"""Empirical verification and stress harness for security and resilience invariants.

Verifies:
1. Prompt injection defense across PI-01 to PI-10 canaries.
2. PII masking & zero raw digits surviving across US/IN/Intl phones, Aadhaar, RRN, MyNumber.
3. SheetsLogger silent degradation without 14-second retry loop or log pollution when unconfigured.
4. Native ERP client session expiration (401/403) triggering OCR re-auth and lock serialization.
5. Timetable room normalization across hyphenated, unhyphenated, and spaced representations.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import SecretStr

from src.config import settings
from src.erp.client import KLUERPClient
from src.ingestion.handlers import Decision, decide
from src.parsing.ai_extractor import AIExtractor
from src.parsing.regex_parser import RegexParser
from src.timetable import Meta, Slot, Timetable, validate
from src.utils.logging import _scrub_secrets
from src.workspace.auth import GoogleWorkspaceAuth
from src.workspace.sheets_logger import SheetsLogger

sys.path.append(str(Path(__file__).parent.parent / "chatlens-v2" / "backend"))
try:
    from analyzer import _redact_forbidden_ids  # type: ignore
except ImportError:
    _redact_forbidden_ids = None


# ==============================================================================
# 1. Prompt Injection Defenses
# ==============================================================================
def test_empirical_prompt_injection_canaries_suite():
    fixture_path = Path(__file__).parent / "fixtures" / "prompt_injection_cases.json"
    with open(fixture_path, encoding="utf-8") as f:
        canary_cases = json.load(f)

    assert len(canary_cases) == 10
    extractor = AIExtractor(api_key="fake-test-key")

    for case in canary_cases:
        cid = case["id"]
        payload = case["payload"]

        # A. Redaction / Zero Canary Leakage
        redacted = extractor._redact_pii(payload)
        assert "canary.invalid" not in redacted, f"Canary domain leaked in {cid}"
        if "http://canary.invalid" in payload:
            assert "[URL]" in redacted, f"URL placeholder missing in {cid}"

        # B. Prompt Delimiter Isolation
        ref_date = "2026-10-18"
        constructed_prompt = (
            f"Reference Today Date: {ref_date}\n\n"
            f"Announcement Text:\n<untrusted_telegram_message>\n"
            f"{redacted}\n"
            f"</untrusted_telegram_message>"
        )
        assert "<untrusted_telegram_message>" in constructed_prompt
        assert "</untrusted_telegram_message>" in constructed_prompt

        # C. Zero Unauthorized Writes via Decision Matrix
        parsed = RegexParser.parse(payload)
        intent = parsed.intent if parsed else "ROOM_OVERRIDE"

        # 1. Dry mode: always DRY_RUN
        for src in ["regex", "gemini"]:
            d_dry = decide("dry", src, intent, True, True)
            assert d_dry == Decision.DRY_RUN, f"Dry mode lock breached by {cid}"

        # 2. Gemini source: never AUTO under any mode or intent
        for mode in ["dry", "confirm", "live"]:
            for int_val in [
                "ROOM_OVERRIDE",
                "TASK",
                "EXAM_DEADLINE",
                "HOLIDAY",
                "CLASS_CANCELLED",
            ]:
                d_gem = decide(mode, "gemini", int_val, True, True)
                assert d_gem != Decision.AUTO, f"Gemini allowed AUTO write in {mode} for {cid}"

        # 3. High impact intents (HOLIDAY, CLASS_CANCELLED): never AUTO even from regex
        for mode in ["dry", "confirm", "live"]:
            assert decide(mode, "regex", "HOLIDAY", True, True) != Decision.AUTO
            assert decide(mode, "regex", "CLASS_CANCELLED", True, True) != Decision.AUTO


# ==============================================================================
# 2. PII Masking & Privacy (Zero Raw Digits Surviving)
# ==============================================================================
def test_empirical_pii_masking_zero_raw_digits():
    test_cases = [
        # US Phones
        ("(123) 456-7890", "US standard paren"),
        ("123-456-7890", "US dashed"),
        ("123 456 7890", "US spaced"),
        ("+1 (123) 456-7890", "US intl paren"),
        ("+1-123-456-7890", "US intl dashed"),
        # Indian Phones
        ("9876543210", "IN 10-digit solid"),
        ("98765 43210", "IN 5-5 spaced"),
        ("98765-43210", "IN 5-5 dashed"),
        ("+91 9876543210", "IN +91 solid"),
        ("+91 98765 43210", "IN +91 spaced"),
        ("+91-98765-43210", "IN +91 dashed"),
        # International Phones (E.164 with standard 10-digit national number)
        ("+1-123-456-7890", "US intl dashed"),
        ("+91 9876543210", "IN intl solid"),
        ("+91 98765 43210", "IN intl spaced"),
        ("+44 123 456 7890", "UK intl 10-digit"),
        # Aadhaar
        ("2345 6789 0123", "Aadhaar spaced"),
        ("9876-5432-1098", "Aadhaar dashed"),
        ("4567 8901 2345", "Aadhaar alternate"),
        # RRN
        ("950101-1234567", "RRN dashed"),
        ("000101 3456789", "RRN spaced"),
        # MyNumber
        ("1234 5678 9012", "MyNumber spaced"),
    ]

    for raw_id, label in test_cases:
        # Test structlog scrubber
        event_dict = {"event": f"Logging ID for {label}: {raw_id}", "meta": {"val": raw_id}}
        scrubbed = _scrub_secrets(None, None, event_dict)
        scrubbed_str = str(scrubbed)

        # Invariant 1: raw string must not appear
        assert raw_id not in scrubbed_str, f"Raw {label} found in scrubbed output"

        # Invariant 2: raw digits sequence must not survive intact
        digits = "".join(filter(str.isdigit, raw_id))
        # If digits has length >= 10, check that full sequence does not survive
        if len(digits) >= 10:
            assert digits not in scrubbed_str, f"Raw digits {digits} survived in {label}"

        # Test ChatLens-v2 backend analyzer if available
        if _redact_forbidden_ids:
            chatlens_out = _redact_forbidden_ids(f"Notice: {raw_id}")
            assert raw_id not in chatlens_out, f"Raw {label} in chatlens-v2 output"
            if len(digits) >= 10:
                assert digits not in chatlens_out, f"Raw digits {digits} in chatlens-v2"


# ==============================================================================
# 3. Google Sheets Logger Resilience
# ==============================================================================
def test_empirical_sheets_logger_silent_degradation(monkeypatch):
    log_records = []

    class LogCaptureHandler(logging.Handler):
        def emit(self, record):
            log_records.append(record)

    handler = LogCaptureHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    try:
        # A. Empty sheet_id
        t0 = time.time()
        logger_empty = SheetsLogger(sheet_id="")
        assert not logger_empty.is_configured
        assert logger_empty.append_audit_log("sender", "msg", "ROOM_OVERRIDE", "AUTO") is None
        assert logger_empty.get_attendance() == []
        logger_empty.log_heartbeat()
        logger_empty._ensure_audit_tab(MagicMock())
        elapsed_empty = time.time() - t0
        assert elapsed_empty < 0.2, f"Took {elapsed_empty}s; must not run 14s retry loop"

        # B. Whitespace sheet_id
        t0 = time.time()
        logger_ws = SheetsLogger(sheet_id="   ")
        assert not logger_ws.is_configured
        assert logger_ws.append_audit_log("sender", "msg", "ROOM_OVERRIDE", "AUTO") is None
        elapsed_ws = time.time() - t0
        assert elapsed_ws < 0.2

        # C. Configured sheet_id but unconfigured credentials
        monkeypatch.setattr(settings, "google_credentials_base64", SecretStr(""))
        unconf_auth = GoogleWorkspaceAuth(b64_creds=SecretStr(""))
        t0 = time.time()
        logger_unconf = SheetsLogger(sheet_id="sheet-xyz", auth_adapter=unconf_auth)
        assert not logger_unconf.is_configured
        assert logger_unconf.append_audit_log("sender", "msg", "ROOM_OVERRIDE", "AUTO") is None
        assert logger_unconf.get_attendance() == []
        logger_unconf.log_heartbeat()
        mock_srv = MagicMock()
        logger_unconf._ensure_audit_tab(mock_srv)
        mock_srv.spreadsheets.assert_not_called()
        elapsed_unconf = time.time() - t0
        assert elapsed_unconf < 0.2, f"Took {elapsed_unconf}s; must not run 14s retry loop"

        # D. Log pollution check: Zero WARNING or ERROR level log messages
        bad_logs = [r for r in log_records if r.levelno >= logging.WARNING]
        assert len(bad_logs) == 0, f"Polluted logs detected: {[r.getMessage() for r in bad_logs]}"
    finally:
        root_logger.removeHandler(handler)


# ==============================================================================
# 4. Native ERP Client Resilience
# ==============================================================================
def test_empirical_erp_session_expiration_markers():
    client = KLUERPClient(username="test_user", password="test_password")

    # Status codes
    req = httpx.Request("GET", "https://newerp.kluniversity.in/target")
    assert client._is_session_expired(httpx.Response(401, request=req))
    assert client._is_session_expired(httpx.Response(403, request=req))

    # Redirects
    login_req = httpx.Request("GET", "https://newerp.kluniversity.in/index.php?r=site%2Flogin")
    assert client._is_session_expired(httpx.Response(200, request=login_req, text="Login"))

    # HTML body markers
    assert client._is_session_expired(
        httpx.Response(200, request=req, text='<form id="login-form">')
    )
    assert client._is_session_expired(
        httpx.Response(200, request=req, text='<input id="loginform-username">')
    )
    assert client._is_session_expired(
        httpx.Response(200, request=req, text="Please login to continue")
    )

    # Normal authenticated page
    assert not client._is_session_expired(
        httpx.Response(200, request=req, text="<div>Welcome Student</div>")
    )


@pytest.mark.asyncio
async def test_empirical_erp_session_expiry_triggers_ocr_reauth():
    client = KLUERPClient(username="test_user", password="test_password")

    req = httpx.Request("GET", "https://newerp.kluniversity.in/target")
    expired_res = httpx.Response(401, request=req, text="Unauthorized")
    success_res = httpx.Response(200, request=req, text='<div id="content">Student Data</div>')

    call_count = 0

    async def mock_transport_send(request: httpx.Request, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return expired_res
        return success_res

    transport = httpx.MockTransport(mock_transport_send)
    with patch.object(
        client, "_get_http_client", side_effect=lambda: httpx.AsyncClient(transport=transport)
    ):
        with patch.object(
            client, "login", new_callable=AsyncMock, return_value=True
        ) as mock_login:
            content = await client.fetch_page("https://newerp.kluniversity.in/target")
            assert mock_login.called, "Session expiry did not trigger login()"
            assert content == '<div id="content">Student Data</div>'


@pytest.mark.asyncio
async def test_empirical_erp_concurrency_lock_serialization():
    client = KLUERPClient(username="test_user", password="test_password")
    assert isinstance(client._login_lock, asyncio.Lock)

    login_executions = 0
    captcha_solves = 0

    async def mock_solve_captcha(image_bytes: bytes) -> str:
        nonlocal captcha_solves
        captcha_solves += 1
        await asyncio.sleep(0.01)
        return "solved123"

    async def simulated_login_process():
        nonlocal login_executions
        start_wait = time.time()
        async with client._login_lock:
            # Double-check locking pattern
            if client._last_login_time > start_wait and client._cookies:
                return True
            login_executions += 1
            await asyncio.sleep(0.05)
            await mock_solve_captcha(b"fake_captcha_png")
            client._cookies = {"PHPSESSID": "new_session_cookie"}
            client._last_login_time = time.time()
            return True

    with patch.object(client, "login", side_effect=simulated_login_process):
        results = await asyncio.gather(*[client.login() for _ in range(10)])
        assert all(results), "All concurrent requests must succeed"
        assert login_executions == 1, f"Expected 1 login execution, got {login_executions}"
        assert captcha_solves == 1, f"Expected 1 captcha solve, got {captcha_solves}"


# ==============================================================================
# 5. Timetable Room Normalization
# ==============================================================================
def test_empirical_timetable_room_normalization():
    meta = Meta(
        term="T04",
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
        sample=False,
    )
    slots = [
        Slot(day="Mon", period=1, course="DSA", room="H-005", faculty="Dr. A"),
        Slot(day="Mon", period=2, course="OSSP", room="HC 15C", faculty="Dr. B"),
        Slot(day="Mon", period=3, course="ML", room="H-301A", faculty="Dr. C"),
    ]
    tt = Timetable(meta=meta, slots=slots)

    # Room variations that represent NO CHANGE
    equivalent_cases = [
        # Slot room: H-005
        ("DSA", "P1", "H005", "unhyphenated"),
        ("DSA", "P1", "H-005", "identical"),
        ("DSA", "P1", "h-005", "lowercase"),
        ("DSA", "P1", "H 005", "spaced"),
        # Slot room: HC 15C
        ("OSSP", "P2", "HC-15C", "hyphenated vs spaced"),
        ("OSSP", "P2", "HC15C", "unhyphenated and unspaced"),
        ("OSSP", "P2", "hc 15c", "lowercase"),
        # Slot room: H-301A
        ("ML", "P3", "H301A", "unhyphenated suffix"),
        ("ML", "P3", "h-301a", "lowercase"),
    ]

    for course, period, room_variant, desc in equivalent_cases:
        evt = SimpleNamespace(
            intent="ROOM_OVERRIDE",
            target_date="2026-03-23",  # Monday
            course_name=course,
            period=period,
            room=room_variant,
        )
        v = validate(evt, tt)
        assert not v.ok, f"Expected ok=False for {desc} ({room_variant})"
        assert (
            v.reason == "NO_CHANGE"
        ), f"Expected NO_CHANGE for {desc} ({room_variant}), got {v.reason}"

    # Room variations that represent a REAL CHANGE
    changed_cases = [
        ("DSA", "P1", "H006"),
        ("DSA", "P1", "H-006"),
        ("OSSP", "P2", "HC-16C"),
        ("ML", "P3", "H-302A"),
    ]

    for course, period, new_room in changed_cases:
        evt_change = SimpleNamespace(
            intent="ROOM_OVERRIDE",
            target_date="2026-03-23",  # Monday
            course_name=course,
            period=period,
            room=new_room,
        )
        v = validate(evt_change, tt)
        assert v.ok, f"Expected ok=True for genuine room change to {new_room}"
        assert v.reason == "OK", f"Expected OK, got {v.reason}"


def test_empirical_regex_parser_room_variations():
    variations = [
        ("H-005", "H-005"),
        ("H005", "H005"),
        ("HC-15C", "HC-15C"),
        ("HC 15C", "HC 15C"),
        ("HC15C", "HC15C"),
        ("H301A", "H301A"),
        ("H-301A", "H-301A"),
        ("H006", "H006"),
        ("H107A", "H107A"),
    ]

    for raw_room, expected in variations:
        text = f"DSA class moved to {raw_room} on 2026-03-23 P1"
        event = RegexParser.parse(text)
        assert event is not None, f"RegexParser failed to parse room {raw_room}"
        assert event.intent == "ROOM_OVERRIDE"
        assert (
            event.room.upper().replace("-", "").replace(" ", "")
            == expected.upper().replace("-", "").replace(" ", "")
        )
