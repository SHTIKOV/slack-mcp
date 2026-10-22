import pytest

from slack_readonly_mcp.allowlist import ChannelAllowlist, parse_allowed_channels


def test_parse_empty_raises():
    with pytest.raises(ValueError, match="SLACK_ALLOWED_CHANNELS"):
        parse_allowed_channels("")


def test_parse_whitespace_only_raises():
    with pytest.raises(ValueError, match="SLACK_ALLOWED_CHANNELS"):
        parse_allowed_channels("  ,  ")


def test_parse_ids_and_names():
    allowlist = parse_allowed_channels("C01234567, #General, dev-team, G09999999")
    assert allowlist.channel_ids == {"C01234567", "G09999999"}
    assert allowlist.names == {"general", "dev-team"}


def test_allows_channel_id():
    allowlist = ChannelAllowlist(channel_ids={"C001"}, names=set())
    assert allowlist.is_allowed(channel_id="C001")
    assert not allowlist.is_allowed(channel_id="C002")


def test_allows_name_case_insensitive_and_hash():
    allowlist = ChannelAllowlist(channel_ids=set(), names={"devops"})
    assert allowlist.is_allowed(name="DevOps")
    assert allowlist.is_allowed(name="#devops")
    assert not allowlist.is_allowed(name="other")


def test_allows_when_either_id_or_name_matches():
    allowlist = ChannelAllowlist(channel_ids={"C42"}, names={"ops"})
    assert allowlist.is_allowed(channel_id="C99", name="ops")
    assert allowlist.is_allowed(channel_id="C42", name="nope")
    assert not allowlist.is_allowed(channel_id="C99", name="nope")
