#!/usr/bin/env python3
"""
8-Bit Legacy — Search-Based Price Refresh

Searches PriceCharting individually for each Shopify product to get
accurate loose + CIB prices. Much better match rate than catalog scraping
since PriceCharting's search handles title variations.

Takes ~3-4 hours for 6,000+ products due to rate limiting (2s per search).

Usage:
  python3 scripts/search-price-refresh.py                 # Report mode
  python3 scripts/search-price-refresh.py --apply         # Apply changes
  python3 scripts/search-price-refresh.py --apply --resume # Resume from last checkpoint
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
from urllib.parse import quote_plus

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

MULTIPLIER = PRICING["default_multiplier"]
ROUND_TO = PRICING.get("round_to", 0.99)
MIN_PROFIT = PRICING["minimum_profit_usd"]
FEE_PCT = PRICING["shopify_fee_percent"]
FEE_FIXED = PRICING["shopify_fee_fixed"]

SEARCH_DELAY = 2.0
SHOPIFY_DELAY = 0.3
CHECKPOINT_FILE = DATA_DIR / "logs" / "search-refresh-checkpoint.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

# Console tag -> PriceCharting search term
TAG_TO_CONSOLE = {
    "nes": "NES", "nes (nintendo entertainment system)": "NES",
    "snes": "SNES", "snes (super nintendo entertainment system)": "SNES",
    "super nintendo": "SNES",
    "nintendo 64": "Nintendo 64", "n64": "Nintendo 64",
    "gamecube": "Gamecube", "nintendo gamecube": "Gamecube",
    "nintendo gamecube > gamecube": "Gamecube",
    "wii": "Wii", "wii u": "Wii U",
    "gameboy": "Gameboy", "game boy": "Gameboy",
    "gameboy color": "Gameboy Color", "gbc": "Gameboy Color",
    "gameboy advance": "Gameboy Advance", "gba": "Gameboy Advance",
    "nintendo ds": "Nintendo DS", "ds": "Nintendo DS",
    "nintendo 3ds": "Nintendo 3DS", "3ds": "Nintendo 3DS",
    "sega genesis": "Sega Genesis", "genesis": "Sega Genesis",
    "sega saturn": "Sega Saturn", "saturn": "Sega Saturn",
    "sega dreamcast": "Sega Dreamcast", "dreamcast": "Sega Dreamcast",
    "sega master system": "Sega Master System",
    "sega cd": "Sega CD", "sega 32x": "Sega 32X",
    "sega game gear": "Sega Game Gear",
    "playstation": "Playstation", "ps1": "Playstation",
    "playstation 2": "Playstation 2", "ps2": "Playstation 2",
    "playstation 3": "Playstation 3", "ps3": "Playstation 3",
    "psp": "PSP",
    "xbox": "Xbox", "xbox 360": "Xbox 360",
    "atari 2600": "Atari 2600", "atari": "Atari 2600",
    "turbografx-16": "TurboGrafx-16",
}

# ── Logging ───────────────────────────────────────────────────────────

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"search-refresh-{timestamp}.log"
CSV_FILE = LOG_DIR / f"search-refresh-{timestamp}.csv"

log_handle = None
csv_writer = None
csv_file_handle = None

def log(msg):
    global log_handle
    if log_handle is None:
        log_handle = open(LOG_FILE, "w")
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line)
    log_handle.write(line + "\n")
    log_handle.flush()

def init_csv():
    global csv_writer, csv_file_handle
    csv_file_handle = open(CSV_FILE, "w", newline="")
    csv_writer = csv.writer(csv_file_handle)
    csv_writer.writerow(["product", "console", "variant", "type", "market_price",
                         "old_price", "new_price", "diff", "profit", "status"])

def write_csv_row(row):
    if csv_writer:
        csv_writer.writerow(row)
        csv_file_handle.flush()


# ── PriceCharting Search ──────────────────────────────────────────────

def parse_price_text(text):
    match = re.search(r"[\$]?([\d,]+\.?\d*)", text.replace(",", ""))
    return float(match.group(1)) if match else 0.0

def search_pricecharting(game_title, console_name):
    """Search PriceCharting for a specific game + console combo."""
    query = f"{game_title} {console_name}"
    url = f"https://www.pricecharting.com/search-products?q={quote_plus(query)}&type=videogames"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"id": "games_table"})
    if not table:
        return None

    tbody = table.find("tbody")
    if not tbody:
        return None

    rows = tbody.find_all("tr")
    if not rows:
        return None

    # Check top results for a console match
    target_console = console_name.lower().strip()

    for row in rows[:5]:  # Check top 5 results
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        title_link = cols[1].find("a")
        if not title_link:
            continue

        result_console = cols[2].get_text(strip=True).lower().strip() if len(cols) > 2 else ""

        # Skip PAL/JP versions — we want NTSC (US) prices
        if "pal" in result_console or "jp " in result_console or "japanese" in result_console:
            continue

        # Verify console matches
        if target_console not in result_console and result_console not in target_console:
            continue

        return {
            "title": title_link.get_text(strip=True),
            "console": cols[2].get_text(strip=True),
            "loose": parse_price_text(cols[3].get_text(strip=True)) if len(cols) > 3 else 0,
            "cib": parse_price_text(cols[4].get_text(strip=True)) if len(cols) > 4 else 0,
            "new": parse_price_text(cols[5].get_text(strip=True)) if len(cols) > 5 else 0,
        }

    return None


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
    """Fetch all game products with variants."""
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

            # Skip Pokemon cards
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

        if page % 20 == 0:
            log(f"  Fetched {len(products)} products (page {page})...")

    log(f"  Total: {len(products)} game products")
    return products


# ── Pricing ───────────────────────────────────────────────────────────

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

def strip_console_suffix(title):
    """Remove ' - NES Game', ' - PS2 Game' etc. from Shopify titles."""
    return re.sub(
        r"\s*[-–]\s*(NES|SNES|N64|Nintendo|Gameboy|Game Boy|Genesis|PS[123P]|"
        r"Gamecube|Dreamcast|Saturn|GBA|Playstation|Xbox|Wii|Sega|Atari|"
        r"TurboGrafx|GBC).*$",
        "", title, flags=re.IGNORECASE
    ).strip()


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Search-based full price refresh")
    parser.add_argument("--apply", action="store_true", help="Apply changes to Shopify")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    args = parser.parse_args()

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        log("ERROR: Shopify credentials not configured")
        sys.exit(1)

    log("=" * 60)
    log(f"SEARCH-BASED PRICE REFRESH — {'APPLY' if args.apply else 'REPORT'}")
    log(f"Multiplier: {MULTIPLIER}x | Min profit: ${MIN_PROFIT:.2f}")
    log(f"Log: {LOG_FILE}")
    log(f"CSV: {CSV_FILE}")
    log("=" * 60)

    init_csv()
    products = fetch_all_shopify_products()

    # Load checkpoint if resuming
    completed_ids = set()
    if args.resume and CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            completed_ids = set(json.load(f).get("completed", []))
        log(f"Resuming — {len(completed_ids)} products already done")

    stats = {
        "total": len(products),
        "searched": 0,
        "matched": 0,
        "no_match": 0,
        "loose_updated": 0,
        "cib_updated": 0,
        "no_change": 0,
        "errors": 0,
        "skipped_resume": 0,
    }

    start_time = time.time()

    for i, sp in enumerate(products):
        if sp["id"] in completed_ids:
            stats["skipped_resume"] += 1
            continue

        # Determine console from tags
        console_name = None
        for tag in sp["tags"]:
            cn = TAG_TO_CONSOLE.get(tag.lower().strip())
            if cn:
                console_name = cn
                break

        if not console_name:
            stats["no_match"] += 1
            continue

        # Strip console suffix from title for cleaner search
        game_title = strip_console_suffix(sp["title"])

        # Search PriceCharting
        result = search_pricecharting(game_title, console_name)
        stats["searched"] += 1
        time.sleep(SEARCH_DELAY)

        if not result:
            stats["no_match"] += 1
            write_csv_row([sp["title"], console_name, "", "", "", "", "", "", "", "NO_MATCH"])
            # Progress update
            if stats["searched"] % 50 == 0:
                elapsed = time.time() - start_time
                rate = stats["searched"] / elapsed * 3600
                remaining = (len(products) - i) / (rate / 3600) if rate > 0 else 0
                log(f"  Progress: {i+1}/{len(products)} | Matched: {stats['matched']} | "
                    f"Rate: {rate:.0f}/hr | ETA: {remaining/60:.0f}min")
            completed_ids.add(sp["id"])
            continue

        stats["matched"] += 1

        # Update each variant
        for variant in sp["variants"]:
            vt = variant["title"]
            old_price = variant["price"]
            is_cib = "complete" in vt or "cib" in vt or "box" in vt
            is_loose = not is_cib

            if is_loose and result["loose"] > 0:
                market = result["loose"]
            elif is_cib and result["cib"] > 0:
                market = result["cib"]
            else:
                continue

            new_price = calc_sell_price(market)
            profit = calc_profit(new_price, market)
            diff = round(new_price - old_price, 2)

            if abs(diff) < 0.50:
                stats["no_change"] += 1
                continue

            variant_type = "cib" if is_cib else "loose"
            status = "APPLIED" if args.apply else "PREVIEW"

            write_csv_row([sp["title"], console_name, vt, variant_type,
                          f"{market:.2f}", f"{old_price:.2f}", f"{new_price:.2f}",
                          f"{diff:.2f}", f"{profit:.2f}", status])

            if args.apply:
                try:
                    res = shopify_gql(
                        """mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                          productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                            productVariants { id price }
                            userErrors { field message }
                          }
                        }""",
                        {"productId": sp["id"], "variants": [{"id": variant["id"], "price": str(new_price)}]},
                    )
                    errors = res.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
                    if errors:
                        stats["errors"] += 1
                        log(f"  ERROR: {sp['title']} [{variant_type}]: {errors[0]['message']}")
                    else:
                        if is_cib:
                            stats["cib_updated"] += 1
                        else:
                            stats["loose_updated"] += 1
                except Exception as e:
                    stats["errors"] += 1
                    log(f"  ERROR: {sp['title']}: {e}")

                time.sleep(SHOPIFY_DELAY)

        completed_ids.add(sp["id"])

        # Save checkpoint every 100 products
        if stats["searched"] % 100 == 0:
            with open(CHECKPOINT_FILE, "w") as f:
                json.dump({"completed": list(completed_ids), "timestamp": datetime.now().isoformat()}, f)
            elapsed = time.time() - start_time
            rate = stats["searched"] / elapsed * 3600
            remaining = (len(products) - i) / (rate / 3600) if rate > 0 else 0
            log(f"  Checkpoint: {i+1}/{len(products)} | Matched: {stats['matched']} | "
                f"Loose: {stats['loose_updated']} | CIB: {stats['cib_updated']} | "
                f"Rate: {rate:.0f}/hr | ETA: {remaining/60:.0f}min")

    # Final summary
    elapsed = time.time() - start_time
    log("\n" + "=" * 60)
    log("RESULTS")
    log("=" * 60)
    log(f"  Total products:       {stats['total']}")
    log(f"  Searched:             {stats['searched']}")
    log(f"  Matched:              {stats['matched']}")
    log(f"  No match:             {stats['no_match']}")
    log(f"  Loose prices updated: {stats['loose_updated']}")
    log(f"  CIB prices updated:   {stats['cib_updated']}")
    log(f"  No significant change:{stats['no_change']}")
    log(f"  Errors:               {stats['errors']}")
    log(f"  Time: {elapsed/60:.1f} minutes")
    log(f"  Match rate: {stats['matched']/max(stats['searched'],1)*100:.1f}%")

    if log_handle:
        log_handle.close()
    if csv_file_handle:
        csv_file_handle.close()

    # Clean up checkpoint on successful completion
    if CHECKPOINT_FILE.exists() and stats["searched"] == stats["total"] - stats["skipped_resume"]:
        CHECKPOINT_FILE.unlink()

    print(f"\nLog: {LOG_FILE}")
    print(f"CSV: {CSV_FILE}")


if __name__ == "__main__":
    main()
