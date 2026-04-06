#!/usr/bin/env python3
"""
8-Bit Legacy — Full Price Refresh

First-run and periodic full price sync for all game products.
Scrapes PriceCharting for each console, matches to Shopify products,
updates both Loose and CIB variant prices, and logs everything.

Usage:
  python3 scripts/full-price-refresh.py --report          # Preview only (no changes)
  python3 scripts/full-price-refresh.py --apply            # Apply all safe changes
  python3 scripts/full-price-refresh.py --apply --console nes  # Only sync NES games

Output:
  Detailed log saved to data/logs/price-refresh-{timestamp}.log
  CSV report saved to data/logs/price-refresh-{timestamp}.csv
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"
DATA_DIR = PROJECT_DIR / "data"
LOG_DIR = DATA_DIR / "logs"

load_dotenv(CONFIG_DIR / ".env")
load_dotenv(PROJECT_DIR / "dashboard" / ".env.local")

# ── Config ────────────────────────────────────────────────────────────

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

with open(CONFIG_DIR / "pricing.json") as f:
    PRICING = json.load(f)

MULTIPLIER = PRICING["default_multiplier"]  # 1.35 for games
ROUND_TO = PRICING.get("round_to", 0.99)
MIN_PROFIT = PRICING["minimum_profit_usd"]
FEE_PCT = PRICING["shopify_fee_percent"]
FEE_FIXED = PRICING["shopify_fee_fixed"]

# Consoles to scrape
ALL_CONSOLES = [
    "nes", "super-nintendo", "nintendo-64", "gamecube", "wii", "wii-u",
    "gameboy", "gameboy-color", "gameboy-advance", "nintendo-ds", "nintendo-3ds",
    "sega-genesis", "sega-saturn", "sega-dreamcast", "sega-cd", "sega-game-gear",
    "playstation", "playstation-2", "playstation-3", "psp",
    "xbox", "xbox-360",
    "atari-2600", "turbografx-16", "neo-geo",
]

SCRAPE_DELAY = 2.0  # seconds between PriceCharting requests
SHOPIFY_DELAY = 0.3  # seconds between Shopify mutations

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

# ── Logging ───────────────────────────────────────────────────────────

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"price-refresh-{timestamp}.log"
CSV_FILE = LOG_DIR / f"price-refresh-{timestamp}.csv"

log_handle = None
csv_rows = []

def log(msg):
    global log_handle
    if log_handle is None:
        log_handle = open(LOG_FILE, "w")
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line)
    log_handle.write(line + "\n")
    log_handle.flush()


# ── PriceCharting Scraper ─────────────────────────────────────────────

def parse_price_text(text):
    match = re.search(r"[\$]?([\d,]+\.?\d*)", text.replace(",", ""))
    return float(match.group(1)) if match else 0.0


def scrape_console(console_slug, max_pages=10):
    """Scrape all items for a console from PriceCharting."""
    items = []
    for page in range(1, max_pages + 1):
        url = f"https://www.pricecharting.com/console/{console_slug}?sort=name&page={page}"
        log(f"  Scraping {console_slug} page {page}...")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            log(f"  ERROR: Failed to scrape {url}: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "games_table"})
        if not table:
            break

        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody else []
        if not rows:
            break

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            # Column layout: [0]=checkbox, [1]=title, [2]=loose, [3]=cib, [4]=new, [5]=actions
            title_link = cols[1].find("a")
            if not title_link:
                continue

            title = title_link.get_text(strip=True)
            loose = parse_price_text(cols[2].get_text(strip=True)) if len(cols) > 2 else 0
            cib = parse_price_text(cols[3].get_text(strip=True)) if len(cols) > 3 else 0
            new_price = parse_price_text(cols[4].get_text(strip=True)) if len(cols) > 4 else 0

            if title and (loose > 0 or cib > 0):
                items.append({
                    "title": title,
                    "console": console_slug,
                    "loose": loose,
                    "cib": cib,
                    "new": new_price,
                })

        time.sleep(SCRAPE_DELAY)

    return items


# ── Shopify ───────────────────────────────────────────────────────────

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


def fetch_all_shopify_products():
    """Fetch all products with their variants from Shopify."""
    log("Fetching all Shopify products...")
    products = []
    cursor = None
    page = 0

    while True:
        page += 1
        after = f', after: "{cursor}"' if cursor else ""
        query = f"""
        {{
          products(first: 50{after}) {{
            edges {{
              cursor
              node {{
                id
                title
                tags
                variants(first: 10) {{
                  edges {{
                    node {{
                      id
                      title
                      price
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
            variants = []
            for ve in node.get("variants", {}).get("edges", []):
                v = ve["node"]
                variants.append({
                    "id": v["id"],
                    "title": (v.get("title") or "").lower(),
                    "price": float(v["price"]),
                    "sku": v.get("sku") or "",
                })

            # Skip Pokemon cards (handled by separate system)
            if any(v["sku"].startswith("PKM-") for v in variants):
                continue

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
        time.sleep(0.5)

        if page % 10 == 0:
            log(f"  Fetched {len(products)} products so far (page {page})...")

    log(f"  Fetched {len(products)} game products total")
    return products


# ── Matching & Pricing ────────────────────────────────────────────────

def calc_sell_price(market_price):
    raw = market_price * MULTIPLIER
    if ROUND_TO is not None:
        rounded = int(raw) + ROUND_TO
        if rounded < raw:
            rounded += 1.0
        return round(rounded, 2)
    return round(raw, 2)


def calc_profit(sell_price, market_price):
    fee = sell_price * FEE_PCT + FEE_FIXED
    return round(sell_price - market_price - fee, 2)


def normalize(s):
    """Normalize a title for matching."""
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def match_and_update(pc_items, shopify_products, apply=False, initial_run=False):
    """Match PriceCharting items to Shopify products and update prices.

    If initial_run=True, the 30% safety limit is raised to 80% since we know
    the existing prices are stale and large changes are expected.
    """
    safety_limit = 0.80 if initial_run else 0.30

    # Build lookup: (normalized_title, console) -> PriceCharting data
    pc_lookup = {}
    for item in pc_items:
        key = normalize(item["title"])
        pc_lookup[(key, item["console"])] = item

    # Also build a title-only lookup as fallback
    pc_by_title = {}
    for item in pc_items:
        key = normalize(item["title"])
        if key not in pc_by_title:
            pc_by_title[key] = item

    # Console slug mapping: Shopify tag -> PriceCharting console slug
    TAG_TO_SLUG = {
        "nes": "nes", "nintendo": "nes",
        "snes": "super-nintendo", "super nintendo": "super-nintendo",
        "n64": "nintendo-64", "nintendo 64": "nintendo-64",
        "gamecube": "gamecube", "nintendo gamecube": "gamecube",
        "wii": "wii", "wii u": "wii-u",
        "gameboy": "gameboy", "game boy": "gameboy",
        "gameboy color": "gameboy-color", "gbc": "gameboy-color",
        "gameboy advance": "gameboy-advance", "gba": "gameboy-advance",
        "nintendo ds": "nintendo-ds", "ds": "nintendo-ds",
        "3ds": "nintendo-3ds", "nintendo 3ds": "nintendo-3ds",
        "genesis": "sega-genesis", "sega genesis": "sega-genesis",
        "saturn": "sega-saturn", "sega saturn": "sega-saturn",
        "dreamcast": "sega-dreamcast", "sega dreamcast": "sega-dreamcast",
        "playstation": "playstation", "ps1": "playstation",
        "ps2": "playstation-2", "playstation 2": "playstation-2",
        "ps3": "playstation-3", "playstation 3": "playstation-3",
        "psp": "psp",
        "xbox": "xbox", "xbox 360": "xbox-360",
        "atari 2600": "atari-2600", "atari": "atari-2600",
    }

    matched = 0
    updated_loose = 0
    updated_cib = 0
    skipped_no_match = 0
    skipped_no_change = 0
    skipped_safety = 0

    for sp in shopify_products:
        sp_title = sp["title"]
        # Strip common suffixes like " - NES Game", " - Nintendo 64 Game", etc.
        clean_title = re.sub(r"\s*[-–]\s*(NES|SNES|N64|Nintendo|Gameboy|Game Boy|Genesis|PS1|PS2|Gamecube|Dreamcast|Saturn|GBA|Playstation|Xbox|Wii|Sega|Atari|TurboGrafx).*$", "", sp_title, flags=re.IGNORECASE)
        sp_norm = normalize(clean_title)

        # Determine Shopify product's console from tags
        sp_console_slug = None
        for tag in sp.get("tags", []):
            slug = TAG_TO_SLUG.get(tag.lower().strip())
            if slug:
                sp_console_slug = slug
                break

        # Try console-specific match first (most accurate)
        pc_item = None
        if sp_console_slug:
            pc_item = pc_lookup.get((sp_norm, sp_console_slug))

        # Fall back to title-only match
        if not pc_item:
            pc_item = pc_by_title.get(sp_norm)

        # Try fuzzy: PriceCharting title in Shopify title or vice versa (console-aware)
        if not pc_item:
            for (pc_key, pc_console), pc_val in pc_lookup.items():
                if sp_console_slug and pc_console != sp_console_slug:
                    continue  # Don't cross-match consoles
                if pc_key in sp_norm or sp_norm in pc_key:
                    pc_item = pc_val
                    break

        if not pc_item:
            skipped_no_match += 1
            continue

        matched += 1

        # Update each variant
        for variant in sp["variants"]:
            vt = variant["title"]
            old_price = variant["price"]
            is_cib = "complete" in vt or "cib" in vt or "box" in vt
            is_loose = not is_cib  # Default variant or "game only"

            if is_loose and pc_item["loose"] > 0:
                market = pc_item["loose"]
            elif is_cib and pc_item["cib"] > 0:
                market = pc_item["cib"]
            else:
                continue

            new_price = calc_sell_price(market)
            profit = calc_profit(new_price, market)
            diff = round(new_price - old_price, 2)

            # Safety check: skip extreme changes
            if old_price > 0:
                change_pct = abs(diff) / old_price
                if change_pct > safety_limit:
                    skipped_safety += 1
                    csv_rows.append({
                        "product": sp_title,
                        "variant": vt,
                        "type": "cib" if is_cib else "loose",
                        "market_price": market,
                        "old_price": old_price,
                        "new_price": new_price,
                        "diff": diff,
                        "profit": profit,
                        "status": f"SAFETY ({change_pct:.0%} change)",
                    })
                    continue

            if abs(diff) < 0.50:
                skipped_no_change += 1
                continue

            csv_rows.append({
                "product": sp_title,
                "variant": vt,
                "type": "cib" if is_cib else "loose",
                "market_price": market,
                "old_price": old_price,
                "new_price": new_price,
                "diff": diff,
                "profit": profit,
                "status": "APPLIED" if apply else "PREVIEW",
            })

            if apply:
                result = shopify_gql(
                    """mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                        productVariants { id price }
                        userErrors { field message }
                      }
                    }""",
                    {"productId": sp["id"], "variants": [{"id": variant["id"], "price": str(new_price)}]},
                )
                errors = result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
                if errors:
                    log(f"  ERROR updating {sp_title} ({vt}): {errors[0]['message']}")
                else:
                    if is_cib:
                        updated_cib += 1
                    else:
                        updated_loose += 1
                time.sleep(SHOPIFY_DELAY)
            else:
                flag = "↑" if diff > 0 else "↓"
                variant_label = "CIB" if is_cib else "LOOSE"
                log(f"  {flag} {sp_title} [{variant_label}]: ${old_price:.2f} → ${new_price:.2f} (market: ${market:.2f}, profit: ${profit:.2f})")

    return {
        "matched": matched,
        "updated_loose": updated_loose,
        "updated_cib": updated_cib,
        "skipped_no_match": skipped_no_match,
        "skipped_no_change": skipped_no_change,
        "skipped_safety": skipped_safety,
    }


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Full price refresh for all game products")
    parser.add_argument("--apply", action="store_true", help="Apply changes to Shopify (default: report only)")
    parser.add_argument("--console", nargs="+", help="Only sync specific consoles (e.g., nes super-nintendo)")
    parser.add_argument("--pages", type=int, default=10, help="Max pages to scrape per console (default: 10)")
    parser.add_argument("--initial-run", action="store_true",
                        help="First run — raises safety limit from 30%% to 80%% since prices are known to be stale")
    args = parser.parse_args()

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        log("ERROR: Shopify credentials not configured")
        sys.exit(1)

    log("=" * 60)
    mode = "APPLY MODE" if args.apply else "REPORT MODE"
    if args.initial_run:
        mode += " (INITIAL RUN — safety limit raised to 80%)"
    log(f"FULL PRICE REFRESH — {mode}")
    log(f"Multiplier: {MULTIPLIER}x | Min profit: ${MIN_PROFIT:.2f}")
    log(f"Log: {LOG_FILE}")
    log("=" * 60)

    # Step 1: Fetch all Shopify products
    shopify_products = fetch_all_shopify_products()

    # Step 2: Scrape PriceCharting for each console
    consoles = args.console if args.console else ALL_CONSOLES
    all_pc_items = []

    for console in consoles:
        log(f"\nScraping {console}...")
        items = scrape_console(console, args.pages)
        log(f"  Found {len(items)} items")
        all_pc_items.extend(items)

    log(f"\nTotal PriceCharting items scraped: {len(all_pc_items)}")

    # Step 3: Match and update
    log(f"\nMatching {len(all_pc_items)} PriceCharting items to {len(shopify_products)} Shopify products...")
    results = match_and_update(all_pc_items, shopify_products, apply=args.apply, initial_run=args.initial_run)

    # Step 4: Save CSV report
    if csv_rows:
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
            writer.writeheader()
            writer.writerows(csv_rows)
        log(f"\nCSV report saved: {CSV_FILE}")

    # Step 5: Summary
    log("\n" + "=" * 60)
    log("RESULTS")
    log("=" * 60)
    log(f"  PriceCharting items scraped: {len(all_pc_items)}")
    log(f"  Shopify products checked:    {len(shopify_products)}")
    log(f"  Matched:                     {results['matched']}")
    log(f"  Loose prices updated:        {results['updated_loose']}")
    log(f"  CIB prices updated:          {results['updated_cib']}")
    log(f"  No match found:              {results['skipped_no_match']}")
    log(f"  No significant change:       {results['skipped_no_change']}")
    log(f"  Safety limit (>30%):         {results['skipped_safety']}")
    log(f"  Total changes in CSV:        {len(csv_rows)}")

    if log_handle:
        log_handle.close()

    print(f"\nFull log: {LOG_FILE}")
    print(f"CSV report: {CSV_FILE}")


if __name__ == "__main__":
    main()
