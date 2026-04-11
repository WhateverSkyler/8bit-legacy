#!/usr/bin/env python3
"""
Permanent CIB inventory fix: set `inventoryPolicy: CONTINUE` on all CIB variants.

This is a HARDER fix than just setting available quantity. With policy=CONTINUE,
Shopify will never mark the variant as out-of-stock regardless of tracked quantity
— matching the dropship reality where we never have physical inventory.

The old fix-cib-inventory.py set `available: 10000` which worked until something
(Shopify sync? Merchant Center? unknown) reset all 6,112 variants back to 0 on
2026-04-11. This script sets the policy at the variant level, so the value is
stable across any inventory sync.

Usage:
    python3 scripts/set-cib-continue-policy.py --dry-run
    python3 scripts/set-cib-continue-policy.py
"""
import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "dashboard" / ".env.local")
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

SHOP = os.getenv("SHOPIFY_STORE_URL", "")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"
GQL_URL = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

DRY_RUN = "--dry-run" in sys.argv


def gql(query, variables=None):
    for attempt in range(5):
        resp = requests.post(GQL_URL, headers=HEADERS, json={"query": query, "variables": variables or {}})
        if resp.status_code == 429:
            time.sleep(2 + attempt)
            continue
        if resp.status_code != 200:
            print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
            time.sleep(2 ** attempt)
            continue
        data = resp.json()
        if any(e.get("extensions", {}).get("code") == "THROTTLED" for e in data.get("errors", [])):
            time.sleep(2 + attempt)
            continue
        return data
    return data


FETCH = """
query($cursor: String) {
  products(first: 100, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      title
      variants(first: 10) {
        nodes {
          id
          title
          inventoryPolicy
        }
      }
    }
  }
}
"""

UPDATE = """
mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants { id inventoryPolicy }
    userErrors { field message }
  }
}
"""


def fetch_cib_variants():
    cib = []
    cursor = None
    total_products = 0
    while True:
        data = gql(FETCH, {"cursor": cursor})
        edge = data.get("data", {}).get("products", {})
        nodes = edge.get("nodes", [])
        for p in nodes:
            total_products += 1
            for v in p["variants"]["nodes"]:
                vtitle = v["title"].lower()
                if "cib" in vtitle or "complete" in vtitle:
                    cib.append({
                        "product_id": p["id"],
                        "product_title": p["title"],
                        "variant_id": v["id"],
                        "variant_title": v["title"],
                        "current_policy": v["inventoryPolicy"],
                    })
        page = edge.get("pageInfo", {})
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
        if total_products % 500 == 0:
            print(f"  scanned {total_products} products, {len(cib)} CIB variants found")
        time.sleep(0.3)
    print(f"Total active products scanned: {total_products}")
    return cib


def main():
    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Fetching all active products + CIB variants...")
    cib = fetch_cib_variants()
    print(f"Total CIB variants: {len(cib)}")

    needs_fix = [v for v in cib if v["current_policy"] != "CONTINUE"]
    already_ok = len(cib) - len(needs_fix)
    print(f"  Already CONTINUE: {already_ok}")
    print(f"  Need fix (DENY): {len(needs_fix)}")

    if not needs_fix:
        print("All CIB variants already have inventoryPolicy: CONTINUE")
        return

    if DRY_RUN:
        print("\nSample of variants that would be updated:")
        for v in needs_fix[:10]:
            print(f"  - {v['product_title']}: {v['variant_title']} (policy={v['current_policy']})")
        print(f"\nWould update {len(needs_fix)} variants. Re-run without --dry-run to apply.")
        return

    # Group by product for bulk updates
    by_product = {}
    for v in needs_fix:
        by_product.setdefault(v["product_id"], []).append(v)

    fixed = 0
    errors = 0
    for i, (pid, variants) in enumerate(by_product.items(), 1):
        variants_input = [
            {"id": v["variant_id"], "inventoryPolicy": "CONTINUE"}
            for v in variants
        ]
        result = gql(UPDATE, {"productId": pid, "variants": variants_input})
        update = result.get("data", {}).get("productVariantsBulkUpdate", {})
        user_errors = update.get("userErrors", [])
        if user_errors:
            print(f"  ERROR {variants[0]['product_title']}: {user_errors}")
            errors += 1
        else:
            fixed += len(variants)
        if i % 100 == 0:
            print(f"  {i}/{len(by_product)} products processed — {fixed} variants fixed")
        time.sleep(0.4)

    print(f"\nDone. Fixed {fixed}/{len(needs_fix)} CIB variants. Errors: {errors}")


if __name__ == "__main__":
    main()
