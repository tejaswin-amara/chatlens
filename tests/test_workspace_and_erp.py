"""Tests for workspace sheets logger guards and ERP client session recovery."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.erp.client import KLUERPClient
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
