from __future__ import annotations

import os
from typing import Any

import httpx


class SlackApiError(RuntimeError):
    """Raised when the Slack web API returns ok=false."""


class SlackWebClient:
    """Thin async wrapper over the Slack web API using browser-session auth.

    Auth mirrors the official web client: the xoxc token is sent as the `token`
    form field and the `d` cookie is sent as a cookie. No app, no bot.
    """

    def __init__(self, *, token: str, d_cookie: str, base_url: str) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            cookies={"d": d_cookie},
            headers={"User-Agent": "slack-readonly-mcp/0.1"},
        )

    async def call(self, method: str, **params: Any) -> dict[str, Any]:
        data = {k: v for k, v in params.items() if v is not None}
        data["token"] = self._token
        resp = await self._http.post(f"{self._base_url}/{method}", data=data)
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("ok", False):
            raise SlackApiError(payload.get("error", "unknown_error"))
        return payload

    async def aclose(self) -> None:
        await self._http.aclose()


def build_client() -> SlackWebClient:
    token = os.environ.get("SLACK_XOXC_TOKEN", "").strip()
    d_cookie = os.environ.get("SLACK_XOXD_COOKIE", "").strip()
    base_url = os.environ.get("SLACK_BASE_URL", "https://slack.com/api").strip()

    if not token or not d_cookie:
        raise RuntimeError(
            "SLACK_XOXC_TOKEN and SLACK_XOXD_COOKIE are required "
            "(see README: how to extract them from your browser session)."
        )

    return SlackWebClient(token=token, d_cookie=d_cookie, base_url=base_url)
