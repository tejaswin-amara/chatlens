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


def test_bot_markdown_400_fallback(mock_bot, mock_request):
    import urllib.error

    success_resp = MagicMock()
    success_resp.read.return_value = b'{"ok": true}'
    mock_request.side_effect = [
        urllib.error.HTTPError(
            url="",
            code=400,
            msg="Bad Request: can't parse entities",
            hdrs={},
            fp=MagicMock(read=lambda: b'{"description": "Bad Request: can\'t parse entities"}'),
        ),
        MagicMock(
            __enter__=lambda s: success_resp,
            __exit__=lambda s, a, b, c: None,
        ),
    ]

    res = mock_bot.send("Hello *bold*")
    assert res == {"ok": True}
    assert mock_request.call_count == 2


def test_bot_delete_webhook(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true, "result": true}'
    mock_request.return_value.__enter__.return_value = mock_resp

    res = mock_bot.delete_webhook()
    assert res == {"ok": True, "result": True}


def test_bot_send_custom_chat_id(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true}'
    mock_request.return_value.__enter__.return_value = mock_resp

    with patch("json.dumps") as mock_dumps:
        mock_dumps.return_value = "{}"
        mock_bot.send("Hello", chat_id=999888)
        call_args = mock_dumps.call_args[0][0]
        assert call_args["chat_id"] == 999888


def _extract_payload(mock_request):
    import json

    call = mock_request.call_args
    kwargs = call.kwargs if hasattr(call, "kwargs") else call[1]
    args = call.args if hasattr(call, "args") else call[0]
    if "data" in kwargs and kwargs["data"] is not None:
        return json.loads(kwargs["data"].decode("utf-8"))
    if len(args) > 1 and args[1] is not None:
        return json.loads(args[1].decode("utf-8"))
    if getattr(args[0], "data", None) is not None:
        return json.loads(args[0].data.decode("utf-8"))
    return {}


def test_bot_set_my_commands(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true, "result": true}'
    mock_request.return_value.__enter__.return_value = mock_resp

    res = mock_bot.set_my_commands()
    assert res == {"ok": True, "result": True}

    req = mock_request.call_args[0][0]
    assert req.full_url.endswith("/setMyCommands")
    payload = _extract_payload(mock_request)
    assert "commands" in payload
    commands = payload["commands"]
    assert len(commands) == 10
    expected_commands = [
        {"command": "today", "description": "Today's classes, rooms & status"},
        {"command": "attendance", "description": "Live attendance & safe bunks"},
        {"command": "deadlines", "description": "Upcoming deadlines & milestones"},
        {"command": "status", "description": "Live daemon & chat monitoring status"},
        {"command": "marks", "description": "In-sem assessment marks"},
        {"command": "cgpa", "description": "Official academic grades & CGPA"},
        {"command": "fee", "description": "Fee orders & payment receipts"},
        {"command": "rescan", "description": "Rescan course group chats"},
        {"command": "undo", "description": "Undo last applied calendar change"},
        {"command": "help", "description": "Show all available options"},
    ]
    assert commands == expected_commands


def test_bot_send_default_quick_buttons(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true}'
    mock_request.return_value.__enter__.return_value = mock_resp

    res = mock_bot.send("Hello")
    assert res == {"ok": True}

    payload = _extract_payload(mock_request)
    assert "reply_markup" in payload
    assert "inline_keyboard" in payload["reply_markup"]
    kb = payload["reply_markup"]["inline_keyboard"]
    assert len(kb) == 2
    assert kb == [
        [
            {"text": "📅 Today", "callback_data": "cmd:today"},
            {"text": "📊 Attendance", "callback_data": "cmd:attendance"},
        ],
        [
            {"text": "⏰ Deadlines", "callback_data": "cmd:deadlines"},
            {"text": "🟢 Status", "callback_data": "cmd:status"},
        ],
    ]


def test_bot_send_empty_buttons_suppresses_quick_actions(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true}'
    mock_request.return_value.__enter__.return_value = mock_resp

    res = mock_bot.send("Hello without buttons", buttons=[])
    assert res == {"ok": True}

    payload = _extract_payload(mock_request)
    assert "reply_markup" not in payload


def test_bot_send_custom_buttons(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true}'
    mock_request.return_value.__enter__.return_value = mock_resp

    custom_btns = [
        [
            {"text": "✅ Yes", "callback_data": "ok:1"},
            {"text": "❌ No", "callback_data": "no:1"},
        ]
    ]
    res = mock_bot.send("Confirm action", buttons=custom_btns)
    assert res == {"ok": True}

    payload = _extract_payload(mock_request)
    assert "reply_markup" in payload
    assert payload["reply_markup"]["inline_keyboard"] == custom_btns


def test_bot_answer_callback(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true, "result": true}'
    mock_request.return_value.__enter__.return_value = mock_resp

    res = mock_bot.answer_callback("cb_9876", text="Acknowledged")
    assert res == {"ok": True, "result": True}

    req = mock_request.call_args[0][0]
    assert req.full_url.endswith("/answerCallbackQuery")
    payload = _extract_payload(mock_request)
    assert payload == {"callback_query_id": "cb_9876", "text": "Acknowledged"}

