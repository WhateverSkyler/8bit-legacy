#!/usr/bin/env python3
"""
Fix CIB (Complete In Box) variant inventory for all active products.
Sets CIB variant available quantity to 10000 to match Game Only variants.
Uses Shopify Admin REST API.

Run from the project root:
    python3 scripts/fix-cib-inventory.py

Or with --dry-run to preview changes:
    python3 scripts/fix-cib-inventory.py --dry-run
"""

import requests
import json
import time
import sys
import os

# Load from dashboard .env.local
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / "dashboard" / ".env.local")
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

SHOP_URL = os.getenv("SHOPIFY_STORE_URL", "")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"

if not SHOP_URL or not ACCESS_TOKEN:
    print("ERROR: Set SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN in dashboard/.env.local")
    sys.exit(1)

HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

BASE_URL = f"https://{SHOP_URL}/admin/api/{API_VERSION}"
DRY_RUN = "--dry-run" in sys.argv


def get_all_products():
    """Fetch all active products with variants."""
    products = []
    url = f"{BASE_URL}/products.json?status=active&limit=250"

    while url:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        products.extend(data.get("products", []))

        # Check for pagination via Link header
        link_header = resp.headers.get("Link", "")
        url = None
        if 'rel="next"' in link_header:
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    url = part.split("<")[1].split(">")[0]

        print(f"  Fetched {len(products)} products so far...")
        time.sleep(0.5)

    return products


def get_locations():
    """Get all locations."""
    url = f"{BASE_URL}/locations.json"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json().get("locations", [])


def set_inventory_level(inventory_item_id, location_id, available):
    """Set inventory level for an item at a location."""
    url = f"{BASE_URL}/inventory_levels/set.json"
    data = {
        "location_id": location_id,
        "inventory_item_id": inventory_item_id,
        "available": available
    }
    resp = requests.post(url, headers=HEADERS, json=data)
    resp.raise_for_status()
    return resp.json()


def main():
    print("=" * 60)
    print("CIB Variant Inventory Fix")
    if DRY_RUN:
        print("** DRY RUN MODE — no changes will be made **")
    print("=" * 60)

    # Get locations
    print("\n1. Fetching locations...")
    locations = get_locations()
    for loc in locations:
        print(f"   Location: {loc['name']} (ID: {loc['id']})")

    if not locations:
        print("ERROR: No locations found!")
        return

    primary_location_id = locations[0]["id"]
    print(f"   Using primary location: {locations[0]['name']}")

    # Get all active products
    print("\n2. Fetching all active products...")
    products = get_all_products()
    print(f"   Found {len(products)} active products")

    # Find CIB variants
    print("\n3. Analyzing CIB variants...")
    cib_variants = []

    for product in products:
        for variant in product.get("variants", []):
            title = variant.get("title", "").lower()
            if "cib" in title or "complete" in title:
                cib_variants.append({
                    "product_title": product["title"],
                    "variant_id": variant["id"],
                    "variant_title": variant["title"],
                    "inventory_item_id": variant["inventory_item_id"],
                    "inventory_quantity": variant.get("inventory_quantity", 0),
                    "inventory_management": variant.get("inventory_management"),
                })

    print(f"   Found {len(cib_variants)} CIB variants total")

    needs_fix = [v for v in cib_variants if v["inventory_quantity"] < 10000]
    already_ok = [v for v in cib_variants if v["inventory_quantity"] >= 10000]

    print(f"   Already at 10000+: {len(already_ok)}")
    print(f"   Need fixing (< 10000): {len(needs_fix)}")

    if not needs_fix:
        print("\n   All CIB variants already have correct inventory!")
        return

    # Show sample
    print(f"\n4. Sample of variants to fix (first 10):")
    for v in needs_fix[:10]:
        print(f"   - {v['product_title']}: {v['variant_title']} = {v['inventory_quantity']}")

    if DRY_RUN:
        print(f"\n** DRY RUN: Would fix {len(needs_fix)} CIB variants **")
        print("   Run without --dry-run to apply changes.")
        return

    # Confirm
    print(f"\n5. About to set inventory to 10000 for {len(needs_fix)} CIB variants.")
    confirm = input("   Continue? (y/n): ").strip().lower()
    if confirm != "y":
        print("   Aborted.")
        return

    # Fix inventory levels
    print(f"\n6. Updating inventory...")
    fixed = 0
    errors = 0

    for i, v in enumerate(needs_fix):
        try:
            set_inventory_level(v["inventory_item_id"], primary_location_id, 10000)
            fixed += 1
            if (i + 1) % 50 == 0:
                print(f"   Progress: {i + 1}/{len(needs_fix)} fixed...")
            time.sleep(0.25)
        except Exception as e:
            errors += 1
            print(f"   ERROR fixing {v['product_title']} ({v['variant_title']}): {e}")
            time.sleep(1)

    print(f"\n{'=' * 60}")
    print(f"RESULTS:")
    print(f"  Total CIB variants found: {len(cib_variants)}")
    print(f"  Already correct: {len(already_ok)}")
    print(f"  Fixed: {fixed}")
    print(f"  Errors: {errors}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
