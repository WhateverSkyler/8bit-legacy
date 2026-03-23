#!/usr/bin/env python3
"""
8-Bit Legacy — PriceCharting → Shopify Price Sync

Takes a PriceCharting collection CSV export and syncs prices to Shopify.

Workflow:
  1. Export your PriceCharting collection as CSV (free account: 1x/week)
  2. Run this script with the CSV path
  3. Script calculates new prices (loose price × multiplier)
  4. Cross-references with Shopify products by title/SKU
  5. Shows a diff report of what would change
  6. Applies updates via Shopify GraphQL bulk mutation (with --apply flag)

Usage:
  python3 price-sync.py data/pricecharting-export.csv                # Dry run (diff report only)
  python3 price-sync.py data/pricecharting-export.csv --apply        # Apply changes to Shopify
  python3 price-sync.py data/pricecharting-export.csv --report       # Save CSV report to data/
  python3 price-sync.py data/pricecharting-export.csv --min-change 1 # Only update if price diff > $1
"""

import argparse
import csv
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load config
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"
DATA_DIR = PROJECT_DIR / "data"

load_dotenv(CONFIG_DIR / ".env")

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

with open(CONFIG_DIR / "pricing.json") as f:
    PRICING_CONFIG = json.load(f)


def load_pricecharting_csv(csv_path: str) -> list[dict]:
    """Load and parse a PriceCharting collection CSV export."""
    items = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # PriceCharting CSV columns vary but typically include:
            # product-name, console-name, loose-price, cib-price, new-price, upc
            item = {
                "name": row.get("product-name", row.get("Product Name", row.get("name", ""))).strip(),
                "console": row.get("console-name", row.get("Console Name", row.get("console", ""))).strip(),
                "loose_price": parse_price(row.get("loose-price", row.get("Loose Price", row.get("loose_price", "0")))),
                "cib_price": parse_price(row.get("cib-price", row.get("CIB Price", row.get("cib_price", "0")))),
                "new_price": parse_price(row.get("new-price", row.get("New Price", row.get("new_price", "0")))),
                "upc": row.get("upc", row.get("UPC", "")).strip(),
                "asin": row.get("asin", row.get("ASIN", "")).strip(),
            }
            if item["name"] and item["loose_price"] > 0:
                items.append(item)
    return items


def parse_price(price_str: str) -> float:
    """Parse a price string like '$12.99' or '12.99' to float."""
    if not price_str:
        return 0.0
    cleaned = price_str.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def calculate_sell_price(market_price: float, category: str = "retro_games") -> float:
    """Calculate the selling price based on market price and multiplier."""
    multiplier = PRICING_CONFIG.get("category_multipliers", {}).get(
        category, PRICING_CONFIG["default_multiplier"]
    )
    raw_price = market_price * multiplier

    # Round to .99 if configured
    round_to = PRICING_CONFIG.get("round_to")
    if round_to is not None:
        # Round up to nearest dollar, then subtract to get .99
        rounded = math.ceil(raw_price) - (1 - round_to)
        # But don't go below the raw price
        if rounded < raw_price:
            rounded += 1.0
        return round(rounded, 2)

    return round(raw_price, 2)


def calculate_profit(sell_price: float, market_price: float) -> float:
    """Calculate estimated profit after Shopify fees."""
    shopify_fee = (sell_price * PRICING_CONFIG["shopify_fee_percent"]) + PRICING_CONFIG["shopify_fee_fixed"]
    return round(sell_price - market_price - shopify_fee, 2)


def check_minimum_profit(sell_price: float, market_price: float) -> bool:
    """Check if the item meets minimum profit threshold."""
    profit = calculate_profit(sell_price, market_price)
    return profit >= PRICING_CONFIG["minimum_profit_usd"]


# --- Shopify GraphQL API ---

SHOPIFY_GRAPHQL_URL = f"https://{SHOPIFY_STORE_URL}/admin/api/2024-10/graphql.json"


def shopify_graphql(query: str, variables: dict = None) -> dict:
    """Execute a Shopify GraphQL query."""
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    resp = requests.post(SHOPIFY_GRAPHQL_URL, json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    if "errors" in data:
        print(f"  GraphQL errors: {data['errors']}")

    return data


def fetch_all_shopify_products() -> list[dict]:
    """Fetch all products from Shopify with their variants and prices."""
    products = []
    cursor = None
    page = 0

    while True:
        page += 1
        after_clause = f', after: "{cursor}"' if cursor else ""
        query = f"""
        {{
          products(first: 50{after_clause}) {{
            edges {{
              cursor
              node {{
                id
                title
                handle
                tags
                variants(first: 10) {{
                  edges {{
                    node {{
                      id
                      title
                      sku
                      price
                      barcode
                    }}
                  }}
                }}
              }}
            }}
            pageInfo {{
              hasNextPage
            }}
          }}
        }}
        """
        data = shopify_graphql(query)
        edges = data.get("data", {}).get("products", {}).get("edges", [])

        for edge in edges:
            node = edge["node"]
            for variant_edge in node["variants"]["edges"]:
                variant = variant_edge["node"]
                products.append({
                    "product_id": node["id"],
                    "product_title": node["title"],
                    "product_handle": node["handle"],
                    "product_tags": node["tags"],
                    "variant_id": variant["id"],
                    "variant_title": variant["title"],
                    "sku": variant.get("sku", ""),
                    "current_price": float(variant["price"]),
                    "barcode": variant.get("barcode", ""),
                })

        has_next = data.get("data", {}).get("products", {}).get("pageInfo", {}).get("hasNextPage", False)
        if not has_next or not edges:
            break

        cursor = edges[-1]["cursor"]
        print(f"  Fetched page {page} ({len(products)} products so far)...")
        time.sleep(0.5)  # Rate limiting

    return products


def match_products(pc_items: list[dict], shopify_products: list[dict]) -> list[dict]:
    """Match PriceCharting items to Shopify products by title similarity."""
    matches = []
    unmatched_pc = []

    # Build lookup maps
    shopify_by_title = {}
    shopify_by_barcode = {}
    for sp in shopify_products:
        # Normalize title for matching
        normalized = sp["product_title"].lower().strip()
        shopify_by_title[normalized] = sp
        if sp["barcode"]:
            shopify_by_barcode[sp["barcode"]] = sp

    for pc_item in pc_items:
        matched = False

        # Try UPC/barcode match first (most reliable)
        if pc_item["upc"] and pc_item["upc"] in shopify_by_barcode:
            sp = shopify_by_barcode[pc_item["upc"]]
            matches.append({"pc": pc_item, "shopify": sp, "match_type": "upc"})
            matched = True
            continue

        # Try exact title match
        pc_title = f"{pc_item['name']}".lower().strip()
        if pc_title in shopify_by_title:
            sp = shopify_by_title[pc_title]
            matches.append({"pc": pc_item, "shopify": sp, "match_type": "title_exact"})
            matched = True
            continue

        # Try title with console
        pc_title_console = f"{pc_item['name']} - {pc_item['console']}".lower().strip()
        if pc_title_console in shopify_by_title:
            sp = shopify_by_title[pc_title_console]
            matches.append({"pc": pc_item, "shopify": sp, "match_type": "title_console"})
            matched = True
            continue

        # Try fuzzy: PC title contained in Shopify title or vice versa
        for normalized, sp in shopify_by_title.items():
            if pc_title in normalized or normalized in pc_title:
                matches.append({"pc": pc_item, "shopify": sp, "match_type": "fuzzy"})
                matched = True
                break

        if not matched:
            unmatched_pc.append(pc_item)

    return matches, unmatched_pc


def generate_diff(matches: list[dict], min_change: float = 0.0) -> list[dict]:
    """Generate a diff of price changes needed."""
    changes = []
    skipped_profit = []
    no_change = []

    for match in matches:
        pc = match["pc"]
        sp = match["shopify"]

        price_field = PRICING_CONFIG.get("price_field", "loose")
        market_price = pc.get(f"{price_field}_price", pc["loose_price"])

        new_price = calculate_sell_price(market_price)
        current_price = sp["current_price"]
        price_diff = round(new_price - current_price, 2)

        # Check minimum profit
        meets_profit = check_minimum_profit(new_price, market_price)
        profit = calculate_profit(new_price, market_price)

        record = {
            "product_title": sp["product_title"],
            "variant_id": sp["variant_id"],
            "pc_name": pc["name"],
            "console": pc["console"],
            "market_price": market_price,
            "current_shopify_price": current_price,
            "new_price": new_price,
            "price_diff": price_diff,
            "estimated_profit": profit,
            "meets_min_profit": meets_profit,
            "match_type": match["match_type"],
        }

        if not meets_profit:
            skipped_profit.append(record)
        elif abs(price_diff) < min_change:
            no_change.append(record)
        elif price_diff != 0:
            changes.append(record)
        else:
            no_change.append(record)

    return changes, skipped_profit, no_change


def apply_price_updates(changes: list[dict]) -> dict:
    """Apply price changes to Shopify via GraphQL mutations."""
    results = {"success": 0, "failed": 0, "errors": []}

    # Batch updates (Shopify allows up to 250 variants per bulk mutation)
    batch_size = 50
    for i in range(0, len(changes), batch_size):
        batch = changes[i : i + batch_size]

        variants_input = []
        for change in batch:
            variants_input.append({
                "id": change["variant_id"],
                "price": str(change["new_price"]),
            })

        # Use productVariantsBulkUpdate requires product ID, so we group by product
        # For simplicity, use individual variant updates
        for change in batch:
            mutation = """
            mutation productVariantUpdate($input: ProductVariantInput!) {
              productVariantUpdate(input: $input) {
                productVariant {
                  id
                  price
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """
            variables = {
                "input": {
                    "id": change["variant_id"],
                    "price": str(change["new_price"]),
                }
            }

            try:
                data = shopify_graphql(mutation, variables)
                errors = data.get("data", {}).get("productVariantUpdate", {}).get("userErrors", [])
                if errors:
                    results["failed"] += 1
                    results["errors"].append({
                        "product": change["product_title"],
                        "errors": errors,
                    })
                else:
                    results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "product": change["product_title"],
                    "errors": str(e),
                })

            time.sleep(0.25)  # Rate limiting: ~4 requests/sec

        print(f"  Batch {i // batch_size + 1}: {len(batch)} updates processed")

    return results


def print_diff_report(changes, skipped_profit, no_change, unmatched):
    """Print a formatted diff report."""
    print("\n" + "=" * 70)
    print("  8-BIT LEGACY — PRICE SYNC REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    print(f"\n  SUMMARY")
    print(f"  ├── Price changes needed:    {len(changes)}")
    print(f"  ├── Below profit threshold:  {len(skipped_profit)}")
    print(f"  ├── No change needed:        {len(no_change)}")
    print(f"  └── Unmatched PC items:      {len(unmatched)}")

    if changes:
        print(f"\n  PRICE CHANGES ({len(changes)} items)")
        print(f"  {'Product':<40} {'Current':>8} {'New':>8} {'Diff':>8} {'Profit':>8}")
        print(f"  {'-' * 40} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 8}")

        total_revenue_change = 0
        for c in sorted(changes, key=lambda x: abs(x["price_diff"]), reverse=True)[:30]:
            title = c["product_title"][:40]
            diff_sign = "+" if c["price_diff"] > 0 else ""
            print(
                f"  {title:<40} ${c['current_shopify_price']:>7.2f} ${c['new_price']:>7.2f} "
                f"{diff_sign}${c['price_diff']:>6.2f} ${c['estimated_profit']:>7.2f}"
            )
            total_revenue_change += c["price_diff"]

        if len(changes) > 30:
            print(f"  ... and {len(changes) - 30} more")

        print(f"\n  Net price adjustment across all changes: ${total_revenue_change:+.2f}")

    if skipped_profit:
        print(f"\n  BELOW PROFIT THRESHOLD ({len(skipped_profit)} items)")
        print(f"  Min profit required: ${PRICING_CONFIG['minimum_profit_usd']:.2f}")
        for s in skipped_profit[:10]:
            title = s["product_title"][:40]
            print(f"  {title:<40} profit: ${s['estimated_profit']:.2f} (market: ${s['market_price']:.2f})")
        if len(skipped_profit) > 10:
            print(f"  ... and {len(skipped_profit) - 10} more")

    if unmatched:
        print(f"\n  UNMATCHED PRICECHARTING ITEMS ({len(unmatched)} items)")
        print(f"  These items exist in PriceCharting but couldn't be matched to a Shopify product:")
        for u in unmatched[:10]:
            print(f"  - {u['name']} ({u['console']}) — loose: ${u['loose_price']:.2f}")
        if len(unmatched) > 10:
            print(f"  ... and {len(unmatched) - 10} more")

    print()


def save_report_csv(changes, skipped_profit, no_change, unmatched):
    """Save the full report as a CSV for review."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = DATA_DIR / f"price-sync-report_{timestamp}.csv"

    all_records = []
    for c in changes:
        c["status"] = "CHANGE"
        all_records.append(c)
    for s in skipped_profit:
        s["status"] = "BELOW_PROFIT"
        all_records.append(s)
    for n in no_change:
        n["status"] = "NO_CHANGE"
        all_records.append(n)

    if all_records:
        with open(report_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_records[0].keys())
            writer.writeheader()
            writer.writerows(all_records)
        print(f"  Report saved to: {report_path}")

    # Save unmatched separately
    if unmatched:
        unmatched_path = DATA_DIR / f"unmatched-items_{timestamp}.csv"
        with open(unmatched_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=unmatched[0].keys())
            writer.writeheader()
            writer.writerows(unmatched)
        print(f"  Unmatched items saved to: {unmatched_path}")


def main():
    parser = argparse.ArgumentParser(description="Sync PriceCharting prices to Shopify")
    parser.add_argument("csv_path", help="Path to PriceCharting CSV export")
    parser.add_argument("--apply", action="store_true", help="Actually apply price changes to Shopify")
    parser.add_argument("--report", action="store_true", help="Save detailed CSV report")
    parser.add_argument("--min-change", type=float, default=0.50, help="Minimum price difference to trigger update (default: $0.50)")
    args = parser.parse_args()

    # Validate
    if not os.path.exists(args.csv_path):
        print(f"Error: CSV file not found: {args.csv_path}")
        sys.exit(1)

    if args.apply and (not SHOPIFY_STORE_URL or not SHOPIFY_ACCESS_TOKEN):
        print("Error: SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN must be set in config/.env")
        sys.exit(1)

    # Step 1: Load PriceCharting data
    print("\n[1/4] Loading PriceCharting CSV...")
    pc_items = load_pricecharting_csv(args.csv_path)
    print(f"  Loaded {len(pc_items)} items from PriceCharting")

    # Step 2: Fetch Shopify products
    print("\n[2/4] Fetching Shopify products...")
    if not SHOPIFY_STORE_URL or not SHOPIFY_ACCESS_TOKEN:
        print("  Shopify credentials not configured — running in CSV-only mode")
        print("  Showing calculated prices for PriceCharting items:\n")

        print(f"  {'Item':<45} {'Market':>8} {'Sell At':>8} {'Profit':>8}")
        print(f"  {'-' * 45} {'-' * 8} {'-' * 8} {'-' * 8}")

        for item in pc_items[:50]:
            sell_price = calculate_sell_price(item["loose_price"])
            profit = calculate_profit(sell_price, item["loose_price"])
            meets = "ok" if check_minimum_profit(sell_price, item["loose_price"]) else "LOW"
            name = f"{item['name']} ({item['console']})"[:45]
            print(f"  {name:<45} ${item['loose_price']:>7.2f} ${sell_price:>7.2f} ${profit:>6.2f} {meets}")

        if len(pc_items) > 50:
            print(f"  ... and {len(pc_items) - 50} more items")
        return

    shopify_products = fetch_all_shopify_products()
    print(f"  Found {len(shopify_products)} Shopify product variants")

    # Step 3: Match & generate diff
    print("\n[3/4] Matching products and calculating prices...")
    matches, unmatched = match_products(pc_items, shopify_products)
    print(f"  Matched: {len(matches)} | Unmatched: {len(unmatched)}")

    changes, skipped_profit, no_change = generate_diff(matches, args.min_change)

    # Step 4: Report
    print_diff_report(changes, skipped_profit, no_change, unmatched)

    if args.report:
        save_report_csv(changes, skipped_profit, no_change, unmatched)

    # Step 5: Apply (if requested)
    if args.apply and changes:
        print(f"\n[4/4] Applying {len(changes)} price updates to Shopify...")
        confirm = input(f"  This will update {len(changes)} product prices. Continue? (y/N): ")
        if confirm.lower() == "y":
            results = apply_price_updates(changes)
            print(f"\n  Results: {results['success']} updated, {results['failed']} failed")
            if results["errors"]:
                print(f"  Errors:")
                for err in results["errors"][:5]:
                    print(f"    - {err['product']}: {err['errors']}")
        else:
            print("  Cancelled.")
    elif args.apply and not changes:
        print("\n  No price changes to apply.")
    else:
        print("  Dry run complete. Use --apply to push changes to Shopify.")


if __name__ == "__main__":
    main()
