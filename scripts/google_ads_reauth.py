#!/usr/bin/env python3
"""Mint a fresh Google Ads refresh token via OAuth installed-app flow.

Reads GOOGLE_ADS_CLIENT_ID / GOOGLE_ADS_CLIENT_SECRET from config/.env,
opens a browser for consent, then patches GOOGLE_ADS_REFRESH_TOKEN in
config/.env and dashboard/.env.local in place.
"""
import os
import re
import sys
from pathlib import Path

from dotenv import dotenv_values
from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parent.parent
CONFIG_ENV = ROOT / "config" / ".env"
DASHBOARD_ENV = ROOT / "dashboard" / ".env.local"
SCOPES = ["https://www.googleapis.com/auth/adwords"]


def patch_env_file(path: Path, key: str, value: str) -> None:
    if not path.exists():
        print(f"! {path} does not exist; skipping")
        return
    text = path.read_text()
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pattern.search(text):
        new_text = pattern.sub(f"{key}={value}", text)
    else:
        new_text = text.rstrip() + f"\n{key}={value}\n"
    path.write_text(new_text)
    print(f"✓ patched {path}")


def main() -> int:
    cfg = dotenv_values(CONFIG_ENV)
    client_id = cfg.get("GOOGLE_ADS_CLIENT_ID")
    client_secret = cfg.get("GOOGLE_ADS_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("! Missing GOOGLE_ADS_CLIENT_ID / GOOGLE_ADS_CLIENT_SECRET in config/.env")
        return 1

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(
        host="localhost",
        port=0,
        authorization_prompt_message="\n>>> If your browser didn't open, visit this URL:\n{url}\n",
        success_message="Auth complete — you can close this tab.",
        open_browser=True,
    )
    refresh_token = creds.refresh_token
    if not refresh_token:
        print("! No refresh_token returned (was offline access granted?)")
        return 2

    print(f"\n✓ Got refresh token: {refresh_token[:20]}...")
    patch_env_file(CONFIG_ENV, "GOOGLE_ADS_REFRESH_TOKEN", refresh_token)
    patch_env_file(DASHBOARD_ENV, "GOOGLE_ADS_REFRESH_TOKEN", refresh_token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
