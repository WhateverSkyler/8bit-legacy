#!/usr/bin/env python3
"""Refresh the YouTube OAuth token to keep it alive within Google's
7-day Testing-mode refresh-token expiry. Run on a 6-day cadence.

Reads/writes config/.yt_token.json. If refresh fails, emits a Navi task
so the user knows they need to re-auth (the cowork brief is at
docs/claude-cowork-brief-2026-05-06-yt-oauth-permanent-fix.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TOKEN = ROOT / "config" / ".yt_token.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

sys.path.insert(0, str(ROOT / "scripts"))
try:
    from navi_alerts import emit_navi_task
except ImportError:
    emit_navi_task = None


def main() -> int:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not TOKEN.exists():
        print(f"[ERROR] no token at {TOKEN}", file=sys.stderr)
        return 1

    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    try:
        creds.refresh(Request())
    except Exception as exc:
        msg = (f"YT token refresh FAILED: {exc}. User must re-auth via "
               "docs/claude-cowork-brief-2026-05-06-yt-oauth-permanent-fix.md")
        print(f"[FAIL] {msg}", file=sys.stderr)
        if emit_navi_task is not None:
            try:
                emit_navi_task(
                    title="YouTube OAuth re-auth required",
                    description=msg,
                    priority="high",
                )
            except Exception:
                pass
        return 2

    TOKEN.write_text(creds.to_json())
    expiry = creds.expiry.isoformat() if creds.expiry else "(unknown)"
    print(f"[OK] refreshed token, new access expires {expiry}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
