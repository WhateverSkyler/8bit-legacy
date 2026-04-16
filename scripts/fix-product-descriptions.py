#!/usr/bin/env python3
"""
8-Bit Legacy — Bulk Product Description Fix

Replaces "30-day" with "90-day" in all product descriptions.
Google displays product description text in search results,
so this must match the actual 90-day return policy.

Usage:
  python3 scripts/fix-product-descriptions.py --dry-run   # Preview changes
  python3 scripts/fix-product-descriptions.py              # Apply changes
  python3 scripts/fix-product-descriptions.py --limit 50   # Process 50 products
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
SHOPIFY_DELAY = 0.5

# Patterns to find and replace
REPLACEMENTS = [
    ("30-day free return policy", "90-day free return policy"),
    ("30-day return policy", "90-day return policy"),
    ("30 day free return policy", "90-day free return policy"),
    ("30 day return policy", "90-day return policy"),
    ("30-day returns", "90-day returns"),
    ("30 day returns", "90-day returns"),
]


def graphql(query: str, variables: dict = None, retries: int = 3):
    """Execute a Shopify GraphQL query with retry logic."""
    url = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    last_exc = None
    for attempt in range(retries):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            last_exc = e
            time.sleep(2 ** attempt)
            continue

        errors = data.get("errors", [])
        if any(e.get("extensions", {}).get("code") == "THROTTLED" for e in errors):
            wait = 2 ** attempt
            print(f"  Throttled, waiting {wait}s...", flush=True)
            time.sleep(wait)
            continue

        if errors:
            print(f"  GraphQL errors: {errors}", file=sys.stderr, flush=True)
        return data

    print(f"  Max retries exceeded: {last_exc}", file=sys.stderr)
    return {}


def fetch_all_products():
    """Fetch all products with descriptions."""
    products = []
    cursor = None

    while True:
        after = f', after: "{cursor}"' if cursor else ""
        query = f"""
        {{
          products(first: 50{after}) {{
            pageInfo {{ hasNextPage endCursor }}
            nodes {{
              id
              title
              descriptionHtml
            }}
          }}
        }}
        """
        data = graphql(query)
        if not data or "data" not in data:
            print("ERROR: Failed to fetch products", file=sys.stderr)
            break

        batch = data["data"]["products"]["nodes"]
        products.extend(batch)

        page_info = data["data"]["products"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
        time.sleep(SHOPIFY_DELAY)

        if len(products) % 500 == 0:
            print(f"  Fetched {len(products)} products...", flush=True)

    return products


def fix_description(html: str) -> tuple[str, bool]:
    """Apply all replacements to a product description. Returns (new_html, changed)."""
    new_html = html
    for old, new in REPLACEMENTS:
        # Case-insensitive replacement
        new_html = re.sub(re.escape(old), new, new_html, flags=re.IGNORECASE)
    return new_html, new_html != html


def update_product_description(product_id: str, new_html: str, dry_run: bool) -> bool:
    """Update a product's description HTML."""
    if dry_run:
        return True

    mutation = """
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        product { id }
        userErrors { field message }
      }
    }
    """
    variables = {
        "input": {
            "id": product_id,
            "descriptionHtml": new_html,
        }
    }

    data = graphql(mutation, variables)
    errors = data.get("data", {}).get("productUpdate", {}).get("userErrors", [])
    if errors:
        print(f"    Error: {errors}")
        return False

    time.sleep(SHOPIFY_DELAY)
    return True


def main():
    parser = argparse.ArgumentParser(description="Fix product descriptions: 30-day → 90-day returns")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of products to process")
    args = parser.parse_args()

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        print("ERROR: SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN must be set")
        sys.exit(1)

    if args.dry_run:
        print("\n  === DRY RUN — no changes will be made ===\n")

    print("Fetching all products from Shopify...", flush=True)
    products = fetch_all_products()
    print(f"  Found {len(products)} products\n", flush=True)

    if args.limit:
        products = products[:args.limit]
        print(f"  Processing first {args.limit} products\n")

    needs_fix = 0
    already_correct = 0
    updated = 0
    failed = 0

    for i, product in enumerate(products):
        desc = product.get("descriptionHtml") or ""
        new_desc, changed = fix_description(desc)

        if not changed:
            already_correct += 1
            continue

        needs_fix += 1

        if args.dry_run and needs_fix <= 5:
            print(f"  [{needs_fix}] {product['title']}")
            # Show what changes
            for old, new in REPLACEMENTS:
                if old.lower() in desc.lower():
                    print(f"       '{old}' → '{new}'")

        if update_product_description(product["id"], new_desc, args.dry_run):
            updated += 1
        else:
            failed += 1

        if not args.dry_run and updated % 100 == 0 and updated > 0:
            print(f"  Updated {updated} products...", flush=True)

    print(f"\n{'='*60}")
    print(f"  RESULTS — Product Description Fix (30-day → 90-day)")
    print(f"{'='*60}")
    print(f"  Total products scanned: {len(products)}")
    print(f"  Already correct:        {already_correct}")
    print(f"  Needed fix:             {needs_fix}")
    print(f"  Updated:                {updated}")
    print(f"  Failed:                 {failed}")

    if args.dry_run:
        print(f"\n  (dry run — run without --dry-run to apply)")
    else:
        print(f"\n  Google will re-crawl product pages over the next 24-48 hours.")
        print(f"  Force a re-crawl: Merchant Center → Products → Feeds → Re-fetch.")


if __name__ == "__main__":
    main()
