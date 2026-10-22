from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

STATE_DIR = Path(
    os.environ.get(
        "SLACK_STATE_DIR",
        str(Path.home() / ".local/state/slack-readonly-mcp"),
    )
).expanduser()
CREDENTIALS_PATH = STATE_DIR / "credentials.json"
BROWSER_PROFILE_DIR = STATE_DIR / "browser-profile"


def save_credentials(
    *, token: str, d_cookie: str, team: str | None = None, base_url: str | None = None
) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"token": token, "d_cookie": d_cookie}
    if team:
        payload["team"] = team
    if base_url:
        payload["base_url"] = base_url
    # Write with restrictive permissions (secrets).
    fd = os.open(str(CREDENTIALS_PATH), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.chmod(CREDENTIALS_PATH, 0o600)
    return CREDENTIALS_PATH


def load_credentials() -> dict[str, Any] | None:
    try:
        with open(CREDENTIALS_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
