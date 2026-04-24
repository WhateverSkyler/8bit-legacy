#!/usr/bin/env python3
"""Set the daily budget on the 8BL-Shopping-Games campaign.

Used for both the initial launch bump and the scheduled post-promo revert.

Usage:
  python3 scripts/ads_set_budget.py --amount 22
  python3 scripts/ads_set_budget.py --amount 15 --reason "promo credit expired"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
for candidate in ((Path("/app/config/.env")), (ROOT / "config" / ".env")):
    if candidate.exists():
        load_dotenv(candidate)
        break
else:
    load_dotenv()

DEV_TOKEN = os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"]
CLIENT_ID = os.environ["GOOGLE_ADS_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_ADS_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["GOOGLE_ADS_REFRESH_TOKEN"]
CUSTOMER_ID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
LOGIN_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")
NAVI_URL = os.environ.get("NAVI_URL", "").rstrip("/")

API_VERSION = "v21"
BASE = f"https://googleads.googleapis.com/{API_VERSION}/customers/{CUSTOMER_ID}"
CAMPAIGN_NAME = "8BL-Shopping-Games"


def get_token() -> str:
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
              "refresh_token": REFRESH_TOKEN, "grant_type": "refresh_token"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}", "developer-token": DEV_TOKEN,
               "Content-Type": "application/json"}
    if LOGIN_CUSTOMER_ID:
        headers["login-customer-id"] = LOGIN_CUSTOMER_ID
    r = requests.request(method, f"{BASE}{path}", headers=headers, json=body, timeout=60)
    if r.status_code >= 400:
        print(r.text, file=sys.stderr)
        r.raise_for_status()
    return r.json() if r.text else {}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--amount", type=float, required=True, help="Daily budget in USD")
    p.add_argument("--reason", default="manual", help="Logged in output + Navi task")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    token = get_token()

    resp = api("POST", "/googleAds:searchStream", token, {
        "query": "SELECT campaign.name, campaign_budget.resource_name, "
                 "campaign_budget.amount_micros "
                 f"FROM campaign WHERE campaign.name = '{CAMPAIGN_NAME}'",
    })
    rows: list[dict] = []
    for chunk in resp if isinstance(resp, list) else [resp]:
        rows.extend(chunk.get("results", []))
    if not rows:
        print(f"FATAL: campaign {CAMPAIGN_NAME!r} not found", file=sys.stderr)
        return 2

    budget = rows[0]["campaignBudget"]
    current = int(budget["amountMicros"]) / 1_000_000.0
    target_micros = int(round(args.amount * 1_000_000))

    print(f"[ads_set_budget] campaign={CAMPAIGN_NAME}")
    print(f"  current budget = ${current:.2f}/day")
    print(f"  target  budget = ${args.amount:.2f}/day")
    print(f"  reason         = {args.reason}")

    if args.dry_run:
        print("  [dry] no change")
        return 0

    if abs(current - args.amount) < 0.01:
        print("  no change needed")
        return 0

    api("POST", "/campaignBudgets:mutate", token, {
        "operations": [{
            "update": {"resourceName": budget["resourceName"],
                       "amountMicros": str(target_micros)},
            "updateMask": "amount_micros",
        }],
    })
    print(f"  ✓ budget updated → ${args.amount:.2f}/day")

    if NAVI_URL:
        try:
            requests.post(f"{NAVI_URL}/api/user-data/sync", json={
                "tasks": [{
                    "title": f"Google Ads budget changed — ${args.amount:.2f}/day",
                    "description": (f"Campaign {CAMPAIGN_NAME} budget updated from "
                                    f"${current:.2f} to ${args.amount:.2f}/day.\n"
                                    f"Reason: {args.reason}"),
                    "priority": "low",
                    "source": "8bit",
                }],
            }, timeout=10)
        except Exception as exc:
            print(f"  [NAVI] post failed: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
