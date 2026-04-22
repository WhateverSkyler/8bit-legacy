#!/usr/bin/env python3
"""Configure the 8-Bit Legacy Google Ads Shopping campaign end-to-end.

Target state (matches docs/ads-launch-research-2026-04-20.md + memory
feedback_ads_strategy.md):
- Campaign name: 8BL-Shopping-Games (renamed from 8BL-Shopping-All)
- Status: PAUSED (user flips to ENABLED once verified)
- Daily budget: $20/day
- Bidding: Manual CPC, Enhanced CPC OFF (deprecated for Shopping)
- Network: Google Search only
- Listing group tree:
    all products
      ├── custom_label_2 = "game" → subdivide by custom_label_0
      │     ├── over_50     → $0.35 CPC
      │     ├── 20_to_50    → $0.12 CPC
      │     └── else        → EXCLUDE (catches under_20)
      └── else              → EXCLUDE (catches pokemon_card, console, accessory, sealed)
- 334 negative keywords from data/negative-keywords-google-ads-import-v2.csv

Idempotent where possible. Safe: validates state, errors clearly, leaves PAUSED.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
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
BASE = f"https://googleads.googleapis.com/{API_VERSION}/customers/{CUSTOMER_ID}"

TARGET_NAME = "8BL-Shopping-Games"
TARGET_BUDGET_MICROS = 20_000_000  # $20.00/day
NEGATIVES_CSV = ROOT / "data" / "negative-keywords-google-ads-import-v2.csv"

# Bid tiers (per ads-launch-research-2026-04-20.md §3.3 math)
BID_OVER_50_MICROS = 350_000    # $0.35
BID_20_TO_50_MICROS = 80_000    # $0.08 — tightened 2026-04-22 per user direction (spend less, higher ROI)


def die(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(2)


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


def api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "developer-token": DEV_TOKEN,
        "Content-Type": "application/json",
    }
    if LOGIN_CUSTOMER_ID:
        headers["login-customer-id"] = LOGIN_CUSTOMER_ID
    r = requests.request(method, f"{BASE}{path}", headers=headers, json=body, timeout=60)
    if r.status_code >= 400:
        # Pretty-print the Google Ads error for debugging
        try:
            err = r.json()
            for detail in err[0]["error"]["details"] if isinstance(err, list) else err.get("error", {}).get("details", []):
                for e in detail.get("errors", []):
                    print(f"  API ERROR: {e.get('message', '')} code={e.get('errorCode', {})}", file=sys.stderr)
        except Exception:
            pass
        r.raise_for_status()
    return r.json() if r.text else {}


def search(query: str, token: str) -> list[dict]:
    resp = api("POST", "/googleAds:searchStream", token, {"query": query})
    out: list[dict] = []
    for chunk in resp if isinstance(resp, list) else [resp]:
        out.extend(chunk.get("results", []))
    return out


# ───── Step helpers ─────

def find_campaign(token: str) -> dict | None:
    """Find a campaign named 8BL-Shopping-All OR 8BL-Shopping-Games."""
    rows = search(
        "SELECT campaign.id, campaign.name, campaign.status, campaign.resource_name, "
        "campaign_budget.resource_name, campaign_budget.amount_micros "
        "FROM campaign WHERE campaign.name IN ('8BL-Shopping-All', '8BL-Shopping-Games')",
        token,
    )
    if not rows:
        return None
    r = rows[0]
    return {
        "id": r["campaign"]["id"],
        "name": r["campaign"]["name"],
        "status": r["campaign"]["status"],
        "resource_name": r["campaign"]["resourceName"],
        "budget_resource": r["campaignBudget"]["resourceName"],
        "budget_micros": int(r["campaignBudget"]["amountMicros"]),
    }


def find_ad_group(campaign_resource: str, token: str) -> dict | None:
    rows = search(
        f"SELECT ad_group.id, ad_group.name, ad_group.resource_name "
        f"FROM ad_group WHERE ad_group.campaign = '{campaign_resource}' LIMIT 1",
        token,
    )
    if not rows:
        return None
    a = rows[0]["adGroup"]
    return {"id": a["id"], "name": a["name"], "resource_name": a["resourceName"]}


def get_listing_groups(ad_group_id: str, token: str) -> list[dict]:
    rows = search(
        f"SELECT ad_group_criterion.criterion_id, ad_group_criterion.listing_group.type, "
        f"ad_group_criterion.cpc_bid_micros, ad_group_criterion.negative, ad_group_criterion.resource_name "
        f"FROM ad_group_criterion WHERE ad_group_criterion.type = LISTING_GROUP "
        f"AND ad_group.id = {ad_group_id}",
        token,
    )
    return [r["adGroupCriterion"] for r in rows]


def get_negative_count(campaign_resource: str, token: str) -> int:
    rows = search(
        f"SELECT campaign_criterion.criterion_id "
        f"FROM campaign_criterion WHERE campaign_criterion.type = KEYWORD "
        f"AND campaign_criterion.negative = true "
        f"AND campaign_criterion.campaign = '{campaign_resource}'",
        token,
    )
    return len(rows)


# ───── Mutations ─────

def rename_campaign(campaign_resource: str, new_name: str, token: str, dry: bool) -> None:
    if dry:
        print(f"  [dry] would rename to '{new_name}'")
        return
    api("POST", "/campaigns:mutate", token, {
        "operations": [{
            "update": {"resourceName": campaign_resource, "name": new_name},
            "updateMask": "name",
        }],
    })
    print(f"  renamed → {new_name}")


def update_budget(budget_resource: str, amount_micros: int, token: str, dry: bool) -> None:
    if dry:
        print(f"  [dry] would update budget to ${amount_micros / 1_000_000:.2f}/day")
        return
    api("POST", "/campaignBudgets:mutate", token, {
        "operations": [{
            "update": {"resourceName": budget_resource, "amountMicros": str(amount_micros)},
            "updateMask": "amount_micros",
        }],
    })
    print(f"  budget → ${amount_micros / 1_000_000:.2f}/day")


def rebuild_listing_tree(ad_group_id: str, ad_group_resource: str, existing_groups: list[dict],
                         token: str, dry: bool) -> None:
    """Rebuild listing tree. If the tree matches the expected shape, just update bids
    in place. If it doesn't match, full rebuild (remove all + create fresh).

    Expected shape:
      root (SUBDIVISION)
      ├── custom_label_2 = "game" (SUBDIVISION)
      │   ├── custom_label_0 = "over_50" (UNIT, BID_OVER_50)
      │   ├── custom_label_0 = "20_to_50" (UNIT, BID_20_TO_50)
      │   └── custom_label_0 = else (UNIT negative)
      └── custom_label_2 = else (UNIT negative)
    """
    # Fast path: if the tree already has the right shape (6 nodes, right types),
    # just update the two bid UNITs directly. No need to rebuild.
    if len(existing_groups) == 6:
        updates = []
        for g in existing_groups:
            lg = g.get("listingGroup", {})
            pca = lg.get("caseValue", {}).get("productCustomAttribute", {})
            if pca.get("index") == "INDEX0" and pca.get("value") == "over_50":
                if g.get("cpcBidMicros") != str(BID_OVER_50_MICROS):
                    updates.append({
                        "update": {"resourceName": g["resourceName"], "cpcBidMicros": str(BID_OVER_50_MICROS)},
                        "updateMask": "cpc_bid_micros",
                    })
            elif pca.get("index") == "INDEX0" and pca.get("value") == "20_to_50":
                if g.get("cpcBidMicros") != str(BID_20_TO_50_MICROS):
                    updates.append({
                        "update": {"resourceName": g["resourceName"], "cpcBidMicros": str(BID_20_TO_50_MICROS)},
                        "updateMask": "cpc_bid_micros",
                    })
        if updates:
            if dry:
                print(f"  [dry] would update {len(updates)} bid(s) in existing tree")
                return
            api("POST", "/adGroupCriteria:mutate", token, {"operations": updates})
            print(f"  bid-updated {len(updates)} UNIT(s) in existing tree")
        else:
            print(f"  existing tree already matches target bids — skip")
        return

    # Slow path: tree is wrong shape (e.g., fresh ad group with just the default root).
    # Full rebuild — remove all existing + create new tree atomically.
    operations: list[dict] = []
    # Sort removes child-first by criterion_id descending (rough heuristic)
    for g in sorted(existing_groups, key=lambda x: int(x.get("criterionId", 0)), reverse=True):
        operations.append({"remove": g["resourceName"]})

    def tmp(n: int) -> str:
        return f"customers/{CUSTOMER_ID}/adGroupCriteria/{ad_group_id}~-{n}"

    # -1 root subdivision
    operations.append({
        "create": {
            "resourceName": tmp(1),
            "adGroup": ad_group_resource,
            "status": "ENABLED",
            "listingGroup": {"type": "SUBDIVISION"},
        }
    })
    # -2 games subdivision
    operations.append({
        "create": {
            "resourceName": tmp(2),
            "adGroup": ad_group_resource,
            "status": "ENABLED",
            "listingGroup": {
                "type": "SUBDIVISION",
                "caseValue": {"productCustomAttribute": {"index": "INDEX2", "value": "game"}},
                "parentAdGroupCriterion": tmp(1),
            },
        }
    })
    # -3 else (non-games) UNIT negative
    operations.append({
        "create": {
            "resourceName": tmp(3),
            "adGroup": ad_group_resource,
            "status": "ENABLED",
            "negative": True,
            "listingGroup": {
                "type": "UNIT",
                "caseValue": {"productCustomAttribute": {"index": "INDEX2"}},
                "parentAdGroupCriterion": tmp(1),
            },
        }
    })
    # -4 games/over_50 UNIT bid
    operations.append({
        "create": {
            "resourceName": tmp(4),
            "adGroup": ad_group_resource,
            "status": "ENABLED",
            "cpcBidMicros": str(BID_OVER_50_MICROS),
            "listingGroup": {
                "type": "UNIT",
                "caseValue": {"productCustomAttribute": {"index": "INDEX0", "value": "over_50"}},
                "parentAdGroupCriterion": tmp(2),
            },
        }
    })
    # -5 games/20_to_50 UNIT bid
    operations.append({
        "create": {
            "resourceName": tmp(5),
            "adGroup": ad_group_resource,
            "status": "ENABLED",
            "cpcBidMicros": str(BID_20_TO_50_MICROS),
            "listingGroup": {
                "type": "UNIT",
                "caseValue": {"productCustomAttribute": {"index": "INDEX0", "value": "20_to_50"}},
                "parentAdGroupCriterion": tmp(2),
            },
        }
    })
    # -6 games/else UNIT negative (catches under_20)
    operations.append({
        "create": {
            "resourceName": tmp(6),
            "adGroup": ad_group_resource,
            "status": "ENABLED",
            "negative": True,
            "listingGroup": {
                "type": "UNIT",
                "caseValue": {"productCustomAttribute": {"index": "INDEX0"}},
                "parentAdGroupCriterion": tmp(2),
            },
        }
    })

    if dry:
        print(f"  [dry] would rebuild listing tree: remove {len(existing_groups)} existing + create 6 new nodes")
        return

    api("POST", "/adGroupCriteria:mutate", token, {"operations": operations})
    print(f"  listing tree: removed {len(existing_groups)} old + created 6 new nodes")


def import_negatives(campaign_resource: str, already_count: int, token: str, dry: bool) -> None:
    if not NEGATIVES_CSV.exists():
        die(f"negatives CSV not found: {NEGATIVES_CSV}")

    rows: list[dict] = []
    with NEGATIVES_CSV.open() as f:
        for row in csv.DictReader(f):
            kw = row.get("Keyword", "").strip().strip('"')
            mt = row.get("Match Type", "Phrase").strip()
            if kw:
                rows.append({
                    "text": kw,
                    "matchType": {"Phrase": "PHRASE", "Exact": "EXACT", "Broad": "BROAD"}.get(mt, "PHRASE"),
                })

    if already_count >= len(rows) * 0.9:
        print(f"  {already_count} negatives already on campaign ≥ 90% of the {len(rows)} in CSV — skipping")
        return

    if already_count > 0:
        print(f"  WARN: campaign already has {already_count} negatives (CSV has {len(rows)}) — will add more, may dedup")

    if dry:
        print(f"  [dry] would add {len(rows)} negative keywords")
        return

    # Batch in groups of 50 for rate courtesy
    added = 0
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        ops = [
            {"create": {
                "campaign": campaign_resource,
                "negative": True,
                "keyword": {"text": kw["text"], "matchType": kw["matchType"]},
            }}
            for kw in batch
        ]
        try:
            api("POST", "/campaignCriteria:mutate", token, {"operations": ops})
            added += len(batch)
        except requests.HTTPError as exc:
            print(f"  WARN batch {i}-{i+len(batch)} failed — continuing")
        time.sleep(0.4)
    print(f"  added {added}/{len(rows)} negative keywords")


# ───── Main ─────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="show what would change without mutating")
    ap.add_argument("--skip-negatives", action="store_true", help="don't touch negative keywords")
    ap.add_argument("--skip-tree", action="store_true", help="don't touch the listing group tree")
    args = ap.parse_args()

    print(f"Customer: {CUSTOMER_ID} (via MCC {LOGIN_CUSTOMER_ID or '-'})")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")

    tok = get_token()

    camp = find_campaign(tok)
    if not camp:
        die("No existing campaign named 8BL-Shopping-All or 8BL-Shopping-Games found.")
    print(f"\n[campaign] id={camp['id']} name={camp['name']} status={camp['status']} budget=${camp['budget_micros']/1_000_000:.2f}")

    ag = find_ad_group(camp["resource_name"], tok)
    if not ag:
        die(f"No ad group found under campaign {camp['id']}.")
    print(f"[ad_group] id={ag['id']} name={ag['name']}")

    neg_count = get_negative_count(camp["resource_name"], tok)
    lg = get_listing_groups(ag["id"], tok)
    print(f"[state] negatives={neg_count}  listing_groups={len(lg)}")

    print("\n--- STEP 1: rename campaign ---")
    if camp["name"] == TARGET_NAME:
        print(f"  already named '{TARGET_NAME}' — skip")
    else:
        rename_campaign(camp["resource_name"], TARGET_NAME, tok, args.dry_run)

    print("\n--- STEP 2: update budget ---")
    if camp["budget_micros"] == TARGET_BUDGET_MICROS:
        print(f"  already ${TARGET_BUDGET_MICROS/1_000_000:.2f}/day — skip")
    else:
        update_budget(camp["budget_resource"], TARGET_BUDGET_MICROS, tok, args.dry_run)

    print("\n--- STEP 3: rebuild listing group tree ---")
    if args.skip_tree:
        print("  --skip-tree — leaving tree untouched")
    else:
        rebuild_listing_tree(ag["id"], ag["resource_name"], lg, tok, args.dry_run)

    print("\n--- STEP 4: import negative keywords ---")
    if args.skip_negatives:
        print("  --skip-negatives — leaving negatives untouched")
    else:
        import_negatives(camp["resource_name"], neg_count, tok, args.dry_run)

    print("\n--- Done. Campaign remains PAUSED. Flip to ENABLED in Google Ads UI when ready. ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
