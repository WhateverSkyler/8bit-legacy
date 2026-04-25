#!/usr/bin/env python3
"""
8-Bit Legacy — Pokemon Card Importer

Imports Pokemon cards from the Pokemon TCG API into Shopify.
Uses TCGPlayer market prices embedded in the API for pricing.

Usage:
  # Import a specific set
  python3 pokemon-card-importer.py --set sv9

  # Import multiple sets
  python3 pokemon-card-importer.py --set sv9 sv8 me3

  # Import all sets released in the last 2 years
  python3 pokemon-card-importer.py --recent 2

  # Import ALL sets (20,000+ cards — takes a while)
  python3 pokemon-card-importer.py --all

  # Auto-detect and import sets not yet in Shopify
  python3 pokemon-card-importer.py --new-sets

  # Preview without creating products
  python3 pokemon-card-importer.py --set sv9 --dry-run

  # Skip cards below a market price threshold
  python3 pokemon-card-importer.py --set sv9 --min-price 1.00

  # List all available sets
  python3 pokemon-card-importer.py --list-sets

  # Import sealed products (booster packs, ETBs, boxes) — manual CSV
  python3 pokemon-card-importer.py --sealed data/pokemon-sealed.csv
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"
DATA_DIR = PROJECT_DIR / "data"

load_dotenv(CONFIG_DIR / ".env")
load_dotenv(PROJECT_DIR / "dashboard" / ".env.local")

# ── Config ────────────────────────────────────────────────────────────

POKEMON_TCG_API = "https://api.pokemontcg.io/v2"
API_KEY = os.getenv("POKEMON_TCG_API_KEY", "")  # Optional — higher rate limits

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_API_VERSION = "2024-10"

# Load pricing config
try:
    with open(CONFIG_DIR / "pricing.json") as f:
        PRICING_CONFIG = json.load(f)
except FileNotFoundError:
    PRICING_CONFIG = {"default_multiplier": 1.35, "minimum_profit_usd": 3.00}

CARD_MULTIPLIER = PRICING_CONFIG.get("category_multipliers", {}).get("pokemon_cards", 1.35)
MIN_PROFIT = PRICING_CONFIG.get("minimum_profit_usd", 3.00)
SHOPIFY_FEE_PERCENT = PRICING_CONFIG.get("shopify_fee_percent", 0.029)
SHOPIFY_FEE_FIXED = PRICING_CONFIG.get("shopify_fee_fixed", 0.30)
ROUND_TO = PRICING_CONFIG.get("round_to", 0.99)

# Rate limiting
TCG_API_DELAY = 0.5   # seconds between Pokemon TCG API requests
SHOPIFY_DELAY = 0.25   # seconds between Shopify mutations

GENERIC_DESCRIPTION = """This card is in great condition. If you have any questions, feel free to reach out!

Shop more Pokemon cards at 8bitlegacy.com"""

PRODUCT_TYPE = "Pokemon Card"

# ── Pokemon TCG API ───────────────────────────────────────────────────

def get_api_headers():
    headers = {"Accept": "application/json"}
    if API_KEY:
        headers["X-Api-Key"] = API_KEY
    return headers


def fetch_all_sets() -> list[dict]:
    """Fetch all Pokemon TCG sets from the API."""
    url = f"{POKEMON_TCG_API}/sets?orderBy=releaseDate&pageSize=250"
    resp = requests.get(url, headers=get_api_headers())
    resp.raise_for_status()
    return resp.json()["data"]


def fetch_cards_for_set(set_id: str) -> list[dict]:
    """Fetch all cards for a given set, handling pagination."""
    cards = []
    page = 1
    page_size = 250

    while True:
        url = f"{POKEMON_TCG_API}/cards?q=set.id:{set_id}&pageSize={page_size}&page={page}"
        resp = requests.get(url, headers=get_api_headers())
        resp.raise_for_status()
        data = resp.json()

        cards.extend(data["data"])

        if len(cards) >= data["totalCount"]:
            break

        page += 1
        time.sleep(TCG_API_DELAY)

    return cards


# ── Pricing ───────────────────────────────────────────────────────────

def get_market_price(card: dict):
    """Extract the best market price from TCGPlayer data in the card response."""
    tcgplayer = card.get("tcgplayer", {})
    prices = tcgplayer.get("prices", {})

    if not prices:
        return None

    # Priority: normal > holofoil > reverseHolofoil > 1stEditionHolofoil > 1stEditionNormal
    # Use whichever variant has a market price
    priority = ["normal", "holofoil", "reverseHolofoil",
                 "1stEditionHolofoil", "1stEditionNormal",
                 "unlimitedHolofoil"]

    for variant in priority:
        if variant in prices and prices[variant].get("market"):
            return prices[variant]["market"]

    # Fallback: try any variant with a market price
    for variant_data in prices.values():
        if isinstance(variant_data, dict) and variant_data.get("market"):
            return variant_data["market"]

    # Last resort: try mid price
    for variant in priority:
        if variant in prices and prices[variant].get("mid"):
            return prices[variant]["mid"]

    return None


def calculate_sell_price(market_price: float) -> float:
    """Apply markup and rounding to get the sell price."""
    raw = market_price * CARD_MULTIPLIER

    if ROUND_TO is not None:
        rounded = int(raw) + ROUND_TO
        if rounded < raw:
            rounded += 1.0
        return round(rounded, 2)

    return round(raw, 2)


def calculate_profit(sell_price: float, market_price: float) -> float:
    """Calculate profit after Shopify fees."""
    fee = sell_price * SHOPIFY_FEE_PERCENT + SHOPIFY_FEE_FIXED
    return round(sell_price - market_price - fee, 2)


# ── Shopify Product Creation ──────────────────────────────────────────

def get_shopify_graphql_url():
    return f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"


def shopify_graphql(query: str, variables: dict = None) -> dict:
    """Execute a Shopify GraphQL request."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    resp = requests.post(
        get_shopify_graphql_url(),
        headers={
            "X-Shopify-Access-Token": SHOPIFY_TOKEN,
            "Content-Type": "application/json",
        },
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


def get_existing_pokemon_tags() -> set[str]:
    """Fetch existing Shopify products tagged 'pokemon' to detect already-imported sets."""
    existing_sets = set()
    cursor = None

    while True:
        after = f', after: "{cursor}"' if cursor else ""
        query = f"""
        {{
          products(first: 250, query: "tag:pokemon"{after}) {{
            edges {{
              cursor
              node {{
                tags
              }}
            }}
            pageInfo {{ hasNextPage }}
          }}
        }}
        """
        data = shopify_graphql(query)
        edges = data.get("data", {}).get("products", {}).get("edges", [])

        for edge in edges:
            for tag in edge["node"]["tags"]:
                tag_lower = tag.lower()
                if tag_lower.startswith("set:"):
                    existing_sets.add(tag_lower.replace("set:", "").strip())

        has_next = data.get("data", {}).get("products", {}).get("pageInfo", {}).get("hasNextPage", False)
        if not has_next or not edges:
            break

        cursor = edges[-1]["cursor"]
        time.sleep(SHOPIFY_DELAY)

    return existing_sets


def create_shopify_product(card: dict, market_price: float, sell_price: float,
                           profit: float, dry_run: bool = False) -> bool:
    """Create a single Shopify product for a Pokemon card."""
    set_name = card["set"]["name"]
    set_id = card["set"]["id"]
    card_number = card.get("number", "")
    card_name = card.get("name", "Unknown")
    rarity = card.get("rarity", "Common")
    supertype = card.get("supertype", "Pokémon")
    card_types = card.get("types", [])
    image_url = card.get("images", {}).get("large") or card.get("images", {}).get("small", "")

    # Product title: "Alakazam (1/102) - Base Set"
    total_in_set = card.get("set", {}).get("printedTotal", card.get("set", {}).get("total", "?"))
    title = f"{card_name} ({card_number}/{total_in_set}) - {set_name}"

    # Tags for filtering/sorting
    tags = [
        "pokemon",
        "tcg",
        "single",
        f"set:{set_name}",
        f"set-id:{set_id}",
        f"rarity:{rarity}",
        f"type:{supertype}",
    ]
    for t in card_types:
        tags.append(f"energy:{t.lower()}")

    # Series tag
    series = card.get("set", {}).get("series", "")
    if series:
        tags.append(f"series:{series}")

    if dry_run:
        flag = "✓" if profit >= MIN_PROFIT else "⚠"
        print(f"  {flag} {title:<55} market: ${market_price:>7.2f}  sell: ${sell_price:>7.2f}  profit: ${profit:>6.2f}")
        return True

    # Step 1: Create the product (Shopify 2024-10 API — no variants in ProductCreateInput)
    create_mutation = """
    mutation productCreate($product: ProductCreateInput!, $media: [CreateMediaInput!]) {
      productCreate(product: $product, media: $media) {
        product {
          id
          title
          variants(first: 1) {
            edges {
              node {
                id
              }
            }
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    create_vars = {
        "product": {
            "title": title,
            "descriptionHtml": GENERIC_DESCRIPTION,
            "productType": PRODUCT_TYPE,
            "vendor": "Pokémon",
            "tags": tags,
            "status": "DRAFT",
        },
        "media": [
            {
                "originalSource": image_url,
                "mediaContentType": "IMAGE",
                "alt": title,
            }
        ] if image_url else [],
    }

    try:
        result = shopify_graphql(create_mutation, create_vars)

        # Check for GraphQL-level errors
        if "errors" in result:
            print(f"  ✗ {title}: {result['errors'][0].get('message', 'Unknown error')}")
            return False

        product_data = result.get("data", {}).get("productCreate", {})
        user_errors = product_data.get("userErrors", [])
        if user_errors:
            print(f"  ✗ {title}: {user_errors[0]['message']}")
            return False

        product = product_data.get("product")
        if not product:
            print(f"  ✗ {title}: No product returned")
            return False

        product_id = product["id"]
        variant_edges = product.get("variants", {}).get("edges", [])
        if not variant_edges:
            print(f"  ✗ {title}: No default variant")
            return False

        variant_id = variant_edges[0]["node"]["id"]

        # Step 2: Update the default variant with price and SKU
        variant_mutation = """
        mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            productVariants { id price sku }
            userErrors { field message }
          }
        }
        """

        variant_vars = {
            "productId": product_id,
            "variants": [{
                "id": variant_id,
                "price": str(sell_price),
                "inventoryItem": {"sku": f"PKM-{set_id}-{card_number}"},
            }],
        }

        variant_result = shopify_graphql(variant_mutation, variant_vars)
        variant_errors = variant_result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
        if variant_errors:
            print(f"  ⚡ {title}: created but variant update failed: {variant_errors[0]['message']}")
            return True  # Product still created

        print(f"  ✓ {title} — ${sell_price:.2f}")
        return True
    except Exception as e:
        print(f"  ✗ {title}: {e}")
        return False


# ── Sealed Products ───────────────────────────────────────────────────

def import_sealed_products(csv_path: str, dry_run: bool = False) -> dict:
    """Import sealed Pokemon products (booster packs, ETBs, boxes) from a CSV.

    Expected CSV columns: name, category, set, market_price, image_url (optional)
    Categories: booster-pack, etb, booster-box, collection-box, tin, blister
    """
    results = {"created": 0, "skipped": 0, "failed": 0}

    if not os.path.exists(csv_path):
        print(f"  CSV not found: {csv_path}")
        print(f"\n  Create a CSV with columns: name, category, set, market_price, image_url")
        print(f"  Example row: Scarlet & Violet Booster Pack,booster-pack,Scarlet & Violet,4.50,https://...")
        return results

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            category = row.get("category", "sealed").strip()
            set_name = row.get("set", "").strip()
            market_price = float(row.get("market_price", 0))
            image_url = row.get("image_url", "").strip()

            if not name or market_price <= 0:
                results["skipped"] += 1
                continue

            sell_price = calculate_sell_price(market_price)
            profit = calculate_profit(sell_price, market_price)

            tags = ["pokemon", "tcg", "sealed", f"category:{category}"]
            if set_name:
                tags.append(f"set:{set_name}")

            if dry_run:
                flag = "✓" if profit >= MIN_PROFIT else "⚠"
                print(f"  {flag} {name:<55} market: ${market_price:>7.2f}  sell: ${sell_price:>7.2f}  profit: ${profit:>6.2f}")
                results["created"] += 1
                continue

            sku = f"PKM-SEALED-{name[:20].replace(' ', '-').upper()}"
            product_type = f"Pokemon {category.replace('-', ' ').title()}"

            create_mutation = """
            mutation productCreate($product: ProductCreateInput!, $media: [CreateMediaInput!]) {
              productCreate(product: $product, media: $media) {
                product {
                  id
                  variants(first: 1) { edges { node { id } } }
                }
                userErrors { field message }
              }
            }
            """

            create_vars = {
                "product": {
                    "title": name,
                    "descriptionHtml": GENERIC_DESCRIPTION,
                    "productType": product_type,
                    "vendor": "Pokémon",
                    "tags": tags,
                    "status": "DRAFT",
                },
                "media": [{"originalSource": image_url, "mediaContentType": "IMAGE", "alt": name}]
                    if image_url else [],
            }

            try:
                result = shopify_graphql(create_mutation, create_vars)
                if "errors" in result:
                    print(f"  ✗ {name}: {result['errors'][0].get('message', 'Unknown')}")
                    results["failed"] += 1
                    continue

                product_data = result.get("data", {}).get("productCreate", {})
                if product_data.get("userErrors"):
                    print(f"  ✗ {name}: {product_data['userErrors'][0]['message']}")
                    results["failed"] += 1
                    continue

                product_id_sealed = product_data["product"]["id"]
                variant_id = product_data["product"]["variants"]["edges"][0]["node"]["id"]

                # Update variant with price and SKU
                variant_mutation = """
                mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                    productVariants { id }
                    userErrors { field message }
                  }
                }
                """
                shopify_graphql(variant_mutation, {
                    "productId": product_id_sealed,
                    "variants": [{"id": variant_id, "price": str(sell_price), "inventoryItem": {"sku": sku}}],
                })

                print(f"  ✓ {name} — ${sell_price:.2f}")
                results["created"] += 1
            except Exception as e:
                print(f"  ✗ {name}: {e}")
                results["failed"] += 1

            time.sleep(SHOPIFY_DELAY)

    return results


# ── Main Import Flow ──────────────────────────────────────────────────

def import_set(set_id: str, dry_run: bool = False, min_price: float = 0,
               max_price: float = 500, save_csv: bool = False) -> dict:
    """Import all cards from a single set."""
    print(f"\n  Fetching cards for set: {set_id}")
    cards = fetch_cards_for_set(set_id)
    print(f"  Found {len(cards)} cards")

    results = {"total": len(cards), "created": 0, "skipped_price": 0,
               "skipped_profit": 0, "failed": 0, "no_price": 0, "skipped_expensive": 0}

    csv_rows = []

    for i, card in enumerate(cards):
        market_price = get_market_price(card)

        if market_price is None:
            results["no_price"] += 1
            continue

        if market_price < min_price:
            results["skipped_price"] += 1
            continue

        if market_price > max_price:
            results["skipped_expensive"] += 1
            continue

        sell_price = calculate_sell_price(market_price)
        profit = calculate_profit(sell_price, market_price)

        if profit < MIN_PROFIT:
            results["skipped_profit"] += 1
            # Still create the product but flag it
            # Cards under profit threshold may still be worth listing for catalog completeness

        if save_csv:
            csv_rows.append({
                "set_id": set_id,
                "set_name": card["set"]["name"],
                "card_name": card["name"],
                "card_number": card.get("number", ""),
                "rarity": card.get("rarity", ""),
                "market_price": market_price,
                "sell_price": sell_price,
                "profit": profit,
                "image_url": card.get("images", {}).get("large", ""),
            })

        success = create_shopify_product(card, market_price, sell_price, profit, dry_run)
        if success:
            results["created"] += 1
        else:
            results["failed"] += 1

        if not dry_run:
            time.sleep(SHOPIFY_DELAY)

    if save_csv and csv_rows:
        DATA_DIR.mkdir(exist_ok=True)
        csv_path = DATA_DIR / f"pokemon-{set_id}-{datetime.now().strftime('%Y%m%d')}.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"\n  Saved pricing data to: {csv_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Import Pokemon cards into Shopify from Pokemon TCG API")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--set", nargs="+", help="Import specific set(s) by ID (e.g., sv9 base1)")
    group.add_argument("--recent", type=int, metavar="YEARS",
                       help="Import sets released in the last N years")
    group.add_argument("--all", action="store_true", help="Import ALL sets (20,000+ cards)")
    group.add_argument("--new-sets", action="store_true",
                       help="Auto-detect and import sets not yet in Shopify")
    group.add_argument("--list-sets", action="store_true", help="List all available sets")
    group.add_argument("--sealed", metavar="CSV",
                       help="Import sealed products from CSV (booster packs, ETBs, etc.)")

    parser.add_argument("--dry-run", action="store_true", help="Preview without creating Shopify products")
    parser.add_argument("--min-price", type=float, default=5.0,
                        help="Skip cards below this market price (default: 5.0). Below $5, "
                             "Shopify fees + eBay LP gap eat all margin.")
    parser.add_argument("--max-price", type=float, default=500,
                        help="Skip cards above this market price (default: 500 = exclude high-value cards)")
    parser.add_argument("--save-csv", action="store_true", help="Save pricing data to CSV")

    args = parser.parse_args()

    # ── List sets ──
    if args.list_sets:
        print("\nFetching all Pokemon TCG sets...")
        sets = fetch_all_sets()
        print(f"\n  {'ID':<20} {'Name':<45} {'Cards':>6}  {'Released'}")
        print(f"  {'-'*20} {'-'*45} {'-'*6}  {'-'*10}")
        for s in sets:
            print(f"  {s['id']:<20} {s['name']:<45} {s['total']:>6}  {s['releaseDate']}")
        print(f"\n  Total: {len(sets)} sets")
        return

    # ── Sealed products ──
    if args.sealed:
        print(f"\nImporting sealed Pokemon products from: {args.sealed}")
        results = import_sealed_products(args.sealed, args.dry_run)
        print(f"\n  Results: {results['created']} created, {results['skipped']} skipped, {results['failed']} failed")
        return

    # ── Determine which sets to import ──
    all_sets = fetch_all_sets()
    set_ids_to_import = []

    if args.set:
        valid_ids = {s["id"] for s in all_sets}
        for sid in args.set:
            if sid in valid_ids:
                set_ids_to_import.append(sid)
            else:
                print(f"  Warning: Set '{sid}' not found in API. Use --list-sets to see valid IDs.")

    elif args.recent:
        cutoff = datetime.now() - timedelta(days=365 * args.recent)
        cutoff_str = cutoff.strftime("%Y/%m/%d")
        set_ids_to_import = [s["id"] for s in all_sets if s["releaseDate"] >= cutoff_str]
        print(f"\n  Found {len(set_ids_to_import)} sets released in the last {args.recent} year(s)")

    elif args.all:
        set_ids_to_import = [s["id"] for s in all_sets]
        total_cards = sum(s["total"] for s in all_sets)
        print(f"\n  Importing ALL {len(set_ids_to_import)} sets ({total_cards} cards)")
        if not args.dry_run:
            print("  This will take a while. Press Ctrl+C to cancel.")
            time.sleep(3)

    elif args.new_sets:
        if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
            print("  Error: Shopify credentials required for --new-sets")
            sys.exit(1)

        print("\n  Checking which sets are already in Shopify...")
        existing = get_existing_pokemon_tags()
        print(f"  Found {len(existing)} existing sets in Shopify")

        for s in all_sets:
            set_name_lower = s["name"].lower()
            if set_name_lower not in existing:
                set_ids_to_import.append(s["id"])

        if set_ids_to_import:
            print(f"  {len(set_ids_to_import)} new set(s) to import:")
            for sid in set_ids_to_import:
                name = next(s["name"] for s in all_sets if s["id"] == sid)
                print(f"    - {name} ({sid})")
        else:
            print("  All sets already imported!")
            return

    if not set_ids_to_import:
        print("  No sets to import.")
        return

    # ── Run imports ──
    if args.dry_run:
        print("\n  === DRY RUN — no Shopify products will be created ===")
    elif not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        print("\n  Warning: Shopify not configured. Running in preview mode.")
        args.dry_run = True

    print(f"\n  Multiplier: {CARD_MULTIPLIER}x | Min profit: ${MIN_PROFIT:.2f} | "
          f"Price range: ${args.min_price:.2f} — ${args.max_price:.2f}")

    grand_total = {"total": 0, "created": 0, "skipped_price": 0,
                   "skipped_profit": 0, "failed": 0, "no_price": 0, "skipped_expensive": 0}

    for set_id in set_ids_to_import:
        set_name = next((s["name"] for s in all_sets if s["id"] == set_id), set_id)
        print(f"\n{'='*60}")
        print(f"  SET: {set_name} ({set_id})")
        print(f"{'='*60}")

        results = import_set(set_id, args.dry_run, args.min_price, args.max_price, args.save_csv)

        for key in grand_total:
            grand_total[key] += results[key]

        print(f"\n  Set results: {results['created']} created, {results['no_price']} no price, "
              f"{results['skipped_price']} below min, {results['skipped_expensive']} above max, "
              f"{results['skipped_profit']} low profit, {results['failed']} failed")

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"  GRAND TOTAL")
    print(f"{'='*60}")
    print(f"  Cards processed:  {grand_total['total']}")
    print(f"  Created:          {grand_total['created']}")
    print(f"  No price data:    {grand_total['no_price']}")
    print(f"  Below min price:  {grand_total['skipped_price']}")
    print(f"  Above max price:  {grand_total['skipped_expensive']}")
    print(f"  Low profit:       {grand_total['skipped_profit']}")
    print(f"  Failed:           {grand_total['failed']}")


if __name__ == "__main__":
    main()
