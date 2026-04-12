#!/usr/bin/env python3
"""
Set Shopify SEO meta descriptions store-wide.

Why: Store-wide audit (2026-04-11) found 100% of 7,290 active products were
missing a SEO meta description. When the meta is missing, Google falls back
to truncated body HTML, which is generic and hurts click-through-rate on
both organic search and Google Shopping listings. Adding a clean templated
description lifts CTR and gives us a consistent brand voice in the SERP
snippet.

Template (game products):
  "Shop {title} for {console} at 8-Bit Legacy. Authentic retro game, fast
  shipping, 90-day returns."

Template (Pokemon cards):
  "Shop {title} Pokemon TCG single at 8-Bit Legacy. Lightly Played, fast
  shipping and secure packaging, 90-day returns."

Rules:
  - Skip anything where the product already has a non-empty SEO description
    (so this script is safe to re-run).
  - Keep the description <= 160 characters (Google truncates beyond that).
  - Never touch the SEO title — that's handled by optimize-product-feed.py.
  - Never touch body HTML / descriptionHtml — that's the store owner's
    editorial content.

Usage:
  python3 scripts/set-seo-descriptions.py --dry-run          # preview
  python3 scripts/set-seo-descriptions.py                    # apply
  python3 scripts/set-seo-descriptions.py --limit 100        # first 100 only
  python3 scripts/set-seo-descriptions.py --only-missing     # default (safe re-run)
"""
import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT = Path(__file__).parent.parent
load_dotenv(PROJECT / "dashboard" / ".env.local")
load_dotenv(PROJECT / "config" / ".env")

SHOP = os.getenv("SHOPIFY_STORE_URL", "")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
GQL_URL = f"https://{SHOP}/admin/api/2024-10/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

SHOPIFY_DELAY = 0.4
MAX_LEN = 160


# Ordered longest-first so "Playstation 2" beats "Playstation" and so on.
CONSOLE_TAG_TO_NAME = [
    ("nes (nintendo entertainment system)", "NES"),
    ("snes (super nintendo entertainment system)", "SNES"),
    ("nintendo gamecube > gamecube", "GameCube"),
    ("nintendo gamecube", "GameCube"),
    ("sega master system", "Sega Master System"),
    ("sega dreamcast", "Sega Dreamcast"),
    ("sega game gear", "Sega Game Gear"),
    ("sega genesis", "Sega Genesis"),
    ("sega saturn", "Sega Saturn"),
    ("sega 32x", "Sega 32X"),
    ("sega cd", "Sega CD"),
    ("playstation 3", "PS3"),
    ("playstation 2", "PS2"),
    ("playstation", "PS1"),
    ("nintendo 3ds", "3DS"),
    ("nintendo 64", "N64"),
    ("nintendo ds", "DS"),
    ("gameboy advance", "Game Boy Advance"),
    ("gameboy color", "Game Boy Color"),
    ("game boy advance", "Game Boy Advance"),
    ("game boy color", "Game Boy Color"),
    ("turbografx-16", "TurboGrafx-16"),
    ("atari 2600", "Atari 2600"),
    ("xbox 360", "Xbox 360"),
    ("wii u", "Wii U"),
    ("super nintendo", "SNES"),
    ("gameboy", "Game Boy"),
    ("game boy", "Game Boy"),
    ("gamecube", "GameCube"),
    ("dreamcast", "Sega Dreamcast"),
    ("genesis", "Sega Genesis"),
    ("saturn", "Sega Saturn"),
    ("xbox", "Xbox"),
    ("atari", "Atari 2600"),
    ("psp", "PSP"),
    ("3ds", "3DS"),
    ("snes", "SNES"),
    ("nes", "NES"),
    ("n64", "N64"),
    ("ps3", "PS3"),
    ("ps2", "PS2"),
    ("ps1", "PS1"),
    ("wii", "Wii"),
    ("ds", "DS"),
]


def detect_console(tags: list[str]) -> str | None:
    """Find the best console name from a product's tags."""
    tag_set = {t.lower().strip() for t in tags}
    # Check full-tag exact matches (longest first)
    for key, name in CONSOLE_TAG_TO_NAME:
        if key in tag_set:
            return name
    # Fall back to substring match on any tag
    for key, name in CONSOLE_TAG_TO_NAME:
        for t in tag_set:
            if key in t:
                return name
    return None


def strip_console_suffix(title: str) -> str:
    """Strip trailing ' - NES Game' / ' - PS2 Game' / ' - Gamecube Game' etc."""
    return re.sub(
        r"\s*[-–]\s*(NES|SNES|N64|Nintendo\s*\d*|Gameboy|Game\s*Boy|Genesis|PS[123P]|"
        r"Gamecube|Dreamcast|Saturn|GBA|GBC|Playstation|Xbox|Wii|Sega|Atari|TurboGrafx)"
        r"\s*(Game|Console)?\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip()


def build_description(title: str, tags: list[str], product_type: str) -> str:
    """Generate a SEO meta description for the product.

    Falls back gracefully if the console can't be detected.
    """
    pt_lc = (product_type or "").lower()
    tags_lc = [t.lower() for t in tags]

    # Pokemon cards
    if "pokemon" in pt_lc or any("pokemon" in t for t in tags_lc):
        desc = f"Shop {title} Pokemon TCG at 8-Bit Legacy. Lightly Played, fast shipping, 90-day returns."
        return desc[:MAX_LEN]

    # Retro game
    clean = strip_console_suffix(title)
    console = detect_console(tags)
    if console:
        desc = f"Shop {clean} for {console} at 8-Bit Legacy. Authentic retro game, fast shipping and 90-day returns."
    else:
        desc = f"Shop {clean} at 8-Bit Legacy. Authentic retro game with fast shipping and 90-day returns."

    # Trim if too long — try truncating at a word boundary, preserving the brand + CTA.
    if len(desc) > MAX_LEN:
        # Shorten the title part instead of chopping the CTA
        suffix = f" at 8-Bit Legacy. Fast shipping, 90-day returns."
        budget = MAX_LEN - len(suffix) - 5  # "Shop " prefix
        clean_trim = clean[:budget].rstrip()
        if console:
            clean_trim = f"{clean_trim} ({console})"
        desc = f"Shop {clean_trim}{suffix}"
        desc = desc[:MAX_LEN]

    return desc


FETCH_QUERY = """
query($cursor: String) {
  products(first: 100, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      title
      productType
      tags
      seo { title description }
    }
  }
}
"""

UPDATE_MUTATION = """
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id }
    userErrors { field message }
  }
}
"""


def gql(query, variables=None, retries=4):
    for attempt in range(retries):
        try:
            r = requests.post(
                GQL_URL,
                headers=HEADERS,
                json={"query": query, "variables": variables or {}},
                timeout=30,
            )
            if r.status_code == 429:
                time.sleep(2 + attempt)
                continue
            r.raise_for_status()
            data = r.json()
            if any(
                e.get("extensions", {}).get("code") == "THROTTLED"
                for e in data.get("errors", [])
            ):
                time.sleep(2 + attempt)
                continue
            return data
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser(description="Set SEO meta descriptions store-wide")
    parser.add_argument("--dry-run", action="store_true", help="Preview without updating")
    parser.add_argument("--limit", type=int, default=0, help="Process first N products only")
    parser.add_argument(
        "--only-missing",
        action="store_true",
        default=True,
        help="Skip products that already have a SEO description (default: true)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing SEO descriptions (opposite of --only-missing)",
    )
    args = parser.parse_args()

    if args.force:
        args.only_missing = False

    if not SHOP or not TOKEN:
        print("ERROR: SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN not set")
        sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = PROJECT / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"seo-descriptions-{'dry' if args.dry_run else 'apply'}-{ts}.log"
    log_f = open(log_path, "w")

    def log(msg):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(line)
        log_f.write(line + "\n")
        log_f.flush()

    log("=" * 60)
    log(f"SET SEO DESCRIPTIONS — {'DRY RUN' if args.dry_run else 'APPLY'}")
    log(f"Mode: {'only missing' if args.only_missing else 'overwrite all'}")
    log(f"Log: {log_path}")
    log("=" * 60)

    stats = {
        "total": 0,
        "updated": 0,
        "skipped_has_desc": 0,
        "skipped_no_console": 0,
        "errors": 0,
    }

    cursor = None
    printed_samples = 0
    start = time.time()

    while True:
        data = gql(FETCH_QUERY, {"cursor": cursor})
        pd = data.get("data", {}).get("products", {})
        nodes = pd.get("nodes", [])
        for p in nodes:
            stats["total"] += 1
            if args.limit and stats["total"] > args.limit:
                break

            existing = (p.get("seo") or {}).get("description") or ""
            if args.only_missing and existing.strip():
                stats["skipped_has_desc"] += 1
                continue

            desc = build_description(p["title"], p.get("tags", []), p.get("productType") or "")

            if printed_samples < 8:
                log(f"  sample: {p['title'][:50]:50s} -> {desc}")
                printed_samples += 1

            if args.dry_run:
                stats["updated"] += 1
                continue

            # Apply update
            try:
                res = gql(
                    UPDATE_MUTATION,
                    {"input": {"id": p["id"], "seo": {"description": desc}}},
                )
                errs = (
                    res.get("data", {}).get("productUpdate", {}).get("userErrors", [])
                )
                if errs:
                    log(f"  ERROR {p['title'][:40]}: {errs[0]['message']}")
                    stats["errors"] += 1
                else:
                    stats["updated"] += 1
            except Exception as e:
                log(f"  ERROR {p['title'][:40]}: {e}")
                stats["errors"] += 1

            time.sleep(SHOPIFY_DELAY)

            if stats["updated"] > 0 and stats["updated"] % 200 == 0:
                elapsed = time.time() - start
                rate = stats["updated"] / elapsed * 60
                log(f"  progress: {stats['updated']} updated | rate={rate:.0f}/min")

        if args.limit and stats["total"] > args.limit:
            break
        if not pd.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = pd["pageInfo"]["endCursor"]

    log("")
    log("=" * 60)
    log("RESULTS")
    log("=" * 60)
    log(f"  Total scanned:        {stats['total']}")
    log(f"  Updated:              {stats['updated']}")
    log(f"  Skipped (has desc):   {stats['skipped_has_desc']}")
    log(f"  Errors:               {stats['errors']}")
    log(f"  Elapsed:              {(time.time()-start)/60:.1f} min")

    log_f.close()


if __name__ == "__main__":
    main()
