from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

from slack_readonly_mcp.allowlist import parse_allowed_channels
from slack_readonly_mcp.client import SlackApiError, build_client
from slack_readonly_mcp.service import AccessDenied, SlackReadonlyService

load_dotenv()


class AppState:
    service: SlackReadonlyService | None = None
    client: Any = None


STATE = AppState()


@asynccontextmanager
async def lifespan(_server: MCPServer) -> AsyncIterator[dict[str, Any]]:
    allowlist = parse_allowed_channels(os.environ.get("SLACK_ALLOWED_CHANNELS", ""))
    client = build_client()
    STATE.client = client
    STATE.service = SlackReadonlyService(client=client, allowlist=allowlist)
    try:
        yield {"service": STATE.service}
    finally:
        STATE.service = None
        STATE.client = None
        await client.aclose()


mcp = MCPServer(
    name="slack-readonly",
    instructions=(
        "Read-only Slack access limited to SLACK_ALLOWED_CHANNELS, using your own "
        "browser session. Use whoami, list_allowed_channels, get_channel, "
        "get_history, get_thread, search_messages, get_user."
    ),
    lifespan=lifespan,
)


def _service() -> SlackReadonlyService:
    if STATE.service is None:
        raise RuntimeError("Slack service is not initialized")
    return STATE.service


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def _guard(coro_factory):
    """Run a service call, mapping known errors to structured JSON."""
    async def runner() -> str:
        try:
            return _dump(await coro_factory())
        except AccessDenied as exc:
            return _dump({"error": "access_denied", "message": str(exc)})
        except SlackApiError as exc:
            return _dump({"error": "slack_api_error", "message": str(exc)})

    return runner()


@mcp.tool()
async def whoami() -> str:
    """Show which Slack account and workspace the session belongs to."""
    return await _guard(lambda: _service().whoami())


@mcp.tool()
async def list_allowed_channels() -> str:
    """List channels visible under SLACK_ALLOWED_CHANNELS."""
    async def op() -> dict[str, Any]:
        chats = await _service().list_channels()
        return {"channels": chats, "count": len(chats)}

    return await _guard(op)


@mcp.tool()
async def get_channel(channel: str) -> str:
    """Get metadata for one allowed channel (id or #name)."""
    return await _guard(lambda: _service().get_channel(channel))


@mcp.tool()
async def get_history(channel: str, limit: int = 50, cursor: str = "") -> str:
    """Fetch recent messages from an allowed channel (newest first). limit max 100."""
    return await _guard(
        lambda: _service().get_history(channel=channel, limit=limit, cursor=cursor)
    )


@mcp.tool()
async def get_thread(channel: str, thread_ts: str, limit: int = 100) -> str:
    """Fetch a thread (parent + replies) from an allowed channel. limit max 200."""
    return await _guard(
        lambda: _service().get_thread(channel=channel, thread_ts=thread_ts, limit=limit)
    )


@mcp.tool()
async def search_messages(query: str, channel: str = "", limit: int = 50) -> str:
    """Search messages. Optionally scope to one channel. Results are filtered to
    SLACK_ALLOWED_CHANNELS. limit max 100."""
    return await _guard(
        lambda: _service().search_messages(
            query=query, channel=channel or None, limit=limit
        )
    )


@mcp.tool()
async def get_user(user: str) -> str:
    """Look up a Slack user by id (e.g. U01234567)."""
    return await _guard(lambda: _service().get_user(user))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
