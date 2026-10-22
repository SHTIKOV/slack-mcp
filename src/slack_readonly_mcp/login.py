from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from slack_readonly_mcp.client import SlackApiError, build_client


async def _whoami() -> None:
    client = build_client()
    try:
        payload = await client.call("auth.test")
    finally:
        await client.aclose()
    print("Session OK.")
    print(f"  user:  {payload.get('user')} ({payload.get('user_id')})")
    print(f"  team:  {payload.get('team')} ({payload.get('team_id')})")
    print(f"  url:   {payload.get('url')}")


def main() -> None:
    load_dotenv()
    try:
        asyncio.run(_whoami())
    except SlackApiError as exc:
        raise SystemExit(
            f"Slack rejected the session: {exc}. "
            "Re-copy SLACK_XOXC_TOKEN and SLACK_XOXD_COOKIE from the browser."
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    main()
