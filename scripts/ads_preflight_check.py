#!/usr/bin/env python3
"""Pre-launch health check for 8BL-Shopping-Games. Runs every box I can check
automatically, produces a pass/fail summary. Run this anytime you want to
confirm the campaign is in the expected shape before flipping to ENABLED.
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
SHOPIFY_URL = os.environ.get("SHOPIFY_STORE_URL")
SHOPIFY_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")


def get_ads_token() -> str:
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN, "grant_type": "refresh_token",
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def ads_query(sql: str, token: str) -> list:
    H = {"Authorization": f"Bearer {token}", "developer-token": DEV_TOKEN,
         "Content-Type": "application/json"}
    if LOGIN_CUSTOMER_ID:
        H["login-customer-id"] = LOGIN_CUSTOMER_ID
    r = requests.post(
        f"https://googleads.googleapis.com/v21/customers/{CUSTOMER_ID}/googleAds:searchStream",
        headers=H, json={"query": sql}, timeout=30,
    )
    if r.status_code >= 400:
        return []
    out = []
    for chunk in r.json() if isinstance(r.json(), list) else [r.json()]:
        out.extend(chunk.get("results", []))
    return out


def shop_query(query: str, variables: dict | None = None) -> dict:
    r = requests.post(
        f"https://{SHOPIFY_URL}/admin/api/2025-01/graphql.json",
        headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}}, timeout=30,
    )
    return r.json()


def main() -> int:
    tok = get_ads_token()
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))

    # 1) Exactly one campaign, correct name + status
    rows = ads_query("SELECT campaign.id, campaign.name, campaign.status FROM campaign", tok)
    campaign_ok = (len(rows) == 1 and rows[0]["campaign"]["name"] == "8BL-Shopping-Games")
    check("Only the intended campaign exists", campaign_ok,
          f"{len(rows)} campaign(s)")
    check("Campaign status is PAUSED", rows and rows[0]["campaign"]["status"] == "PAUSED",
          f"status={rows[0]['campaign']['status']}" if rows else "")

    # 2) Listing tree
    rows = ads_query(
        "SELECT ad_group_criterion.criterion_id, ad_group_criterion.listing_group.type, "
        "ad_group_criterion.listing_group.case_value.product_custom_attribute.index, "
        "ad_group_criterion.listing_group.case_value.product_custom_attribute.value, "
        "ad_group_criterion.cpc_bid_micros, ad_group_criterion.negative "
        "FROM ad_group_criterion WHERE ad_group_criterion.type = LISTING_GROUP "
        "AND ad_group.id = 202385540384", tok)
    tree = {}
    for row in rows:
        ac = row["adGroupCriterion"]
        lg = ac.get("listingGroup", {})
        pca = lg.get("caseValue", {}).get("productCustomAttribute", {})
        key = f"{pca.get('index', 'ROOT')}={pca.get('value', '_else_')}" if pca else "ROOT"
        tree[key] = (lg.get("type"), int(ac.get("cpcBidMicros", 0)), ac.get("negative", False))
    expected = {
        "ROOT": ("SUBDIVISION", None, False),
        "INDEX2=_else_": ("UNIT", 0, True),
        "INDEX2=game": ("SUBDIVISION", 0, False),
        "INDEX0=_else_": ("UNIT", 0, True),
        "INDEX0=20_to_50": ("UNIT", 80000, False),
        "INDEX0=over_50": ("UNIT", 350000, False),
    }
    tree_ok = True
    mismatches = []
    for k, e in expected.items():
        a = tree.get(k)
        if not a or e[0] != a[0] or (e[1] is not None and e[1] != a[1]) or e[2] != a[2]:
            tree_ok = False
            mismatches.append(k)
    check("Listing tree matches plan", tree_ok, "; ".join(mismatches) or "6 nodes OK")

    # 3) Negative keywords
    rows = ads_query(
        "SELECT campaign_criterion.criterion_id FROM campaign_criterion "
        "WHERE campaign_criterion.type = KEYWORD AND campaign_criterion.negative = true", tok)
    check("Negative keywords imported (≥334)", len(rows) >= 334, f"actual={len(rows)}")

    # 4) Network + bidding settings
    rows = ads_query(
        "SELECT campaign.network_settings.target_google_search, "
        "campaign.network_settings.target_search_network, "
        "campaign.network_settings.target_content_network, "
        "campaign.manual_cpc.enhanced_cpc_enabled, campaign.shopping_setting.merchant_id "
        "FROM campaign WHERE campaign.id = 23766662629", tok)
    if rows:
        c = rows[0]["campaign"]
        check("Google Search ON", c["networkSettings"].get("targetGoogleSearch") is True)
        check("Search Partners OFF", c["networkSettings"].get("targetSearchNetwork") is False)
        check("Display OFF", c["networkSettings"].get("targetContentNetwork") is False)
        check("Enhanced CPC OFF", c.get("manualCpc", {}).get("enhancedCpcEnabled") is False)
        check("Merchant Center linked (5296797260)",
              c["shoppingSetting"].get("merchantId") == "5296797260")

    # 5) Budget
    rows = ads_query(
        "SELECT campaign.id, campaign_budget.amount_micros, campaign_budget.explicitly_shared "
        "FROM campaign WHERE campaign.id = 23766662629", tok)
    if rows:
        b = rows[0]["campaignBudget"]
        check("Budget = $20/day", int(b["amountMicros"]) == 20_000_000,
              f"${int(b['amountMicros'])/1_000_000:.2f}")
        check("Budget dedicated (not shared)", b.get("explicitlyShared", False) is False)

    # 6) Geo targeting
    rows = ads_query(
        "SELECT campaign_criterion.criterion_id, campaign_criterion.location.geo_target_constant "
        "FROM campaign_criterion WHERE campaign_criterion.type = LOCATION", tok)
    check("US-only geo targeting",
          len(rows) == 1 and rows[0]["campaignCriterion"]["location"]["geoTargetConstant"].endswith("/2840"),
          f"{len(rows)} location(s)")

    # 7) Conversion actions
    rows = ads_query(
        "SELECT conversion_action.name, conversion_action.status, conversion_action.primary_for_goal "
        "FROM conversion_action WHERE conversion_action.name LIKE 'Google Shopping App%'", tok)
    active_primary = sum(1 for r in rows
                          if r["conversionAction"]["status"] == "ENABLED"
                          and r["conversionAction"].get("primaryForGoal"))
    check("All 7 Shopping App conversion actions enabled+primary", active_primary == 7,
          f"{active_primary}/7")

    # 8) Tag freshness — spot-check 10 over_50-tagged products
    if SHOPIFY_URL and SHOPIFY_TOKEN:
        resp = shop_query(
            'query { products(first:10, query:"tag:\\"price_tier:over_50\\"") '
            '{ edges { node { title priceRangeV2 { minVariantPrice { amount } } } } } }')
        edges = resp.get("data", {}).get("products", {}).get("edges", [])
        drifted = sum(1 for e in edges
                      if float(e["node"]["priceRangeV2"]["minVariantPrice"]["amount"]) < 50)
        check("Over_50 tag accuracy (sample of 10)", drifted == 0,
              f"{drifted}/{len(edges)} drifted below $50" if drifted else "all $50+")

    # 9) Store reachability — homepage + 3 Winners
    urls = [
        "https://8bitlegacy.com/",
        "https://8bitlegacy.com/products/galerians-ps1-game",
        "https://8bitlegacy.com/products/mystical-ninja-starring-goemon-nintendo-64-game",
        "https://8bitlegacy.com/products/silent-hill-2-ps2-game",
    ]
    for u in urls:
        try:
            r = requests.get(u, timeout=10)
            check(f"Reachable: {u.replace('https://8bitlegacy.com','')}", r.status_code == 200,
                  f"HTTP {r.status_code}")
        except Exception as ex:
            check(f"Reachable: {u}", False, str(ex))

    # Summary
    print("\n" + "=" * 70)
    print("  PRE-LAUNCH HEALTH CHECK")
    print("=" * 70)
    fails = []
    for name, ok, detail in results:
        mark = "✅" if ok else "❌"
        extra = f"  · {detail}" if detail else ""
        print(f"  {mark} {name}{extra}")
        if not ok:
            fails.append(name)
    print(f"\n  {len(results) - len(fails)} pass / {len(fails)} fail")
    if fails:
        print("\n  Failed checks:")
        for f in fails:
            print(f"    - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
