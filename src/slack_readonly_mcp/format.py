from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _ts_to_iso(ts: Any) -> str | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def format_message(msg: dict[str, Any]) -> dict[str, Any]:
    ts = msg.get("ts")
    files = msg.get("files") or []
    attachments = msg.get("attachments") or []
    return {
        "ts": ts,
        "date": _ts_to_iso(ts),
        "text": msg.get("text") or "",
        "user": msg.get("user") or msg.get("username") or msg.get("bot_id"),
        "thread_ts": msg.get("thread_ts"),
        "reply_count": msg.get("reply_count"),
        "has_files": bool(files),
        "has_attachments": bool(attachments),
    }


def format_search_match(match: dict[str, Any]) -> dict[str, Any]:
    channel = match.get("channel") or {}
    ts = match.get("ts")
    return {
        "ts": ts,
        "date": _ts_to_iso(ts),
        "text": match.get("text") or "",
        "user": match.get("user") or match.get("username"),
        "channel_id": channel.get("id"),
        "channel_name": channel.get("name"),
        "permalink": match.get("permalink"),
    }


def format_channel(ch: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": ch.get("id"),
        "name": ch.get("name") or ch.get("name_normalized"),
        "is_private": ch.get("is_private"),
        "is_im": ch.get("is_im"),
        "is_mpim": ch.get("is_mpim"),
        "is_archived": ch.get("is_archived"),
        "num_members": ch.get("num_members"),
        "user": ch.get("user"),  # set for DMs
        "topic": (ch.get("topic") or {}).get("value"),
        "purpose": (ch.get("purpose") or {}).get("value"),
    }


def format_user(user: dict[str, Any]) -> dict[str, Any]:
    profile = user.get("profile") or {}
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "real_name": user.get("real_name") or profile.get("real_name"),
        "display_name": profile.get("display_name"),
        "is_bot": user.get("is_bot"),
        "deleted": user.get("deleted"),
        "tz": user.get("tz"),
    }
