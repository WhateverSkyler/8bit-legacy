#!/usr/bin/env python3
"""Zernio smoke test — verify API key, list connected accounts, check health.

Usage:
    python3 scripts/setup_zernio.py              # list + health only (safe)
    python3 scripts/setup_zernio.py --smoke-post # post a throwaway image to IG and delete after 60s

Run this after you've connected IG / FB / TikTok / YouTube in the Zernio dashboard
(https://zernio.com/dashboard).
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from zernio_client import ZernioClient, ZernioError  # noqa: E402


PLATFORM_ORDER = ["instagram", "facebook", "tiktok", "youtube", "twitter", "threads"]


def _platform_rank(p: str) -> int:
    try:
        return PLATFORM_ORDER.index(p)
    except ValueError:
        return len(PLATFORM_ORDER)


def list_accounts(client: ZernioClient) -> list[dict]:
    data = client.list_accounts()
    accounts = data if isinstance(data, list) else data.get("accounts", [])
    accounts.sort(key=lambda a: _platform_rank((a.get("platform") or "").lower()))
    return accounts


def print_accounts(accounts: list[dict]) -> None:
    if not accounts:
        print("  (no accounts connected yet — go to https://zernio.com/dashboard and OAuth into IG/FB/TikTok/YT first)")
        return
    for acc in accounts:
        print(f"  {acc.get('platform', '?'):<10} {acc.get('id', '?'):<30} @{acc.get('handle') or acc.get('username') or acc.get('name', '?')}")


def print_health(client: ZernioClient) -> None:
    h = client.accounts_health()
    summary = h.get("summary", {}) if isinstance(h, dict) else {}
    print(f"  total={summary.get('total', '?')}  healthy={summary.get('healthy', '?')}  "
          f"expired={summary.get('expired', '?')}  requiresReauth={summary.get('requiresReauth', '?')}")
    unhealthy = [a for a in (h.get("accounts") or []) if a.get("status") and a["status"] != "healthy"]
    for a in unhealthy:
        print(f"  ⚠ {a.get('platform')} {a.get('id')} → {a.get('status')}: {a.get('message', '')}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-post", action="store_true",
                        help="Post a tiny throwaway image to IG, wait 60s, delete (requires IG connected)")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON instead of the human summary")
    args = parser.parse_args()

    try:
        client = ZernioClient()
    except ZernioError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2

    print("→ Listing connected accounts…")
    accounts = list_accounts(client)
    if args.json:
        print(json.dumps(accounts, indent=2))
    else:
        print_accounts(accounts)

    print("\n→ Account health…")
    print_health(client)

    if args.smoke_post:
        ig = next((a for a in accounts if (a.get("platform") or "").lower() == "instagram"), None)
        if not ig:
            print("\n⚠ --smoke-post requires an Instagram account connected; skipping.")
            return 0
        print(f"\n→ Smoke post to IG ({ig['id']})…")
        print("  (not implemented in this first pass — run after Track B photo scheduler is wired)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
