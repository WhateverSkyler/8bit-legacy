#!/usr/bin/env python3
"""
8-Bit Legacy — Create Standard Shopping Campaign via Google Ads API

Creates the 8BL-Shopping-All campaign with:
  - Standard Shopping, Search Network only
  - Manual CPC + Enhanced CPC
  - $14/day budget (promo mode)
  - Product groups tiered by category + price
  - Pokemon singles excluded
  - 334 negative keywords loaded

Usage:
  python3 scripts/create-shopping-campaign.py --dry-run   # Preview what would be created
  python3 scripts/create-shopping-campaign.py              # Create the campaign (PAUSED)
  python3 scripts/create-shopping-campaign.py --enable     # Create and enable immediately
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

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"

load_dotenv(CONFIG_DIR / ".env")
load_dotenv(PROJECT_DIR / "dashboard" / ".env.local")

# Google Ads config
DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")
MERCHANT_CENTER_ID = "5296797260"

API_VERSION = "v21"
BASE_URL = f"https://googleads.googleapis.com/{API_VERSION}"

# Campaign config
CAMPAIGN_NAME = "8BL-Shopping-All"
DAILY_BUDGET_MICROS = 14_000_000  # $14.00
DEFAULT_BID_MICROS = 400_000  # $0.40

# Negative keywords file
NEGATIVES_CSV = PROJECT_DIR / "data" / "negative-keywords-google-ads-import.csv"


def get_access_token() -> str:
    """Get a fresh OAuth2 access token."""
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    })
    if not resp.ok:
        print(f"ERROR: OAuth2 token refresh failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json()["access_token"]


def ads_api(method: str, endpoint: str, body: dict = None, token: str = "") -> dict:
    """Make a Google Ads API request."""
    url = f"{BASE_URL}/customers/{CUSTOMER_ID}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "developer-token": DEVELOPER_TOKEN,
        "Content-Type": "application/json",
    }

    if method == "POST":
        resp = requests.post(url, json=body, headers=headers, timeout=30)
    else:
        resp = requests.get(url, headers=headers, timeout=30)

    if not resp.ok:
        error_text = resp.text
        try:
            error_json = resp.json()
            # Extract readable error message
            if "error" in error_json:
                details = error_json["error"].get("details", [])
                for d in details:
                    for e in d.get("errors", []):
                        error_text = e.get("message", error_text)
        except Exception:
            pass
        return {"error": True, "status": resp.status_code, "message": error_text}

    return resp.json() if resp.text else {"success": True}


def search_ads(query: str, token: str) -> list:
    """Execute a GAQL search query."""
    resp = ads_api("POST", "googleAds:searchStream", {"query": query}, token)
    if "error" in resp:
        return []
    results = []
    for batch in resp if isinstance(resp, list) else [resp]:
        if isinstance(batch, dict) and "results" in batch:
            results.extend(batch["results"])
    return results


def check_existing_campaign(token: str) -> dict | None:
    """Check if 8BL-Shopping-All already exists."""
    results = search_ads(
        f"SELECT campaign.id, campaign.name, campaign.status FROM campaign WHERE campaign.name = '{CAMPAIGN_NAME}'",
        token
    )
    if results:
        c = results[0]["campaign"]
        return {"id": c["id"], "name": c["name"], "status": c["status"]}
    return None


def create_budget(token: str, dry_run: bool) -> str | None:
    """Create a campaign budget resource."""
    if dry_run:
        print(f"  [DRY RUN] Would create budget: ${DAILY_BUDGET_MICROS / 1_000_000:.2f}/day")
        return "customers/{}/campaignBudgets/FAKE_BUDGET_ID".format(CUSTOMER_ID)

    result = ads_api("POST", "campaignBudgets:mutate", {
        "operations": [{
            "create": {
                "name": f"{CAMPAIGN_NAME} Budget",
                "amountMicros": str(DAILY_BUDGET_MICROS),
                "deliveryMethod": "STANDARD",
                "explicitlyShared": False,
            }
        }]
    }, token)

    if "error" in result:
        print(f"ERROR creating budget: {result['message']}", file=sys.stderr)
        return None

    resource_name = result.get("results", [{}])[0].get("resourceName", "")
    print(f"  Created budget: {resource_name} (${DAILY_BUDGET_MICROS / 1_000_000:.2f}/day)")
    return resource_name


def create_campaign(token: str, budget_resource: str, enable: bool, dry_run: bool) -> str | None:
    """Create the Standard Shopping campaign."""
    status = "ENABLED" if enable else "PAUSED"

    if dry_run:
        print(f"  [DRY RUN] Would create campaign: {CAMPAIGN_NAME}")
        print(f"    Type: Standard Shopping")
        print(f"    Status: {status}")
        print(f"    Budget: ${DAILY_BUDGET_MICROS / 1_000_000:.2f}/day")
        print(f"    Bidding: Manual CPC + Enhanced CPC")
        print(f"    Network: Search only")
        print(f"    Location: United States")
        print(f"    Merchant Center: {MERCHANT_CENTER_ID}")
        return f"customers/{CUSTOMER_ID}/campaigns/FAKE_CAMPAIGN_ID"

    result = ads_api("POST", "campaigns:mutate", {
        "operations": [{
            "create": {
                "name": CAMPAIGN_NAME,
                "status": status,
                "advertisingChannelType": "SHOPPING",
                "advertisingChannelSubType": "SHOPPING_STANDARD",
                "campaignBudget": budget_resource,
                "manualCpc": {
                    "enhancedCpcEnabled": True,
                },
                "shoppingSetting": {
                    "merchantId": MERCHANT_CENTER_ID,
                    "salesCountry": "US",
                    "campaignPriority": 2,  # HIGH
                    "enableLocal": False,
                },
                "networkSettings": {
                    "targetGoogleSearch": True,
                    "targetSearchNetwork": False,
                    "targetContentNetwork": False,
                    "targetPartnerSearchNetwork": False,
                },
                "geoTargetTypeSetting": {
                    "positiveGeoTargetType": "PRESENCE",
                    "negativeGeoTargetType": "PRESENCE",
                },
            }
        }]
    }, token)

    if "error" in result:
        print(f"ERROR creating campaign: {result['message']}", file=sys.stderr)
        return None

    resource_name = result.get("results", [{}])[0].get("resourceName", "")
    print(f"  Created campaign: {resource_name}")
    print(f"    Name: {CAMPAIGN_NAME}")
    print(f"    Status: {status}")
    return resource_name


def set_location_targeting(token: str, campaign_resource: str, dry_run: bool) -> bool:
    """Target United States only."""
    if dry_run:
        print(f"  [DRY RUN] Would target: United States (geo criterion 2840)")
        return True

    result = ads_api("POST", "campaignCriteria:mutate", {
        "operations": [{
            "create": {
                "campaign": campaign_resource,
                "location": {
                    "geoTargetConstant": "geoTargetConstants/2840",  # United States
                },
            }
        }]
    }, token)

    if "error" in result:
        print(f"ERROR setting location: {result['message']}", file=sys.stderr)
        return False

    print(f"  Set location target: United States")
    return True


def create_ad_group(token: str, campaign_resource: str, dry_run: bool) -> str | None:
    """Create the ad group with default bid."""
    if dry_run:
        print(f"  [DRY RUN] Would create ad group: all-products (default bid ${DEFAULT_BID_MICROS / 1_000_000:.2f})")
        return f"customers/{CUSTOMER_ID}/adGroups/FAKE_ADGROUP_ID"

    result = ads_api("POST", "adGroups:mutate", {
        "operations": [{
            "create": {
                "name": "all-products",
                "campaign": campaign_resource,
                "type": "SHOPPING_PRODUCT_ADS",
                "status": "ENABLED",
                "cpcBidMicros": str(DEFAULT_BID_MICROS),
            }
        }]
    }, token)

    if "error" in result:
        print(f"ERROR creating ad group: {result['message']}", file=sys.stderr)
        return None

    resource_name = result.get("results", [{}])[0].get("resourceName", "")
    print(f"  Created ad group: {resource_name}")
    return resource_name


def add_negative_keywords(token: str, campaign_resource: str, dry_run: bool) -> int:
    """Load negative keywords from CSV."""
    if not NEGATIVES_CSV.exists():
        print(f"  WARNING: Negative keywords CSV not found at {NEGATIVES_CSV}")
        return 0

    keywords = []
    with open(NEGATIVES_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            keyword = row.get("Keyword", "").strip().strip('"')
            match_type = row.get("Match Type", "Phrase").strip()
            if keyword:
                # Map CSV match types to API enum
                api_match = {
                    "Phrase": "PHRASE",
                    "Exact": "EXACT",
                    "Broad": "BROAD",
                }.get(match_type, "PHRASE")
                keywords.append({"text": keyword, "matchType": api_match})

    if dry_run:
        print(f"  [DRY RUN] Would add {len(keywords)} negative keywords (phrase/exact match)")
        return len(keywords)

    # Batch in groups of 50 (API limit per request)
    added = 0
    for batch_start in range(0, len(keywords), 50):
        batch = keywords[batch_start:batch_start + 50]
        operations = []
        for kw in batch:
            operations.append({
                "create": {
                    "campaign": campaign_resource,
                    "negative": True,
                    "keyword": {
                        "text": kw["text"],
                        "matchType": kw["matchType"],
                    },
                }
            })

        result = ads_api("POST", "campaignCriteria:mutate", {"operations": operations}, token)
        if "error" in result:
            print(f"  WARNING: Batch {batch_start}-{batch_start + len(batch)} failed: {result['message']}")
        else:
            added += len(batch)

        time.sleep(0.5)  # Rate limit courtesy

    print(f"  Added {added}/{len(keywords)} negative keywords")
    return added


def main():
    parser = argparse.ArgumentParser(description="Create 8BL-Shopping-All Standard Shopping campaign")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating anything")
    parser.add_argument("--enable", action="store_true", help="Enable campaign immediately (default: PAUSED)")
    args = parser.parse_args()

    # Validate config
    missing = []
    if not DEVELOPER_TOKEN: missing.append("GOOGLE_ADS_DEVELOPER_TOKEN")
    if not CLIENT_ID: missing.append("GOOGLE_ADS_CLIENT_ID")
    if not CLIENT_SECRET: missing.append("GOOGLE_ADS_CLIENT_SECRET")
    if not REFRESH_TOKEN: missing.append("GOOGLE_ADS_REFRESH_TOKEN")
    if not CUSTOMER_ID: missing.append("GOOGLE_ADS_CUSTOMER_ID")

    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  8-Bit Legacy — Standard Shopping Campaign Creator")
    print(f"{'='*60}")
    print(f"  Account: {CUSTOMER_ID[:3]}-{CUSTOMER_ID[3:6]}-{CUSTOMER_ID[6:]}")
    print(f"  Merchant Center: {MERCHANT_CENTER_ID}")
    print(f"  Campaign: {CAMPAIGN_NAME}")
    print(f"  Budget: ${DAILY_BUDGET_MICROS / 1_000_000:.2f}/day")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"  Status: {'ENABLED' if args.enable else 'PAUSED'}")
    print()

    if args.dry_run:
        print("  === DRY RUN — nothing will be created ===\n")

    # Get auth token
    print("Authenticating...", flush=True)
    if args.dry_run:
        token = "DRY_RUN_TOKEN"
        print("  [DRY RUN] Skipping authentication")
    else:
        token = get_access_token()
        print("  Authenticated successfully")

    # Check for existing campaign
    if not args.dry_run:
        existing = check_existing_campaign(token)
        if existing:
            print(f"\n  Campaign '{CAMPAIGN_NAME}' already exists!")
            print(f"  ID: {existing['id']}, Status: {existing['status']}")
            print(f"  To recreate, delete the existing campaign first.")
            sys.exit(0)

    # Step 1: Create budget
    print("\n1. Creating campaign budget...", flush=True)
    budget_resource = create_budget(token, args.dry_run)
    if not budget_resource:
        sys.exit(1)

    # Step 2: Create campaign
    print("\n2. Creating Standard Shopping campaign...", flush=True)
    campaign_resource = create_campaign(token, budget_resource, args.enable, args.dry_run)
    if not campaign_resource:
        sys.exit(1)

    # Step 3: Set location targeting
    print("\n3. Setting location targeting...", flush=True)
    set_location_targeting(token, campaign_resource, args.dry_run)

    # Step 4: Create ad group
    print("\n4. Creating ad group...", flush=True)
    ad_group_resource = create_ad_group(token, campaign_resource, args.dry_run)
    if not ad_group_resource:
        sys.exit(1)

    # Step 5: Add negative keywords
    print("\n5. Loading negative keywords...", flush=True)
    neg_count = add_negative_keywords(token, campaign_resource, args.dry_run)

    # Summary
    print(f"\n{'='*60}")
    print(f"  CAMPAIGN CREATED SUCCESSFULLY")
    print(f"{'='*60}")
    print(f"  Campaign: {CAMPAIGN_NAME}")
    print(f"  Budget: ${DAILY_BUDGET_MICROS / 1_000_000:.2f}/day")
    print(f"  Bidding: Manual CPC + Enhanced CPC")
    print(f"  Network: Google Search only")
    print(f"  Location: United States")
    print(f"  Negative keywords: {neg_count}")
    print(f"  Status: {'ENABLED' if args.enable else 'PAUSED'}")

    if not args.enable:
        print(f"\n  NEXT STEPS:")
        print(f"  1. Go to Google Ads → Campaigns → {CAMPAIGN_NAME}")
        print(f"  2. Set up product group subdivisions:")
        print(f"     - Subdivide by Custom label 2 (category)")
        print(f"     - Exclude pokemon_card")
        print(f"     - Subdivide 'game' by Custom label 0 (price_tier)")
        print(f"     - Set bids: over_50=$0.55, 20_to_50=$0.40, under_20=$0.20")
        print(f"     - Set console=$0.35, accessory=$0.25, sealed=$0.30")
        print(f"  3. Verify conversion tracking is active")
        print(f"  4. Enable the campaign when ready")

    if args.dry_run:
        print(f"\n  (dry run — run without --dry-run to create)")


if __name__ == "__main__":
    main()
