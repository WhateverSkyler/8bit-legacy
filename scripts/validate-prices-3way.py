#!/usr/bin/env python3
"""
Three-way price validation: PriceCharting (market) vs. 8-Bit Legacy (us) vs. DKOldies (competitor).

After a bulk price refresh, pick random products from the refresh CSV and compare all three.
Flags:
  - OVERPRICED: our price > DKOldies regular-condition price (exclude their flawed variant)
  - THIN_MARGIN: our price < PC market × 1.1 (not enough cushion over Shopify fees)

Usage:
  python3 scripts/validate-prices-3way.py --csv data/logs/pc-direct-*.csv --sample 10
  python3 scripts/validate-prices-3way.py --titles "Chrono Cross - PS1 Game,ActRaiser - SNES Game"
"""
import argparse
import csv
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

PROJECT = Path(__file__).parent.parent
load_dotenv(PROJECT / "config" / ".env")
load_dotenv(PROJECT / "dashboard" / ".env.local")

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

with open(PROJECT / "config" / "pricing.json") as f:
    PRICING = json.load(f)
MULTIPLIER = PRICING["default_multiplier"]
FEE_PCT = PRICING["shopify_fee_percent"]
FEE_FIXED = PRICING["shopify_fee_fixed"]
MIN_PROFIT = PRICING["minimum_profit_usd"]

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# Our console tag -> DKOldies URL suffix
DKO_CONSOLE_SUFFIX = {
    "NES": "nes",
    "SNES": "snes",
    "N64": "n64",
    "Gamecube": "gamecube",
    "Wii": "wii",
    "Gameboy": "game-boy",
    "GBC": "game-boy-color",
    "GBA": "game-boy-advance",
    "DS": "ds",
    "3DS": "3ds",
    "Sega Genesis": "genesis",
    "Sega Saturn": "saturn",
    "Sega Dreamcast": "dreamcast",
    "PS1": "ps1",
    "PS2": "ps2",
    "PS3": "ps3",
    "PSP": "psp",
    "Xbox": "xbox",
    "Xbox 360": "xbox-360",
    "Atari 2600": "atari-2600",
}

# Our Shopify title suffix -> canonical console tag
TITLE_SUFFIX_TO_CONSOLE = {
    "NES": "NES", "SNES": "SNES", "N64": "N64", "Nintendo 64": "N64",
    "Gamecube": "Gamecube", "Wii": "Wii",
    "Gameboy": "Gameboy", "GameBoy": "Gameboy", "Game Boy": "Gameboy",
    "GBC": "GBC", "Gameboy Color": "GBC",
    "GBA": "GBA", "Gameboy Advance": "GBA",
    "DS": "DS", "3DS": "3DS",
    "Sega Genesis": "Sega Genesis", "Genesis": "Sega Genesis",
    "Sega Saturn": "Sega Saturn", "Saturn": "Sega Saturn",
    "Dreamcast": "Sega Dreamcast", "Sega Dreamcast": "Sega Dreamcast",
    "PS1": "PS1", "Playstation": "PS1",
    "PS2": "PS2", "Playstation 2": "PS2",
    "PS3": "PS3", "Playstation 3": "PS3",
    "PSP": "PSP",
    "Xbox": "Xbox", "Xbox 360": "Xbox 360",
    "Atari 2600": "Atari 2600",
}

# Tag -> PriceCharting search console string (used for the query)
PC_CONSOLE_NAME = {
    "NES": "NES", "SNES": "SNES", "N64": "Nintendo 64",
    "Gamecube": "Gamecube", "Wii": "Wii",
    "Gameboy": "Gameboy", "GBC": "Gameboy Color", "GBA": "Gameboy Advance",
    "DS": "Nintendo DS", "3DS": "Nintendo 3DS",
    "Sega Genesis": "Sega Genesis", "Sega Saturn": "Sega Saturn",
    "Sega Dreamcast": "Sega Dreamcast",
    "PS1": "Playstation", "PS2": "Playstation 2", "PS3": "Playstation 3",
    "PSP": "PSP", "Xbox": "Xbox", "Xbox 360": "Xbox 360",
    "Atari 2600": "Atari 2600",
}

# Tag -> alternate names that may appear in PC result console column (avoid PAL/JP)
PC_CONSOLE_VARIANTS = {
    "NES": ["nes"],
    "SNES": ["super nintendo", "snes"],
    "N64": ["nintendo 64", "n64"],
    "Gamecube": ["gamecube"],
    "Wii": ["wii"],
    "Gameboy": ["gameboy", "game boy"],
    "GBC": ["gameboy color", "game boy color"],
    "GBA": ["gameboy advance", "game boy advance"],
    "DS": ["nintendo ds"],
    "3DS": ["nintendo 3ds"],
    "Sega Genesis": ["genesis", "sega genesis"],
    "Sega Saturn": ["saturn", "sega saturn"],
    "Sega Dreamcast": ["dreamcast", "sega dreamcast"],
    "PS1": ["playstation"],
    "PS2": ["playstation 2"],
    "PS3": ["playstation 3"],
    "PSP": ["psp"],
    "Xbox": ["xbox"],
    "Xbox 360": ["xbox 360"],
    "Atari 2600": ["atari 2600"],
}


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def parse_title(shopify_title):
    """Extract (game_name, console_tag) from a Shopify product title."""
    m = re.match(r"^(.*?)\s*[-–]\s*(.+?)(?:\s+Game)?\s*$", shopify_title)
    if not m:
        return shopify_title, None
    game = m.group(1).strip()
    console_raw = m.group(2).strip().rstrip(" Game").strip()
    console = TITLE_SUFFIX_TO_CONSOLE.get(console_raw)
    if not console:
        # Try prefix match
        for k, v in TITLE_SUFFIX_TO_CONSOLE.items():
            if console_raw.startswith(k):
                console = v
                break
    return game, console


def fetch_pc(game, console_tag):
    """Fetch PriceCharting loose + CIB market price. Returns dict or None."""
    pc_console = PC_CONSOLE_NAME.get(console_tag)
    if not pc_console:
        return None
    q = f"{game} {pc_console}"
    url = f"https://www.pricecharting.com/search-products?q={quote_plus(q)}&type=prices"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        r.raise_for_status()
    except Exception:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    # Direct product page?
    if soup.find(id="product_name"):
        loose_el = soup.find(id="used_price")
        cib_el = soup.find(id="complete_price")
        loose = _price_num(loose_el.get_text(" ", strip=True)) if loose_el else 0
        cib = _price_num(cib_el.get_text(" ", strip=True)) if cib_el else 0
        return {"loose": loose, "cib": cib, "title": soup.find(id="product_name").get_text(strip=True)}
    # Search page
    table = soup.find("table", {"id": "games_table"})
    if not table or not table.find("tbody"):
        return None
    rows = table.find("tbody").find_all("tr")[:8]
    variants = PC_CONSOLE_VARIANTS.get(console_tag, [pc_console.lower()])
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue
        result_console = cols[2].get_text(strip=True).lower()
        # Skip PAL / JP listings
        if result_console.startswith("pal ") or "japanese" in result_console:
            continue
        if not any(v == result_console or v == result_console.strip() for v in variants):
            continue
        # Title similarity: the first listed result with matching console is the best match
        title_link = cols[1].find("a")
        result_title = title_link.get_text(strip=True) if title_link else ""
        # Strip console suffix from PC title ("ActRaiserSuper Nintendo" -> "ActRaiser")
        for v in variants + [pc_console]:
            idx = result_title.lower().find(v.lower())
            if idx > 0:
                result_title = result_title[:idx].strip()
                break
        # Require first word match
        if game.split()[0].lower() not in result_title.lower():
            continue
        return {
            "loose": _price_num(cols[3].get_text(strip=True)),
            "cib": _price_num(cols[4].get_text(strip=True)),
            "title": result_title,
        }
    return None


def _price_num(text):
    m = re.search(r"\$?([\d,]+\.?\d*)", text.replace(",", ""))
    return float(m.group(1)) if m else 0.0


def fetch_dkoldies(game, console_tag, variant_kind):
    """Fetch DKOldies price for the regular (non-flawed) variant.
    variant_kind: 'loose' or 'cib'."""
    suffix = DKO_CONSOLE_SUFFIX.get(console_tag)
    if not suffix:
        return None
    slug = slugify(game)
    urls = []
    if variant_kind == "loose":
        urls = [
            f"https://www.dkoldies.com/{slug}-{suffix}-game/",
            f"https://www.dkoldies.com/{slug}-{suffix}/",
        ]
    else:  # cib — DKOldies uses both URL patterns depending on the game
        urls = [
            f"https://www.dkoldies.com/complete-{slug}-{suffix}/",
            f"https://www.dkoldies.com/complete-{slug}-{suffix}-game/",
        ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
            if r.status_code != 200:
                continue
        except Exception:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        # The DEFAULT (main) price on the product page is regular condition.
        # Cosmetically flawed is a radio variant — its price shows separately.
        # JSON-LD "offers.price" = main/default variant = regular condition.
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                d = json.loads(s.string)
                if isinstance(d, dict) and d.get("@type") == "Product":
                    offers = d.get("offers", {})
                    # DKOldies returns offers as a list
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    price = offers.get("price")
                    if price:
                        return {
                            "price": float(price),
                            "url": url,
                            "name": d.get("name", ""),
                            "description": (d.get("description") or "")[:100],
                        }
            except Exception:
                continue
    return None


def fetch_our_price(game, console_tag):
    """Fetch our 8-Bit Legacy Shopify price by searching product title."""
    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        return None
    # Build query — Shopify product search
    query = f"{game}"
    q = """
    query($q: String!) {
      products(first: 5, query: $q) {
        nodes {
          id title handle tags
          variants(first: 10) {
            nodes { title price }
          }
        }
      }
    }
    """
    try:
        r = requests.post(
            f"https://{SHOPIFY_STORE}/admin/api/2024-10/graphql.json",
            headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"},
            json={"query": q, "variables": {"q": f"title:*{game}*"}},
            timeout=30,
        )
        r.raise_for_status()
    except Exception:
        return None
    nodes = r.json().get("data", {}).get("products", {}).get("nodes", [])
    # Find matching console
    for node in nodes:
        title = node.get("title", "")
        _, node_console = parse_title(title)
        if node_console != console_tag:
            continue
        loose = cib = None
        for v in node.get("variants", {}).get("nodes", []):
            vt = v.get("title", "").lower()
            if "complete" in vt or "cib" in vt or "box" in vt:
                cib = float(v["price"])
            else:
                loose = float(v["price"])
        return {"loose": loose, "cib": cib, "title": title, "handle": node.get("handle")}
    return None


def profit_after_fees(sell_price, market_price):
    fee = sell_price * FEE_PCT + FEE_FIXED
    return round(sell_price - market_price - fee, 2)


def validate(game, console_tag):
    """Run the 3-way comparison for one product. Returns dict."""
    pc = fetch_pc(game, console_tag)
    time.sleep(1.5)
    ours = fetch_our_price(game, console_tag)
    dko_loose = fetch_dkoldies(game, console_tag, "loose")
    time.sleep(1.5)
    dko_cib = fetch_dkoldies(game, console_tag, "cib")
    time.sleep(1.5)
    return {
        "game": game, "console": console_tag,
        "pc": pc, "ours": ours, "dko_loose": dko_loose, "dko_cib": dko_cib,
    }


def report_row(r):
    game = r["game"][:32]
    lines = [f"\n{game:<32} [{r['console']}]"]
    pc_loose = r["pc"].get("loose") if r["pc"] else None
    pc_cib = r["pc"].get("cib") if r["pc"] else None
    our_loose = r["ours"].get("loose") if r["ours"] else None
    our_cib = r["ours"].get("cib") if r["ours"] else None
    dko_l = r["dko_loose"].get("price") if r["dko_loose"] else None
    dko_c = r["dko_cib"].get("price") if r["dko_cib"] else None

    def flag(ours, pc, dko):
        flags = []
        if ours and pc and ours < pc * 1.1:
            flags.append("THIN_MARGIN")
        if ours and dko and ours > dko:
            flags.append("OVERPRICED")
        if ours and pc:
            profit = profit_after_fees(ours, pc)
            if profit < MIN_PROFIT:
                flags.append(f"LOW_PROFIT(${profit:.2f})")
        return " ".join(flags)

    lines.append(f"  LOOSE: PC ${pc_loose or 0:>7.2f}  OURS ${our_loose or 0:>7.2f}  "
                 f"DKO ${dko_l or 0:>7.2f}  {flag(our_loose, pc_loose, dko_l)}")
    lines.append(f"  CIB:   PC ${pc_cib or 0:>7.2f}  OURS ${our_cib or 0:>7.2f}  "
                 f"DKO ${dko_c or 0:>7.2f}  {flag(our_cib, pc_cib, dko_c)}")
    return "\n".join(lines)


def sample_from_csv(csv_path, n=10):
    """Pick n random APPLIED rows from a refresh CSV."""
    rows = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") == "APPLIED":
                rows.append(row)
    if not rows:
        return []
    return random.sample(rows, min(n, len(rows)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="Refresh CSV to sample from")
    ap.add_argument("--sample", type=int, default=10)
    ap.add_argument("--titles", help="Comma-separated product titles to check instead of sampling")
    args = ap.parse_args()

    if args.titles:
        titles = [t.strip() for t in args.titles.split(",")]
    elif args.csv:
        rows = sample_from_csv(args.csv, args.sample)
        # Dedup by product (CSV has 1 row per variant)
        seen = set()
        titles = []
        for row in rows:
            t = row.get("product") or row.get("product_title") or ""
            if t not in seen:
                seen.add(t)
                titles.append(t)
    else:
        print("Pass --csv or --titles"); sys.exit(1)

    print(f"\nValidating {len(titles)} products (PC vs. OURS vs. DKOldies)...")
    print("Legend: THIN_MARGIN = ours < PC × 1.1  |  OVERPRICED = ours > DKO regular price")
    print("=" * 80)

    results = []
    for t in titles:
        game, console = parse_title(t)
        if not console:
            print(f"\n{t}: could not parse console — skipping")
            continue
        r = validate(game, console)
        results.append(r)
        print(report_row(r))

    # Summary
    overpriced = sum(1 for r in results for tag in [
        (r["ours"] or {}).get("loose"), (r["ours"] or {}).get("cib")
    ] if tag and ((r["dko_loose"] or {}).get("price") or 0) and tag > ((r["dko_loose"] or {}).get("price") or 1e9))

    print("\n" + "=" * 80)
    print(f"Checked {len(results)} products")
    print("=" * 80)


if __name__ == "__main__":
    main()
