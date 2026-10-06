from chatlens.storage import MessageStore


def test_v1_search(tmp_path):
    store = MessageStore(str(tmp_path / "test.db"))
    store.ingest(
        [
            {
                "platform": "test",
                "chat_name": "A",
                "sender": "me",
                "timestamp": "2026",
                "text": "budget meeting today",
            },
            {
                "platform": "test",
                "chat_name": "B",
                "sender": "me",
                "timestamp": "2026",
                "text": "C++ budget OR something",
            },
            {
                "platform": "test",
                "chat_name": "B",
                "sender": "me",
                "timestamp": "2026",
                "text": "what's the budget?",
            },
        ]
    )

    # These should no longer raise OperationalError
    res1 = store.search("what's the budget?")
    assert len(res1) > 0

    res2 = store.search("budget-meeting")
    assert len(res2) > 0

    res3 = store.search("C++ budget")
    assert len(res3) > 0

    res4 = store.search("AND OR NOT")
    assert isinstance(res4, list)

    res5 = store.search("budget meeting")
    assert len(res5) > 0

    # Test chat name filter
    res6 = store.search("budget", chat_name="B")
    assert len(res6) == 2
    assert all(r["chat_name"] == "B" for r in res6)

    res7 = store.search("budget", chat_name="A")
    assert len(res7) == 1
    assert res7[0]["chat_name"] == "A"
