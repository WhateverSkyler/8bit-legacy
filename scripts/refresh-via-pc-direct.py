#!/usr/bin/env python3
"""
PriceCharting-direct refresh — fixes the direct-product-page bug.

Previous scripts (search-price-refresh.py, refresh-prices-unified.py) only
parsed PC's search-results table. But when PC has an exact match it redirects
directly to the product page, and the old code saw that as NO_MATCH. That bug
is why 301 CIBs and 482 loose variants fell back to synthetic / stale — PC
actually has real market data for nearly all of them.

This script:
  1. Loads product IDs from --ids-file (default: data/bad-prices-union-ids.json)
  2. For each: searches PC, handling BOTH response types (direct page + search)
  3. Validates console match before trusting the result
  4. Applies loose + CIB prices via Shopify mutation
  5. Logs everything; supports --resume via checkpoint file

Usage:
  python3 scripts/refresh-via-pc-direct.py              # dry run
  python3 scripts/refresh-via-pc-direct.py --apply      # write changes
  python3 scripts/refresh-via-pc-direct.py --apply --resume
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

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

with open(CONFIG_DIR / "pricing.json") as f:
    PRICING = json.load(f)

MULTIPLIER = PRICING["default_multiplier"]
ROUND_TO = PRICING.get("round_to", 0.99)
FEE_PCT = PRICING["shopify_fee_percent"]
FEE_FIXED = PRICING["shopify_fee_fixed"]
MIN_PROFIT = PRICING["minimum_profit_usd"]

PC_DELAY = 2.5
SHOPIFY_DELAY = 0.3
MAX_MARKET = 800.0

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

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

# Console name → canonical slug fragment that appears in PC URLs / h2
CONSOLE_SIGNATURES = {
    "NES": ["nes"],
    "SNES": ["snes", "super-nintendo", "super nintendo"],
    "Nintendo 64": ["n64", "nintendo-64", "nintendo 64"],
    "Gamecube": ["gamecube"],
    "Wii": ["wii"],
    "Wii U": ["wii-u", "wii u"],
    "Gameboy": ["gameboy", "game-boy", "game boy"],
    "Gameboy Color": ["gameboy-color", "gbc", "gameboy color"],
    "Gameboy Advance": ["gameboy-advance", "gba", "gameboy advance"],
    "Nintendo DS": ["nintendo-ds", "ds"],
    "Nintendo 3DS": ["3ds"],
    "Sega Genesis": ["genesis", "sega-genesis"],
    "Sega Saturn": ["saturn", "sega-saturn"],
    "Sega Dreamcast": ["dreamcast", "sega-dreamcast"],
    "Sega Master System": ["master-system", "sega-master-system"],
    "Sega CD": ["sega-cd"],
    "Sega 32X": ["sega-32x", "32x"],
    "Sega Game Gear": ["game-gear", "sega-game-gear"],
    "Playstation": ["playstation", "ps1"],
    "Playstation 2": ["playstation-2", "ps2"],
    "Playstation 3": ["playstation-3", "ps3"],
    "PSP": ["psp"],
    "Xbox": ["xbox"],
    "Xbox 360": ["xbox-360"],
    "Atari 2600": ["atari-2600", "atari 2600"],
    "TurboGrafx-16": ["turbografx-16"],
}

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"pc-direct-{timestamp}.log"
CSV_FILE = LOG_DIR / f"pc-direct-{timestamp}.csv"
CHECKPOINT = LOG_DIR / "pc-direct-checkpoint.json"

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
    csv_writer.writerow(["product_id", "product", "console", "variant_type",
                         "pc_match", "pc_console", "market_price",
                         "old_price", "new_price", "diff", "status", "notes"])


def write_csv(row):
    if csv_writer:
        csv_writer.writerow(row)
        csv_file_handle.flush()


def parse_price_text(text):
    m = re.search(r"\$?([\d,]+\.?\d*)", text.replace(",", ""))
    return float(m.group(1)) if m else 0.0


def strip_console_suffix(title):
    return re.sub(
        r"\s*[-–]\s*(NES|SNES|N64|Nintendo 64|Nintendo|Gameboy Advance|Gameboy Color|"
        r"Gameboy|Game Boy|Genesis|PS[123P]|"
        r"Gamecube|Dreamcast|Saturn|GBA|Playstation|Xbox|Wii( U)?|Sega|Atari|"
        r"TurboGrafx|GBC|DS|3DS)\s+Game\s*$",
        "", title, flags=re.IGNORECASE,
    ).strip()


def _console_matches(expected_console, observed_text):
    """Check whether a PC page's console string or URL matches what we expect."""
    sig = CONSOLE_SIGNATURES.get(expected_console, [expected_console.lower()])
    ot = observed_text.lower()
    return any(s in ot for s in sig)


def _query_variants(title):
    yield title
    if ":" in title:
        yield title.split(":", 1)[0].strip()
    if title.lower().startswith("the "):
        yield title[4:]
    if " & " in title:
        yield title.replace(" & ", " and ")
    if " and " in title.lower():
        yield re.sub(r"\s+and\s+", " & ", title, count=1, flags=re.IGNORECASE)
    words = title.split()
    if len(words) >= 4:
        yield " ".join(words[:3])


def _parse_direct_product_page(soup, expected_console):
    """Parse a direct PC product page. Returns dict or None."""
    name_el = soup.find(id="product_name")
    if not name_el:
        return None
    # Console signal appears in h2#product_name child or nearby h2
    console_text = ""
    console_h2 = soup.find("h2")
    if console_h2:
        console_text = console_h2.get_text(" ", strip=True)
    # Also check the canonical URL
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        console_text += " " + canonical["href"]
    if not _console_matches(expected_console, console_text):
        return None
    loose = cib = 0.0
    el = soup.find(id="used_price")
    if el:
        loose = parse_price_text(el.get_text(" ", strip=True))
    el = soup.find(id="complete_price")
    if el:
        cib = parse_price_text(el.get_text(" ", strip=True))
    return {
        "title": name_el.get_text(strip=True),
        "console_observed": console_text[:80],
        "loose": loose,
        "cib": cib,
        "source": "pc_direct",
    }


def _parse_search_results_page(soup, expected_console, game_title):
    """Parse a PC search-results page. Returns dict or None."""
    table = soup.find("table", {"id": "games_table"})
    if not table or not table.find("tbody"):
        return None
    best = None
    for row in table.find("tbody").find_all("tr")[:10]:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue
        link = cols[1].find("a") if len(cols) > 1 else None
        if not link:
            continue
        result_title = link.get_text(strip=True)
        result_console = cols[2].get_text(strip=True) if len(cols) > 2 else ""
        if not _console_matches(expected_console, result_console):
            continue
        if any(bad in result_console.lower() for bad in (" pal", "jp ", "japanese", " jp", "japan")):
            continue
        # Title similarity
        qt = set(re.sub(r"[^a-z0-9 ]", "", game_title.lower()).split()) - {"the", "a", "an"}
        rt = set(re.sub(r"[^a-z0-9 ]", "", result_title.lower()).split()) - {"the", "a", "an"}
        if not qt:
            continue
        overlap = len(qt & rt) / len(qt)
        if overlap < 0.5:
            continue
        loose = parse_price_text(cols[3].get_text(strip=True)) if len(cols) > 3 else 0
        cib = parse_price_text(cols[4].get_text(strip=True)) if len(cols) > 4 else 0
        candidate = {
            "title": result_title,
            "console_observed": result_console,
            "loose": loose,
            "cib": cib,
            "source": "pc_search",
            "similarity": overlap,
        }
        if best is None or overlap > best["similarity"]:
            best = candidate
    return best


def search_pricecharting(game_title, console_name):
    """PC lookup — tries multiple query variants and both response formats."""
    attempts = 0
    for variant in _query_variants(game_title):
        q = f"{variant} {console_name}"
        url = f"https://www.pricecharting.com/search-products?q={quote_plus(q)}&type=prices"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
            resp.raise_for_status()
        except Exception as e:
            if attempts == 0:
                log(f"  PC fetch error: {e}")
            attempts += 1
            time.sleep(1.5)
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        # Direct product page?
        direct = _parse_direct_product_page(soup, console_name)
        if direct:
            return direct
        # Otherwise search-results page
        result = _parse_search_results_page(soup, console_name, game_title)
        if result:
            return result
        attempts += 1
        if attempts < 3:
            time.sleep(1.0)
    return None


def shopify_gql(query, variables=None, retries=4):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    for a in range(retries):
        try:
            resp = requests.post(
                f"https://{SHOPIFY_STORE}/admin/api/2024-10/graphql.json",
                headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
            if resp.status_code == 429:
                time.sleep(2 + a)
                continue
            resp.raise_for_status()
            data = resp.json()
            if any(e.get("extensions", {}).get("code") == "THROTTLED"
                   for e in data.get("errors", [])):
                time.sleep(2 + a)
                continue
            return data
        except requests.exceptions.RequestException:
            time.sleep(min(2 ** a, 30))
    raise RuntimeError("shopify retries exceeded")


def fetch_product(product_id):
    q = """
    query($id: ID!) {
      product(id: $id) {
        id title tags
        variants(first: 10) {
          edges { node { id title price sku } }
        }
      }
    }
    """
    d = shopify_gql(q, {"id": product_id})
    return d.get("data", {}).get("product")


def calc_sell_price(market):
    raw = market * MULTIPLIER
    if ROUND_TO is not None:
        r = int(raw) + ROUND_TO
        if r < raw:
            r += 1.0
        return round(r, 2)
    return round(raw, 2)


def update_variant(product_id, variant_id, new_price):
    d = shopify_gql(
        """mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            productVariants { id price }
            userErrors { field message }
          }
        }""",
        {"productId": product_id, "variants": [{"id": variant_id, "price": str(new_price)}]},
    )
    errors = d.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
    return errors[0]["message"] if errors else None


def is_cib(title):
    t = title.lower()
    return "complete" in t or "cib" in t or "box" in t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--ids-file", default=str(DATA_DIR / "bad-prices-union-ids.json"))
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        log("ERROR: missing Shopify credentials"); sys.exit(1)

    log("=" * 60)
    log(f"PC-DIRECT REFRESH — {'APPLY' if args.apply else 'REPORT'}")
    log(f"Multiplier: {MULTIPLIER}x | Log: {LOG_FILE}")
    log("=" * 60)

    init_csv()

    with open(args.ids_file) as f:
        ids = json.load(f)
    if args.limit:
        ids = ids[: args.limit]

    completed = set()
    if args.resume and CHECKPOINT.exists():
        completed = set(json.load(open(CHECKPOINT)).get("completed", []))
        log(f"Resume: skipping {len(completed)} already done")

    log(f"Processing {len(ids)} products ({len(ids) - len(completed)} remaining)")

    stats = {"total": len(ids), "matched": 0, "no_match": 0,
             "loose_applied": 0, "cib_applied": 0, "no_change": 0,
             "no_console": 0, "errors": 0, "skipped": len(completed)}
    start = time.time()

    for i, pid in enumerate(ids):
        if pid in completed:
            continue
        try:
            product = fetch_product(pid)
        except Exception as e:
            log(f"  fetch error {pid}: {e}")
            stats["errors"] += 1
            continue
        if not product:
            continue

        title_full = product["title"]
        game_title = strip_console_suffix(title_full)

        console = None
        for tag in product.get("tags", []):
            t = tag.lower().strip()
            if t.startswith("console:"):
                t = t.split(":", 1)[1].strip()
            cn = TAG_TO_CONSOLE.get(t)
            if cn:
                console = cn
                break

        if not console:
            stats["no_console"] += 1
            write_csv([pid, title_full, "", "", "NO_CONSOLE", "", "", "", "", "", "SKIP", ""])
            completed.add(pid)
            continue

        result = search_pricecharting(game_title, console)
        time.sleep(PC_DELAY)

        if not result:
            stats["no_match"] += 1
            write_csv([pid, title_full, console, "", "NO_MATCH", "", "", "", "", "", "SKIP", ""])
            completed.add(pid)
            continue

        stats["matched"] += 1

        variants = product.get("variants", {}).get("edges", [])
        loose_v = None
        cib_v = None
        for edge in variants:
            v = edge["node"]
            if is_cib(v.get("title", "")):
                cib_v = v
            else:
                loose_v = v

        for variant_kind, variant, market in [
            ("loose", loose_v, result.get("loose", 0)),
            ("cib", cib_v, result.get("cib", 0)),
        ]:
            if not variant or not market or market <= 0 or market > MAX_MARKET:
                continue
            old_price = float(variant["price"])
            new_price = calc_sell_price(market)
            diff = round(new_price - old_price, 2)
            if abs(diff) < 0.50:
                stats["no_change"] += 1
                write_csv([pid, title_full, console, variant_kind,
                           result["source"], result.get("console_observed", ""),
                           f"{market:.2f}", f"{old_price:.2f}", f"{new_price:.2f}",
                           f"{diff:.2f}", "NO_CHANGE", ""])
                continue
            status = "APPLIED" if args.apply else "PREVIEW"
            if args.apply:
                err = update_variant(pid, variant["id"], new_price)
                if err:
                    stats["errors"] += 1
                    status = "ERROR"
                    write_csv([pid, title_full, console, variant_kind,
                               result["source"], result.get("console_observed", ""),
                               f"{market:.2f}", f"{old_price:.2f}", f"{new_price:.2f}",
                               f"{diff:.2f}", status, err[:80]])
                    continue
                time.sleep(SHOPIFY_DELAY)
            if variant_kind == "loose":
                stats["loose_applied"] += 1
            else:
                stats["cib_applied"] += 1
            write_csv([pid, title_full, console, variant_kind,
                       result["source"], result.get("console_observed", ""),
                       f"{market:.2f}", f"{old_price:.2f}", f"{new_price:.2f}",
                       f"{diff:.2f}", status, ""])

        completed.add(pid)

        if (i + 1) % 50 == 0:
            with open(CHECKPOINT, "w") as f:
                json.dump({"completed": list(completed),
                           "timestamp": datetime.now().isoformat()}, f)
            elapsed = time.time() - start
            rate = (i + 1 - stats["skipped"]) / elapsed if elapsed else 0
            eta = (len(ids) - i - 1) / rate / 60 if rate > 0 else 0
            log(f"  {i+1}/{len(ids)} | matched {stats['matched']} | "
                f"loose {stats['loose_applied']} | cib {stats['cib_applied']} | "
                f"no_match {stats['no_match']} | ETA {eta:.0f}m")

    # Final checkpoint save
    with open(CHECKPOINT, "w") as f:
        json.dump({"completed": list(completed),
                   "timestamp": datetime.now().isoformat()}, f)

    elapsed = time.time() - start
    log("\n" + "=" * 60)
    log("RESULTS")
    log("=" * 60)
    log(f"  Total:           {stats['total']}")
    log(f"  PC matched:      {stats['matched']}  ({stats['matched']*100/stats['total']:.1f}%)")
    log(f"  No match:        {stats['no_match']}")
    log(f"  No console tag:  {stats['no_console']}")
    log(f"  Loose applied:   {stats['loose_applied']}")
    log(f"  CIB applied:     {stats['cib_applied']}")
    log(f"  No change:       {stats['no_change']}")
    log(f"  Errors:          {stats['errors']}")
    log(f"  Time:            {elapsed/60:.1f} min")

    if log_handle:
        log_handle.close()
    if csv_file_handle:
        csv_file_handle.close()
    print(f"\nLog: {LOG_FILE}")
    print(f"CSV: {CSV_FILE}")


if __name__ == "__main__":
    main()
