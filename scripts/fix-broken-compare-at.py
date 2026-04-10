#!/usr/bin/env python3
"""
8-Bit Legacy — Fix Broken compare_at_price

One-off cleanup for variants where compare_at_price < price (creating
a "negative discount" state). Fallout from the CIB-fix script setting
compare_at to the loose Game Only price, then a subsequent price refresh
raising the CIB price.

Customer impact is invisible (Shopify hides strike-through when
compare_at <= price), but it pollutes the smart "Sale" collection
(rule: compare_at_price > 0) and breaks manage-sales.py --list-active.

Usage:
  python3 scripts/fix-broken-compare-at.py --dry-run     # Preview
  python3 scripts/fix-broken-compare-at.py --apply       # Clear bad compare_at
"""

import argparse
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

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_API_VERSION = "2024-10"

SHOPIFY_DELAY = 0.3


def shopify_gql(query, variables=None, retries=5):
    url = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    for attempt in range(retries):
        resp = requests.post(
            url,
            headers={
                "X-Shopify-Access-Token": SHOPIFY_TOKEN,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        errors = data.get("errors", [])
        if any(e.get("extensions", {}).get("code") == "THROTTLED" for e in errors):
            wait = 2 ** attempt
            print(f"  Throttled, waiting {wait}s...", flush=True)
            time.sleep(wait)
            continue

        if errors:
            print(f"  GraphQL errors: {errors}", file=sys.stderr, flush=True)
        return data

    return data


def fetch_all_variants_with_compare_at():
    """Fetch every variant with a non-null compare_at_price."""
    products = []
    cursor = None
    page = 0

    while True:
        after = f', after: "{cursor}"' if cursor else ""
        query = f"""
        {{
          products(first: 50{after}) {{
            pageInfo {{ hasNextPage endCursor }}
            nodes {{
              id
              title
              variants(first: 10) {{
                nodes {{
                  id
                  title
                  price
                  compareAtPrice
                }}
              }}
            }}
          }}
        }}
        """
        data = shopify_gql(query)
        if not data.get("data"):
            print(f"  ERROR fetching page {page}: {data}", file=sys.stderr, flush=True)
            break

        batch = data["data"]["products"]["nodes"]
        for p in batch:
            for v in p["variants"]["nodes"]:
                if v.get("compareAtPrice"):
                    products.append({
                        "product_id": p["id"],
                        "product_title": p["title"],
                        "variant_id": v["id"],
                        "variant_title": v.get("title") or "Default",
                        "price": float(v["price"]),
                        "compare_at": float(v["compareAtPrice"]),
                    })

        page_info = data["data"]["products"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
        page += 1
        if page % 10 == 0:
            print(f"  Scanned {page * 50} products...", flush=True)
        time.sleep(SHOPIFY_DELAY)

    return products


def clear_compare_at(product_id, variant_ids):
    """Clear compare_at_price on the given variants of a product."""
    mutation = """
    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        productVariants { id compareAtPrice }
        userErrors { field message }
      }
    }
    """
    variants_input = [{"id": vid, "compareAtPrice": None} for vid in variant_ids]
    result = shopify_gql(mutation, {"productId": product_id, "variants": variants_input})
    errors = result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
    if errors:
        print(f"    ERROR: {errors}", file=sys.stderr, flush=True)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Fix variants with compare_at < price")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Preview only")
    group.add_argument("--apply", action="store_true", help="Apply the fix")
    args = parser.parse_args()

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        print("ERROR: SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN must be set", file=sys.stderr)
        sys.exit(1)

    mode = "DRY RUN" if args.dry_run else "APPLY"
    print(f"\n  === {mode} — finding variants with compare_at < price ===\n", flush=True)

    print("Scanning all products for compare_at_price set...", flush=True)
    variants = fetch_all_variants_with_compare_at()
    print(f"  Found {len(variants)} variants with compare_at_price set\n", flush=True)

    # Find broken ones: compare_at < price
    broken = [v for v in variants if v["compare_at"] < v["price"]]

    if not broken:
        print("  No broken compare_at_price values found. Nothing to fix.")
        return

    print(f"  {len(broken)} variants have compare_at < price (broken):\n", flush=True)
    print(f"  {'Product':<55} {'Variant':<15} {'compare_at':>10} {'price':>10}")
    print(f"  {'-'*55} {'-'*15} {'-'*10} {'-'*10}")
    for v in sorted(broken, key=lambda x: x["compare_at"] - x["price"]):
        title = v["product_title"][:53]
        vtitle = v["variant_title"][:13]
        print(f"  {title:<55} {vtitle:<15} ${v['compare_at']:>8.2f} ${v['price']:>8.2f}")

    if args.dry_run:
        print(f"\n  (dry run — no changes made. Run with --apply to clear these compare_at values)")
        return

    # APPLY
    print(f"\n  Applying fix: clearing compare_at_price on {len(broken)} variants...\n", flush=True)

    # Group by product so we can use bulk variant update
    by_product = {}
    for v in broken:
        by_product.setdefault(v["product_id"], {
            "title": v["product_title"],
            "variant_ids": [],
        })["variant_ids"].append(v["variant_id"])

    fixed = 0
    failed = 0
    for product_id, info in by_product.items():
        print(f"  Clearing {len(info['variant_ids'])} variant(s) on: {info['title'][:60]}", flush=True)
        if clear_compare_at(product_id, info["variant_ids"]):
            fixed += len(info["variant_ids"])
        else:
            failed += len(info["variant_ids"])
        time.sleep(SHOPIFY_DELAY)

    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Cleared:  {fixed}")
    print(f"  Failed:   {failed}")


if __name__ == "__main__":
    main()
