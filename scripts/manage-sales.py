#!/usr/bin/env python3
"""
8-Bit Legacy — Sales & Deals Manager

Creates and manages sales across the store. Sets compare-at prices on Shopify
products so they show as discounted, and manages the "Sale" collection.

Usage:
  # Preview a 10% off sale on all NES games
  python3 scripts/manage-sales.py --console nes --discount 10 --dry-run

  # Apply 15% off to all PS1 games
  python3 scripts/manage-sales.py --console playstation --discount 15 --apply

  # Sale on products in a price range ($20-$50, 10% off)
  python3 scripts/manage-sales.py --min-price 20 --max-price 50 --discount 10 --apply

  # Sale on specific titles (substring match)
  python3 scripts/manage-sales.py --search "Mario" --discount 10 --apply

  # Clear all active sales (remove compare-at prices)
  python3 scripts/manage-sales.py --clear-all --apply

  # Show current active sales
  python3 scripts/manage-sales.py --list-active

  # Deals of the Week — random selection of popular games, 15% off
  python3 scripts/manage-sales.py --deals-of-week 10 --discount 15 --apply

  # Console spotlight — pick a console, discount the top N popular titles
  python3 scripts/manage-sales.py --console snes --top 20 --discount 12 --apply
"""

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"
DATA_DIR = PROJECT_DIR / "data"

load_dotenv(CONFIG_DIR / ".env")
load_dotenv(PROJECT_DIR / "dashboard" / ".env.local")

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_API_VERSION = "2024-10"

SHOPIFY_DELAY = 0.3

# Console tag mapping (lowercase tag → display name)
CONSOLE_TAGS = {
    "nes": "NES", "snes": "SNES", "n64": "Nintendo 64",
    "gamecube": "GameCube", "wii": "Wii", "wii u": "Wii U",
    "gameboy": "Game Boy", "gameboy color": "Game Boy Color",
    "gameboy advance": "Game Boy Advance", "gba": "Game Boy Advance",
    "nintendo ds": "Nintendo DS", "3ds": "Nintendo 3DS",
    "genesis": "Sega Genesis", "sega genesis": "Sega Genesis",
    "saturn": "Sega Saturn", "dreamcast": "Sega Dreamcast",
    "sega cd": "Sega CD", "sega game gear": "Game Gear",
    "sega master system": "Master System", "sega 32x": "Sega 32X",
    "playstation": "PlayStation", "ps1": "PlayStation",
    "playstation 2": "PlayStation 2", "ps2": "PlayStation 2",
    "playstation 3": "PlayStation 3", "ps3": "PlayStation 3",
    "psp": "PSP",
    "xbox": "Xbox", "xbox 360": "Xbox 360",
    "atari 2600": "Atari 2600", "turbografx-16": "TurboGrafx-16",
}


# ── Shopify API ──────────────────────────────────────────────────────

def shopify_gql(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(
        f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json",
        headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"},
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all_products(console_filter=None, search_filter=None):
    """Fetch all active products. Optionally filter by console tag or title search."""
    products = []
    cursor = None
    page = 0

    # Build query filter
    query_parts = ["status:active"]
    if search_filter:
        query_parts.append(f"title:*{search_filter}*")
    query_filter = " AND ".join(query_parts)

    while True:
        page += 1
        after = f', after: "{cursor}"' if cursor else ""
        query = f"""
        {{
          products(first: 50, query: "{query_filter}"{after}) {{
            edges {{
              cursor
              node {{
                id
                title
                tags
                status
                variants(first: 10) {{
                  edges {{
                    node {{
                      id
                      title
                      price
                      compareAtPrice
                      sku
                    }}
                  }}
                }}
              }}
            }}
            pageInfo {{ hasNextPage }}
          }}
        }}
        """
        data = shopify_gql(query)
        edges = data.get("data", {}).get("products", {}).get("edges", [])

        for edge in edges:
            node = edge["node"]
            tags_lower = [t.lower() for t in node.get("tags", [])]

            # Filter by console if specified
            if console_filter:
                console_match = False
                for tag in tags_lower:
                    if console_filter.lower() in tag:
                        console_match = True
                        break
                if not console_match:
                    continue

            variants = []
            for ve in node.get("variants", {}).get("edges", []):
                v = ve["node"]
                variants.append({
                    "id": v["id"],
                    "title": v.get("title") or "Default",
                    "price": float(v["price"]),
                    "compare_at": float(v["compareAtPrice"]) if v.get("compareAtPrice") else None,
                    "sku": v.get("sku") or "",
                })

            products.append({
                "id": node["id"],
                "title": node["title"],
                "tags": node.get("tags", []),
                "variants": variants,
            })

        has_next = data.get("data", {}).get("products", {}).get("pageInfo", {}).get("hasNextPage", False)
        if not has_next or not edges:
            break
        cursor = edges[-1]["cursor"]
        time.sleep(SHOPIFY_DELAY)

        if page % 10 == 0:
            print(f"  Fetched {len(products)} products so far...")

    return products


def set_compare_at_prices(product_id, variant_updates, dry_run=True):
    """Set compare-at prices on variants to show sale pricing.

    variant_updates: list of {id, compare_at_price, price} dicts
    """
    if dry_run:
        return True

    mutation = """
    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        productVariants { id price compareAtPrice }
        userErrors { field message }
      }
    }
    """

    variants_input = []
    for vu in variant_updates:
        variant_data = {"id": vu["id"]}
        if vu.get("compare_at_price") is not None:
            variant_data["compareAtPrice"] = str(vu["compare_at_price"])
        if vu.get("new_price") is not None:
            variant_data["price"] = str(vu["new_price"])
        variants_input.append(variant_data)

    result = shopify_gql(mutation, {"productId": product_id, "variants": variants_input})
    errors = result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
    if errors:
        print(f"  ERROR: {errors[0]['message']}")
        return False
    return True


def clear_compare_at_price(product_id, variant_ids, dry_run=True):
    """Remove compare-at prices (end a sale)."""
    if dry_run:
        return True

    mutation = """
    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        productVariants { id }
        userErrors { field message }
      }
    }
    """

    variants_input = [{"id": vid, "compareAtPrice": None} for vid in variant_ids]
    result = shopify_gql(mutation, {"productId": product_id, "variants": variants_input})
    errors = result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
    if errors:
        print(f"  ERROR: {errors[0]['message']}")
        return False
    return True


def add_sale_tag(product_id, dry_run=True):
    """Add 'sale' and 'on-sale' tags to a product."""
    if dry_run:
        return True

    mutation = """
    mutation tagsAdd($id: ID!, $tags: [String!]!) {
      tagsAdd(id: $id, tags: $tags) {
        userErrors { field message }
      }
    }
    """
    result = shopify_gql(mutation, {"id": product_id, "tags": ["sale", "on-sale"]})
    errors = result.get("data", {}).get("tagsAdd", {}).get("userErrors", [])
    return not errors


def remove_sale_tag(product_id, dry_run=True):
    """Remove 'sale' and 'on-sale' tags from a product."""
    if dry_run:
        return True

    mutation = """
    mutation tagsRemove($id: ID!, $tags: [String!]!) {
      tagsRemove(id: $id, tags: $tags) {
        userErrors { field message }
      }
    }
    """
    result = shopify_gql(mutation, {"id": product_id, "tags": ["sale", "on-sale"]})
    return True


# ── Sale Logic ───────────────────────────────────────────────────────

def apply_discount_to_products(products, discount_percent, min_price=0, max_price=99999,
                                top_n=None, dry_run=True):
    """Apply a percentage discount to products by setting compare-at prices.

    The current price becomes the compare-at (strikethrough) price,
    and the new discounted price becomes the actual price.
    """
    discount_factor = 1 - (discount_percent / 100)

    # Filter by price range
    eligible = []
    for p in products:
        max_variant_price = max(v["price"] for v in p["variants"]) if p["variants"] else 0
        if min_price <= max_variant_price <= max_price:
            # Skip products already on sale
            already_on_sale = any(v["compare_at"] is not None for v in p["variants"])
            if not already_on_sale:
                p["max_variant_price"] = max_variant_price
                eligible.append(p)

    # Sort by price descending for "top N" selection (higher value items first)
    eligible.sort(key=lambda p: p["max_variant_price"], reverse=True)

    if top_n and len(eligible) > top_n:
        eligible = eligible[:top_n]

    total_updated = 0
    total_savings = 0

    print(f"\n  {'Product':<55} {'Original':>9} {'Sale':>9} {'Save':>7}")
    print(f"  {'-'*55} {'-'*9} {'-'*9} {'-'*7}")

    for p in eligible:
        variant_updates = []
        for v in p["variants"]:
            if v["compare_at"] is not None:
                continue  # Already on sale

            original_price = v["price"]
            new_price = round(original_price * discount_factor, 2)

            # Round to .99
            new_price = int(new_price) + 0.99
            if new_price >= original_price:
                continue

            savings = original_price - new_price
            total_savings += savings

            variant_updates.append({
                "id": v["id"],
                "compare_at_price": original_price,
                "new_price": new_price,
            })

        if not variant_updates:
            continue

        # Show the first variant's pricing as representative
        vu = variant_updates[0]
        print(f"  {p['title'][:55]:<55} ${vu['compare_at_price']:>7.2f} ${vu['new_price']:>7.2f} ${vu['compare_at_price'] - vu['new_price']:>5.2f}")

        if set_compare_at_prices(p["id"], variant_updates, dry_run):
            add_sale_tag(p["id"], dry_run)
            total_updated += 1

        if not dry_run:
            time.sleep(SHOPIFY_DELAY)

    return total_updated, total_savings


def clear_all_sales(products, dry_run=True):
    """Remove compare-at prices and sale tags from all products."""
    cleared = 0

    for p in products:
        on_sale_variants = [v for v in p["variants"] if v["compare_at"] is not None]
        if not on_sale_variants:
            continue

        variant_ids = [v["id"] for v in on_sale_variants]
        print(f"  Clearing sale: {p['title'][:60]}")

        if clear_compare_at_price(p["id"], variant_ids, dry_run):
            remove_sale_tag(p["id"], dry_run)
            cleared += 1

        if not dry_run:
            time.sleep(SHOPIFY_DELAY)

    return cleared


def list_active_sales(products):
    """Show all products currently on sale."""
    on_sale = []
    for p in products:
        for v in p["variants"]:
            if v["compare_at"] is not None:
                discount = round((1 - v["price"] / v["compare_at"]) * 100, 1)
                on_sale.append({
                    "title": p["title"],
                    "variant": v["title"],
                    "original": v["compare_at"],
                    "sale": v["price"],
                    "discount": discount,
                })

    if not on_sale:
        print("\n  No active sales found.")
        return

    print(f"\n  {'Product':<50} {'Variant':<15} {'Original':>9} {'Sale':>9} {'Off':>6}")
    print(f"  {'-'*50} {'-'*15} {'-'*9} {'-'*9} {'-'*6}")

    for item in sorted(on_sale, key=lambda x: x["discount"], reverse=True):
        print(f"  {item['title'][:50]:<50} {item['variant'][:15]:<15} ${item['original']:>7.2f} ${item['sale']:>7.2f} {item['discount']:>5.1f}%")

    print(f"\n  Total items on sale: {len(on_sale)}")


def deals_of_the_week(products, count, discount_percent, dry_run=True):
    """Select random popular games for a "Deals of the Week" promotion."""
    # Filter to products with reasonable prices
    eligible = [p for p in products
                if p["variants"]
                and max(v["price"] for v in p["variants"]) >= 10
                and not any(v["compare_at"] is not None for v in p["variants"])]

    if len(eligible) < count:
        print(f"  Only {len(eligible)} eligible products (need {count})")
        count = len(eligible)

    # Weighted random: higher price = more likely to be picked (better deal perception)
    weights = [max(v["price"] for v in p["variants"]) for p in eligible]
    selected = []
    remaining = list(range(len(eligible)))

    for _ in range(min(count, len(remaining))):
        remaining_weights = [weights[i] for i in remaining]
        total = sum(remaining_weights)
        if total == 0:
            break
        probs = [w / total for w in remaining_weights]
        chosen_idx = random.choices(remaining, weights=remaining_weights, k=1)[0]
        selected.append(eligible[chosen_idx])
        remaining.remove(chosen_idx)

    print(f"\n  Deals of the Week — {discount_percent}% off {len(selected)} products:")

    updated, savings = apply_discount_to_products(selected, discount_percent, dry_run=dry_run)

    return updated, savings


# ── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Manage sales and deals on 8-Bit Legacy")

    # Action modes
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list-active", action="store_true", help="Show all products currently on sale")
    group.add_argument("--clear-all", action="store_true", help="Remove all active sales")
    group.add_argument("--deals-of-week", type=int, metavar="COUNT",
                       help="Select N random popular games for Deals of the Week")

    # Filters
    parser.add_argument("--console", help="Filter by console (e.g., nes, snes, playstation)")
    parser.add_argument("--search", help="Filter by title substring")
    parser.add_argument("--min-price", type=float, default=0, help="Minimum price filter")
    parser.add_argument("--max-price", type=float, default=99999, help="Maximum price filter")
    parser.add_argument("--top", type=int, help="Only discount the top N highest-value products")

    # Sale parameters
    parser.add_argument("--discount", type=float, help="Discount percentage (e.g., 10 for 10%% off)")

    # Execution mode
    parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    parser.add_argument("--apply", action="store_true", help="Apply changes to Shopify")

    args = parser.parse_args()

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        print("ERROR: Shopify credentials not configured")
        sys.exit(1)

    # Validate args
    if not args.list_active and not args.clear_all and not args.deals_of_week:
        if not args.discount:
            parser.print_help()
            print("\nProvide --discount or use --list-active, --clear-all, or --deals-of-week")
            return

    dry_run = not args.apply

    # Fetch products
    print("Fetching products...")
    products = fetch_all_products(console_filter=args.console, search_filter=args.search)
    print(f"  Found {len(products)} products")

    # Execute action
    if args.list_active:
        list_active_sales(products)
        return

    if args.clear_all:
        mode = "DRY RUN" if dry_run else "CLEARING"
        print(f"\n  Mode: {mode}")
        cleared = clear_all_sales(products, dry_run)
        print(f"\n  {'Would clear' if dry_run else 'Cleared'} {cleared} products from sale")
        return

    if args.deals_of_week:
        if not args.discount:
            print("ERROR: --deals-of-week requires --discount")
            return
        mode = "DRY RUN" if dry_run else "APPLYING"
        print(f"\n  Mode: {mode}")
        updated, savings = deals_of_the_week(products, args.deals_of_week, args.discount, dry_run)
        print(f"\n  {'Would update' if dry_run else 'Updated'} {updated} products")
        print(f"  Total customer savings: ${savings:.2f}")
        return

    # Standard sale application
    if args.discount:
        mode = "DRY RUN" if dry_run else "APPLYING"
        label = args.console or args.search or "all products"
        print(f"\n  Mode: {mode}")
        print(f"  Target: {label}")
        print(f"  Discount: {args.discount}% off")

        updated, savings = apply_discount_to_products(
            products, args.discount,
            min_price=args.min_price,
            max_price=args.max_price,
            top_n=args.top,
            dry_run=dry_run,
        )

        print(f"\n  {'Would update' if dry_run else 'Updated'} {updated} products")
        print(f"  Total customer savings: ${savings:.2f}")


if __name__ == "__main__":
    main()
