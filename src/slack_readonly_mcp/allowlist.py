from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelAllowlist:
    channel_ids: set[str]
    names: set[str]

    def is_allowed(
        self,
        *,
        channel_id: str | None = None,
        name: str | None = None,
    ) -> bool:
        if channel_id and channel_id in self.channel_ids:
            return True
        if name:
            normalized = name.lstrip("#").lower()
            if normalized in self.names:
                return True
        return False


def _looks_like_id(token: str) -> bool:
    # Slack conversation ids: C/G/D + uppercase alnum (channels, groups, DMs).
    return (
        len(token) >= 2
        and token[0] in "CGD"
        and token[1:].isalnum()
        and token == token.upper()
    )


def parse_allowed_channels(raw: str) -> ChannelAllowlist:
    """Parse SLACK_ALLOWED_CHANNELS. Fail closed: empty is an error."""
    tokens = [part.strip() for part in (raw or "").split(",")]
    tokens = [t for t in tokens if t]

    if not tokens:
        raise ValueError(
            "SLACK_ALLOWED_CHANNELS is required and must list at least one "
            "channel id or #name (comma-separated)."
        )

    channel_ids: set[str] = set()
    names: set[str] = set()

    for token in tokens:
        if _looks_like_id(token):
            channel_ids.add(token)
        else:
            names.add(token.lstrip("#").lower())

    return ChannelAllowlist(channel_ids=channel_ids, names=names)
