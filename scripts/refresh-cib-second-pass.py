#!/usr/bin/env python3
"""
Second-pass CIB refresh for synthetic-CIB products the main sweep missed.

Uses RELAXED eBay sampling vs refresh-prices-unified.py:
- MIN_EBAY_SAMPLE = 3 (vs 4 main sweep — bumped from 2 after smoke test showed outliers)
- Sorts by price DESC (CIB listings skew high, not low)
- Broader CIB keyword match (accepts "in box" or "w/ manual" alone)
- Secondary query variant: title + console + "cib"

After eBay attempts, applies ratio sanity check:
  If CIB < Loose × 1.3, set CIB = Loose × 1.8 (clean synthetic from fresh loose).
Logged as source=synthetic_ratio_repair.

Usage:
  python3 scripts/refresh-cib-second-pass.py --apply
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

import requests
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

EBAY_DELAY = 0.8
SHOPIFY_DELAY = 0.3
MIN_EBAY_SAMPLE = 3
EBAY_ACTIVE_DISCOUNT = 0.92
MAX_MARKET_PRICE = 1500.0           # higher cap for high-value rarities
RATIO_FLOOR = 1.3                   # CIB must be ≥ Loose × this
RATIO_CEILING = 3.5                 # CIB/Loose > this w/ thin samples = outlier
OUTLIER_SAMPLE_THRESHOLD = 8        # trust high ratio only if sample ≥ this
SYNTHETIC_UPLIFT = 1.8              # clean synthetic when eBay fails

ROMAN_TO_ARABIC = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6",
                   "vii": "7", "viii": "8", "ix": "9", "x": "10"}

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"cib-second-pass-{timestamp}.log"
CSV_FILE = LOG_DIR / f"cib-second-pass-{timestamp}.csv"

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
    csv_writer.writerow(["product", "console", "source", "loose_price",
                         "old_cib", "new_cib", "ratio", "status", "notes"])


def write_csv_row(row):
    if csv_writer:
        csv_writer.writerow(row)
        csv_file_handle.flush()


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


def _normalize_numeral(w):
    return ROMAN_TO_ARABIC.get(w, w)


def _title_matches(game_title, listing_title, console_name):
    """Relaxed title overlap check."""
    q = set(re.sub(r"[^a-z0-9 ]", " ", game_title.lower()).split())
    q -= {"the", "a", "an", "of", "and", "&", "in", "for", "to"}
    q = {_normalize_numeral(w) for w in q}
    qnums = {w for w in q if re.fullmatch(r"[0-9]+", w)}
    lw = set(re.sub(r"[^a-z0-9 ]", " ", listing_title.lower()).split())
    lw = {_normalize_numeral(w) for w in lw}
    lnums = {w for w in lw if re.fullmatch(r"[0-9]+", w)}
    meaningful = q - {console_name.lower()}
    if meaningful:
        overlap = len(meaningful & lw) / len(meaningful)
        if overlap < 0.5:          # relaxed from 0.6
            return False
    stray = {n for n in (lnums - qnums) if not (n.isdigit() and int(n) > 1900)}
    if not qnums and stray:
        return False
    if qnums and not (qnums & lnums):
        return False
    return True


def _is_cib_listing(title_lower):
    """Broader CIB matcher — any box/manual mention that isn't explicitly loose."""
    bad = ("lot of", "repro", "bootleg", "pal ", "pal-", "japanese", "japan version",
           "not working", "for parts", "sealed", "brand new", "factory sealed",
           "case only", "manual only", "box only", "empty box", "insert only",
           "cartridge only", "cart only", "loose cart", "loose cartridge",
           "wata", "vga", " psa ", "cgc", "pca ", "graded", "authenticated",
           "mint condition", "museum", "collector's grade")
    if any(b in title_lower for b in bad):
        return False
    return any(k in title_lower for k in ("complete", "cib", "in box", "w/ box", "with box",
                                           "w/ manual", "with manual", "w/manual"))


def ebay_cib_price(game_title, console_name):
    """Broader CIB search: two queries (w/ and w/o 'cib' suffix), DESC + ASC sort."""
    try:
        token = get_ebay_token()
    except Exception as e:
        log(f"  eBay auth error: {e}")
        return None

    prices = []
    for query_suffix, sort in [("complete in box", "price desc"),
                               ("cib", "price desc"),
                               ("", "price desc")]:
        try:
            q = f"{game_title} {console_name} {query_suffix}".strip()
            resp = requests.get(
                "https://api.ebay.com/buy/browse/v1/item_summary/search",
                headers={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"},
                params={
                    "q": q,
                    "filter": "buyingOptions:{FIXED_PRICE},deliveryCountry:US,price:[5..3000],priceCurrency:USD",
                    "sort": sort,
                    "limit": 50,
                },
                timeout=20,
            )
            resp.raise_for_status()
        except Exception as e:
            log(f"  eBay query error ({query_suffix}): {e}")
            continue
        time.sleep(EBAY_DELAY)
        for item in resp.json().get("itemSummaries", []):
            try:
                p = float(item["price"]["value"])
            except (KeyError, TypeError, ValueError):
                continue
            title_lower = item.get("title", "").lower()
            if not _is_cib_listing(title_lower):
                continue
            if not _title_matches(game_title, title_lower, console_name):
                continue
            prices.append(p)
        if len(prices) >= MIN_EBAY_SAMPLE * 2:
            break

    # Dedupe near-identical prices (same listing can appear in multiple searches)
    unique_prices = sorted(set(round(p, 2) for p in prices))
    if len(unique_prices) < MIN_EBAY_SAMPLE:
        return None
    # Trim 15% each end, median
    n = len(unique_prices)
    trim = int(n * 0.15)
    trimmed = unique_prices[trim:n - trim] if trim else unique_prices
    median = statistics.median(trimmed)
    sold_estimate = median * EBAY_ACTIVE_DISCOUNT
    if sold_estimate > MAX_MARKET_PRICE:
        return None
    return {"market": round(sold_estimate, 2), "sample_size": len(unique_prices)}


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


def fetch_product_variants(product_id):
    query = """
    query($id: ID!) {
      product(id: $id) {
        id title tags
        variants(first: 10) {
          edges { node { id title price sku } }
        }
      }
    }
    """
    data = shopify_gql(query, {"id": product_id})
    return data.get("data", {}).get("product")


def calc_sell_price(market):
    raw = market * MULTIPLIER
    if ROUND_TO is not None:
        rounded = int(raw) + ROUND_TO
        if rounded < raw:
            rounded += 1.0
        return round(rounded, 2)
    return round(raw, 2)


def strip_console_suffix(title):
    return re.sub(
        r"\s*[-–]\s*(NES|SNES|N64|Nintendo|Gameboy|Game Boy|Genesis|PS[123P]|"
        r"Gamecube|Dreamcast|Saturn|GBA|Playstation|Xbox|Wii|Sega|Atari|"
        r"TurboGrafx|GBC).*$",
        "", title, flags=re.IGNORECASE,
    ).strip()


TAG_TO_CONSOLE = {
    "nes": "NES", "snes": "SNES", "super nintendo": "SNES",
    "nintendo 64": "Nintendo 64", "n64": "Nintendo 64",
    "gamecube": "Gamecube", "nintendo gamecube": "Gamecube",
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


def main():
    parser = argparse.ArgumentParser(description="CIB second-pass refresh (relaxed)")
    parser.add_argument("--apply", action="store_true", help="Write changes to Shopify")
    parser.add_argument("--ids-file", default=str(DATA_DIR / "remaining-synthetic-ids.json"),
                        help="JSON file listing Shopify product GIDs to process")
    parser.add_argument("--limit", type=int, help="Smoke-test: cap number of products")
    args = parser.parse_args()

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN or not EBAY_APP_ID or not EBAY_CERT_ID:
        log("ERROR: missing credentials"); sys.exit(1)

    log("=" * 60)
    log(f"CIB SECOND-PASS REFRESH — {'APPLY' if args.apply else 'REPORT'}")
    log(f"Sampling: min {MIN_EBAY_SAMPLE} comps, title overlap 0.5, broader CIB match")
    log(f"Ratio floor: CIB ≥ Loose × {RATIO_FLOOR} (synthetic {SYNTHETIC_UPLIFT}x fallback)")
    log(f"Log: {LOG_FILE}")
    log(f"CSV: {CSV_FILE}")
    log("=" * 60)

    init_csv()
    with open(args.ids_file) as f:
        ids = json.load(f)
    if args.limit:
        ids = ids[: args.limit]
    log(f"Processing {len(ids)} products")

    stats = {"total": len(ids), "ebay_cib": 0, "synthetic_repair": 0,
             "no_cib_variant": 0, "cib_already_ok": 0, "errors": 0}
    start = time.time()

    for i, pid in enumerate(ids):
        try:
            product = fetch_product_variants(pid)
        except Exception as e:
            log(f"  fetch error for {pid}: {e}")
            stats["errors"] += 1
            continue
        if not product:
            continue

        title_full = product["title"]
        game_title = strip_console_suffix(title_full)
        console_name = None
        for tag in product.get("tags", []):
            t = tag.lower().strip()
            if t.startswith("console:"):
                t = t.split(":", 1)[1].strip()
            cn = TAG_TO_CONSOLE.get(t)
            if cn:
                console_name = cn
                break
        if not console_name:
            write_csv_row([title_full, "", "", "", "", "", "", "NO_CONSOLE", ""])
            continue

        variants = product.get("variants", {}).get("edges", [])
        loose = None
        cib = None
        for edge in variants:
            v = edge["node"]
            vt = (v.get("title") or "").lower()
            if any(k in vt for k in ("complete", "cib", "box")):
                cib = v
            else:
                loose = v
        if not cib or not loose:
            stats["no_cib_variant"] += 1
            write_csv_row([title_full, console_name, "", "", "", "", "", "NO_VARIANTS", ""])
            continue

        loose_price = float(loose["price"])
        old_cib = float(cib["price"])

        # Try aggressive eBay CIB query
        eb = ebay_cib_price(game_title, console_name)
        time.sleep(EBAY_DELAY)

        if eb and eb["market"] > 0:
            new_cib_market = eb["market"]
            new_cib = calc_sell_price(new_cib_market)
            ebay_ratio = new_cib / loose_price if loose_price else 0
            # Ceiling guard: thin-sample high ratios are likely graded/outlier noise
            if ebay_ratio > RATIO_CEILING and eb["sample_size"] < OUTLIER_SAMPLE_THRESHOLD:
                new_cib_market = loose_price / MULTIPLIER * SYNTHETIC_UPLIFT
                new_cib = calc_sell_price(new_cib_market)
                source = f"synthetic_outlier_guard(ebay_was_{eb['market']:.2f}_n={eb['sample_size']})"
            # Floor guard: eBay says CIB < Loose × 1.3 — repair
            elif new_cib < loose_price * RATIO_FLOOR:
                new_cib_market_synth = loose_price / MULTIPLIER * SYNTHETIC_UPLIFT
                new_cib_synth = calc_sell_price(new_cib_market_synth)
                if new_cib_synth > new_cib:
                    new_cib = new_cib_synth
                    source = f"synthetic_ratio_repair(ebay_was_{eb['market']:.2f})"
                else:
                    source = f"ebay({eb['sample_size']})"
            else:
                source = f"ebay({eb['sample_size']})"
        else:
            # eBay failed — apply ratio sanity repair
            new_cib_market = loose_price / MULTIPLIER * SYNTHETIC_UPLIFT
            new_cib = calc_sell_price(new_cib_market)
            source = "synthetic_ratio_repair"

        ratio = round(new_cib / loose_price, 2) if loose_price else 0
        diff = round(new_cib - old_cib, 2)

        if abs(diff) < 0.50:
            stats["cib_already_ok"] += 1
            write_csv_row([title_full, console_name, source, f"{loose_price:.2f}",
                          f"{old_cib:.2f}", f"{new_cib:.2f}", f"{ratio:.2f}",
                          "NO_CHANGE", f"diff={diff}"])
            continue

        status = "APPLIED" if args.apply else "PREVIEW"
        if source.startswith("ebay"):
            stats["ebay_cib"] += 1
        else:
            stats["synthetic_repair"] += 1

        write_csv_row([title_full, console_name, source, f"{loose_price:.2f}",
                      f"{old_cib:.2f}", f"{new_cib:.2f}", f"{ratio:.2f}",
                      status, f"diff={diff}"])

        if args.apply:
            try:
                res = shopify_gql(
                    """mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                        productVariants { id price }
                        userErrors { field message }
                      }
                    }""",
                    {"productId": pid, "variants": [{"id": cib["id"], "price": str(new_cib)}]},
                )
                errors = res.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
                if errors:
                    stats["errors"] += 1
                    log(f"  SHOPIFY_ERROR: {title_full}: {errors[0]['message']}")
            except Exception as e:
                stats["errors"] += 1
                log(f"  SHOPIFY_EXC: {title_full}: {e}")
            time.sleep(SHOPIFY_DELAY)

        if (i + 1) % 50 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            eta = (len(ids) - i - 1) / rate if rate > 0 else 0
            log(f"  Progress: {i+1}/{len(ids)} | eBay CIB: {stats['ebay_cib']} | "
                f"Synth repair: {stats['synthetic_repair']} | Already OK: {stats['cib_already_ok']} | "
                f"ETA: {eta/60:.0f}min")

    elapsed = time.time() - start
    log("\n" + "=" * 60)
    log("RESULTS")
    log("=" * 60)
    log(f"  Total products:     {stats['total']}")
    log(f"  eBay CIB matches:   {stats['ebay_cib']}")
    log(f"  Synthetic repairs:  {stats['synthetic_repair']}")
    log(f"  Already OK (<$0.50): {stats['cib_already_ok']}")
    log(f"  Missing variants:   {stats['no_cib_variant']}")
    log(f"  Errors:             {stats['errors']}")
    log(f"  Time: {elapsed/60:.1f} min")

    if log_handle:
        log_handle.close()
    if csv_file_handle:
        csv_file_handle.close()

    print(f"\nLog: {LOG_FILE}")
    print(f"CSV: {CSV_FILE}")


if __name__ == "__main__":
    main()
