import importlib
import os
import stat

import pytest


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SLACK_STATE_DIR", str(tmp_path))
    import slack_readonly_mcp.credentials as creds

    importlib.reload(creds)
    import slack_readonly_mcp.client as client

    importlib.reload(client)
    yield tmp_path
    # restore module state for other tests
    monkeypatch.delenv("SLACK_STATE_DIR", raising=False)
    importlib.reload(creds)
    importlib.reload(client)


def test_save_and_load_roundtrip(state_dir):
    import slack_readonly_mcp.credentials as creds

    path = creds.save_credentials(token="tok", d_cookie="dc", team="Acme")
    assert creds.load_credentials() == {
        "token": "tok",
        "d_cookie": "dc",
        "team": "Acme",
    }
    # file must be owner-only
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_load_missing_returns_none(state_dir):
    import slack_readonly_mcp.credentials as creds

    assert creds.load_credentials() is None


def test_build_client_falls_back_to_saved(state_dir, monkeypatch):
    import slack_readonly_mcp.credentials as creds
    import slack_readonly_mcp.client as client

    monkeypatch.delenv("SLACK_XOXC_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_XOXD_COOKIE", raising=False)
    monkeypatch.delenv("SLACK_BASE_URL", raising=False)
    creds.save_credentials(token="tok", d_cookie="dc", base_url="https://x.slack.com/api")

    c = client.build_client()
    assert c._token == "tok"
    assert c._base_url == "https://x.slack.com/api"


def test_build_client_env_wins_over_saved(state_dir, monkeypatch):
    import slack_readonly_mcp.credentials as creds
    import slack_readonly_mcp.client as client

    creds.save_credentials(token="saved", d_cookie="saved-d")
    monkeypatch.setenv("SLACK_XOXC_TOKEN", "envtok")
    monkeypatch.setenv("SLACK_XOXD_COOKIE", "env-d")

    c = client.build_client()
    assert c._token == "envtok"
    assert c._base_url == "https://slack.com/api"


def test_build_client_without_any_credentials_raises(state_dir, monkeypatch):
    import slack_readonly_mcp.client as client

    monkeypatch.delenv("SLACK_XOXC_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_XOXD_COOKIE", raising=False)
    with pytest.raises(RuntimeError, match="slack-readonly-login"):
        client.build_client()


def test_pick_team_prefers_active():
    from slack_readonly_mcp.browserlogin import _pick_team

    config = {
        "lastActiveTeamId": "T2",
        "teams": {
            "T1": {"token": "tok1", "name": "First"},
            "T2": {"token": "tok2", "name": "Second"},
        },
    }
    token, label = _pick_team(config)
    assert token == "tok2"
    assert label == "Second"


def test_pick_team_skips_tokenless_and_errors_when_empty():
    from slack_readonly_mcp.browserlogin import _pick_team

    assert _pick_team({"teams": {"T1": {"token": "x", "name": "N"}}}) == ("x", "N")
    with pytest.raises(RuntimeError):
        _pick_team({"teams": {}})
