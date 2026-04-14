#!/usr/bin/env python3
"""
8-Bit Legacy — Unified Price Refresh (PriceCharting primary, eBay fallback)

For every product in --ids-file (or the full retro-games catalog if omitted):
  1. Try PriceCharting search (up to 5 query variants)
  2. If PC returns nothing, fall back to eBay Browse API active listings
     using 25th-percentile-of-trimmed-median for each variant separately
  3. Apply market × 1.35 × $X.99 rounding, write to Shopify, log everything

Pokemon cards (SKU prefix PKM-) are skipped — they run on the TCGPlayer sync job.

Usage:
  python3 scripts/refresh-prices-unified.py                             # report mode (no writes)
  python3 scripts/refresh-prices-unified.py --apply                     # write changes to Shopify
  python3 scripts/refresh-prices-unified.py --apply --ids-file data/refresh-union-ids.json
  python3 scripts/refresh-prices-unified.py --apply --resume            # resume from checkpoint
  python3 scripts/refresh-prices-unified.py --apply --limit 20          # smoke test
"""

import argparse
import base64
import csv
import json
import os
import re
import statistics
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

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
EBAY_APP_ID = os.getenv("EBAY_APP_ID", "")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID", "")

with open(CONFIG_DIR / "pricing.json") as f:
    PRICING = json.load(f)

MULTIPLIER = PRICING["default_multiplier"]
ROUND_TO = PRICING.get("round_to", 0.99)
FEE_PCT = PRICING["shopify_fee_percent"]
FEE_FIXED = PRICING["shopify_fee_fixed"]
MIN_PROFIT = PRICING["minimum_profit_usd"]

SEARCH_DELAY = 2.5                     # PC pacing — slightly slower than last run to avoid re-block
EBAY_DELAY = 0.8                       # eBay allows ~5K/day, this keeps us well under
SHOPIFY_DELAY = 0.3
MAX_MARKET_PRICE = 800.0
MIN_EBAY_SAMPLE = 4                    # need at least this many active listings to trust median
EBAY_ACTIVE_DISCOUNT = 0.92            # active-listing median × this ≈ sold-price estimate

CHECKPOINT_FILE = LOG_DIR / "refresh-unified-checkpoint.json"

HEADERS_PC = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

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

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"refresh-unified-{timestamp}.log"
CSV_FILE = LOG_DIR / f"refresh-unified-{timestamp}.csv"

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
    csv_writer.writerow(["product", "console", "variant", "type", "source",
                         "market_price", "old_price", "new_price", "diff",
                         "profit", "status", "notes"])


def write_csv_row(row):
    if csv_writer:
        csv_writer.writerow(row)
        csv_file_handle.flush()


# ── PriceCharting ─────────────────────────────────────────────────────

def parse_price_text(text):
    match = re.search(r"[\$]?([\d,]+\.?\d*)", text.replace(",", ""))
    return float(match.group(1)) if match else 0.0


def title_similarity(query_title, result_title):
    qt = re.sub(r"[^a-z0-9 ]", "", query_title.lower()).split()
    rt_clean = re.sub(
        r"(NES|SNES|Nintendo 64|Gamecube|Gameboy|Genesis|Playstation|PS[123]|"
        r"Dreamcast|Saturn|GBA|Xbox|Wii|Sega|Atari|TurboGrafx|GameBoy|Game Boy).*$",
        "", result_title, flags=re.IGNORECASE,
    ).strip()
    rt = re.sub(r"[^a-z0-9 ]", "", rt_clean.lower()).split()
    if not qt or not rt:
        return 0.0
    query_set, result_set = set(qt), set(rt)
    extra_words = result_set - query_set
    sequel_indicators = {"2", "3", "4", "5", "6", "7", "8", "9", "ii", "iii", "iv",
                         "part", "second", "math", "assassin", "case", "screw", "attack",
                         "special", "edition", "deluxe", "bundle", "collection"}
    if extra_words & sequel_indicators:
        return 0.1
    common = query_set & result_set
    score = len(common) / max(len(query_set), len(result_set))
    if extra_words:
        score *= max(0.5, 1.0 - len(extra_words) * 0.2)
    return score


def _query_variants(title):
    yield title
    if ":" in title:
        yield title.split(":", 1)[0].strip()
    if title.lower().startswith("the "):
        yield title[4:]
    if " & " in title:
        yield title.replace(" & ", " and ", 1)
    if " and " in title.lower():
        yield re.sub(r"\s+and\s+", " & ", title, count=1, flags=re.IGNORECASE)
    words = title.split()
    if len(words) >= 4:
        yield " ".join(words[:3])


def _fetch_pc_candidates(query, console_name):
    url = f"https://www.pricecharting.com/search-products?q={quote_plus(query)}&type=videogames"
    try:
        resp = requests.get(url, headers=HEADERS_PC, timeout=15)
        resp.raise_for_status()
    except Exception:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"id": "games_table"})
    if not table:
        return None
    tbody = table.find("tbody")
    if not tbody:
        return None
    target_console = console_name.lower().strip()
    candidates = []
    for row in tbody.find_all("tr")[:8]:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue
        link = cols[1].find("a")
        if not link:
            continue
        result_title = link.get_text(strip=True)
        result_console = cols[2].get_text(strip=True).lower().strip()
        if "pal" in result_console or "jp " in result_console or "japanese" in result_console:
            continue
        if target_console not in result_console and result_console not in target_console:
            continue
        candidates.append({
            "title": result_title,
            "console": cols[2].get_text(strip=True),
            "loose": parse_price_text(cols[3].get_text(strip=True)) if len(cols) > 3 else 0,
            "cib": parse_price_text(cols[4].get_text(strip=True)) if len(cols) > 4 else 0,
        })
    return candidates or None


def search_pricecharting(game_title, console_name):
    attempts = 0
    found = None
    for variant in _query_variants(game_title):
        query = f"{variant} {console_name}"
        result = _fetch_pc_candidates(query, console_name)
        attempts += 1
        if result:
            found = result
            break
        if attempts > 1:
            time.sleep(1.2)
    if not found:
        return None
    for c in found:
        c["similarity"] = title_similarity(game_title, c["title"])
    best = max(found, key=lambda c: c["similarity"])
    if best["similarity"] < 0.3:
        return None
    if best["loose"] > MAX_MARKET_PRICE:
        best["loose"] = 0
    if best["cib"] > MAX_MARKET_PRICE:
        best["cib"] = 0
    return best


# ── eBay ──────────────────────────────────────────────────────────────

_ebay_token_cache = {"token": None, "expires_at": 0}


def get_ebay_token():
    if _ebay_token_cache["token"] and time.time() < _ebay_token_cache["expires_at"] - 60:
        return _ebay_token_cache["token"]
    creds = base64.b64encode(f"{EBAY_APP_ID}:{EBAY_CERT_ID}".encode()).decode()
    resp = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _ebay_token_cache["token"] = data["access_token"]
    _ebay_token_cache["expires_at"] = time.time() + data.get("expires_in", 7200)
    return _ebay_token_cache["token"]


def trimmed_median(prices, trim_pct=0.15):
    if len(prices) < MIN_EBAY_SAMPLE:
        return None
    prices = sorted(prices)
    trim_n = int(len(prices) * trim_pct)
    trimmed = prices[trim_n: len(prices) - trim_n] if trim_n else prices
    if not trimmed:
        return None
    return statistics.median(trimmed)


ROMAN_TO_ARABIC = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6",
                   "vii": "7", "viii": "8", "ix": "9", "x": "10"}


def _normalize_numeral(w):
    return ROMAN_TO_ARABIC.get(w, w)


def _classify_listing(title_lower):
    """Return 'cib', 'loose', or None for titles we should skip."""
    bad = ("lot of", "repro", "reproduction", "bootleg", "pal ", "pal-", "japanese",
           "japan version", "not working", "for parts", "read description",
           "untested", "damaged", "case only", "manual only", "box only")
    if any(b in title_lower for b in bad):
        return None
    if any(s in title_lower for s in ("sealed", "brand new", "factory sealed", "new sealed")):
        return None
    is_cib = any(k in title_lower for k in (
        "complete in box", " cib ", " cib,", " cib!", "cib complete",
        "complete w/ box", "w/ box and manual", "with box and manual",
        "box, manual", "complete with manual and box", "w/manual and box",
    )) or (
        ("complete" in title_lower and ("box" in title_lower or "manual" in title_lower))
    )
    if is_cib:
        return "cib"
    # Heuristic "loose": default unless listing mentions CIB keywords
    if any(k in title_lower for k in ("cib", "complete in box", "w/ box", "with box")):
        return None  # ambiguous CIB-ish that didn't quite hit above
    return "loose"


def ebay_search_prices(game_title, console_name):
    """Return {'loose': {...}|None, 'cib': {...}|None} — single broad query, classify in code."""
    try:
        token = get_ebay_token()
    except Exception as e:
        log(f"  eBay auth error: {e}")
        return {"loose": None, "cib": None}
    try:
        resp = requests.get(
            "https://api.ebay.com/buy/browse/v1/item_summary/search",
            headers={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"},
            params={
                "q": f"{game_title} {console_name}",
                "filter": "buyingOptions:{FIXED_PRICE},deliveryCountry:US,price:[1..2000],priceCurrency:USD",
                "sort": "price",
                "limit": 100,
            },
            timeout=20,
        )
        resp.raise_for_status()
    except Exception as e:
        log(f"  eBay search error: {e}")
        return {"loose": None, "cib": None}

    items = resp.json().get("itemSummaries", [])
    query_words = set(re.sub(r"[^a-z0-9 ]", " ", game_title.lower()).split())
    query_words -= {"the", "a", "an", "of", "and", "&", "in", "for", "to"}
    query_words = {_normalize_numeral(w) for w in query_words}
    query_numbers = {w for w in query_words if re.fullmatch(r"[0-9]+", w)}
    query_has_number = bool(query_numbers)

    buckets = {"loose": [], "cib": []}
    for item in items:
        try:
            p = float(item["price"]["value"])
        except (KeyError, TypeError, ValueError):
            continue
        title_lower = item.get("title", "").lower()
        variant = _classify_listing(title_lower)
        if variant is None:
            continue
        listing_words = set(re.sub(r"[^a-z0-9 ]", " ", title_lower).split())
        listing_words = {_normalize_numeral(w) for w in listing_words}
        meaningful_query = query_words - {console_name.lower()}
        if meaningful_query:
            overlap = len(meaningful_query & listing_words) / len(meaningful_query)
            if overlap < 0.6:
                continue
        listing_numbers = {w for w in listing_words if re.fullmatch(r"[0-9]+", w)}
        stray_numbers = {n for n in (listing_numbers - query_numbers)
                         if not (n.isdigit() and int(n) > 1900)}
        if not query_has_number and stray_numbers:
            continue
        if query_has_number and not (query_numbers & listing_numbers):
            continue
        buckets[variant].append(p)

    out = {}
    for kind, prices in buckets.items():
        median = trimmed_median(prices)
        if median is None:
            out[kind] = None
            continue
        sold_estimate = median * EBAY_ACTIVE_DISCOUNT
        if sold_estimate > MAX_MARKET_PRICE:
            out[kind] = None
            continue
        out[kind] = {"market": round(sold_estimate, 2), "sample_size": len(prices),
                     "raw_median": round(median, 2)}
    return out


# ── Shopify ───────────────────────────────────────────────────────────

def shopify_gql(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(
        f"https://{SHOPIFY_STORE}/admin/api/2024-10/graphql.json",
        headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all_shopify_products():
    log("Fetching all Shopify products…")
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
                id title tags
                variants(first: 10) {{
                  edges {{ node {{ id title price sku }} }}
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
            if any(v["sku"].startswith("PKM-") for v in variants):
                continue
            products.append({
                "id": node["id"],
                "title": node["title"],
                "tags": node.get("tags", []),
                "variants": variants,
            })
        if not data.get("data", {}).get("products", {}).get("pageInfo", {}).get("hasNextPage", False) or not edges:
            break
        cursor = edges[-1]["cursor"]
        time.sleep(0.5)
        if page % 20 == 0:
            log(f"  Fetched {len(products)} products (page {page})…")
    log(f"  Total: {len(products)} game products")
    return products


# ── Pricing helpers ───────────────────────────────────────────────────

def calc_sell_price(market):
    raw = market * MULTIPLIER
    if ROUND_TO is not None:
        rounded = int(raw) + ROUND_TO
        if rounded < raw:
            rounded += 1.0
        return round(rounded, 2)
    return round(raw, 2)


def calc_profit(sell, market):
    fee = sell * FEE_PCT + FEE_FIXED
    return round(sell - market - fee, 2)


def strip_console_suffix(title):
    return re.sub(
        r"\s*[-–]\s*(NES|SNES|N64|Nintendo|Gameboy|Game Boy|Genesis|PS[123P]|"
        r"Gamecube|Dreamcast|Saturn|GBA|Playstation|Xbox|Wii|Sega|Atari|"
        r"TurboGrafx|GBC).*$",
        "", title, flags=re.IGNORECASE,
    ).strip()


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Unified PC+eBay price refresh")
    parser.add_argument("--apply", action="store_true", help="Write changes to Shopify")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--ids-file", help="JSON file with list of Shopify product GIDs to process")
    parser.add_argument("--limit", type=int, help="Cap number of products processed (smoke test)")
    parser.add_argument("--no-ebay", action="store_true", help="Skip eBay fallback (PC only)")
    args = parser.parse_args()

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        log("ERROR: Shopify credentials missing")
        sys.exit(1)
    if not args.no_ebay and (not EBAY_APP_ID or not EBAY_CERT_ID):
        log("WARNING: eBay creds missing — running PC-only")
        args.no_ebay = True

    log("=" * 60)
    log(f"UNIFIED PRICE REFRESH — {'APPLY' if args.apply else 'REPORT'}")
    log(f"Multiplier: {MULTIPLIER}× | Round to: $X.{int((ROUND_TO or 0)*100):02d} | Min profit: ${MIN_PROFIT:.2f}")
    log(f"eBay fallback: {'OFF' if args.no_ebay else 'ON'} (active×{EBAY_ACTIVE_DISCOUNT} trimmed median, min {MIN_EBAY_SAMPLE} comps)")
    log(f"Log: {LOG_FILE}")
    log(f"CSV: {CSV_FILE}")
    log("=" * 60)

    init_csv()
    products = fetch_all_shopify_products()

    if args.ids_file:
        with open(args.ids_file) as f:
            allow = set(json.load(f))
        before = len(products)
        products = [p for p in products if p["id"] in allow]
        log(f"Filtered to --ids-file list: {len(products)}/{before} match")

    if args.limit:
        products = products[: args.limit]
        log(f"Limited to first {len(products)} products")

    completed_ids = set()
    if args.resume and CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            completed_ids = set(json.load(f).get("completed", []))
        log(f"Resume mode — {len(completed_ids)} products already done")

    stats = {"total": len(products), "pc_match": 0, "ebay_match": 0,
             "no_match": 0, "loose_updated": 0, "cib_updated": 0,
             "no_change": 0, "errors": 0, "skipped": 0}

    start = time.time()

    for i, sp in enumerate(products):
        if sp["id"] in completed_ids:
            stats["skipped"] += 1
            continue

        # Figure out the console
        console_name = None
        for tag in sp["tags"]:
            cn = TAG_TO_CONSOLE.get(tag.lower().strip())
            if cn:
                console_name = cn
                break
        if not console_name:
            stats["no_match"] += 1
            write_csv_row([sp["title"], "", "", "", "", "", "", "", "", "", "NO_CONSOLE", "no console tag"])
            completed_ids.add(sp["id"])
            continue

        game_title = strip_console_suffix(sp["title"])

        # Try PC first
        pc = search_pricecharting(game_title, console_name)
        time.sleep(SEARCH_DELAY)

        # Per-variant market price + source
        loose_market = pc["loose"] if pc and pc.get("loose", 0) > 0 else 0
        cib_market = pc["cib"] if pc and pc.get("cib", 0) > 0 else 0
        loose_source = "pc" if loose_market > 0 else ""
        cib_source = "pc" if cib_market > 0 else ""

        # Fall back to eBay for whichever variant PC missed (single query, splits in code)
        if not args.no_ebay and (loose_market == 0 or cib_market == 0):
            eb = ebay_search_prices(game_title, console_name)
            time.sleep(EBAY_DELAY)
            if loose_market == 0 and eb.get("loose"):
                loose_market = eb["loose"]["market"]
                loose_source = f"ebay({eb['loose']['sample_size']})"
            if cib_market == 0 and eb.get("cib"):
                cib_market = eb["cib"]["market"]
                cib_source = f"ebay({eb['cib']['sample_size']})"

        if loose_market > 0 or cib_market > 0:
            if loose_source.startswith("pc") or cib_source.startswith("pc"):
                stats["pc_match"] += 1
            elif loose_source.startswith("ebay") or cib_source.startswith("ebay"):
                stats["ebay_match"] += 1
        else:
            stats["no_match"] += 1
            write_csv_row([sp["title"], console_name, "", "", "", "", "", "", "", "", "NO_MATCH", "PC and eBay both failed"])
            completed_ids.add(sp["id"])
            if (i + 1) % 25 == 0:
                elapsed = time.time() - start
                rate = (i + 1) / elapsed
                remaining = (len(products) - i - 1) / rate if rate > 0 else 0
                log(f"  Progress: {i+1}/{len(products)} | PC: {stats['pc_match']} | eBay: {stats['ebay_match']} | "
                    f"No match: {stats['no_match']} | ETA: {remaining/60:.0f}min")
            continue

        # Update each variant
        for variant in sp["variants"]:
            vt = variant["title"]
            is_cib = "complete" in vt or "cib" in vt or "box" in vt
            if is_cib and cib_market > 0:
                market, source, vtype = cib_market, cib_source, "cib"
            elif not is_cib and loose_market > 0:
                market, source, vtype = loose_market, loose_source, "loose"
            else:
                continue

            old_price = variant["price"]
            new_price = calc_sell_price(market)
            diff = round(new_price - old_price, 2)
            profit = calc_profit(new_price, market)

            if abs(diff) < 0.50:
                stats["no_change"] += 1
                write_csv_row([sp["title"], console_name, vt, vtype, source,
                               f"{market:.2f}", f"{old_price:.2f}", f"{new_price:.2f}",
                               f"{diff:.2f}", f"{profit:.2f}", "NO_CHANGE", ""])
                continue

            status = "APPLIED" if args.apply else "PREVIEW"
            write_csv_row([sp["title"], console_name, vt, vtype, source,
                           f"{market:.2f}", f"{old_price:.2f}", f"{new_price:.2f}",
                           f"{diff:.2f}", f"{profit:.2f}", status, ""])

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
                        log(f"  SHOPIFY_ERROR: {sp['title']} [{vtype}]: {errors[0]['message']}")
                    else:
                        if is_cib:
                            stats["cib_updated"] += 1
                        else:
                            stats["loose_updated"] += 1
                except Exception as e:
                    stats["errors"] += 1
                    log(f"  SHOPIFY_EXC: {sp['title']}: {e}")
                time.sleep(SHOPIFY_DELAY)

        completed_ids.add(sp["id"])

        if (i + 1) % 50 == 0:
            with open(CHECKPOINT_FILE, "w") as f:
                json.dump({"completed": list(completed_ids), "timestamp": datetime.now().isoformat()}, f)
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            remaining = (len(products) - i - 1) / rate if rate > 0 else 0
            log(f"  Checkpoint: {i+1}/{len(products)} | PC: {stats['pc_match']} | eBay: {stats['ebay_match']} | "
                f"Loose upd: {stats['loose_updated']} | CIB upd: {stats['cib_updated']} | "
                f"No match: {stats['no_match']} | ETA: {remaining/60:.0f}min")

    elapsed = time.time() - start
    log("\n" + "=" * 60)
    log("RESULTS")
    log("=" * 60)
    log(f"  Total products:       {stats['total']}")
    log(f"  PC matches:           {stats['pc_match']}")
    log(f"  eBay matches:         {stats['ebay_match']}")
    log(f"  No match (both failed): {stats['no_match']}")
    log(f"  Loose prices updated: {stats['loose_updated']}")
    log(f"  CIB prices updated:   {stats['cib_updated']}")
    log(f"  No change (<$0.50):   {stats['no_change']}")
    log(f"  Errors:               {stats['errors']}")
    log(f"  Skipped (resume):     {stats['skipped']}")
    log(f"  Time: {elapsed/60:.1f} min")
    total_successful = stats["pc_match"] + stats["ebay_match"]
    if stats["total"] > 0:
        log(f"  Match rate: {total_successful/max(stats['total']-stats['skipped'],1)*100:.1f}%")

    if log_handle:
        log_handle.close()
    if csv_file_handle:
        csv_file_handle.close()

    if CHECKPOINT_FILE.exists() and stats["skipped"] + stats["pc_match"] + stats["ebay_match"] + stats["no_match"] >= stats["total"]:
        CHECKPOINT_FILE.unlink()

    print(f"\nLog: {LOG_FILE}")
    print(f"CSV: {CSV_FILE}")


if __name__ == "__main__":
    main()
