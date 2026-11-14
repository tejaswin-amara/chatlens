from unittest.mock import MagicMock, patch

import pytest

from src.notify.bot import DEFAULT_BOT_COMMANDS, BotClient, BotError


@pytest.fixture
def mock_bot(monkeypatch):
    # send() needs a configured destination even in credential-free CI tests.
    import contextlib
    import time

    from src.notify.bot import rate_limiter, settings
    from src.utils.deduplication import deduplicator

    monkeypatch.setattr(settings, "owner_chat_id", 123456789)
    with contextlib.suppress(Exception):
        deduplicator.meta_set("consent:999888", "1")
    rate_limiter._chat_buckets.clear()
    rate_limiter.global_bucket.tokens = rate_limiter.global_bucket.capacity
    rate_limiter.global_bucket.last_update = time.time()
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


def _extract_payload(target):
    import json

    call = target if isinstance(target, tuple) else getattr(target, "call_args", None)
    if call is None:
        return {}
    kwargs = getattr(call, "kwargs", call[1] if len(call) > 1 else {})
    args = getattr(call, "args", call[0] if len(call) > 0 else ())
    if "data" in kwargs and kwargs["data"] is not None:
        return json.loads(kwargs["data"].decode("utf-8"))
    if len(args) > 1 and args[1] is not None:
        return json.loads(args[1].decode("utf-8"))
    if len(args) > 0 and getattr(args[0], "data", None) is not None:
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
    assert len(commands) == len(DEFAULT_BOT_COMMANDS)
    assert commands == DEFAULT_BOT_COMMANDS


def test_bot_set_my_commands_with_scope(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true, "result": true}'
    mock_request.return_value.__enter__.return_value = mock_resp

    scope = {"type": "all_private_chats"}
    res = mock_bot.set_my_commands(scope=scope)
    assert res == {"ok": True, "result": True}

    payload = _extract_payload(mock_request)
    assert payload.get("scope") == scope
    assert len(payload.get("commands", [])) == len(DEFAULT_BOT_COMMANDS)


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


def test_bot_chunk_text_splits_long_message(mock_bot):
    chunk1 = "First chunk content: " + ("A" * 3950)
    chunk2 = "Second chunk content: " + ("B" * 500)
    long_text = chunk1 + "\n\n" + chunk2
    chunks = mock_bot._chunk_text(long_text, max_chunk_size=4000)
    assert len(chunks) == 2
    for c in chunks:
        assert len(c) <= 4000
    assert "First chunk content" in chunks[0]
    assert "Second chunk content" in chunks[1]


def test_bot_send_chunks_message_exceeding_limit(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true, "result": {"message_id": 999}}'
    mock_request.return_value.__enter__.return_value = mock_resp

    long_text = ("First long section\n\n" + ("X" * 3500)) + (
        "\n\nSecond long section\n\n" + ("Y" * 2000)
    )
    res = mock_bot.send(long_text)
    assert res["ok"] is True
    # Should have sent 2 requests
    assert mock_request.call_count == 2


def test_bot_edit_truncates_long_message(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true, "result": {"message_id": 123}}'
    mock_request.return_value.__enter__.return_value = mock_resp

    long_text = "Z" * 5000
    mock_bot.edit(123, long_text)
    payload = _extract_payload(mock_request)
    assert len(payload["text"]) <= 4000
    assert payload["text"].endswith("...")


def test_bot_send_massive_underscores_markdown_chunking(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true, "result": {"message_id": 1}}'
    mock_request.return_value.__enter__.return_value = mock_resp

    text = "a_b " * 950  # Raw length 3800; expands to 4750 when sanitized
    res = mock_bot.send(text, parse_mode="Markdown")
    assert res["ok"] is True
    assert mock_request.call_count >= 2

    for call in mock_request.call_args_list:
        payload = _extract_payload(call)
        assert len(payload["text"]) <= 4000
        assert payload.get("parse_mode") == "Markdown"


def test_bot_edit_massive_underscores_markdown_truncation(mock_bot, mock_request):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"ok": true, "result": {"message_id": 123}}'
    mock_request.return_value.__enter__.return_value = mock_resp

    text = "hello_" * 700  # Raw length 4200; expands to 4900 when sanitized
    res = mock_bot.edit(123, text, parse_mode="Markdown")
    assert res["ok"] is True

    payload = _extract_payload(mock_request)
    assert len(payload["text"]) <= 4000
    assert payload["text"].endswith("...")
    assert payload.get("parse_mode") == "Markdown"


def test_bot_send_markdown_massive_underscores_avoids_telegram_400(mock_bot):
    def mock_req(endpoint, data, timeout=30):
        if len(data.get("text", "")) > 4096:
            raise BotError("Telegram Bot HTTPError 400: Bad Request: message is too long")
        return {"ok": True, "result": {"message_id": 1}}

    mock_bot._request = mock_req
    text = "@bot " + ("a_b " * 950)
    res = mock_bot.send(text, chat_id=123456789, parse_mode="Markdown")
    assert res["ok"] is True
