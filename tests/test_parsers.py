"""Self-check tests for ChatLens parsers. Run: python -m tests.test_parsers"""

import json
import os
import tempfile

# --- Telegram parser tests ---

def test_telegram_single_chat():
    """Telegram single-chat JSON export with mixed text formats."""
    from chatlens.parsers.telegram import parse_telegram_export

    data = {
        "name": "Test Chat",
        "type": "personal_chat",
        "id": 12345,
        "messages": [
            {
                "id": 1,
                "type": "message",
                "date": "2024-01-15T10:30:00",
                "from": "Alice",
                "from_id": "user123",
                "text": "Hello there!"
            },
            {
                "id": 2,
                "type": "message",
                "date": "2024-01-15T10:31:00",
                "from": "Bob",
                "from_id": "user456",
                "text": [
                    {"type": "plain", "text": "Check this "},
                    {"type": "link", "text": "https://example.com"},
                    {"type": "plain", "text": " out"}
                ]
            },
            {
                "id": 3,
                "type": "service",
                "date": "2024-01-15T10:32:00",
                "text": "Alice joined"
            },
            {
                "id": 4,
                "type": "message",
                "date": "2024-01-15T10:33:00",
                "from": "Alice",
                "from_id": "user123",
                "text": "",
                "photo": "photos/photo1.jpg"
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(data, f)
        path = f.name

    try:
        msgs = parse_telegram_export(path)
        assert len(msgs) == 2, f"Expected 2 messages (skip service + empty), got {len(msgs)}"
        assert msgs[0]['sender'] == 'Alice'
        assert msgs[0]['text'] == 'Hello there!'
        assert msgs[0]['platform'] == 'telegram'
        assert msgs[1]['text'] == 'Check this https://example.com out'
        assert msgs[1]['sender'] == 'Bob'
        print("✓ test_telegram_single_chat passed")
    finally:
        os.unlink(path)


def test_telegram_full_export():
    """Telegram full-account export with chats.list structure."""
    from chatlens.parsers.telegram import parse_telegram_export

    data = {
        "chats": {
            "list": [
                {
                    "name": "Group A",
                    "type": "public_group",
                    "id": 1,
                    "messages": [
                        {"id": 1, "type": "message", "date": "2024-02-01T09:00:00", "from": "Carol", "from_id": "u1", "text": "Morning!"}
                    ]
                },
                {
                    "name": "Group B",
                    "type": "private_group",
                    "id": 2,
                    "messages": [
                        {"id": 1, "type": "message", "date": "2024-02-01T10:00:00", "from": "Dave", "from_id": "u2", "text": "Hey"}
                    ]
                }
            ]
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(data, f)
        path = f.name

    try:
        msgs = parse_telegram_export(path)
        assert len(msgs) == 2, f"Expected 2 messages across 2 chats, got {len(msgs)}"
        assert msgs[0]['chat_name'] == 'Group A'
        assert msgs[1]['chat_name'] == 'Group B'
        print("✓ test_telegram_full_export passed")
    finally:
        os.unlink(path)


# --- WhatsApp parser tests ---

def test_whatsapp_basic():
    """WhatsApp .txt export with standard DD/MM/YY format."""
    from chatlens.parsers.whatsapp import parse_whatsapp_export

    content = """15/01/24, 10:30 - Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them. Tap to learn more.
15/01/24, 10:30 - Alice: Hello!
15/01/24, 10:31 - Bob: Hi there, how are you?
This is a continuation of Bob's message
on multiple lines.
15/01/24, 10:32 - Alice: <Media omitted>
15/01/24, 10:33 - Alice: I'm good thanks!
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        path = f.name

    try:
        msgs = parse_whatsapp_export(path)
        # Should get 3 messages: Alice Hello, Bob multi-line, Alice good thanks
        # Skip system message and media omitted
        assert len(msgs) == 3, f"Expected 3 messages, got {len(msgs)}: {[m['text'] for m in msgs]}"
        assert msgs[0]['sender'] == 'Alice'
        assert msgs[0]['text'] == 'Hello!'
        assert 'continuation' in msgs[1]['text']
        assert 'multiple lines' in msgs[1]['text']
        assert msgs[1]['sender'] == 'Bob'
        assert msgs[2]['text'] == "I'm good thanks!"
        assert msgs[0]['platform'] == 'whatsapp'
        print("✓ test_whatsapp_basic passed")
    finally:
        os.unlink(path)


def test_whatsapp_us_format():
    """WhatsApp .txt export with US date format (MM/DD/YY) and 12h time."""
    from chatlens.parsers.whatsapp import parse_whatsapp_export

    content = """1/15/24, 10:30 AM - Alice: Hello!
1/15/24, 10:31 AM - Bob: Hey!
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        path = f.name

    try:
        msgs = parse_whatsapp_export(path)
        assert len(msgs) == 2, f"Expected 2 messages, got {len(msgs)}"
        print("✓ test_whatsapp_us_format passed")
    finally:
        os.unlink(path)


# --- Run all ---

if __name__ == '__main__':
    test_telegram_single_chat()
    test_telegram_full_export()
    test_whatsapp_basic()
    test_whatsapp_us_format()
    print("\nAll parser tests passed ✓")
