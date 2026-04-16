#!/usr/bin/env python3
"""
8-Bit Legacy — Product Feed Audit for Google Shopping Ads

Checks all Shopify products for Google Shopping readiness before
launching paid ads. Reports issues by severity.

Issues checked:
  CRITICAL — will cause ad disapproval or waste money:
    - Missing product image
    - $0 or negative price
    - Pokemon singles in feed (1.15x margin can't support ad cost)
    - Missing custom labels (price_tier, console, category, margin)
    - Product status not ACTIVE

  WARNING — reduces ad quality/performance:
    - Title too short (< 20 chars) or missing console name
    - Missing SEO meta description
    - Only 1 image (Google Shopping Quality Score rewards 3+)
    - Price under $10 (fees eat all profit after ad cost)

  INFO — for awareness:
    - Products by category breakdown
    - Products by price tier breakdown
    - Products excluded from ads (pokemon_card)

Usage:
  python3 scripts/audit-product-feed.py              # Full audit
  python3 scripts/audit-product-feed.py --limit 100  # Audit first 100
  python3 scripts/audit-product-feed.py --json       # JSON output
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from collections import Counter, defaultdict

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
            time.sleep(2 ** attempt)
            continue
        return data

    print(f"  Max retries exceeded: {last_exc}", file=sys.stderr)
    return {}


def fetch_all_products():
    """Fetch all products with images, variants, tags, SEO data."""
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
              handle
              productType
              status
              tags
              seo {{ title description }}
              images(first: 5) {{
                nodes {{ url }}
              }}
              variants(first: 10) {{
                nodes {{
                  title
                  price
                  sku
                  inventoryQuantity
                }}
              }}
            }}
          }}
        }}
        """
        data = graphql(query)
        if not data or "data" not in data:
            print("ERROR: Failed to fetch products from Shopify", file=sys.stderr)
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


def get_tag_value(tags: list[str], prefix: str) -> str | None:
    """Extract a custom label value from tags (e.g., 'price_tier:over_50' -> 'over_50')."""
    for tag in tags:
        if tag.startswith(prefix):
            return tag[len(prefix):]
    return None


CONSOLE_NAMES = [
    "nes", "snes", "n64", "gamecube", "wii", "gameboy", "gba", "gbc", "ds", "3ds",
    "ps1", "ps2", "ps3", "psp", "dreamcast", "saturn", "genesis", "game gear",
    "sega cd", "xbox", "atari", "turbografx", "neo geo", "jaguar",
    "playstation", "nintendo", "sega", "sony", "microsoft",
]


def audit_product(product: dict) -> dict:
    """Audit a single product. Returns dict of issues by severity."""
    issues = {"critical": [], "warning": [], "info": []}

    title = product["title"]
    tags = product.get("tags", [])
    status = product.get("status", "")
    images = product.get("images", {}).get("nodes", [])
    variants = product.get("variants", {}).get("nodes", [])
    seo_desc = product.get("seo", {}).get("description") or ""
    product_type = product.get("productType", "")

    # ── CRITICAL checks ──

    # Not active
    if status != "ACTIVE":
        issues["critical"].append(f"Product status is {status}, not ACTIVE")

    # No images
    if not images:
        issues["critical"].append("No product image — will be disapproved by Google")

    # $0 or negative price
    prices = [float(v["price"]) for v in variants if v.get("price")]
    if not prices:
        issues["critical"].append("No variants with a price")
    elif min(prices) <= 0:
        issues["critical"].append(f"Zero or negative price: ${min(prices):.2f}")

    # Missing custom labels
    price_tier = get_tag_value(tags, "price_tier:")
    console = get_tag_value(tags, "console:")
    category = get_tag_value(tags, "category:")
    margin = get_tag_value(tags, "margin:")

    missing_labels = []
    if not price_tier:
        missing_labels.append("price_tier")
    if not console:
        missing_labels.append("console")
    if not category:
        missing_labels.append("category")
    if not margin:
        missing_labels.append("margin")
    if missing_labels:
        issues["critical"].append(f"Missing custom labels: {', '.join(missing_labels)}")

    # Pokemon singles — should be excluded from paid ads
    if category == "pokemon_card":
        issues["info"].append("Pokemon card — will be excluded from paid ads (1.15x margin)")

    # ── WARNING checks ──

    # Title quality
    if len(title) < 20:
        issues["warning"].append(f"Title too short ({len(title)} chars): '{title}'")

    title_lower = title.lower()
    has_console_in_title = any(c in title_lower for c in CONSOLE_NAMES)
    if not has_console_in_title and category == "game":
        issues["warning"].append("Game title missing console name — hurts search matching")

    # Missing SEO description
    if not seo_desc:
        issues["warning"].append("Missing SEO meta description — reduces Shopping ad CTR")

    # Only 1 image
    if len(images) == 1:
        issues["warning"].append("Only 1 image — Google Shopping Quality Score rewards 3+")

    # Very low price
    if prices and min(prices) < 10 and category != "pokemon_card":
        issues["warning"].append(f"Price ${min(prices):.2f} — likely unprofitable after ad cost + fees")

    # No SKU on variants
    variants_without_sku = [v for v in variants if not v.get("sku")]
    if variants_without_sku:
        issues["warning"].append(f"{len(variants_without_sku)} variant(s) missing SKU")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Audit product feed for Google Shopping ads readiness")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of products to audit")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--critical-only", action="store_true", help="Only show products with critical issues")
    args = parser.parse_args()

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        print("ERROR: SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN must be set in config/.env or dashboard/.env.local")
        sys.exit(1)

    print("Fetching all products from Shopify...", flush=True)
    products = fetch_all_products()
    print(f"  Found {len(products)} products\n", flush=True)

    if args.limit:
        products = products[:args.limit]
        print(f"  Auditing first {args.limit} products\n")

    # ── Run audit ──
    results = {
        "total_products": len(products),
        "critical_count": 0,
        "warning_count": 0,
        "clean_count": 0,
        "products_with_critical": [],
        "products_with_warnings": [],
        "category_breakdown": Counter(),
        "price_tier_breakdown": Counter(),
        "status_breakdown": Counter(),
        "pokemon_count": 0,
        "missing_images": 0,
        "missing_labels": 0,
        "missing_seo": 0,
    }

    for product in products:
        tags = product.get("tags", [])
        category = get_tag_value(tags, "category:") or "unknown"
        price_tier = get_tag_value(tags, "price_tier:") or "unknown"
        status = product.get("status", "UNKNOWN")

        results["category_breakdown"][category] += 1
        results["price_tier_breakdown"][price_tier] += 1
        results["status_breakdown"][status] += 1

        if category == "pokemon_card":
            results["pokemon_count"] += 1

        issues = audit_product(product)

        if issues["critical"]:
            results["critical_count"] += 1
            results["products_with_critical"].append({
                "title": product["title"],
                "handle": product.get("handle", ""),
                "issues": issues["critical"],
            })
            # Track specific issue types
            for issue in issues["critical"]:
                if "No product image" in issue:
                    results["missing_images"] += 1
                if "Missing custom labels" in issue:
                    results["missing_labels"] += 1

        elif issues["warning"]:
            results["warning_count"] += 1
            if not args.critical_only:
                results["products_with_warnings"].append({
                    "title": product["title"],
                    "handle": product.get("handle", ""),
                    "issues": issues["warning"],
                })
                for issue in issues["warning"]:
                    if "Missing SEO" in issue:
                        results["missing_seo"] += 1
        else:
            results["clean_count"] += 1

    # ── Output ──
    if args.json:
        # Convert Counter objects to dicts for JSON
        results["category_breakdown"] = dict(results["category_breakdown"])
        results["price_tier_breakdown"] = dict(results["price_tier_breakdown"])
        results["status_breakdown"] = dict(results["status_breakdown"])
        print(json.dumps(results, indent=2))
        return

    # Human-readable report
    print("=" * 70)
    print("  PRODUCT FEED AUDIT — GOOGLE SHOPPING ADS READINESS")
    print("=" * 70)

    print(f"\n  Total products:   {results['total_products']}")
    print(f"  Clean (no issues): {results['clean_count']}")
    print(f"  With warnings:    {results['warning_count']}")
    print(f"  With CRITICAL:    {results['critical_count']}")

    print(f"\n{'─' * 70}")
    print("  CATEGORY BREAKDOWN (custom_label_2)")
    print(f"{'─' * 70}")
    for cat, count in sorted(results["category_breakdown"].items(), key=lambda x: -x[1]):
        ads_note = " [EXCLUDED from ads]" if cat == "pokemon_card" else ""
        print(f"    {cat:20s}  {count:>6,}{ads_note}")

    print(f"\n{'─' * 70}")
    print("  PRICE TIER BREAKDOWN (custom_label_0)")
    print(f"{'─' * 70}")
    for tier, count in sorted(results["price_tier_breakdown"].items(), key=lambda x: -x[1]):
        bid = {"over_50": "$0.55", "20_to_50": "$0.40", "under_20": "$0.20"}.get(tier, "N/A")
        print(f"    {tier:20s}  {count:>6,}   max CPC: {bid}")

    print(f"\n{'─' * 70}")
    print("  KEY METRICS")
    print(f"{'─' * 70}")
    print(f"    Products without images:     {results['missing_images']}")
    print(f"    Products missing labels:     {results['missing_labels']}")
    print(f"    Products missing SEO desc:   {results['missing_seo']}")
    print(f"    Pokemon cards (excluded):    {results['pokemon_count']}")

    # Eligible for ads = total - pokemon - critical
    eligible = results["total_products"] - results["pokemon_count"] - results["critical_count"]
    print(f"\n    ELIGIBLE FOR PAID ADS:       {eligible:,}")

    if results["products_with_critical"]:
        print(f"\n{'─' * 70}")
        print(f"  CRITICAL ISSUES ({results['critical_count']} products)")
        print(f"{'─' * 70}")
        for p in results["products_with_critical"][:25]:
            print(f"\n    {p['title']}")
            print(f"    Handle: {p['handle']}")
            for issue in p["issues"]:
                print(f"      - {issue}")

        if len(results["products_with_critical"]) > 25:
            print(f"\n    ... and {len(results['products_with_critical']) - 25} more. Run with --json for full list.")

    if not args.critical_only and results["products_with_warnings"]:
        print(f"\n{'─' * 70}")
        print(f"  WARNINGS ({results['warning_count']} products, showing first 10)")
        print(f"{'─' * 70}")
        for p in results["products_with_warnings"][:10]:
            print(f"\n    {p['title']}")
            for issue in p["issues"]:
                print(f"      - {issue}")

    print(f"\n{'=' * 70}")
    if results["critical_count"] == 0:
        print("  VERDICT: FEED IS HEALTHY — ready for Google Shopping ads")
    elif results["critical_count"] < 50:
        print(f"  VERDICT: MOSTLY HEALTHY — {results['critical_count']} critical issues to fix before launch")
    else:
        print(f"  VERDICT: NEEDS WORK — {results['critical_count']} critical issues. Fix before spending ad budget.")
    print("=" * 70)


if __name__ == "__main__":
    main()
