from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from slack_readonly_mcp.client import SlackApiError, SlackWebClient, build_client
from slack_readonly_mcp.credentials import (
    BROWSER_PROFILE_DIR,
    save_credentials,
)

SLACK_URL = "https://app.slack.com/client"


async def _already_valid() -> dict[str, Any] | None:
    """Return whoami payload if saved/env credentials still work, else None."""
    try:
        client = build_client()
    except RuntimeError:
        return None
    try:
        return await client.call("auth.test")
    except (SlackApiError, Exception):
        return None
    finally:
        await client.aclose()


def _pick_team(config: dict[str, Any]) -> tuple[str, str]:
    """Return (token, team_label) from a parsed localConfig_v2 object."""
    teams = config.get("teams") or {}
    if not teams:
        raise RuntimeError("No teams in Slack localConfig yet (not signed in?)")

    active = config.get("lastActiveTeamId") or config.get("activeTeamId")
    ordered = []
    if active and active in teams:
        ordered.append(active)
    ordered += [tid for tid in teams if tid != active]

    for tid in ordered:
        team = teams[tid] or {}
        token = (team.get("token") or "").strip()
        if token:
            label = team.get("name") or team.get("domain") or team.get("url") or tid
            return token, str(label)

    raise RuntimeError("No workspace token found in Slack localConfig")


async def _wait_for_token(page, timeout_s: int) -> tuple[str, str]:
    for _ in range(timeout_s):
        raw = await page.evaluate(
            "() => window.localStorage.getItem('localConfig_v2')"
        )
        if raw:
            try:
                config = json.loads(raw)
                return _pick_team(config)
            except (json.JSONDecodeError, RuntimeError):
                pass
        await page.wait_for_timeout(1000)
    raise RuntimeError(
        f"Timed out after {timeout_s}s waiting for Slack sign-in in the browser."
    )


async def _get_d_cookie(context) -> str:
    for url in ("https://slack.com", "https://app.slack.com"):
        for cookie in await context.cookies(url):
            if cookie.get("name") == "d" and cookie.get("value"):
                return cookie["value"]
    for cookie in await context.cookies():
        if cookie.get("name") == "d" and cookie.get("value"):
            return cookie["value"]
    raise RuntimeError("Could not find the Slack 'd' cookie in the browser session.")


async def _extract(timeout_s: int) -> tuple[str, str, str]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright is not installed. Run: uv sync --extra browser"
        ) from exc

    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    # Default to Playwright's own bundled Chromium (avoids snap confinement that
    # blocks a persistent profile under ~/.local). Point SLACK_CHROMIUM_PATH at a
    # system browser only if you know it can write the profile dir.
    exe = os.environ.get("SLACK_CHROMIUM_PATH", "").strip()
    launch_kwargs: dict[str, Any] = {
        "headless": False,
        "args": ["--no-first-run", "--no-default-browser-check"],
    }
    if exe and Path(exe).exists():
        launch_kwargs["executable_path"] = exe

    async with async_playwright() as pw:
        try:
            context = await pw.chromium.launch_persistent_context(
                str(BROWSER_PROFILE_DIR), **launch_kwargs
            )
        except Exception as exc:  # noqa: BLE001 - surface a clear setup hint
            raise SystemExit(
                f"Could not launch Chromium ({exc}). Install the bundled browser "
                "with: uv run --extra browser playwright install chromium"
            ) from exc
        try:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(SLACK_URL, wait_until="domcontentloaded")
            print(
                "A browser window opened. Sign in to Slack if needed; "
                "waiting for the session..."
            )
            token, team = await _wait_for_token(page, timeout_s)
            d_cookie = await _get_d_cookie(context)
            return token, team, d_cookie
        finally:
            await context.close()


async def _run(timeout_s: int, force: bool) -> None:
    if not force:
        existing = await _already_valid()
        if existing:
            print(
                "Already authorized as "
                f"{existing.get('user')} @ {existing.get('team')}. "
                "Use --force to re-authorize."
            )
            return

    token, team, d_cookie = await _extract(timeout_s)
    path = save_credentials(token=token, d_cookie=d_cookie, team=team)
    print(f"Saved credentials for workspace '{team}' to {path}")

    client = SlackWebClient(
        token=token,
        d_cookie=d_cookie,
        base_url=os.environ.get("SLACK_BASE_URL", "https://slack.com/api"),
    )
    try:
        who = await client.call("auth.test")
    finally:
        await client.aclose()
    print(f"Session OK: {who.get('user')} ({who.get('user_id')}) @ {who.get('team')}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Authorize Slack read-only MCP via a real browser session."
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Seconds to wait for sign-in (default 300).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-authorize even if existing credentials still work.",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.timeout, args.force))


if __name__ == "__main__":
    main()
