from unittest.mock import AsyncMock

import pytest

from slack_readonly_mcp.allowlist import ChannelAllowlist
from slack_readonly_mcp.service import AccessDenied, SlackReadonlyService


def _client_with(convos, extra=None):
    client = AsyncMock()

    async def call(method, **params):
        if method == "users.conversations":
            return {"channels": convos, "response_metadata": {"next_cursor": ""}}
        if extra and method in extra:
            return extra[method]
        raise AssertionError(f"unexpected call {method} {params}")

    client.call = AsyncMock(side_effect=call)
    return client


@pytest.fixture
def allowlist():
    return ChannelAllowlist(channel_ids={"C01"}, names={"ops"})


async def test_list_channels_filters_to_allowlist(allowlist):
    convos = [
        {"id": "C01", "name": "dev", "is_private": False},
        {"id": "C02", "name": "random", "is_private": False},
        {"id": "C03", "name": "ops", "is_private": True},
    ]
    service = SlackReadonlyService(client=_client_with(convos), allowlist=allowlist)
    chats = await service.list_channels()
    assert {c["id"] for c in chats} == {"C01", "C03"}


async def test_get_history_denies_outside_allowlist(allowlist):
    convos = [{"id": "C99", "name": "secret", "is_private": True}]
    service = SlackReadonlyService(client=_client_with(convos), allowlist=allowlist)
    with pytest.raises(AccessDenied):
        await service.get_history(channel="C99", limit=10)


async def test_get_history_returns_messages(allowlist):
    convos = [{"id": "C01", "name": "dev"}]
    extra = {
        "conversations.history": {
            "messages": [{"ts": "1700000000.0001", "text": "hi", "user": "U1"}],
            "response_metadata": {"next_cursor": "NEXT"},
        }
    }
    service = SlackReadonlyService(client=_client_with(convos, extra), allowlist=allowlist)
    result = await service.get_history(channel="#dev", limit=5)
    assert result["channel"]["id"] == "C01"
    assert result["messages"][0]["text"] == "hi"
    assert result["next_cursor"] == "NEXT"


async def test_resolve_by_name_not_found_denies(allowlist):
    convos = [{"id": "C01", "name": "dev"}]
    service = SlackReadonlyService(client=_client_with(convos), allowlist=allowlist)
    with pytest.raises(AccessDenied):
        await service.get_channel("#nope")


async def test_search_filters_results_to_allowlist(allowlist):
    convos = [{"id": "C01", "name": "dev"}]
    extra = {
        "search.messages": {
            "messages": {
                "matches": [
                    {"ts": "1.1", "text": "a", "channel": {"id": "C01", "name": "dev"}},
                    {"ts": "2.2", "text": "b", "channel": {"id": "C99", "name": "x"}},
                ]
            }
        }
    }
    service = SlackReadonlyService(client=_client_with(convos, extra), allowlist=allowlist)
    result = await service.search_messages(query="deploy", limit=20)
    assert result["count"] == 1
    assert result["messages"][0]["channel_id"] == "C01"


async def test_search_scoped_to_channel_injects_in_filter():
    convos = [{"id": "C01", "name": "dev"}]
    captured = {}
    client = AsyncMock()

    async def call(method, **params):
        if method == "users.conversations":
            return {"channels": convos, "response_metadata": {"next_cursor": ""}}
        if method == "search.messages":
            captured["query"] = params["query"]
            return {"messages": {"matches": []}}
        raise AssertionError(method)

    client.call = AsyncMock(side_effect=call)
    allow = ChannelAllowlist(channel_ids={"C01"}, names=set())
    service = SlackReadonlyService(client=client, allowlist=allow)
    await service.search_messages(query="release", channel="C01", limit=10)
    assert captured["query"] == "in:#dev release"
