#!/usr/bin/env python3
"""
Fix products that got wrong PriceCharting matches during price refresh.
Re-searches each one with better matching and corrects the Shopify price.

Usage:
  python3 scripts/fix-bad-prices.py                # Preview mode
  python3 scripts/fix-bad-prices.py --apply         # Apply corrections
"""

import argparse
import os
import re
import sys
import time
import json
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
load_dotenv(PROJECT_DIR / "config" / ".env")
load_dotenv(PROJECT_DIR / "dashboard" / ".env.local")

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
PRICING = json.load(open(PROJECT_DIR / "config" / "pricing.json"))
MULTIPLIER = PRICING["default_multiplier"]
ROUND_TO = PRICING.get("round_to", 0.99)

HEADERS_PC = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def calc_sell_price(market_price):
    raw = market_price * MULTIPLIER
    if ROUND_TO is not None:
        rounded = int(raw) + ROUND_TO
        if rounded < raw:
            rounded += 1.0
        return round(rounded, 2)
    return round(raw, 2)


def shopify_gql(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(
        f"https://{SHOPIFY_STORE}/admin/api/2024-10/graphql.json",
        headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"},
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


def parse_price_text(text):
    match = re.search(r"[\$]?([\d,]+\.?\d*)", text.replace(",", ""))
    return float(match.group(1)) if match else 0.0


def search_correct_price(game_title, console_name):
    """Search PriceCharting with strict title matching to get the correct game."""
    query = f"{game_title} {console_name}"
    url = f"https://www.pricecharting.com/search-products?q={quote_plus(query)}&type=videogames"

    resp = requests.get(url, headers=HEADERS_PC, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"id": "games_table"})
    if not table:
        return None

    tbody = table.find("tbody")
    if not tbody:
        return None

    rows = tbody.find_all("tr")
    target_console = console_name.lower().strip()
    query_words = set(re.sub(r'[^a-z0-9 ]', '', game_title.lower()).split())

    for row in rows[:10]:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        title_link = cols[1].find("a")
        if not title_link:
            continue

        result_title = title_link.get_text(strip=True)
        result_console = cols[2].get_text(strip=True).lower().strip()

        if "pal" in result_console or "jp " in result_console:
            continue
        if target_console not in result_console and result_console not in target_console:
            continue

        # Strip console suffix from result title for comparison
        rt_clean = re.sub(r'(NES|SNES|Nintendo 64|Gamecube|Gameboy|Genesis|'
                          r'Playstation|Dreamcast|Saturn|GBA|Xbox|Wii|Sega|'
                          r'GameBoy|Game Boy).*$',
                          '', result_title, flags=re.IGNORECASE).strip()
        result_words = set(re.sub(r'[^a-z0-9 ]', '', rt_clean.lower()).split())

        # Must not have sequel indicators
        sequel_words = {'2', '3', '4', '5', '6', '7', '8', '9', 'ii', 'iii', 'iv',
                        'part', 'second', 'math', 'assassin', 'case', 'screw', 'attack',
                        'special', 'edition', 'deluxe', 'bundle'}
        extra = result_words - query_words
        if extra & sequel_words:
            continue

        # Good enough match
        return {
            "title": result_title,
            "loose": parse_price_text(cols[3].get_text(strip=True)),
            "cib": parse_price_text(cols[4].get_text(strip=True)),
        }

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    # Products that got wrong matches — identified by manual verification
    # Format: (Shopify product title substring, console for search, correct game title for search)
    bad_matches = [
        ("Elemental Gearbolt - PS1 Game", "Playstation", "Elemental Gearbolt"),
        ("Donkey Kong Jr - NES Game", "NES", "Donkey Kong Jr"),
        ("Gotcha - NES Game", "NES", "Gotcha"),
        ("Bomberman 64 - Nintendo 64 Game", "Nintendo 64", "Bomberman 64"),
        ("Bubble Bobble - NES Game", "NES", "Bubble Bobble"),
        ("Chip and Dale Rescue Rangers - NES Game", "NES", "Chip and Dale Rescue Rangers"),
        ("Duck Tales - NES Game", "NES", "Duck Tales"),
        ("Mega Man - NES Game", "NES", "Mega Man"),
    ]

    print(f"{'=' * 70}")
    print(f"BAD PRICE MATCH CLEANUP — {'APPLY' if args.apply else 'PREVIEW'}")
    print(f"{'=' * 70}")

    for shopify_title, console, search_title in bad_matches:
        print(f"\n--- {shopify_title} ---")

        # Find the Shopify product
        query_escaped = shopify_title.replace('"', '\\"')
        data = shopify_gql(f'''{{
            products(first: 1, query: "title:'{query_escaped}' status:active") {{
                nodes {{
                    id title
                    variants(first: 5) {{
                        nodes {{ id title price }}
                    }}
                }}
            }}
        }}''')

        products = data.get("data", {}).get("products", {}).get("nodes", [])
        if not products:
            print(f"  Product not found in Shopify")
            continue

        product = products[0]
        print(f"  Found: {product['title']}")

        # Get correct price from PriceCharting
        result = search_correct_price(search_title, console)
        if not result:
            print(f"  No correct match found on PriceCharting")
            continue

        print(f"  Correct match: {result['title']} — Loose: ${result['loose']:.2f}, CIB: ${result['cib']:.2f}")

        # Update each variant
        for variant in product["variants"]["nodes"]:
            vt = (variant["title"] or "").lower()
            old_price = float(variant["price"])

            if "cib" in vt or "complete" in vt:
                market = result["cib"]
                vtype = "CIB"
            else:
                market = result["loose"]
                vtype = "Loose"

            if market <= 0:
                continue

            new_price = calc_sell_price(market)
            diff = new_price - old_price

            print(f"  {vtype}: ${old_price:.2f} → ${new_price:.2f} (market: ${market:.2f}, diff: {diff:+.2f})")

            if args.apply:
                res = shopify_gql(
                    """mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                        productVariants { id price }
                        userErrors { field message }
                      }
                    }""",
                    {"productId": product["id"], "variants": [{"id": variant["id"], "price": str(new_price)}]},
                )
                errors = res.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
                if errors:
                    print(f"    ERROR: {errors[0]['message']}")
                else:
                    print(f"    APPLIED")
                time.sleep(0.3)

        time.sleep(2)

    print(f"\n{'=' * 70}")
    print("Done!" if args.apply else "Run with --apply to fix these prices.")


if __name__ == "__main__":
    main()
