from slack_readonly_mcp.format import (
    format_channel,
    format_message,
    format_search_match,
    format_user,
)


def test_format_message_basic():
    out = format_message(
        {
            "ts": "1700000000.000100",
            "text": "hello",
            "user": "U55",
            "thread_ts": None,
        }
    )
    assert out["ts"] == "1700000000.000100"
    assert out["text"] == "hello"
    assert out["user"] == "U55"
    assert out["has_files"] is False
    assert out["date"].startswith("2023-11-14T")


def test_format_message_with_files_and_fallback_user():
    out = format_message({"ts": "bad", "bot_id": "B1", "files": [{}]})
    assert out["user"] == "B1"
    assert out["has_files"] is True
    assert out["text"] == ""
    assert out["date"] is None


def test_format_search_match():
    out = format_search_match(
        {
            "ts": "1700000000.000200",
            "text": "deploy done",
            "user": "U7",
            "channel": {"id": "C01", "name": "dev"},
            "permalink": "https://x.slack.com/archives/C01/p1",
        }
    )
    assert out["channel_id"] == "C01"
    assert out["channel_name"] == "dev"
    assert out["permalink"].endswith("/p1")


def test_format_channel():
    out = format_channel(
        {
            "id": "C01",
            "name": "dev",
            "is_private": False,
            "num_members": 12,
            "topic": {"value": "ship it"},
            "purpose": {"value": "dev chat"},
        }
    )
    assert out["id"] == "C01"
    assert out["name"] == "dev"
    assert out["num_members"] == 12
    assert out["topic"] == "ship it"
    assert out["purpose"] == "dev chat"


def test_format_user():
    out = format_user(
        {
            "id": "U1",
            "name": "kostya",
            "real_name": "Kostya",
            "profile": {"display_name": "k"},
            "is_bot": False,
        }
    )
    assert out == {
        "id": "U1",
        "name": "kostya",
        "real_name": "Kostya",
        "display_name": "k",
        "is_bot": False,
        "deleted": None,
        "tz": None,
    }
