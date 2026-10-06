from unittest.mock import MagicMock, patch

import pytest

from src.notify.bot import BotClient, BotError


@pytest.fixture
def mock_bot():
    return BotClient(token="bot123:test_token")


@pytest.fixture
def mock_request():
    with patch("urllib.request.urlopen") as mock_open:
        yield mock_open


def test_bot_success(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true}'
    mock_request.return_value.__enter__.return_value = mock_resp

    res = mock_bot.send("Hello")
    assert res == {"ok": True}


def test_bot_429_retry_capped(mock_bot, mock_request):
    import urllib.error

    err_resp = MagicMock()
    err_resp.read.return_value = b'{"parameters": {"retry_after": 100}}'

    mock_request.side_effect = [
        urllib.error.HTTPError(url="", code=429, msg="Too Many Requests", hdrs={}, fp=err_resp),
        MagicMock(
            __enter__=lambda s: MagicMock(read=lambda: b'{"ok": true}'),
            __exit__=lambda s, a, b, c: None,
        ),
    ]

    with patch("time.sleep") as mock_sleep:
        res = mock_bot.send("Hello")
        assert res == {"ok": True}
        mock_sleep.assert_called_once_with(60)


def test_bot_400_no_retry(mock_bot, mock_request):
    import urllib.error

    mock_request.side_effect = urllib.error.HTTPError(
        url="", code=400, msg="Bad Request", hdrs={}, fp=MagicMock(read=lambda: b"{}")
    )

    with pytest.raises(BotError, match="Telegram Bot HTTPError 400"):
        mock_bot.send("Hello")


def test_bot_500_retry(mock_bot, mock_request):
    import urllib.error

    mock_request.side_effect = [
        urllib.error.HTTPError(
            url="", code=500, msg="Server Error", hdrs={}, fp=MagicMock(read=lambda: b"{}")
        ),
        urllib.error.HTTPError(
            url="", code=502, msg="Bad Gateway", hdrs={}, fp=MagicMock(read=lambda: b"{}")
        ),
        MagicMock(
            __enter__=lambda s: MagicMock(read=lambda: b'{"ok": true}'),
            __exit__=lambda s, a, b, c: None,
        ),
    ]

    with patch("time.sleep") as mock_sleep:
        res = mock_bot.send("Hello")
        assert res == {"ok": True}
        assert mock_sleep.call_count == 2


def test_bot_max_retries_fail(mock_bot, mock_request):
    import urllib.error

    mock_request.side_effect = [
        urllib.error.HTTPError(
            url="", code=500, msg="Server Error", hdrs={}, fp=MagicMock(read=lambda: b"{}")
        ),
        urllib.error.HTTPError(
            url="", code=500, msg="Server Error", hdrs={}, fp=MagicMock(read=lambda: b"{}")
        ),
        urllib.error.HTTPError(
            url="", code=500, msg="Server Error", hdrs={}, fp=MagicMock(read=lambda: b"{}")
        ),
    ]

    with patch("time.sleep"):
        with pytest.raises(BotError):
            mock_bot.send("Hello")


def test_bot_409_conflict(mock_bot, mock_request):
    import urllib.error

    mock_request.side_effect = urllib.error.HTTPError(
        url="", code=409, msg="Conflict", hdrs={}, fp=MagicMock(read=lambda: b"{}")
    )

    with patch("time.sleep"):
        res = mock_bot.get_updates(offset=0)
        assert res == {"ok": True, "result": []}


def test_bot_parse_mode_auto(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true}'
    mock_request.return_value.__enter__.return_value = mock_resp

    with patch("json.dumps") as mock_dumps:
        mock_dumps.return_value = "{}"
        mock_bot.send("Hello **bold**")
        call_args = mock_dumps.call_args[0][0]
        assert call_args["parse_mode"] == "Markdown"


def test_bot_token_redacted_on_error(mock_bot, mock_request):
    import urllib.error

    err_fp = MagicMock()
    err_fp.read.return_value = b'{"description": "Forbidden: bot token is invalid"}'
    mock_request.side_effect = urllib.error.HTTPError(
        url="", code=401, msg="Unauthorized", hdrs={}, fp=err_fp
    )

    with pytest.raises(BotError) as excinfo:
        mock_bot.send("Hello")

    assert "bot123:test_token" not in str(excinfo.value)
