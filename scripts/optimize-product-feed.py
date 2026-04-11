#!/usr/bin/env python3
"""
8-Bit Legacy — Google Shopping Feed Optimizer

Adds custom labels and SEO titles to Shopify products for better
Google Shopping performance (both free listings and paid ads).

Custom labels (mapped via Shopify tags):
  custom_label_0: price_tier (under_20, 20_to_50, over_50)
  custom_label_1: console slug (nes, snes, n64, ps1, ps2, etc.)
  custom_label_2: category (game, pokemon_card, sealed)
  custom_label_3: margin_tier (high, medium, low) — based on multiplier

SEO titles: "[Game Name] - [Console] | 8-Bit Legacy"

Usage:
  python3 scripts/optimize-product-feed.py --dry-run     # Preview changes
  python3 scripts/optimize-product-feed.py               # Apply changes
  python3 scripts/optimize-product-feed.py --limit 50    # Process 50 products
"""

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

SHOPIFY_DELAY = 0.5  # seconds between API calls

# ── Console slug mapping ─────────────────────────────────────────────

CONSOLE_SLUG_MAP = {
    "nes (nintendo entertainment system)": "nes",
    "snes (super nintendo entertainment system)": "snes",
    "nintendo 64": "n64",
    "gameboy": "gameboy",
    "gameboy color": "gbc",
    "gameboy advance": "gba",
    "nintendo gamecube": "gamecube",
    "gamecube": "gamecube",
    "wii": "wii",
    "wii u": "wii-u",
    "nintendo ds": "ds",
    "nintendo 3ds": "3ds",
    "playstation": "ps1",
    "playstation 2": "ps2",
    "playstation 3": "ps3",
    "psp": "psp",
    "xbox": "xbox",
    "xbox 360": "xbox-360",
    "sega genesis": "genesis",
    "sega master system": "master-system",
    "sega dreamcast": "dreamcast",
    "sega saturn": "saturn",
    "sega cd": "sega-cd",
    "sega 32x": "32x",
    "sega game gear": "game-gear",
    "atari 2600": "atari-2600",
    "atari 7800": "atari-7800",
    "turbografx-16": "tg16",
    "neo geo": "neo-geo",
    "pokemon card": "pokemon",
}


def get_console_slug(product_type: str) -> str:
    """Map a Shopify product type to a clean console slug."""
    pt_lower = product_type.lower().strip()
    # Handle messy types like "Nintendo Gamecube > Gamecube, Gamecube"
    for key, slug in CONSOLE_SLUG_MAP.items():
        if key in pt_lower:
            return slug
    return pt_lower.replace(" ", "-")[:20]


def get_category(product_type: str, tags: list[str], title: str = "") -> str:
    """Determine product category from type, tags, and title.

    NOTE: productType is used by this store as the *console family name*
    (e.g. "NES (Nintendo Entertainment System)"), NOT as a category indicator.
    So substring-matching 'system' or 'console' in productType is wrong — every
    NES/SNES game would be flagged as a console. Use the title suffix instead.
    """
    pt_lower = product_type.lower()
    tags_lower = [t.lower() for t in tags]
    title_lower = title.lower().strip()

    if "pokemon card" in pt_lower or any("pokemon" in t for t in tags_lower):
        return "pokemon_card"
    if any(t in tags_lower for t in ["sealed", "etb", "booster"]):
        return "sealed"

    # Title-suffix-based detection: "... Game" = game, "... Console" = console, etc.
    if title_lower.endswith("game") or " game" in title_lower:
        return "game"
    if title_lower.endswith("console") or title_lower.endswith("system"):
        return "console"
    if any(t in title_lower for t in ["controller", "memory card", "adapter", "cable"]):
        return "accessory"

    # Fall back to productType only if title isn't descriptive
    if any(t in pt_lower for t in ["accessory", "controller"]):
        return "accessory"
    if "console" in pt_lower and "(" not in pt_lower:
        # Raw "Console" productType without parenthetical = actual console
        return "console"
    return "game"


def get_price_tier(price: float) -> str:
    """Categorize price into tiers for ad segmentation."""
    if price < 20:
        return "under_20"
    elif price <= 50:
        return "20_to_50"
    else:
        return "over_50"


def get_margin_tier(category: str) -> str:
    """Determine margin tier based on category multiplier."""
    # Based on config/pricing.json multipliers
    high = ["accessories"]  # 1.40x
    low = ["pokemon_card"]  # 1.15x
    # Everything else is medium (1.30-1.35x)
    if category in high:
        return "high"
    elif category in low:
        return "low"
    return "medium"


def build_seo_title(title: str) -> str:
    """Build SEO-optimized title: '[Game] - [Console] | 8-Bit Legacy'"""
    # Already has " | 8-Bit Legacy" suffix
    if "8-bit legacy" in title.lower():
        return title
    return f"{title} | 8-Bit Legacy"


def graphql(query: str, variables: dict = None, retries: int = 5) -> dict:
    """Execute a Shopify GraphQL query with retry on throttle."""
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

        # Check for throttle
        errors = data.get("errors", [])
        if any(e.get("extensions", {}).get("code") == "THROTTLED" for e in errors):
            wait = 2 ** attempt
            print(f"  Throttled, waiting {wait}s...")
            time.sleep(wait)
            continue

        if errors:
            print(f"  GraphQL errors: {errors}", file=sys.stderr)
        return data

    print("  Max retries exceeded on throttle", file=sys.stderr)
    return data


def fetch_all_products():
    """Fetch all products with pagination."""
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
              productType
              status
              tags
              seo {{ title description }}
              variants(first: 2) {{
                nodes {{
                  price
                }}
              }}
            }}
          }}
        }}
        """
        data = graphql(query)
        batch = data["data"]["products"]["nodes"]
        products.extend(batch)

        page_info = data["data"]["products"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
        time.sleep(SHOPIFY_DELAY)

        if len(products) % 500 == 0:
            print(f"  Fetched {len(products)} products...")

    return products


def update_product(product_id: str, tags: list[str], seo_title: str, dry_run: bool) -> bool:
    """Update a product's tags and SEO title."""
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
            "tags": tags,
            "seo": {"title": seo_title},
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
    parser = argparse.ArgumentParser(description="Optimize Shopify product feed for Google Shopping")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of products to process")
    args = parser.parse_args()

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        print("ERROR: SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN must be set in config/.env or dashboard/.env.local")
        sys.exit(1)

    if args.dry_run:
        print("\n  === DRY RUN — no changes will be made ===\n")

    print("Fetching all products from Shopify...")
    products = fetch_all_products()
    print(f"  Found {len(products)} products\n")

    if args.limit:
        products = products[: args.limit]
        print(f"  Processing first {args.limit} products\n")

    updated = 0
    skipped = 0
    failed = 0

    # Custom label tag prefixes (Google Shopping reads these from Shopify tags)
    LABEL_PREFIX_0 = "price_tier:"
    LABEL_PREFIX_1 = "console:"
    LABEL_PREFIX_2 = "category:"
    LABEL_PREFIX_3 = "margin:"

    for i, product in enumerate(products):
        title = product["title"]
        product_type = product.get("productType", "")
        existing_tags = product.get("tags", [])
        existing_seo = product.get("seo", {}).get("title") or ""

        # Get lowest variant price
        prices = [float(v["price"]) for v in product["variants"]["nodes"] if v["price"]]
        min_price = min(prices) if prices else 0

        # Compute labels
        console_slug = get_console_slug(product_type)
        category = get_category(product_type, existing_tags, title)
        price_tier = get_price_tier(min_price)
        margin_tier = get_margin_tier(category)

        # Build new tag set: keep existing non-label tags, add/replace labels
        new_tags = [
            t for t in existing_tags
            if not t.startswith(("price_tier:", "console:", "category:", "margin:"))
        ]
        new_tags.append(f"price_tier:{price_tier}")
        new_tags.append(f"console:{console_slug}")
        new_tags.append(f"category:{category}")
        new_tags.append(f"margin:{margin_tier}")

        # Build SEO title
        new_seo_title = build_seo_title(title)

        # Check if anything changed
        tags_changed = set(new_tags) != set(existing_tags)
        seo_changed = new_seo_title != existing_seo

        if not tags_changed and not seo_changed:
            skipped += 1
            continue

        if args.dry_run and i < 10:
            changes = []
            if tags_changed:
                added = set(new_tags) - set(existing_tags)
                changes.append(f"tags +{list(added)}")
            if seo_changed:
                changes.append(f"seo: '{new_seo_title}'")
            print(f"  [{i+1}] {title}")
            print(f"       {', '.join(changes)}")

        if update_product(product["id"], new_tags, new_seo_title, args.dry_run):
            updated += 1
        else:
            failed += 1

        if not args.dry_run and updated % 100 == 0 and updated > 0:
            print(f"  Updated {updated} products...")

    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Total products: {len(products)}")
    print(f"  Updated:        {updated}")
    print(f"  Skipped:        {skipped}")
    print(f"  Failed:         {failed}")

    if args.dry_run:
        print(f"\n  (dry run — no changes made. Run without --dry-run to apply)")


if __name__ == "__main__":
    main()
