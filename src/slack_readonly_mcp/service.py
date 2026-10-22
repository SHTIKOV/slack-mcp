from __future__ import annotations

import re
from typing import Any

from slack_readonly_mcp.allowlist import ChannelAllowlist
from slack_readonly_mcp.format import (
    format_channel,
    format_message,
    format_search_match,
    format_user,
)

_ID_RE = re.compile(r"^[CGD][A-Z0-9]+$")
_CONV_TYPES = "public_channel,private_channel,mpim,im"


class AccessDenied(PermissionError):
    """Raised when a channel is outside SLACK_ALLOWED_CHANNELS."""


class SlackReadonlyService:
    def __init__(self, *, client: Any, allowlist: ChannelAllowlist) -> None:
        self._client = client
        self._allowlist = allowlist
        self._index: dict[str, dict[str, Any]] | None = None

    async def _conversation_index(self) -> dict[str, dict[str, Any]]:
        """Channels the authed user is a member of, cached. id -> channel dict."""
        if self._index is not None:
            return self._index

        index: dict[str, dict[str, Any]] = {}
        cursor = ""
        while True:
            payload = await self._client.call(
                "users.conversations",
                types=_CONV_TYPES,
                limit=200,
                exclude_archived=False,
                cursor=cursor or None,
            )
            for ch in payload.get("channels", []):
                if ch.get("id"):
                    index[ch["id"]] = ch
            cursor = (payload.get("response_metadata") or {}).get("next_cursor") or ""
            if not cursor:
                break
        self._index = index
        return index

    def _ensure_allowed(self, ch: dict[str, Any]) -> None:
        if not self._allowlist.is_allowed(
            channel_id=ch.get("id"),
            name=ch.get("name") or ch.get("name_normalized"),
        ):
            raise AccessDenied(
                f"Access to channel '{ch.get('id') or ch.get('name')}' "
                "is denied by SLACK_ALLOWED_CHANNELS"
            )

    async def _resolve_channel(self, ref: str) -> dict[str, Any]:
        ref = ref.strip()
        if _ID_RE.match(ref):
            index = await self._conversation_index()
            ch = index.get(ref)
            if ch is None:
                ch = (await self._client.call("conversations.info", channel=ref)).get(
                    "channel", {}
                )
        else:
            wanted = ref.lstrip("#").lower()
            index = await self._conversation_index()
            ch = next(
                (
                    c
                    for c in index.values()
                    if (c.get("name") or c.get("name_normalized") or "").lower() == wanted
                ),
                None,
            )
            if ch is None:
                raise AccessDenied(
                    f"Channel '{ref}' not found among your conversations"
                )
        self._ensure_allowed(ch)
        return ch

    async def list_channels(self) -> list[dict[str, Any]]:
        index = await self._conversation_index()
        out = [
            format_channel(ch)
            for ch in index.values()
            if self._allowlist.is_allowed(
                channel_id=ch.get("id"),
                name=ch.get("name") or ch.get("name_normalized"),
            )
        ]
        return out

    async def get_channel(self, channel: str) -> dict[str, Any]:
        return format_channel(await self._resolve_channel(channel))

    async def get_history(
        self, *, channel: str, limit: int = 50, cursor: str = ""
    ) -> dict[str, Any]:
        ch = await self._resolve_channel(channel)
        limit = max(1, min(int(limit), 100))
        payload = await self._client.call(
            "conversations.history",
            channel=ch["id"],
            limit=limit,
            cursor=cursor or None,
        )
        return {
            "channel": format_channel(ch),
            "messages": [format_message(m) for m in payload.get("messages", [])],
            "next_cursor": (payload.get("response_metadata") or {}).get("next_cursor")
            or "",
        }

    async def get_thread(
        self, *, channel: str, thread_ts: str, limit: int = 100
    ) -> dict[str, Any]:
        ch = await self._resolve_channel(channel)
        limit = max(1, min(int(limit), 200))
        payload = await self._client.call(
            "conversations.replies",
            channel=ch["id"],
            ts=thread_ts,
            limit=limit,
        )
        return {
            "channel": format_channel(ch),
            "thread_ts": thread_ts,
            "messages": [format_message(m) for m in payload.get("messages", [])],
        }

    async def search_messages(
        self, *, query: str, channel: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit), 100))
        full_query = query
        if channel:
            ch = await self._resolve_channel(channel)
            full_query = f"in:#{ch.get('name')} {query}" if ch.get("name") else query
        payload = await self._client.call(
            "search.messages",
            query=full_query,
            count=limit,
        )
        matches = ((payload.get("messages") or {}).get("matches")) or []
        allowed = [
            format_search_match(m)
            for m in matches
            if self._allowlist.is_allowed(
                channel_id=(m.get("channel") or {}).get("id"),
                name=(m.get("channel") or {}).get("name"),
            )
        ]
        return {"query": full_query, "messages": allowed, "count": len(allowed)}

    async def get_user(self, user: str) -> dict[str, Any]:
        payload = await self._client.call("users.info", user=user.strip())
        return format_user(payload.get("user", {}))

    async def whoami(self) -> dict[str, Any]:
        payload = await self._client.call("auth.test")
        return {
            "user": payload.get("user"),
            "user_id": payload.get("user_id"),
            "team": payload.get("team"),
            "team_id": payload.get("team_id"),
            "url": payload.get("url"),
        }
