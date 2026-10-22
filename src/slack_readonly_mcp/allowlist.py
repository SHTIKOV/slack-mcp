from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelAllowlist:
    channel_ids: set[str]
    names: set[str]
    allow_all: bool = False

    def is_allowed(
        self,
        *,
        channel_id: str | None = None,
        name: str | None = None,
    ) -> bool:
        if self.allow_all:
            return True
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
    """Parse SLACK_ALLOWED_CHANNELS. Fail closed: empty is an error.

    A single `*` token allows every channel/DM the signed-in user can access
    (read-only). This must be set explicitly; an empty value still errors.
    """
    tokens = [part.strip() for part in (raw or "").split(",")]
    tokens = [t for t in tokens if t]

    if not tokens:
        raise ValueError(
            "SLACK_ALLOWED_CHANNELS is required and must list at least one "
            "channel id or #name (comma-separated), or '*' for all channels."
        )

    if "*" in tokens:
        return ChannelAllowlist(channel_ids=set(), names=set(), allow_all=True)

    channel_ids: set[str] = set()
    names: set[str] = set()

    for token in tokens:
        if _looks_like_id(token):
            channel_ids.add(token)
        else:
            names.add(token.lstrip("#").lower())

    return ChannelAllowlist(channel_ids=channel_ids, names=names)
