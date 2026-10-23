import asyncio
import time
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.config import settings
from src.erp.client import KLUERPClient
from src.timetable import Meta, Slot, Timetable, validate
from src.workspace.auth import GoogleWorkspaceAuth
from src.workspace.sheets_logger import SheetsLogger


def test_sheets_logger_heartbeat_empty_sheet_id():
    """Verify log_heartbeat immediately returns when sheet_id is empty, avoiding HTTP 400."""
    logger = SheetsLogger(sheet_id="")
    with patch.object(logger.auth, "get_sheets_service") as mock_service:
        logger.log_heartbeat()
        mock_service.assert_not_called()


def test_sheets_logger_heartbeat_whitespace_sheet_id():
    """Verify log_heartbeat strips whitespace and returns early without making requests."""
    logger = SheetsLogger(sheet_id="   ")
    with patch.object(logger.auth, "get_sheets_service") as mock_service:
        logger.log_heartbeat()
        mock_service.assert_not_called()


def test_sheets_logger_heartbeat_configured_sheet_id():
    """Verify log_heartbeat updates Status!A1 when sheet_id is present."""
    logger = SheetsLogger(sheet_id="test_sheet_123")
    mock_service = MagicMock()
    mock_values = MagicMock()
    mock_service.spreadsheets.return_value.values.return_value = mock_values
    mock_values.update.return_value.execute.return_value = {"updatedCells": 1}

    with patch.object(logger.auth, "get_sheets_service", return_value=mock_service):
        logger.log_heartbeat()
        mock_values.update.assert_called_once()
        args, kwargs = mock_values.update.call_args
        assert kwargs["spreadsheetId"] == "test_sheet_123"
        assert kwargs["range"] == "Status!A1"


def test_sheets_logger_init_preserves_empty_string(monkeypatch):
    """Verify explicit sheet_id='' is preserved even when settings.google_sheet_id is set."""
    monkeypatch.setattr(settings, "google_sheet_id", "configured_fallback_id")
    logger_empty = SheetsLogger(sheet_id="")
    assert logger_empty.sheet_id == ""
    assert not logger_empty.is_configured

    logger_none = SheetsLogger(sheet_id=None)
    assert logger_none.sheet_id == "configured_fallback_id"


def test_sheets_logger_unconfigured_guard_and_skips(monkeypatch):
    """Verify is_configured is False and methods skip cleanly when creds/sheet_id are missing."""
    mock_auth = MagicMock()
    mock_auth.b64_creds = None
    mock_auth.get_sheets_service.side_effect = ValueError("Unconfigured creds")

    # Empty or whitespace sheet_id
    logger_empty = SheetsLogger(sheet_id="", auth_adapter=mock_auth)
    assert not logger_empty.is_configured
    assert logger_empty.append_audit_log("sender", "msg", "INTENT", "SUCCESS") is None
    assert logger_empty.get_attendance() == []
    logger_empty.log_heartbeat()
    logger_empty._ensure_audit_tab(MagicMock())
    mock_auth.get_sheets_service.assert_not_called()

    # Unconfigured credentials with real auth adapter (where b64_creds is empty)
    from pydantic import SecretStr

    monkeypatch.setattr(settings, "google_credentials_base64", SecretStr(""))
    unconfigured_auth = GoogleWorkspaceAuth(b64_creds=SecretStr(""))
    logger_unconfigured = SheetsLogger(sheet_id="sheet123", auth_adapter=unconfigured_auth)
    assert not logger_unconfigured.is_configured
    assert logger_unconfigured.append_audit_log("sender", "msg", "INTENT", "SUCCESS") is None
    assert logger_unconfigured.get_attendance() == []
    logger_unconfigured.log_heartbeat()
    mock_service = MagicMock()
    logger_unconfigured._ensure_audit_tab(mock_service)
    mock_service.spreadsheets.assert_not_called()


def test_erp_client_is_session_expired():
    """Verify session expiration markers are correctly identified."""
    client = KLUERPClient(username="test_user", password="test_password")

    req = httpx.Request("GET", "https://newerp.kluniversity.in/dashboard")
    res_normal = httpx.Response(200, request=req, text="<div>Welcome Student</div>")
    assert not client._is_session_expired(res_normal)

    login_req = httpx.Request("GET", "https://newerp.kluniversity.in/index.php?r=site%2Flogin")
    res_login_redirect = httpx.Response(
        200,
        request=login_req,
        text="<div>Login</div>",
    )
    assert client._is_session_expired(res_login_redirect)

    res_form_marker = httpx.Response(
        200,
        request=req,
        text='<form id="login-form" action="/site/login"><input id="loginform-username"/></form>',
    )
    assert client._is_session_expired(res_form_marker)

    res_please_login = httpx.Response(
        200,
        request=req,
        text="""<div>Please login to continue to student portal</div>""",
    )
    assert client._is_session_expired(res_please_login)


def test_erp_client_status_codes_session_expired():
    """Verify HTTP 401 and 403 status codes are recognized as session expired."""
    client = KLUERPClient(username="test_user", password="test_password")
    req = httpx.Request("POST", "https://newerp.kluniversity.in/target")

    res_401 = httpx.Response(401, request=req, text="Unauthorized")
    assert client._is_session_expired(res_401)

    res_403 = httpx.Response(403, request=req, text="Forbidden")
    assert client._is_session_expired(res_403)


@pytest.mark.asyncio
async def test_erp_client_fetch_page_session_recovery():
    """Verify fetch_page recovers transparently when session expires."""
    client = KLUERPClient(username="test_user", password="test_password")

    req = httpx.Request("GET", "https://newerp.kluniversity.in/target")
    expired_res = httpx.Response(
        200,
        request=req,
        text='<form id="login-form"><input id="loginform-username"/></form>',
    )
    success_res = httpx.Response(
        200,
        request=req,
        text='<div id="target-content">Verified Content</div>',
    )

    call_count = 0

    async def mock_send(request: httpx.Request, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return expired_res
        return success_res

    transport = httpx.MockTransport(mock_send)

    with patch.object(
        client, "_get_http_client", side_effect=lambda: httpx.AsyncClient(transport=transport)
    ):
        with patch.object(client, "login", new_callable=AsyncMock, return_value=True) as mock_login:
            content = await client.fetch_page("https://newerp.kluniversity.in/target")
            assert mock_login.called
            assert content == '<div id="target-content">Verified Content</div>'


@pytest.mark.asyncio
async def test_erp_client_get_marks_session_recovery():
    """Verify get_marks transparently recovers when POST returns expired session."""
    client = KLUERPClient(username="test_user", password="test_password")

    marks_html = """
    <html><body>
    <table>
      <tr>
        <th>Course Code</th><th>Course Name</th><th>Component</th>
        <th>Max Marks</th><th>Secured Marks</th>
      </tr>
      <tr>
        <td>25CS2103E</td><td>DSA-3</td><td>InSem1</td><td>50</td><td>42</td>
      </tr>
    </table>
    </body></html>
    """
    expired_res = httpx.Response(
        401,
        request=httpx.Request("POST", "https://newerp.kluniversity.in/marks"),
        text="Unauthorized",
    )
    success_res = httpx.Response(
        200,
        request=httpx.Request("POST", "https://newerp.kluniversity.in/marks"),
        text=marks_html,
    )

    call_count = 0

    async def mock_send(request: httpx.Request, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return expired_res
        return success_res

    transport = httpx.MockTransport(mock_send)

    with patch.object(
        client, "_get_http_client", side_effect=lambda: httpx.AsyncClient(transport=transport)
    ):
        with patch.object(
            client,
            "fetch_page",
            new_callable=AsyncMock,
            return_value='<form name="_csrf" value="tok123"></form>',
        ):
            with patch.object(
                client, "login", new_callable=AsyncMock, return_value=True
            ) as mock_login:
                records = await client.get_marks("29", "1")
                assert mock_login.called
                assert len(records) >= 1
                assert records[0]["course_code"] == "25CS2103E"
                assert records[0]["secured_marks"] == 42.0


@pytest.mark.asyncio
async def test_erp_client_marks_cache_offline_fallback(tmp_path, monkeypatch):
    """Verify get_marks falls back to SQLite table erp_marks_cache when request fails."""
    db_file = str(tmp_path / "test_spark.db")
    monkeypatch.setattr(settings, "spark_db", db_file)

    client = KLUERPClient(username="test_user", password="test_password")

    sample_records = [
        {
            "course_code": "25CS2103E",
            "course_name": "DSA-3",
            "component": "InSem1",
            "max_marks": 50,
            "secured_marks": 45.0,
            "percentage": 90.0,
        }
    ]
    # Save to SQLite table erp_marks_cache
    client._save_marks_cache("29", "1", sample_records)

    # Simulate network failure in fetch_page
    with patch.object(client, "fetch_page", side_effect=httpx.ConnectError("Network offline")):
        cached = await client.get_marks("29", "1")
        assert len(cached) == 1
        assert cached[0]["course_code"] == "25CS2103E"
        assert cached[0]["secured_marks"] == 45.0


@pytest.mark.asyncio
async def test_erp_client_login_lock_serialization():
    """Verify _login_lock serializes concurrent logins and skips redundant login."""
    client = KLUERPClient(username="test_user", password="test_password")
    assert isinstance(client._login_lock, asyncio.Lock)

    login_call_count = 0

    async def fake_login_internal():
        nonlocal login_call_count
        login_call_count += 1
        await asyncio.sleep(0.05)
        client._cookies = {"PHPSESSID": "fresh_session"}
        client._last_login_time = time.time()
        return True

    async def concurrent_login():
        start_wait = time.time()
        async with client._login_lock:
            if client._last_login_time > start_wait and client._cookies:
                return True
            return await fake_login_internal()

    results = await asyncio.gather(concurrent_login(), concurrent_login())
    assert all(results)
    assert login_call_count == 1


def test_timetable_room_normalization():
    """Verify validate() normalizes room strings with hyphens and spaces."""
    meta = Meta(
        term="T04",
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
        sample=False,
    )
    slots = [
        Slot(day="Mon", period=1, course="DSA", room="H-005", faculty="Dr. X"),
        Slot(day="Mon", period=2, course="OSSP", room="HC 15C", faculty="Dr. Y"),
    ]
    tt = Timetable(meta=meta, slots=slots)

    class DummyEvent:
        intent = "ROOM_OVERRIDE"
        target_date = "2026-03-23"  # Monday
        course_name = "DSA"
        period = "P1"
        room = "H005"

    verdict = validate(DummyEvent(), tt)
    assert not verdict.ok
    assert verdict.reason == "NO_CHANGE"

    class DummyEvent2:
        intent = "ROOM_OVERRIDE"
        target_date = "2026-03-23"  # Monday
        course_name = "OSSP"
        period = "P2"
        room = "HC-15C"

    verdict2 = validate(DummyEvent2(), tt)
    assert not verdict2.ok
    assert verdict2.reason == "NO_CHANGE"

    class DummyEvent3:
        intent = "ROOM_OVERRIDE"
        target_date = "2026-03-23"  # Monday
        course_name = "DSA"
        period = "P1"
        room = "H006"

    verdict3 = validate(DummyEvent3(), tt)
    assert verdict3.ok
    assert verdict3.reason == "OK"
