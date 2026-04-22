#!/usr/bin/env python3
"""Read-only audit of the Google Ads account + campaigns + conversion actions.

Emits a summary to stdout so the transcript stays bounded. No mutations.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")

DEV_TOKEN = os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"]
CLIENT_ID = os.environ["GOOGLE_ADS_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_ADS_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["GOOGLE_ADS_REFRESH_TOKEN"]
CUSTOMER_ID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
LOGIN_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")

API_VERSION = "v21"
BASE = f"https://googleads.googleapis.com/{API_VERSION}"


def get_token() -> str:
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def search(query: str, token: str) -> list:
    headers = {
        "Authorization": f"Bearer {token}",
        "developer-token": DEV_TOKEN,
        "Content-Type": "application/json",
    }
    if LOGIN_CUSTOMER_ID:
        headers["login-customer-id"] = LOGIN_CUSTOMER_ID
    r = requests.post(
        f"{BASE}/customers/{CUSTOMER_ID}/googleAds:searchStream",
        headers=headers,
        json={"query": query},
        timeout=60,
    )
    if r.status_code >= 400:
        print(f"QUERY FAILED ({r.status_code}): {query}", file=sys.stderr)
        print(r.text[:2000], file=sys.stderr)
        r.raise_for_status()
    results = []
    data = r.json()
    # searchStream returns a list of response chunks
    for chunk in data if isinstance(data, list) else [data]:
        for row in chunk.get("results", []):
            results.append(row)
    return results


def main() -> int:
    tok = get_token()

    print("\n=== ACCOUNT ===")
    rows = search(
        "SELECT customer.id, customer.descriptive_name, customer.currency_code, customer.time_zone, customer.status FROM customer LIMIT 1",
        tok,
    )
    for r in rows:
        c = r["customer"]
        print(f"  id={c.get('id')} name={c.get('descriptiveName')} currency={c.get('currencyCode')} tz={c.get('timeZone')} status={c.get('status')}")

    print("\n=== CAMPAIGNS ===")
    rows = search(
        "SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type, "
        "campaign.advertising_channel_sub_type, campaign.bidding_strategy_type, "
        "campaign_budget.amount_micros "
        "FROM campaign ORDER BY campaign.id",
        tok,
    )
    if not rows:
        print("  (no campaigns)")
    for r in rows:
        c = r["campaign"]
        b = r.get("campaignBudget", {})
        budget = int(b.get("amountMicros", 0)) / 1_000_000 if b.get("amountMicros") else 0
        print(
            f"  {c['id']:>12}  {c['name'][:36]:36}  {c['status']:10}  "
            f"{c['advertisingChannelType']:8}  {c.get('advertisingChannelSubType','-'):20}  "
            f"${budget:5.2f}/day  bid={c['biddingStrategyType']}"
        )

    print("\n=== AD GROUPS ===")
    rows = search(
        "SELECT ad_group.id, ad_group.name, ad_group.status, ad_group.type, "
        "ad_group.cpc_bid_micros, campaign.id "
        "FROM ad_group ORDER BY campaign.id, ad_group.id",
        tok,
    )
    if not rows:
        print("  (no ad groups)")
    for r in rows:
        a = r["adGroup"]
        cpc = int(a.get("cpcBidMicros", 0)) / 1_000_000
        print(f"  camp={r['campaign']['id']} ag={a['id']} name={a['name']} status={a['status']} type={a['type']} cpc=${cpc:.2f}")

    print("\n=== CONVERSION ACTIONS ===")
    rows = search(
        "SELECT conversion_action.id, conversion_action.name, conversion_action.status, "
        "conversion_action.category, conversion_action.type, conversion_action.origin, "
        "conversion_action.primary_for_goal "
        "FROM conversion_action ORDER BY conversion_action.name",
        tok,
    )
    for r in rows:
        a = r["conversionAction"]
        prim = "★" if a.get("primaryForGoal") else " "
        print(f"  {prim} {a['id']:>12}  {a['name'][:42]:42}  cat={a['category']:18}  status={a['status']:10}  origin={a['origin']}")

    print("\n=== CUSTOMER CONVERSION GOALS (active) ===")
    try:
        rows = search(
            "SELECT customer_conversion_goal.category, customer_conversion_goal.origin "
            "FROM customer_conversion_goal",
            tok,
        )
        for r in rows:
            g = r["customerConversionGoal"]
            print(f"  category={g['category']:18}  origin={g['origin']}")
    except Exception as e:
        print(f"  (skipping goals query: {e})")

    print("\n=== CAMPAIGN CRITERIA (negatives) ===")
    rows = search(
        "SELECT campaign_criterion.campaign, campaign_criterion.type, campaign_criterion.negative, "
        "campaign_criterion.keyword.text, campaign_criterion.keyword.match_type, "
        "campaign_criterion.location.geo_target_constant "
        "FROM campaign_criterion WHERE campaign_criterion.type IN (KEYWORD, LOCATION)",
        tok,
    )
    total_neg = 0
    total_loc = 0
    by_camp: dict[str, dict[str, int]] = {}
    for r in rows:
        cc = r["campaignCriterion"]
        camp = cc["campaign"].split("/")[-1]
        t = cc["type"]
        if t == "KEYWORD" and cc.get("negative"):
            total_neg += 1
            by_camp.setdefault(camp, {"negatives": 0, "locations": 0})["negatives"] += 1
        elif t == "LOCATION":
            total_loc += 1
            by_camp.setdefault(camp, {"negatives": 0, "locations": 0})["locations"] += 1
    for camp, counts in by_camp.items():
        print(f"  campaign {camp}: {counts['negatives']} neg keywords, {counts['locations']} locations")
    print(f"  TOTAL: {total_neg} negative keywords across all campaigns, {total_loc} location criteria")

    print("\n=== MERCHANT CENTER LINK ===")
    try:
        rows = search(
            "SELECT merchant_center_link.id, merchant_center_link.merchant_center_id, "
            "merchant_center_link.status "
            "FROM merchant_center_link",
            tok,
        )
        for r in rows:
            m = r["merchantCenterLink"]
            print(f"  id={m['id']} mc_id={m['merchantCenterId']} status={m['status']}")
    except Exception as e:
        print(f"  (query failed: {e})")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
